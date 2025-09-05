from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.storage import default_storage, FileSystemStorage
from django.core.files.base import ContentFile
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
try:
    from langchain.chat_models import init_chat_model  # LangChain unified chat interface
except Exception:  # pragma: no cover
    init_chat_model = None

from .serializers import (
    UserRegisterSerializer,
    UserSerializer,
    DocumentUploadSerializer,
    QuerySerializer,
)

# LangChain / Chroma imports
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
try:
    from langchain_openai import OpenAIEmbeddings  # optional
except Exception:  # pragma: no cover
    OpenAIEmbeddings = None
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader
import os
from typing import List

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover
    ChatOpenAI = None
try:
    from transformers import pipeline  # noqa: F401  # kept for potential future use
except Exception:  # pragma: no cover
    pipeline = None


class RegisterView(generics.CreateAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]


class WhoAmIView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


def _get_embeddings():
    provider = getattr(settings, 'RAG_EMBEDDINGS_PROVIDER', 'huggingface')
    if provider == 'openai' and OpenAIEmbeddings is not None:
        return OpenAIEmbeddings()
    model_name = getattr(
        settings, 'RAG_HF_MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2'
    )
    return HuggingFaceEmbeddings(model_name=model_name)


def _get_vectorstore():
    persist_dir = getattr(settings, 'CHROMA_PERSIST_DIR', os.path.join(settings.BASE_DIR, 'chroma'))
    embeddings = _get_embeddings()
    return Chroma(collection_name='documents', embedding_function=embeddings, persist_directory=persist_dir)


def _load_file_to_documents(file_path: str, source: str):
    ext = os.path.splitext(file_path)[1].lower()
    docs = []
    if ext in ['.txt', '.md', '.csv', '.log']:
        loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()
    elif ext in ['.pdf']:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
    else:
        # Fallback: treat as plain text
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            docs = loader.load()
        except Exception:
            docs = []
    # attach simple source metadata
    for d in docs:
        d.metadata = {**d.metadata, 'source': source or os.path.basename(file_path)}
    return docs


class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        files = serializer.validated_data['files']
        source = serializer.validated_data.get('source') or ''

        saved_paths = []
        user_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(request.user.id))
        os.makedirs(user_dir, exist_ok=True)

        storage = FileSystemStorage(location=user_dir)
        for f in files:
            saved_name = storage.save(f.name, f)
            saved_paths.append(os.path.join(user_dir, saved_name))

        # Load and chunk documents
        raw_docs = []
        for p in saved_paths:
            raw_docs.extend(_load_file_to_documents(p, source=source))

        if not raw_docs:
            return Response({'detail': 'No readable documents found.'}, status=status.HTTP_400_BAD_REQUEST)

        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
        chunks = splitter.split_documents(raw_docs)

        # Add user scoping in metadata
        for c in chunks:
            c.metadata = {**c.metadata, 'user_id': str(request.user.id)}

        vectordb = _get_vectorstore()
        vectordb.add_documents(chunks)
        try:
            vectordb.persist()
        except Exception:
            pass

        return Response({'detail': 'Documents ingested', 'files': [os.path.basename(p) for p in saved_paths], 'chunks': len(chunks)})


class QueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = QuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data['query']
        top_k = serializer.validated_data.get('top_k', 4)
        generate = serializer.validated_data.get('generate', True)
        temperature = serializer.validated_data.get('temperature', 0.7)

        vectordb = _get_vectorstore()
        # Build Chroma where filter using operators
        where_filter = {'user_id': {'$eq': str(request.user.id)}}

        # Retrieve with scores; Chroma returns distance (lower is better)
        fetch_k = int(getattr(settings, 'RAG_FETCH_K', max(top_k * 5, 20)))
        results_with_scores = vectordb.similarity_search_with_score(
            query, k=fetch_k, filter=where_filter
        )

        # Sort by ascending distance and take top_k
        results_with_scores.sort(key=lambda x: x[1])
        top_results = results_with_scores[:top_k]

        context_blocks: List[str] = [doc.page_content for doc, _ in top_results]
        payload = [
            {
                'content': doc.page_content,
                'metadata': doc.metadata,
                # Friendly similarity approximation for clients: 1 - min(1, distance)
                'score': max(0.0, 1.0 - min(1.0, dist)),
            }
            for doc, dist in top_results
        ]

        if not generate:
            return Response({'results': payload})

        answer, citations = self._generate_answer(query, top_results, temperature)
        return Response({'results': payload, 'answer': answer, 'citations': citations})

    def _generate_answer(self, query: str, results: List, temperature: float):
        # Prepare numbered, source-aware context to enable citations
        numbered_context_lines: List[str] = []
        citations: List[dict] = []
        for idx, (doc, sim) in enumerate(results, start=1):
            source = doc.metadata.get('source') if isinstance(doc.metadata, dict) else None
            page = doc.metadata.get('page') if isinstance(doc.metadata, dict) else None
            header = f"[{idx}] source={source or 'unknown'}" + (f", page={page}" if page is not None else "")
            numbered_context_lines.append(f"{header}\n{doc.page_content}")
            citations.append({'index': idx, 'source': source, 'page': page, 'score': sim})

        context_text = "\n\n".join(numbered_context_lines)
        prompt = (
            "You are a careful, grounded assistant. Use ONLY the provided context blocks to answer.\n"
            "- Cite sources inline like [1], [2] referencing the numbered blocks.\n"
            "- If the answer isn't supported by the context, say you don't know.\n"
            "- Prefer concise, direct answers.\n\n"
            f"Context blocks (numbered):\n{context_text}\n\nQuestion: {query}\nAnswer (with citations):"
        )
        try:
            if init_chat_model is None:
                return "LangChain init_chat_model is not available. Please install/update langchain."

            model_name = getattr(settings, 'RAG_LLM_MODEL', 'gemini-2.5-flash')
            api_key = (
                getattr(settings, 'GEMINI_API_KEY', None)
                or getattr(settings, 'GOOGLE_API_KEY', None)
            )

            chat = init_chat_model(
                model_name,
                model_provider="google_genai",
                temperature=temperature,
                api_key=api_key,
            )

            ai_message = chat.invoke(prompt)
            # LangChain returns an AIMessage with .content
            text = getattr(ai_message, 'content', None)
            if isinstance(text, str) and text.strip():
                return text.strip(), citations
            return "No response generated.", citations
        except Exception as e:
            return f"Generation error: {str(e)}", citations

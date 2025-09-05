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
from .models import Document

# LangChain / Chroma imports
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader
import os
import time
from typing import List

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
        document_instances = []
        user_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(request.user.id))
        os.makedirs(user_dir, exist_ok=True)

        storage = FileSystemStorage(location=user_dir)
        for f in files:
            saved_name = storage.save(f.name, f)
            saved_path = os.path.join(user_dir, saved_name)
            saved_paths.append(saved_path)
            
            # Create Document model instance
            document = Document.objects.create(
                user=request.user,
                title=os.path.splitext(f.name)[0],  # filename without extension
                filename=f.name,
                file_path=saved_path,
                file_size=f.size,
                file_type=f.content_type or os.path.splitext(f.name)[1],
                chroma_collection_id=f"user_{request.user.id}_{os.path.splitext(f.name)[0]}_{int(time.time())}"
            )
            document_instances.append(document)

        # Load and chunk documents with document IDs
        all_chunks = []
        for i, p in enumerate(saved_paths):
            raw_docs = _load_file_to_documents(p, source=source)
            if raw_docs:
                splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)
                doc_chunks = splitter.split_documents(raw_docs)
                
                # Add document ID and user ID to metadata for each chunk
                doc_id = document_instances[i].id
                for chunk in doc_chunks:
                    chunk.metadata = {
                        **chunk.metadata,
                        'user_id': str(request.user.id),
                        'document_id': str(doc_id)
                    }
                all_chunks.extend(doc_chunks)

        if not all_chunks:
            return Response({'detail': 'No readable documents found.'}, status=status.HTTP_400_BAD_REQUEST)

        vectordb = _get_vectorstore()
        vectordb.add_documents(all_chunks)
        try:
            vectordb.persist()
        except Exception:
            pass

        return Response({
            'detail': 'Documents ingested', 
            'files': [os.path.basename(p) for p in saved_paths], 
            'chunks': len(all_chunks),
            'document_ids': [doc.id for doc in document_instances]
        })


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


class UserDocumentsView(APIView):
    """View to list user's uploaded documents"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all documents uploaded by the current user"""
        documents = Document.objects.filter(user=request.user, is_active=True).order_by('-upload_date')
        
        document_data = []
        for doc in documents:
            document_data.append({
                'id': doc.id,
                'title': doc.title,
                'filename': doc.filename,
                'file_size': doc.file_size,
                'file_size_human': doc.file_size_human,
                'file_type': doc.file_type,
                'upload_date': doc.upload_date,
                'last_modified': doc.last_modified,
                'chroma_collection_id': doc.chroma_collection_id,
            })
        
        return Response({
            'documents': document_data,
            'count': len(document_data)
        })


class DeleteDocumentView(APIView):
    """View to delete a specific document"""
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, document_id):
        """Delete a document from both database and Chroma DB"""
        try:
            document = Document.objects.get(id=document_id, user=request.user, is_active=True)
        except Document.DoesNotExist:
            return Response({'detail': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Delete from Chroma DB using document ID
            self._delete_from_chroma_db(document.id)
            
            # Delete the physical file
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)
            
            # Mark document as inactive (soft delete)
            document.is_active = False
            document.save()
            
            return Response({'detail': f'Document "{document.title}" deleted successfully'})
            
        except Exception as e:
            return Response({'detail': f'Error deleting document: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _delete_from_chroma_db(self, document_id):
        """Helper method to delete document chunks from Chroma DB"""
        try:
            # Get the vectorstore
            vectordb = _get_vectorstore()
            
            # Get all documents with the specific document_id
            # We need to search for documents with this document_id in metadata
            # Since Chroma doesn't have a direct delete by metadata filter,
            # we'll need to get the document IDs and delete them
            
            # First, let's get all documents to find the ones with our document_id
            # This is a workaround since Chroma doesn't support delete by metadata filter directly
            try:
                # Get the collection
                collection = vectordb._collection
                
                # Query for documents with the specific document_id
                results = collection.get(
                    where={"document_id": {"$eq": str(document_id)}}
                )
                
                if results and results.get('ids'):
                    # Delete the documents by their IDs
                    collection.delete(ids=results['ids'])
                    
                    # Persist the changes
                    try:
                        vectordb.persist()
                    except Exception:
                        pass  # Persist might not be available in all Chroma versions
                        
            except Exception as e:
                # Fallback: if the above doesn't work, we'll log the error but continue
                print(f"Warning: Could not delete from Chroma DB: {str(e)}")
                # Don't raise the exception, just log it since the file deletion is more important
                
        except Exception as e:
            raise Exception(f"Failed to delete from Chroma DB: {str(e)}")

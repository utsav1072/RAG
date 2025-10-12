from django.test import TestCase
from .models import Chat, User, Document
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.files.uploadedfile import SimpleUploadedFile
import os

# unit test for chat model
class ChatModelTest(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create(username="testuser")
        data = [{"Test" : "dummy"}, {"Test2" : "dummy2"}]
        self.chat = Chat.objects.create(user=self.user, sender="Test", chatBotResponse="Test", citations=data)

    def test_chat_creation(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.chat.sender, "Test")
        self.assertEqual(self.chat.chatBotResponse, "Test")
        data = [{"Test" : "dummy"}, {"Test2" : "dummy2"}]
        self.assertEqual(self.chat.citations, data)
        self.assertIsNotNone(self.chat.created_at)

# unit test for document model
class DocumentModelTest(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create(username="testuser")
        self.document = Document.objects.create(
            user=self.user,
            title="Sample PDF",
            filename="sample.pdf",
            file_path="/path/to/sample.pdf",
            file_size=3145728,  # 3 MB
            file_type="application/pdf",
            chroma_collection_id="chroma_123",
            is_active=True
        )

    def test_document_creation(self):
        self.assertEqual(self.document.title, "Sample PDF")
        self.assertEqual(self.document.filename, "sample.pdf")
        self.assertEqual(self.document.file_path, "/path/to/sample.pdf")
        self.assertEqual(self.document.file_type, "application/pdf")
        self.assertTrue(self.document.is_active)
        self.assertEqual(self.document.user.username, "testuser")

    def test_file_size_human_readable(self):
        self.assertEqual(self.document.file_size_human, "3.0 MB")

    def test_str_representation(self):
        expected = "Sample PDF (testuser)"
        self.assertEqual(str(self.document), expected)


# Testing Relationship between chat model and user model
class ChatUserRelationshipTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create(username="testuser")
        self.chat = Chat.objects.create(user=self.user, sender="User", chatBotResponse="Hello")

    def test_chat_is_linked_to_user(self):
        self.assertEqual(self.chat.user.username, "testuser")

# Registration Test
class AuthRegisterTests(APITestCase):
    def test_register_user_success(self):
        url = reverse('auth_register')
        data = {
            "username" : "testuser",
            "email" : "test@gmail.com",
            "password" : "Test@123",
            "password2" : "Test@123"
        }
        _response = self.client.post(url, data, format='json')
        self.assertEqual(_response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", _response.data)
        self.assertEqual(_response.data['username'], 'testuser')
        self.assertEqual(_response.data['email'], 'test@gmail.com')

    def test_register_user_password_mismatch(self):
        url = reverse('auth_register')
        data = {
            "username" : "testuser",
            "email" : "test@gmail.com",
            "password" : "Test@12",
            "password2" : "Test@123"
        }
        _response = self.client.post(url, data, format='json')
        self.assertEqual(_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_user_password_short(self):
        url = reverse('auth_register')
        data = {
            "username" : "testuser",
            "email" : "test@gmail.com",
            "password" : "123",
            "password2" : "123"
        }
        _response = self.client.post(url, data, format='json')
        self.assertEqual(_response.status_code, status.HTTP_400_BAD_REQUEST)

class AuthTokenTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="testuser", password="Password123")

    def test_token_obtain_success(self):
        url = reverse('token_obtain_pair')
        data = {"username": "testuser", "password": "Password123"}
        _response = self.client.post(url, data, format='json')
        self.assertEqual(_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", _response.data)
        self.assertIn("refresh", _response.data)

    def test_token_obtain_wrongcredentials(self):
        url = reverse('token_obtain_pair')
        data = {"username": "testuser", "password": "wrong"}
        _response = self.client.post(url, data, format='json')
        self.assertEqual(_response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="testuser", password="Password123")
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_whoami_authenticated(self):
        url = reverse('auth_me')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], "testuser")

    def test_whoami_unauthenticated(self):
        url = reverse('auth_me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

from django.test import override_settings
import tempfile

class DocumentIngestionTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a temporary directory for MEDIA_ROOT
        cls.media_root = tempfile.mkdtemp(prefix="django_test_media_")

    @classmethod
    def tearDownClass(cls):
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # Create a settings override context manager
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.user = User.objects.create(username="testuser", password="password@123")
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def tearDown(self):
        # Disable the settings override and restore original settings
        self.settings_override.disable()
        super().tearDown()

    def test_document_ingestion_success(self):
        from django.conf import settings
        file_path = os.path.join(settings.BASE_DIR, "chatbot", "test_files", "sample.pdf")
        with open(file_path, "rb") as f:
            dummy_file = SimpleUploadedFile("sample.pdf", f.read(), content_type="application/pdf")

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        url = reverse('documents_upload')
        _response = self.client.post(url,{'files' : dummy_file}, format='multipart')
        self.assertEqual(_response.status_code, status.HTTP_201_CREATED)

    def test_document_ingestion_missing_file(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        url = reverse('documents_upload')
        _response = self.client.post(url,{}, format='multipart')
        self.assertEqual(_response.status_code, status.HTTP_400_BAD_REQUEST)

class QueryAndIngestionTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a temporary directory for MEDIA_ROOT
        cls.media_root = tempfile.mkdtemp(prefix="django_test_media_")

    @classmethod
    def tearDownClass(cls):
        # Clean up the temporary directory
        import shutil
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # Create a settings override context manager
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.user = User.objects.create(username="testuser", password="password@123")
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        # uploading Dummy Document to query
        from django.conf import settings
        file_path = os.path.join(settings.BASE_DIR, "chatbot", "test_files", "sample.pdf")
        with open(file_path, "rb") as f:
            dummy_file = SimpleUploadedFile("sample.pdf", f.read(), content_type="application/pdf")

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        url = reverse('documents_upload')
        _response = self.client.post(url,{'files' : dummy_file}, format='multipart')


    def tearDown(self):
        # Disable the settings override and restore original settings
        self.settings_override.disable()
        super().tearDown()
    
    def test_query_success(self):
        url = reverse('rag_query')
        _response = self.client.post(url, {'query' : 'Kumar Utsav', 'top_k' : 4}, format='json')
        self.assertEqual(_response.status_code, status.HTTP_200_OK)
        # print(_response.data['answer'])
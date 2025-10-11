from django.test import TestCase
from .models import Chat, User, Document
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

# unit test for chat model
class ChatModelTest(TestCase):
    def setUp(self):
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
        self.user = User.objects.create(username="testuser")
        self.chat = Chat.objects.create(user=self.user, sender="User", chatBotResponse="Hello")

    def test_chat_is_linked_to_user(self):
        self.assertEqual(self.chat.user.username, "testuser")

# Registration Test
class AuthTest(APITestCase):
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

    

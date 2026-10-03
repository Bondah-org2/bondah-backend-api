from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test.utils import override_settings
from dating.models import Chat, Message
from .base import TEST_OVERRIDES

User = get_user_model()


@override_settings(**TEST_OVERRIDES)
class CreateChatViewTests(APITestCase):
    """Tests for POST /chats/create/"""

    def setUp(self):
        self.url = reverse("chat-create")
        self.user = User.objects.create_user(
            email="user1@example.com", password="Pass123!", name="User One"
        )
        self.other_user = User.objects.create_user(
            email="user2@example.com", password="Pass123!", name="User Two"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_direct_chat_success(self):
        """Creates a new direct chat between two users."""
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["chat_type"], "direct")

    def test_returns_existing_chat(self):
        """Returns 200 with existing chat if a direct chat already exists."""
        response1 = self.client.post(
            self.url,
            {"participants": [self.other_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        response2 = self.client.post(
            self.url,
            {"participants": [self.other_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data["id"], response2.data["id"])

    def test_cannot_chat_with_self(self):
        """Returns 400 if user tries to start a chat with themselves."""
        response = self.client.post(
            self.url,
            {"participants": [self.user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_direct_chat_requires_exactly_one_participant(self):
        """Returns 400 if more than one participant is provided for a direct chat."""
        third_user = User.objects.create_user(
            email="user3@example.com", password="Pass123!", name="User Three"
        )
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id, third_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_participant_id(self):
        """Returns 400 if a participant ID doesn't exist."""
        response = self.client.post(
            self.url,
            {"participants": [99999], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_bondmaker_cannot_create_matchmaker_intro(self):
        """Returns 400 if a regular user tries to create a matchmaker_intro chat."""
        third_user = User.objects.create_user(
            email="user3@example.com", password="Pass123!", name="User Three"
        )
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id, third_user.id], "chat_type": "matchmaker_intro"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bondmaker_can_create_matchmaker_intro(self):
        """A bondmaker can create a matchmaker_intro chat with two other users."""
        self.user.is_matchmaker = True
        self.user.save()
        third_user = User.objects.create_user(
            email="user3@example.com", password="Pass123!", name="User Three"
        )
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id, third_user.id], "chat_type": "matchmaker_intro"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_request_rejected(self):
        """Returns 401 if user is not authenticated."""
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url,
            {"participants": [self.other_user.id], "chat_type": "direct"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(**TEST_OVERRIDES)
class MessageDetailViewTests(APITestCase):
    """Tests for PATCH and DELETE /chats/{chat_id}/messages/{message_id}/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="sender@example.com", password="Pass123!", name="Sender"
        )
        self.other_user = User.objects.create_user(
            email="receiver@example.com", password="Pass123!", name="Receiver"
        )
        self.chat = Chat.objects.create(chat_type="direct", created_by=self.user)
        self.chat.participants.add(self.user, self.other_user)
        self.message = Message.objects.create(
            chat=self.chat,
            sender=self.user,
            message_type="text",
            content="Hello there",
        )
        self.url = reverse(
            "message-detail",
            kwargs={"chat_id": self.chat.id, "message_id": self.message.id},
        )
        self.client.force_authenticate(user=self.user)

    def test_edit_message_success(self):
        """Sender can edit their own message."""
        response = self.client.patch(self.url, {"content": "Updated!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.message.refresh_from_db()
        self.assertEqual(self.message.content, "Updated!")
        self.assertTrue(self.message.is_edited)

    def test_non_sender_cannot_edit(self):
        """Another participant cannot edit someone else's message."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(self.url, {"content": "Hacked!"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_for_me(self):
        """Delete for me hides the message only for the requester."""
        response = self.client.delete(
            self.url, {"delete_type": "for_me"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Message.objects.filter(id=self.message.id).exists())
        self.assertIn(self.user, self.message.deleted_for.all())

    def test_delete_for_everyone_by_sender(self):
        """Sender can delete a message for everyone — removes it from DB."""
        response = self.client.delete(
            self.url, {"delete_type": "for_everyone"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Message.objects.filter(id=self.message.id).exists())

    def test_non_sender_cannot_delete_for_everyone(self):
        """Another user cannot delete a message for everyone."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(
            self.url, {"delete_type": "for_everyone"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(**TEST_OVERRIDES)
class SendMessageViewTests(APITestCase):
    """Tests for POST /chats/{chat_id}/send/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="msgsender@example.com", password="Pass123!", name="Msg Sender"
        )
        self.other_user = User.objects.create_user(
            email="msgreceiver@example.com", password="Pass123!", name="Msg Receiver"
        )
        self.chat = Chat.objects.create(chat_type="direct", created_by=self.user)
        self.chat.participants.add(self.user, self.other_user)
        self.url = f"/api/v1/chats/{self.chat.id}/send/"
        self.client.force_authenticate(user=self.user)

    def test_send_text_message(self):
        """Can send a plain text message."""
        response = self.client.post(
            self.url,
            {"message_type": "text", "content": "Hey!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "Hey!")

    def test_send_image_message(self):
        """Can send an image message with a media_url."""
        response = self.client.post(
            self.url,
            {"message_type": "image", "media_url": "https://res.cloudinary.com/test/img.jpg"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_text_message_without_content_rejected(self):
        """Text message with no content returns 400."""
        response = self.client.post(
            self.url,
            {"message_type": "text"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_media_message_without_url_rejected(self):
        """Image message without media_url returns 400."""
        response = self.client.post(
            self.url,
            {"message_type": "image"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_participant_cannot_send(self):
        """A user not in the chat cannot send a message."""
        outsider = User.objects.create_user(
            email="outsider@example.com", password="Pass123!", name="Outsider"
        )
        self.client.force_authenticate(user=outsider)
        response = self.client.post(
            self.url,
            {"message_type": "text", "content": "Intruding!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

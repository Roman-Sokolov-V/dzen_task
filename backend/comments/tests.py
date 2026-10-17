import tempfile
from unittest.mock import AsyncMock

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from comments.models import Comment
from comments.serializers import (
    CommentActivitySerializer,
    CommentFlatSerializer,
    CommentRootListSerializer,
)
from comments.consumers import CommentConsumer, normalize_comment_ordering
from rest_framework.settings import api_settings

User = get_user_model()


class CommentTests(APITestCase):
    """Tests for comment viewing, creation, updating, and deletion."""

    def setUp(self):
        self.list_url = "/api/comments/"
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.staff_user = User.objects.create_superuser(
            username="staff",
            email="staff@example.com",
            password="staffpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )
        # A small GIF file (1x1 pixel) for testing image upload
        self.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04"
            b"\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
            b"\x02\x4c\x01\x00\x3b"
        )
        self.uploaded_image = SimpleUploadedFile(
            name="test_image.gif", content=self.small_gif, content_type="image/gif"
        )
        # A small text file (less than 100 KB)
        self.small_txt = SimpleUploadedFile(
            name="test_file.txt",
            content=b"This is a test file content.",
            content_type="text/plain",
        )

    def _authenticate(self, user):
        """Authenticate the given user."""
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_anonymous_can_list_comments(self):
        """Unauthenticated user can list comments."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming paginated response, check that we got a list (or paginated results)
        # We'll just check that the request succeeded.

    def test_anonymous_can_retrieve_comment(self):
        """Unauthenticated user can retrieve a comment."""
        # First create a comment as authenticated user to have something to retrieve
        self._authenticate(self.user)
        create_response = self.client.post(
            self.list_url, {"content": "Test comment"}, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data["id"]
        # Now unauthenticated retrieve
        self.client.credentials()  # Remove authentication
        retrieve_url = f"{self.list_url}{comment_id}/"
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "Test comment")

    def test_authenticated_user_can_create_comment_with_text(self):
        """Authenticated user can create a comment with text content."""
        self._authenticate(self.user)
        data = {"content": "This is a test comment."}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "This is a test comment.")
        # Author should be set to the authenticated user
        self.assertEqual(response.data["author"], self.user.username)

    def test_comment_create_serializer_sanitizes_xss_attributes(self):
        from comments.serializers import CommentCreateSerializer

        unsafe_content = '<strong onclick="alert(1)">Safe text</strong>'
        serializer = CommentCreateSerializer(data={"content": unsafe_content})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["content"], "<strong>Safe text</strong>"
        )
        comment = serializer.save(author=self.user)
        self.assertEqual(comment.content, "<strong>Safe text</strong>")

    def test_comment_output_serializers_sanitize_legacy_xss(self):
        unsafe_content = '<strong onmouseover="alert(1)">Legacy text</strong>'
        comment = Comment.objects.create(author=self.user, content=unsafe_content)

        self.assertEqual(
            CommentRootListSerializer(comment).data["content"],
            "<strong>Legacy text</strong>",
        )
        self.assertEqual(
            CommentActivitySerializer(comment).data["content"],
            "<strong>Legacy text</strong>",
        )

    def test_model_validator_rejects_unsafe_html_attributes(self):
        from comments.validators import validate_html_tags

        with self.assertRaises(ValidationError):
            validate_html_tags(
                '<a href="javascript:alert(1)" onclick="alert(1)">link</a>'
            )

    def test_comment_sanitizer_preserves_allowed_anchor_attributes(self):
        from comments.serializers import CommentCreateSerializer
        from comments.validators import validate_html_tags

        allowed_content = (
            '<a href="https://example.com" title="Example">link</a>'
            "<code>code</code><i>italic</i><strong>bold</strong>"
        )
        serializer = CommentCreateSerializer(data={"content": allowed_content})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["content"], allowed_content)
        validate_html_tags(allowed_content)

    def test_comment_serializer_removes_unsafe_tags_and_link_schemes(self):
        from comments.serializers import CommentCreateSerializer

        serializer = CommentCreateSerializer(
            data={
                "content": (
                    '<a href="javascript:alert(1)" onclick="alert(1)">link</a>'
                    '<img src="x" onerror="alert(1)">'
                )
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        sanitized_content = serializer.validated_data["content"]
        self.assertNotIn("javascript:", sanitized_content)
        self.assertNotIn("onclick", sanitized_content)
        self.assertNotIn("<img", sanitized_content)
        self.assertIn("link", sanitized_content)

    def test_tree_endpoint_sanitizes_legacy_cached_html(self):
        comment = Comment.objects.create(author=self.user, content="Safe root")
        cache.set(
            f"comment_tree_{comment.id}",
            {
                "id": comment.id,
                "content": '<strong onclick="alert(1)">Legacy root</strong>',
                "replies": [
                    {
                        "id": comment.id + 1,
                        "content": '<i onmouseover="alert(1)">Legacy reply</i>',
                        "replies": [],
                    }
                ],
            },
            900,
        )

        response = self.client.get(f"{self.list_url}{comment.id}/tree/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "<strong>Legacy root</strong>")
        self.assertEqual(
            response.data["replies"][0]["content"],
            "<i>Legacy reply</i>",
        )

    def test_websocket_ordering_is_allowlisted(self):
        self.assertEqual(
            normalize_comment_ordering("author__username"), "author__username"
        )
        self.assertEqual(
            normalize_comment_ordering("created_at; DROP TABLE comments_comment"),
            "-created_at",
        )
        self.assertEqual(normalize_comment_ordering(["created_at"]), "-created_at")

    def test_api_and_websocket_use_configured_page_size(self):
        for index in range(api_settings.PAGE_SIZE + 1):
            Comment.objects.create(author=self.user, content=f"Root {index}")

        api_response = self.client.get(self.list_url)
        self.assertEqual(len(api_response.data["results"]), api_settings.PAGE_SIZE)

        consumer = CommentConsumer()
        consumer.current_ordering = "-created_at"
        consumer.current_offset = 0
        consumer.current_limit = None
        consumer.send_json = AsyncMock()

        async_to_sync(consumer.send_initial_comments)()

        websocket_response = consumer.send_json.await_args.args[0]
        self.assertEqual(len(websocket_response["data"]), api_settings.PAGE_SIZE)
        self.assertEqual(websocket_response["limit"], api_settings.PAGE_SIZE)
        self.assertTrue(websocket_response["has_more"])

    def test_activity_serializer_includes_root_id_for_replies(self):
        self._authenticate(self.user)
        root_response = self.client.post(
            self.list_url, {"content": "Root comment"}, format="json"
        )
        self.assertEqual(root_response.status_code, status.HTTP_201_CREATED)
        tree_url = f"{self.list_url}{root_response.data['id']}/tree/"
        self.assertEqual(self.client.get(tree_url).data["replies"], [])

        reply_response = self.client.post(
            self.list_url,
            {"content": "Reply comment", "parent": root_response.data["id"]},
            format="json",
        )
        self.assertEqual(reply_response.status_code, status.HTTP_201_CREATED)

        root = Comment.objects.get(pk=root_response.data["id"])
        reply = Comment.objects.get(pk=reply_response.data["id"])

        self.assertEqual(CommentActivitySerializer(root).data["root_id"], root.id)
        self.assertEqual(CommentActivitySerializer(reply).data["root_id"], root.id)
        self.assertIsNone(CommentActivitySerializer(reply).data["avatar"])
        self.assertIsNone(CommentFlatSerializer(reply).data["avatar"])
        self.assertIsNone(CommentRootListSerializer(root).data["avatar"])
        updated_tree = self.client.get(tree_url)
        self.assertIsNone(updated_tree.data["avatar"])
        self.assertEqual(
            [item["id"] for item in updated_tree.data["replies"]], [reply.id]
        )
        self.assertIsNone(updated_tree.data["replies"][0]["avatar"])

    def test_comment_serializers_include_author_avatar_url(self):
        root = Comment.objects.create(author=self.user, content="Root comment")
        reply = Comment.objects.create(
            author=self.user,
            content="Reply comment",
            parent=root,
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                self.user.avatar.save(
                    "avatar.gif",
                    SimpleUploadedFile(
                        name="avatar.gif",
                        content=self.small_gif,
                        content_type="image/gif",
                    ),
                    save=True,
                )
                root.refresh_from_db()
                reply.refresh_from_db()

                root_avatar = CommentRootListSerializer(root).data["avatar"]
                activity_avatar = CommentActivitySerializer(reply).data["avatar"]
                flat_avatar = CommentFlatSerializer(reply).data["avatar"]
                tree_data = self.client.get(f"{self.list_url}{root.id}/tree/").data

        self.assertTrue(root_avatar)
        self.assertEqual(activity_avatar, root_avatar)
        self.assertEqual(flat_avatar, root_avatar)
        self.assertTrue(tree_data["avatar"].endswith(root_avatar))
        self.assertTrue(tree_data["replies"][0]["avatar"].endswith(root_avatar))

    def test_authenticated_user_can_create_comment_with_image(self):
        """Authenticated user can create a comment with an image."""
        self._authenticate(self.user)
        data = {"content": "Comment with image", "image": self.uploaded_image}
        response = self.client.post(self.list_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "Comment with image")
        self.assertEqual(response.data["author"], self.user.username)
        # Image should be present (we don't check the exact URL due to possible processing)
        self.assertIsNotNone(response.data.get("image"))

    def test_authenticated_user_can_create_comment_with_file(self):
        """Authenticated user can create a comment with a text file."""
        self._authenticate(self.user)
        data = {"content": "Comment with file", "file": self.small_txt}
        response = self.client.post(self.list_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "Comment with file")
        self.assertEqual(response.data["author"], self.user.username)
        self.assertIsNotNone(response.data.get("file"))

    def test_authenticated_user_cannot_create_comment_without_content(self):
        """Authenticated user cannot create a comment without content, image, or file."""
        self._authenticate(self.user)
        data = {}  # No content, image, or file
        response = self.client.post(self.list_url, data, format="json")
        # Should fail validation (400)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authenticated_user_can_update_own_comment(self):
        """Authenticated user can update their own comment."""
        self._authenticate(self.user)
        create_response = self.client.post(
            self.list_url, {"content": "Original comment"}, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data["id"]
        # Update the comment
        update_data = {"content": "Updated comment"}
        update_url = f"{self.list_url}{comment_id}/"
        response = self.client.patch(update_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "Updated comment")

    def test_authenticated_user_cannot_update_others_comment(self):
        """Authenticated user cannot update another user's comment."""
        # Create a comment as another user
        self._authenticate(self.other_user)
        create_response = self.client.post(
            self.list_url, {"content": "Other user's comment"}, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data["id"]
        # Now try to update as regular user (not the author)
        self._authenticate(self.user)
        update_data = {"content": "Hacked comment"}
        update_url = f"{self.list_url}{comment_id}/"
        response = self.client.patch(update_url, update_data, format="json")
        # Should be forbidden (403) or not found (404) depending on permission implementation
        self.assertIn(
            response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        )

    def test_staff_can_delete_any_comment(self):
        """Staff user can delete any comment."""
        # Create a comment as a regular user
        self._authenticate(self.user)
        create_response = self.client.post(
            self.list_url, {"content": "Comment to be deleted by staff"}, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data["id"]
        # Authenticate as staff and delete
        self._authenticate(self.staff_user)
        delete_url = f"{self.list_url}{comment_id}/"
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify comment is deleted
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_user_can_delete_own_comment(self):
        """Authenticated user can delete their own comment."""
        self._authenticate(self.user)
        create_response = self.client.post(
            self.list_url, {"content": "Comment to delete"}, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data["id"]
        delete_url = f"{self.list_url}{comment_id}/"
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify comment is deleted
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_user_cannot_delete_others_comment(self):
        """Authenticated user cannot delete another user's comment."""
        # Create a comment as another user
        self._authenticate(self.other_user)
        create_response = self.client.post(
            self.list_url, {"content": "Other user's comment to delete"}, format="json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data["id"]
        # Try to delete as regular user (not the author)
        self._authenticate(self.user)
        delete_url = f"{self.list_url}{comment_id}/"
        response = self.client.delete(delete_url)
        # Should be forbidden (403) or not found (404)
        self.assertIn(
            response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        )
        # Verify comment still exists
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

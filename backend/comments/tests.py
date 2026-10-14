from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from comments.models import Comment
from comments.serializers import CommentActivitySerializer

User = get_user_model()


class CommentTests(APITestCase):
    """Tests for comment viewing, creation, updating, and deletion."""

    def setUp(self):
        self.list_url = '/api/comments/'
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.staff_user = User.objects.create_superuser(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True,
            is_superuser=True
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        # A small GIF file (1x1 pixel) for testing image upload
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        self.uploaded_image = SimpleUploadedFile(
            name='test_image.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        # A small text file (less than 100 KB)
        self.small_txt = SimpleUploadedFile(
            name='test_file.txt',
            content=b'This is a test file content.',
            content_type='text/plain'
        )

    def _authenticate(self, user):
        """Authenticate the given user."""
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

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
            self.list_url,
            {'content': 'Test comment'},
            format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data['id']
        # Now unauthenticated retrieve
        self.client.credentials()  # Remove authentication
        retrieve_url = f'{self.list_url}{comment_id}/'
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Test comment')

    def test_authenticated_user_can_create_comment_with_text(self):
        """Authenticated user can create a comment with text content."""
        self._authenticate(self.user)
        data = {'content': 'This is a test comment.'}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'This is a test comment.')
        # Author should be set to the authenticated user
        self.assertEqual(response.data['author'], self.user.username)

    def test_activity_serializer_includes_root_id_for_replies(self):
        self._authenticate(self.user)
        root_response = self.client.post(
            self.list_url,
            {'content': 'Root comment'},
            format='json'
        )
        self.assertEqual(root_response.status_code, status.HTTP_201_CREATED)
        tree_url = f"{self.list_url}{root_response.data['id']}/tree/"
        self.assertEqual(self.client.get(tree_url).data['replies'], [])

        reply_response = self.client.post(
            self.list_url,
            {'content': 'Reply comment', 'parent': root_response.data['id']},
            format='json'
        )
        self.assertEqual(reply_response.status_code, status.HTTP_201_CREATED)

        root = Comment.objects.get(pk=root_response.data['id'])
        reply = Comment.objects.get(pk=reply_response.data['id'])

        self.assertEqual(CommentActivitySerializer(root).data['root_id'], root.id)
        self.assertEqual(CommentActivitySerializer(reply).data['root_id'], root.id)
        updated_tree = self.client.get(tree_url)
        self.assertEqual(
            [item['id'] for item in updated_tree.data['replies']],
            [reply.id]
        )

    def test_authenticated_user_can_create_comment_with_image(self):
        """Authenticated user can create a comment with an image."""
        self._authenticate(self.user)
        data = {
            'content': 'Comment with image',
            'image': self.uploaded_image
        }
        response = self.client.post(self.list_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Comment with image')
        self.assertEqual(response.data['author'], self.user.username)
        # Image should be present (we don't check the exact URL due to possible processing)
        self.assertIsNotNone(response.data.get('image'))

    def test_authenticated_user_can_create_comment_with_file(self):
        """Authenticated user can create a comment with a text file."""
        self._authenticate(self.user)
        data = {
            'content': 'Comment with file',
            'file': self.small_txt
        }
        response = self.client.post(self.list_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Comment with file')
        self.assertEqual(response.data['author'], self.user.username)
        self.assertIsNotNone(response.data.get('file'))

    def test_authenticated_user_cannot_create_comment_without_content(self):
        """Authenticated user cannot create a comment without content, image, or file."""
        self._authenticate(self.user)
        data = {}  # No content, image, or file
        response = self.client.post(self.list_url, data, format='json')
        # Should fail validation (400)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authenticated_user_can_update_own_comment(self):
        """Authenticated user can update their own comment."""
        self._authenticate(self.user)
        create_response = self.client.post(
            self.list_url,
            {'content': 'Original comment'},
            format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data['id']
        # Update the comment
        update_data = {'content': 'Updated comment'}
        update_url = f'{self.list_url}{comment_id}/'
        response = self.client.patch(update_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Updated comment')

    def test_authenticated_user_cannot_update_others_comment(self):
        """Authenticated user cannot update another user's comment."""
        # Create a comment as another user
        self._authenticate(self.other_user)
        create_response = self.client.post(
            self.list_url,
            {'content': "Other user's comment"},
            format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data['id']
        # Now try to update as regular user (not the author)
        self._authenticate(self.user)
        update_data = {'content': 'Hacked comment'}
        update_url = f'{self.list_url}{comment_id}/'
        response = self.client.patch(update_url, update_data, format='json')
        # Should be forbidden (403) or not found (404) depending on permission implementation
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_staff_can_delete_any_comment(self):
        """Staff user can delete any comment."""
        # Create a comment as a regular user
        self._authenticate(self.user)
        create_response = self.client.post(
            self.list_url,
            {'content': 'Comment to be deleted by staff'},
            format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data['id']
        # Authenticate as staff and delete
        self._authenticate(self.staff_user)
        delete_url = f'{self.list_url}{comment_id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify comment is deleted
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_user_can_delete_own_comment(self):
        """Authenticated user can delete their own comment."""
        self._authenticate(self.user)
        create_response = self.client.post(
            self.list_url,
            {'content': 'Comment to delete'},
            format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data['id']
        delete_url = f'{self.list_url}{comment_id}/'
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
            self.list_url,
            {'content': "Other user's comment to delete"},
            format='json'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comment_id = create_response.data['id']
        # Try to delete as regular user (not the author)
        self._authenticate(self.user)
        delete_url = f'{self.list_url}{comment_id}/'
        response = self.client.delete(delete_url)
        # Should be forbidden (403) or not found (404)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        # Verify comment still exists
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
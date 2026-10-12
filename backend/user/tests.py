from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class UserAuthenticationTests(APITestCase):
    """Tests for user registration and authentication."""

    def setUp(self):
        self.register_url = "/api/user/register/"
        self.token_url = "/api/user/token/"
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "captcha_key": "dummy_key",
            "captcha_value": "dummy_value",
        }

    def test_register_user_unauthenticated(self):
        """Unauthenticated user can register."""
        response = self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_obtain_token_after_registration(self):
        """After registration, you can obtain a token."""
        # Registration
        response = self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Obtaining token
        token_response = self.client.post(
            self.token_url,
            {
                "username": self.user_data["username"],
                "password": self.user_data["password"],
            },
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)
        self.assertIn("refresh", token_response.data)

    def test_authenticated_user_can_access_user_list(self):
        """Authenticated user can get the list of users."""
        # Create two users
        user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="pass123"
        )
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="pass123"
        )

        # Authenticate as user1
        token = AccessToken.for_user(user1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/api/user/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle pagination
        results = (
            response.data["results"] if "results" in response.data else response.data
        )
        self.assertEqual(len(results), 2)
        usernames = [u["username"] for u in results]
        self.assertIn("user1", usernames)
        self.assertIn("user2", usernames)

    def test_authenticated_user_can_retrieve_own_user(self):
        """Authenticated user can retrieve their own data."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Request to retrieve own data
        response = self.client.get(f"/api/user/{user.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], user.username)

    def test_unauthenticated_cannot_access_user_list(self):
        """Unauthenticated user cannot access the user list."""
        response = self.client.get("/api/user/")
        # Expect authentication error (401 or 403)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_cannot_retrieve_user(self):
        """Unauthenticated user cannot retrieve user data."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        response = self.client.get(f"/api/user/{user.pk}/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class UserPermissionTests(APITestCase):
    """Tests for checking permissions on updating and deleting users."""

    def setUp(self):
        # Create a regular user and an administrator
        self.user = User.objects.create_user(
            username="regularuser",
            email="regular@example.com",
            password="regularpass123",
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )
        # Another regular user for checking someone else's profile
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

        self.detail_url = lambda pk: f"/api/user/{pk}/"

    def _authenticate(self, user):
        """Helper to authenticate a user."""
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_user_can_update_own_profile(self):
        """User can update their own profile."""
        self._authenticate(self.user)
        updated_data = {
            "username": self.user.username,
            "email": "updated@example.com",
            "first_name": "Updated",
            "last_name": "User",
        }
        response = self.client.patch(
            self.detail_url(self.user.pk), updated_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.first_name, "Updated")

    def test_admin_can_update_any_user(self):
        """Administrator can update any user's profile."""
        self._authenticate(self.admin)
        updated_data = {
            "username": self.other_user.username,
            "email": "admin_updated@example.com",
            "first_name": "Admin",
            "last_name": "Updated",
        }
        response = self.client.patch(
            self.detail_url(self.other_user.pk), updated_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.other_user.refresh_from_db()
        self.assertEqual(self.other_user.email, "admin_updated@example.com")

    def test_user_cannot_update_other_user(self):
        """Regular user cannot update another user's profile."""
        self._authenticate(self.user)
        updated_data = {"email": "hacked@example.com"}
        response = self.client.patch(
            self.detail_url(self.other_user.pk), updated_data, format="json"
        )
        # Expect permission denied (403) or not found (404)
        self.assertIn(
            response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        )

    def test_user_can_delete_own_account(self):
        """User can delete their own account."""
        self._authenticate(self.user)
        response = self.client.delete(self.detail_url(self.user.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_admin_can_delete_any_user(self):
        """Administrator can delete any user."""
        self._authenticate(self.admin)
        response = self.client.delete(self.detail_url(self.other_user.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.other_user.pk).exists())

    def test_user_cannot_delete_other_user(self):
        """Regular user cannot delete another user's account."""
        self._authenticate(self.user)
        response = self.client.delete(self.detail_url(self.other_user.pk))
        self.assertIn(
            response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        )
        self.assertTrue(User.objects.filter(pk=self.other_user.pk).exists())
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')
USER_PAYLOAD = {
    'email': 'example@gmail.com',
    'password': 'password',
    'name': 'Test Name'
}


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_user_successful(self):
        response = self.client.post(CREATE_USER_URL, USER_PAYLOAD)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=USER_PAYLOAD['email'])
        self.assertTrue(user.check_password(USER_PAYLOAD['password']))
        self.assertNotIn('password', response.data)

    def test_user_with_email_exists(self):
        create_user(**USER_PAYLOAD)

        response = self.client.post(CREATE_USER_URL, USER_PAYLOAD)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        user_payload = {
            'email': 'example@gmail.com',
            'password': 'pass',
            'name': 'Test Name'
        }

        response = self.client.post(CREATE_USER_URL, user_payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=user_payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        create_user(**USER_PAYLOAD)

        token_payload = {
            'email': USER_PAYLOAD['email'],
            'password': USER_PAYLOAD['password']
        }

        response = self.client.post(TOKEN_URL, token_payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_create_token_invalid_credentials(self):
        create_user(**USER_PAYLOAD)

        token_payload = {
            'email': USER_PAYLOAD['email'],
            'password': 'incorrect_password'
        }

        response = self.client.post(TOKEN_URL, token_payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('token', response.data)

    def test_create_token_blank_password(self):
        create_user(**USER_PAYLOAD)

        token_payload = {
            'email': USER_PAYLOAD['email'],
            'password': ''
        }

        response = self.client.post(TOKEN_URL, token_payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('token', response.data)

    def test_retrieve_user_unauthorized(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    def setUp(self):
        self.user = create_user(**USER_PAYLOAD)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile(self):
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'email': self.user.email,
            'name': self.user.name
        })

    def test_create_profile_not_allowed(self):
        response = self.client.post(ME_URL, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_profile(self):
        user_payload = {
            'email': 'email@example.com',
            'password': 'new_password',
            'name': 'New Name',
        }
        response = self.client.patch(ME_URL, user_payload)

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.email, user_payload['email'])
        self.assertEqual(self.user.name, user_payload['name'])
        self.assertTrue(self.user.check_password(user_payload['password']))

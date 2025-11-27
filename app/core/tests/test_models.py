from django.test import TestCase
from django.contrib.auth import get_user_model

from unittest.mock import patch
from decimal import Decimal
from core import models


def create_user(email='user@gmail.com', password='password'):
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    def test_create_user_with_email_successful(self):
        email = "test@example.com"
        password = "test_password"
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com']
        ]
        for original_email, normalized_email in sample_emails:
            user = create_user(original_email, 'asdasda')
            self.assertEqual(user.email, normalized_email)

    def test_new_user_without_email(self):
        with self.assertRaises(ValueError):
            create_user('', 'asdasdsa')

    def test_create_superuser(self):
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'asdasdsa'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        user = create_user()
        recipe = models.Recipe.objects.create(
            user=user,
            title='Test title',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Test description'
        )

        self.assertEqual(str(recipe), 'Test title')

    def test_create_tag(self):
        user = create_user()
        tag = models.Tag.objects.create(user=user, name='tag 1')

        self.assertEqual(str(tag), 'tag 1')

    def test_create_ingredient(self):
        user = create_user()
        ingredient = models.Ingredient.objects.create(
            user=user,
            name='ingredient1'
        )

        self.assertEqual(str(ingredient), ingredient.name)

    @patch('core.models.recipe.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe.recipe_image_file_path(None, 'myimage.jpg')

        self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')

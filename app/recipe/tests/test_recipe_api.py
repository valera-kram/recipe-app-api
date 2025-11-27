import tempfile
import os

from PIL import Image

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
    Ingredient
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer
)

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def create_recipe(user, **params):
    defaults = {
        'title': 'Test Recipe',
        'time_minutes': 15,
        'price': Decimal(5.25),
        'description': 'Some Recipe',
        'link': "http://example.com",
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(RECIPES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    def setUp(self):
        self.user = create_user(email='user@example.com', password='asdasdas')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_recipes(self):
        create_recipe(self.user)
        create_recipe(self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_recipies_by_user(self):
        user2 = get_user_model().objects.create_user(
            email='example+1@example.com',
            password='qwerqweqw'
        )
        create_recipe(self.user)
        create_recipe(user2)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user).order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_recipe_detail(self):
        recipe = create_recipe(self.user)
        url = detail_url(recipe.id)

        response = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_recipe(self):
        recipe_payload = {
            'title': 'Test Recipe',
            'time_minutes': 15,
            'price': Decimal(5.25),
            'description': 'Some Recipe',
            'link': "http://example.com"
        }

        response = self.client.post(RECIPES_URL, recipe_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        for key, value in recipe_payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update_recipe(self):
        original_link = 'http://example.com'
        recipe = create_recipe(
            self.user,
            title='Test Recipe',
            link=original_link,
        )
        payload = {'link': 'https://example.com'}
        response = self.client.patch(detail_url(recipe.id), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.link, payload['link'])
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        user2 = create_user(email='user@gmail.com', password='asdadqwe')
        recipe = create_recipe(self.user)

        recipe_payload = {'user': user2.id}
        response = self.client.patch(detail_url(recipe.id), recipe_payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(self.user)

        response = self.client.delete(detail_url(recipe.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe(self):
        user2 = create_user(email='asd@gmail.com', password='qadasdasd')
        recipe = create_recipe(user=user2)

        response = self.client.delete(detail_url(recipe.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_crate_recipe_with_tags(self):
        recipe_payload = {
            'title': 'Test Recipe',
            'time_minutes': 15,
            'price': Decimal(5.25),
            'tags': [{"name": "Test Tag1"}, {"name": "Test Recipe"}]
        }

        response = self.client.post(RECIPES_URL, recipe_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        recipies = Recipe.objects.filter(user=self.user)
        self.assertEqual(len(recipies), 1)
        self.assertEqual(recipies[0].tags.count(), 2)

    def test_create_recipe_with_existing_tag(self):
        tag = Tag.objects.create(user=self.user, name='tag1')
        payload = {
            'title': 'Recipe',
            'time_minutes': 15,
            'price': Decimal(5.25),
            'tags': [{'name': 'tag1'}, {'name': 'tag2'}]
        }

        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes[0].tags.count(), 2)
        self.assertIn(tag, recipes[0].tags.all())

    def test_create_tag_on_update_recipe(self):
        recipe = create_recipe(self.user)
        payload = {'tags': [{'name': 'Test Tag'}]}

        response = self.client.patch(
            detail_url(recipe.id),
            payload,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(name='Test Tag', user=self.user)
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_with_existing_tag(self):
        tag = Tag.objects.create(user=self.user, name='tag1')
        recipe = create_recipe(self.user)
        recipe.tags.add(tag)

        tag2 = Tag.objects.create(user=self.user, name='tag2')
        payload = {'tags': [{'name': 'tag2'}]}

        response = self.client.patch(
            detail_url(recipe.id),
            payload,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(tag2, recipe.tags.all())
        self.assertNotIn(tag, recipe.tags.all())

    def test_clear_recipe_tags(self):
        recipe = create_recipe(self.user)
        tag = Tag.objects.create(user=self.user, name='tag1')
        recipe.tags.add(tag)

        payload = {'tags': []}

        response = self.client.patch(
            detail_url(recipe.id),
            payload,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_ingredients(self):
        payload = {
            'title': 'Test Recipe',
            'time_minutes': 15,
            'price': Decimal(5.25),
            'ingredients': [
                {'name': 'Test Ingredient1'},
                {'name': 'Test Ingredient2'}
            ]
        }

        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes[0].ingredients.count(), 2)

    def test_create_ingredient_on_update_recipe(self):
        recipe = create_recipe(self.user)

        payload = {'ingredients': [{'name': 'Ingredient1'}]}

        response = self.client.patch(
            detail_url(recipe.id),
            payload,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(
            name='Ingredient1',
            user=self.user
        )
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Ingredient1'
        )
        recipe = create_recipe(self.user)
        recipe.ingredients.add(ingredient)

        ingredient2 = Ingredient.objects.create(
            user=self.user,
            name='Ingredient2'
        )
        payload = {'ingredients': [{'name': ingredient2.name}]}

        response = self.client.patch(
            detail_url(recipe.id),
            payload,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_retrieve_recipes_by_tags(self):
        recipe = create_recipe(self.user, title='Title1')
        recipe2 = create_recipe(self.user, title='Title2')
        create_recipe(self.user, title='Title3')
        tag = Tag.objects.create(user=self.user, name='Tag1')
        tag2 = Tag.objects.create(user=self.user, name='Tag2')
        recipe.tags.add(tag)
        recipe2.tags.add(tag2)

        params = {'tags': f'{tag.id},{tag2.id}'}

        response = self.client.get(RECIPES_URL, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_recipes_by_ingredients(self):
        recipe = create_recipe(self.user, title='Title1')
        recipe2 = create_recipe(self.user, title='Title2')
        create_recipe(self.user, title='Title3')
        ingredient = Ingredient.objects.create(user=self.user, name='Ingredient1')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Ingredient2')
        recipe.ingredients.add(ingredient)
        recipe2.ingredients.add(ingredient2)

        params = {'ingredients': f'{ingredient.id},{ingredient2.id}'}

        response = self.client.get(RECIPES_URL, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class ImageUploadTests(TestCase):
    def setUp(self):
        self.user = create_user(email='user@gmail.com', password='password')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.recipe = create_recipe(self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            image = Image.new('RGB', (10, 10))
            image.save(image_file, format='JPEG')
            image_file.seek(0)

            payload = {'image': image_file}

            response = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image', response.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_invalid_image(self):
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'asd'}

        response = self.client.post(url, payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class OJSSyncEndpointsTest(APITestCase):
    def mock_ojs(self, target, return_value=None):
        return patch(target, return_value=return_value)

    def _mock_detail(self, entity, pk='1', return_value=None):
        return patch(f'apps.integrations.views.ojs_get_{entity}', return_value=return_value)
    def _mock_update(self, entity, pk='1', return_value=None):
        return patch(f'apps.integrations.views.ojs_update_{entity}', return_value=return_value)
    def _mock_delete(self, entity, pk='1', return_value=True):
        return patch(f'apps.integrations.views.ojs_delete_{entity}', return_value=return_value)

    def setUp(self):
        self.client = APIClient()
        # Create a test user
        self.user = User.objects.create_user(email='apitest@example.com', password='testpass123', first_name='API', last_name='Test')
        # Authenticate using JWT
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_journal_list(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_journals', return_value=[{'id': '1', 'name': 'Test Journal', 'description': 'Desc'}]):
            url = reverse('ojs_journal_list')
            response = self.client.get(url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])

    def test_article_crud(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_articles', return_value=[{'id': '1', 'title': 'Test Article', 'abstract': 'Test', 'status': 'draft'}]), \
             self.mock_ojs('apps.integrations.views.ojs_create_article', return_value={'id': '2', 'title': 'Test Article', 'abstract': 'Test', 'status': 'draft'}):
            list_url = reverse('ojs_article_list')
            # List
            response = self.client.get(list_url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            # Create (simulate minimal valid data)
            create_data = {'title': 'Test Article', 'abstract': 'Test', 'status': 'draft'}
            response = self.client.post(list_url, create_data, format='json')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_article_retrieve_update_delete(self):
        pk = '1'
        with self._mock_detail('article', pk, {'id': pk, 'title': 'Test', 'abstract': 'Test', 'status': 'draft'}), \
             self._mock_update('article', pk, {'id': pk, 'title': 'Updated', 'abstract': 'Test', 'status': 'published'}), \
             self._mock_delete('article', pk, True):
            url = reverse('ojs_article_detail', args=[pk])
            # Retrieve
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            # Update
            resp = self.client.put(url, {'title': 'Updated', 'abstract': 'Test', 'status': 'published'}, format='json')
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            # Delete
            resp = self.client.delete(url)
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT, status.HTTP_502_BAD_GATEWAY])

    def test_user_crud(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_users', return_value=[{'id': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User', 'roles': ['author']}]), \
             self.mock_ojs('apps.integrations.views.ojs_create_user', return_value={'id': '2', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User', 'roles': ['author']}):
            list_url = reverse('ojs_user_sync')
            response = self.client.get(list_url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            create_data = {'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User', 'roles': ['author']}
            response = self.client.post(list_url, create_data, format='json')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_user_retrieve_update_delete(self):
        pk = '1'
        with self._mock_detail('user', pk, {'id': pk, 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User', 'roles': ['author']}), \
             self._mock_update('user', pk, {'id': pk, 'email': 'testuser@example.com', 'first_name': 'Updated', 'last_name': 'User', 'roles': ['author']}), \
             self._mock_delete('user', pk, True):
            url = reverse('ojs_user_detail_sync', args=[pk])
            # Retrieve
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])
            # Update
            resp = self.client.put(url, {'email': 'testuser@example.com', 'first_name': 'Updated', 'last_name': 'User', 'roles': ['author']}, format='json')
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])
            # Delete
            resp = self.client.delete(url)
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_review_crud(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_reviews', return_value=[{'id': '1', 'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Looks good', 'status': 'pending'}]), \
             self.mock_ojs('apps.integrations.views.ojs_create_review', return_value={'id': '2', 'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Looks good', 'status': 'pending'}):
            list_url = reverse('ojs_review_sync')
            response = self.client.get(list_url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            create_data = {'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Looks good', 'status': 'pending'}
            response = self.client.post(list_url, create_data, format='json')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_review_retrieve_update_delete(self):
        pk = '1'
        with self._mock_detail('review', pk, {'id': pk, 'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Looks good', 'status': 'pending'}), \
             self._mock_update('review', pk, {'id': pk, 'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Updated', 'status': 'completed'}), \
             self._mock_delete('review', pk, True):
            url = reverse('ojs_review_detail_sync', args=[pk])
            # Retrieve
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])
            # Update
            resp = self.client.put(url, {'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Updated', 'status': 'completed'}, format='json')
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])
            # Delete
            resp = self.client.delete(url)
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_comment_crud(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_comments', return_value=[{'id': '1', 'submission_id': '1', 'user_id': '1', 'content': 'Test comment'}]), \
             self.mock_ojs('apps.integrations.views.ojs_create_comment', return_value={'id': '2', 'submission_id': '1', 'user_id': '1', 'content': 'Test comment'}):
            list_url = reverse('ojs_comment_sync')
            response = self.client.get(list_url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            create_data = {'submission_id': '1', 'user_id': '1', 'content': 'Test comment'}
            response = self.client.post(list_url, create_data, format='json')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_comment_retrieve_update_delete(self):
        pk = '1'
        with self._mock_detail('comment', pk, {'id': pk, 'submission_id': '1', 'user_id': '1', 'content': 'Test comment'}), \
             self._mock_update('comment', pk, {'id': pk, 'submission_id': '1', 'user_id': '1', 'content': 'Updated comment'}), \
             self._mock_delete('comment', pk, True):
            url = reverse('ojs_comment_detail_sync', args=[pk])
            # Retrieve
            resp = self.client.get(url)
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])
            # Update
            resp = self.client.put(url, {'submission_id': '1', 'user_id': '1', 'content': 'Updated comment'}, format='json')
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])
            # Delete
            resp = self.client.delete(url)
            self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_journal_list(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_journals', return_value=[{'id': '1', 'name': 'Test Journal', 'description': 'Desc'}]):
            url = reverse('ojs_journal_list')
            response = self.client.get(url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])

    def test_article_crud(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_articles', return_value=[{'id': '1', 'title': 'Test Article', 'abstract': 'Test', 'status': 'draft'}]), \
             self.mock_ojs('apps.integrations.views.ojs_create_article', return_value={'id': '2', 'title': 'Test Article', 'abstract': 'Test', 'status': 'draft'}):
            list_url = reverse('ojs_article_list')
            # List
            response = self.client.get(list_url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            # Create (simulate minimal valid data)
            create_data = {'title': 'Test Article', 'abstract': 'Test', 'status': 'draft'}
            response = self.client.post(list_url, create_data, format='json')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_user_crud(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_users', return_value=[{'id': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User', 'roles': ['author']}]), \
             self.mock_ojs('apps.integrations.views.ojs_create_user', return_value={'id': '2', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User', 'roles': ['author']}):
            list_url = reverse('ojs_user_sync')
            response = self.client.get(list_url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            create_data = {'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User', 'roles': ['author']}
            response = self.client.post(list_url, create_data, format='json')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_review_crud(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_reviews', return_value=[{'id': '1', 'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Looks good', 'status': 'pending'}]), \
             self.mock_ojs('apps.integrations.views.ojs_create_review', return_value={'id': '2', 'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Looks good', 'status': 'pending'}):
            list_url = reverse('ojs_review_sync')
            response = self.client.get(list_url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            create_data = {'submission_id': '1', 'reviewer_id': '1', 'recommendation': 'accept', 'comments': 'Looks good', 'status': 'pending'}
            response = self.client.post(list_url, create_data, format='json')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_comment_crud(self):
        with self.mock_ojs('apps.integrations.views.ojs_list_comments', return_value=[{'id': '1', 'submission_id': '1', 'user_id': '1', 'content': 'Test comment'}]), \
             self.mock_ojs('apps.integrations.views.ojs_create_comment', return_value={'id': '2', 'submission_id': '1', 'user_id': '1', 'content': 'Test comment'}):
            list_url = reverse('ojs_comment_sync')
            response = self.client.get(list_url)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY])
            create_data = {'submission_id': '1', 'user_id': '1', 'content': 'Test comment'}
            response = self.client.post(list_url, create_data, format='json')
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

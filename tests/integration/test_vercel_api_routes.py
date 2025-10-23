"""
Tests for Vercel API routes to ensure they work correctly with Flask structure.
"""
import unittest.mock as mock
import pytest
import json
from flask import Flask

from deployments.vercel.api.hello_notion import app as hello_app
from deployments.vercel.api.run_daily_plan import app as daily_plan_app
from deployments.vercel.api.scheduled_daily_plan import app as scheduled_app

class TestVercelAPIRoutes:
    """Test Vercel API route handlers with Flask structure."""
    
    def test_hello_notion_with_query_param(self):
        """Test hello-notion endpoint with query parameter."""
        with hello_app.test_client() as client:
            response = client.get('/?name=TestUser')
            
            assert response.status_code == 200
            assert "Hello, TestUser" in response.get_json()['body']
    
    def test_hello_notion_with_body_param(self):
        """Test hello-notion endpoint with body parameter."""
        with hello_app.test_client() as client:
            response = client.post('/', json={'name': 'TestUser'})
            
            assert response.status_code == 200
            assert "Hello, TestUser" in response.get_json()['body']
    
    def test_hello_notion_without_name(self):
        """Test hello-notion endpoint without name parameter."""
        with hello_app.test_client() as client:
            response = client.get('/')
            
            assert response.status_code == 200
            assert "This HTTP triggered function executed successfully" in response.get_json()['body']
    
    def test_hello_notion_with_invalid_json(self):
        """Test hello-notion endpoint with invalid JSON in body."""
        with hello_app.test_client() as client:
            response = client.post('/', data='invalid json', content_type='application/json')
            
            assert response.status_code == 200
            assert "This HTTP triggered function executed successfully" in response.get_json()['body']
    
    @mock.patch('deployments.vercel.api.run_daily_plan.NotionService')
    def test_run_daily_plan_success(self, mock_service_class):
        """Test run-daily-plan endpoint with successful execution."""
        mock_service = mock.MagicMock()
        mock_service.run_daily_plan.return_value = {
            'status_code': 200,
            'message': 'Daily plan executed successfully'
        }
        mock_service_class.return_value = mock_service
        
        with daily_plan_app.test_client() as client:
            response = client.post('/')
            
            assert response.status_code == 200
            result = response.get_json()
            assert 'successfully' in result['body']
            mock_service.run_daily_plan.assert_called_once()
    
    @mock.patch('deployments.vercel.api.run_daily_plan.NotionService')
    def test_run_daily_plan_error(self, mock_service_class):
        """Test run-daily-plan endpoint with error."""
        mock_service = mock.MagicMock()
        mock_service.run_daily_plan.return_value = {
            'status_code': 500,
            'error': 'Test error occurred'
        }
        mock_service_class.return_value = mock_service
        
        with daily_plan_app.test_client() as client:
            response = client.post('/')
            
            assert response.status_code == 200
            result = response.get_json()
            assert 'Test error occurred' in result['body']
    
    @mock.patch('deployments.vercel.api.scheduled_daily_plan.NotionService')
    def test_scheduled_daily_plan_success(self, mock_service_class):
        """Test scheduled-daily-plan endpoint with successful execution."""
        mock_service = mock.MagicMock()
        mock_service.run_daily_plan.return_value = {
            'status_code': 200,
            'message': 'Daily plan executed successfully'
        }
        mock_service_class.return_value = mock_service
        
        with scheduled_app.test_client() as client:
            response = client.post('/')
            
            assert response.status_code == 200
            result = response.get_json()
            assert 'Scheduled execution completed' in result['body']
            mock_service.run_daily_plan.assert_called_once()
    
    @mock.patch('deployments.vercel.api.scheduled_daily_plan.NotionService')
    def test_scheduled_daily_plan_error(self, mock_service_class):
        """Test scheduled-daily-plan endpoint with error."""
        mock_service = mock.MagicMock()
        mock_service.run_daily_plan.return_value = {
            'status_code': 500,
            'error': 'Test error occurred'
        }
        mock_service_class.return_value = mock_service
        
        with scheduled_app.test_client() as client:
            response = client.post('/')
            
            assert response.status_code == 200
            result = response.get_json()
            assert 'Scheduled execution completed' in result['body']
            mock_service.run_daily_plan.assert_called_once()
    
    def test_hello_notion_api_route(self):
        """Test hello-notion endpoint via API route."""
        with hello_app.test_client() as client:
            response = client.get('/api/hello-notion?name=TestUser')
            
            assert response.status_code == 200
            assert "Hello, TestUser" in response.get_json()['body']
    
    def test_run_daily_plan_api_route(self):
        """Test run-daily-plan endpoint via API route."""
        with daily_plan_app.test_client() as client:
            response = client.post('/api/run-daily-plan')
            
            assert response.status_code == 200
            # Should return some response (success or error)
            assert 'body' in response.get_json()
    
    def test_scheduled_daily_plan_api_route(self):
        """Test scheduled-daily-plan endpoint via API route."""
        with scheduled_app.test_client() as client:
            response = client.post('/api/scheduled-daily-plan')
            
            assert response.status_code == 200
            # Should return some response (success or error)
            assert 'body' in response.get_json()

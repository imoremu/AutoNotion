"""
Integration tests for shared service with Flask API routes.
"""
import unittest.mock as mock
import pytest
import os
from flask import Flask

from shared.notion_service import NotionService
from deployments.vercel.api.hello_notion import app as hello_app
from deployments.vercel.api.run_daily_plan import app as daily_plan_app
from deployments.vercel.api.scheduled_daily_plan import app as scheduled_app

class TestSharedServiceIntegration:
    """Test shared service integration with Flask API routes."""
    
    def test_shared_service_initialization(self):
        """Test that shared service can be initialized."""
        service = NotionService()
        assert service is not None
        assert hasattr(service, 'get_environment_variables')
        assert hasattr(service, 'run_daily_plan')
        assert hasattr(service, 'hello_notion')
    
    @mock.patch.dict(os.environ, {
        'NOTION_API_KEY': 'test_key',
        'NOTION_REGISTRY_DB_ID': 'test_registry',
        'NOTION_TASKS_DB_ID': 'test_tasks'
    })
    def test_shared_service_with_env_vars(self):
        """Test shared service with environment variables."""
        service = NotionService()
        api_key, registry_db_id, tasks_db_id = service.get_environment_variables()
        
        assert api_key == 'test_key'
        assert registry_db_id == 'test_registry'
        assert tasks_db_id == 'test_tasks'
    
    def test_shared_service_without_env_vars(self):
        """Test shared service without environment variables."""
        with mock.patch.dict(os.environ, {}, clear=True):
            service = NotionService()
            api_key, registry_db_id, tasks_db_id = service.get_environment_variables()
            
            assert api_key is None
            assert registry_db_id is None
            assert tasks_db_id is None
    
    def test_shared_service_hello_notion(self):
        """Test shared service hello_notion method."""
        service = NotionService()
        
        # Test with name
        result = service.hello_notion("TestUser")
        assert result['status_code'] == 200
        assert "Hello, TestUser" in result['message']
        
        # Test without name
        result = service.hello_notion()
        assert result['status_code'] == 200
        assert "This HTTP triggered function executed successfully" in result['message']
    
    @mock.patch('shared.notion_service.NotionDailyPlanner')
    def test_shared_service_run_daily_plan_success(self, mock_planner_class):
        """Test shared service run_daily_plan method with success."""
        with mock.patch.dict(os.environ, {
            'NOTION_API_KEY': 'test_key',
            'NOTION_REGISTRY_DB_ID': 'test_registry',
            'NOTION_TASKS_DB_ID': 'test_tasks'
        }):
            mock_planner = mock.MagicMock()
            mock_planner_class.return_value = mock_planner
            
            service = NotionService()
            result = service.run_daily_plan()
            
            assert result['status_code'] == 200
            assert 'successfully' in result['message']
            mock_planner.run_daily_plan.assert_called_once()
    
    def test_shared_service_run_daily_plan_missing_env_vars(self):
        """Test shared service run_daily_plan method with missing environment variables."""
        with mock.patch.dict(os.environ, {}, clear=True):
            service = NotionService()
            result = service.run_daily_plan()
            
            assert result['status_code'] == 400
            assert 'Missing Notion environment variables' in result['error']
    
    @mock.patch('shared.notion_service.NotionDailyPlanner')
    def test_shared_service_run_daily_plan_exception(self, mock_planner_class):
        """Test shared service run_daily_plan method with exception."""
        with mock.patch.dict(os.environ, {
            'NOTION_API_KEY': 'test_key',
            'NOTION_REGISTRY_DB_ID': 'test_registry',
            'NOTION_TASKS_DB_ID': 'test_tasks'
        }):
            mock_planner = mock.MagicMock()
            mock_planner.run_daily_plan.side_effect = Exception("Test error")
            mock_planner_class.return_value = mock_planner
            
            service = NotionService()
            result = service.run_daily_plan()
            
            assert result['status_code'] == 500
            assert 'Test error' in result['error']
    
    def test_flask_apps_use_shared_service(self):
        """Test that Flask apps can use the shared service."""
        # Test hello_notion app
        with hello_app.test_client() as client:
            response = client.get('/?name=TestUser')
            assert response.status_code == 200
            assert "Hello, TestUser" in response.get_json()['body']
        
        # Test run_daily_plan app (will fail due to missing env vars, but should not crash)
        with daily_plan_app.test_client() as client:
            response = client.post('/')
            assert response.status_code == 200
            result = response.get_json()
            assert 'body' in result
        
        # Test scheduled_daily_plan app (will fail due to missing env vars, but should not crash)
        with scheduled_app.test_client() as client:
            response = client.post('/')
            assert response.status_code == 200
            result = response.get_json()
            assert 'body' in result
    
    def test_flask_apps_error_handling(self):
        """Test that Flask apps handle errors gracefully."""
        # Test with invalid JSON
        with hello_app.test_client() as client:
            response = client.post('/', data='invalid json', content_type='application/json')
            assert response.status_code == 200
            assert 'body' in response.get_json()
        
        # Test with missing parameters
        with hello_app.test_client() as client:
            response = client.get('/')
            assert response.status_code == 200
            assert 'body' in response.get_json()
    
    def test_flask_apps_logging_integration(self):
        """Test that Flask apps integrate with logging system."""
        # Test that apps can be created without logging errors
        assert hello_app is not None
        assert daily_plan_app is not None
        assert scheduled_app is not None
        
        # Test that apps can handle requests without logging errors
        with hello_app.test_client() as client:
            response = client.get('/')
            assert response.status_code == 200
        
        with daily_plan_app.test_client() as client:
            response = client.post('/')
            assert response.status_code == 200
        
        with scheduled_app.test_client() as client:
            response = client.post('/')
            assert response.status_code == 200

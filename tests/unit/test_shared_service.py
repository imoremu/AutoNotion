"""
Tests for the shared NotionService class used by both Azure Functions and Vercel.
"""
import unittest.mock as mock
import pytest
import os
from shared.notion_service import NotionService

class TestNotionService:
    """Test the shared NotionService class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.service = NotionService()
    
    def test_get_environment_variables_success(self):
        """Test successful retrieval of environment variables."""
        with mock.patch.dict(os.environ, {
            'NOTION_API_KEY': 'test_key',
            'NOTION_REGISTRY_DB_ID': 'test_registry',
            'NOTION_TASKS_DB_ID': 'test_tasks'
        }):
            api_key, registry_db_id, tasks_db_id = self.service.get_environment_variables()
            
            assert api_key == 'test_key'
            assert registry_db_id == 'test_registry'
            assert tasks_db_id == 'test_tasks'
    
    def test_get_environment_variables_missing_key(self):
        """Test handling of missing API key."""
        with mock.patch.dict(os.environ, {
            'NOTION_REGISTRY_DB_ID': 'test_registry',
            'NOTION_TASKS_DB_ID': 'test_tasks'
        }, clear=True):
            api_key, registry_db_id, tasks_db_id = self.service.get_environment_variables()
            
            assert api_key is None
            assert registry_db_id is None
            assert tasks_db_id is None
    
    def test_get_environment_variables_missing_all(self):
        """Test handling when all environment variables are missing."""
        with mock.patch.dict(os.environ, {}, clear=True):
            api_key, registry_db_id, tasks_db_id = self.service.get_environment_variables()
            
            assert api_key is None
            assert registry_db_id is None
            assert tasks_db_id is None
    
    @mock.patch('shared.notion_service.NotionDailyPlanner')
    def test_run_daily_plan_success(self, mock_planner_class):
        """Test successful daily plan execution."""
        with mock.patch.dict(os.environ, {
            'NOTION_API_KEY': 'test_key',
            'NOTION_REGISTRY_DB_ID': 'test_registry',
            'NOTION_TASKS_DB_ID': 'test_tasks'
        }):
            mock_planner = mock.MagicMock()
            mock_planner_class.return_value = mock_planner
            
            result = self.service.run_daily_plan()
            
            assert result['status_code'] == 200
            assert 'successfully' in result['message']
            mock_planner.run_daily_plan.assert_called_once()
    
    @mock.patch('shared.notion_service.NotionDailyPlanner')
    def test_run_daily_plan_missing_env_vars(self, mock_planner_class):
        """Test daily plan execution with missing environment variables."""
        with mock.patch.dict(os.environ, {}, clear=True):
            result = self.service.run_daily_plan()
            
            assert result['status_code'] == 400
            assert 'Missing Notion environment variables' in result['error']
            mock_planner_class.assert_not_called()
    
    @mock.patch('shared.notion_service.NotionDailyPlanner')
    def test_run_daily_plan_exception(self, mock_planner_class):
        """Test daily plan execution with exception."""
        with mock.patch.dict(os.environ, {
            'NOTION_API_KEY': 'test_key',
            'NOTION_REGISTRY_DB_ID': 'test_registry',
            'NOTION_TASKS_DB_ID': 'test_tasks'
        }):
            mock_planner = mock.MagicMock()
            mock_planner.run_daily_plan.side_effect = Exception("Test error")
            mock_planner_class.return_value = mock_planner
            
            result = self.service.run_daily_plan()
            
            assert result['status_code'] == 500
            assert 'Test error' in result['error']
    
    def test_hello_notion_with_name(self):
        """Test hello notion with name parameter."""
        result = self.service.hello_notion("TestUser")
        
        assert result['status_code'] == 200
        assert "Hello, TestUser" in result['message']
    
    def test_hello_notion_without_name(self):
        """Test hello notion without name parameter."""
        result = self.service.hello_notion()
        
        assert result['status_code'] == 200
        assert "This HTTP triggered function executed successfully" in result['message']
    
    def test_hello_notion_with_none_name(self):
        """Test hello notion with None name parameter."""
        result = self.service.hello_notion(None)
        
        assert result['status_code'] == 200
        assert "This HTTP triggered function executed successfully" in result['message']

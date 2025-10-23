"""
Tests to ensure dual deployment compatibility between Azure Functions and Vercel.
"""
import unittest.mock as mock
import pytest
import os
from shared.notion_service import NotionService

class TestDualDeployment:
    """Test that both Azure Functions and Vercel can use the same business logic."""
    
    def test_shared_service_imports_correctly(self):
        """Test that the shared service can be imported without issues."""
        from shared.notion_service import NotionService
        service = NotionService()
        assert service is not None
    
    def test_shared_service_has_required_methods(self):
        """Test that the shared service has all required methods."""
        service = NotionService()
        
        # Check that all required methods exist
        assert hasattr(service, 'get_environment_variables')
        assert hasattr(service, 'run_daily_plan')
        assert hasattr(service, 'hello_notion')
        
        # Check that methods are callable
        assert callable(service.get_environment_variables)
        assert callable(service.run_daily_plan)
        assert callable(service.hello_notion)
    
    def test_environment_variables_consistency(self):
        """Test that both platforms use the same environment variables."""
        required_vars = ['NOTION_API_KEY', 'NOTION_REGISTRY_DB_ID', 'NOTION_TASKS_DB_ID']
        
        # Test that the service checks for all required variables
        with mock.patch.dict(os.environ, {}, clear=True):
            service = NotionService()
            api_key, registry_db_id, tasks_db_id = service.get_environment_variables()
            
            assert api_key is None
            assert registry_db_id is None
            assert tasks_db_id is None
        
        # Test that the service works with all variables set
        with mock.patch.dict(os.environ, {
            'NOTION_API_KEY': 'test_key',
            'NOTION_REGISTRY_DB_ID': 'test_registry',
            'NOTION_TASKS_DB_ID': 'test_tasks'
        }):
            service = NotionService()
            api_key, registry_db_id, tasks_db_id = service.get_environment_variables()
            
            assert api_key == 'test_key'
            assert registry_db_id == 'test_registry'
            assert tasks_db_id == 'test_tasks'
    
    def test_business_logic_consistency(self):
        """Test that the shared service provides consistent business logic."""
        service = NotionService()
        
        # Test hello_notion method
        result = service.hello_notion("TestUser")
        assert result['status_code'] == 200
        assert "Hello, TestUser" in result['message']
        
        # Test that the method returns the same format for both platforms
        assert 'status_code' in result
        assert 'message' in result
    
    @mock.patch('shared.notion_service.NotionDailyPlanner')
    def test_daily_plan_consistency(self, mock_planner_class):
        """Test that the daily plan logic is consistent across platforms."""
        with mock.patch.dict(os.environ, {
            'NOTION_API_KEY': 'test_key',
            'NOTION_REGISTRY_DB_ID': 'test_registry',
            'NOTION_TASKS_DB_ID': 'test_tasks'
        }):
            mock_planner = mock.MagicMock()
            mock_planner_class.return_value = mock_planner
            
            service = NotionService()
            result = service.run_daily_plan()
            
            # Verify the result format is consistent
            assert 'status_code' in result
            assert result['status_code'] == 200
            assert 'message' in result
            
            # Verify the underlying business logic is called
            mock_planner.run_daily_plan.assert_called_once()
    
    def test_error_handling_consistency(self):
        """Test that error handling is consistent across platforms."""
        service = NotionService()
        
        # Test missing environment variables
        with mock.patch.dict(os.environ, {}, clear=True):
            result = service.run_daily_plan()
            
            assert result['status_code'] == 400
            assert 'error' in result
            assert 'Missing Notion environment variables' in result['error']
    
    def test_logging_consistency(self):
        """Test that logging is set up consistently."""
        service = NotionService()
        
        # Verify that the service has a logger
        assert hasattr(service, 'logger')
        assert service.logger is not None
        
        # Verify that the logger is properly configured
        assert service.logger.name == 'shared.notion_service'

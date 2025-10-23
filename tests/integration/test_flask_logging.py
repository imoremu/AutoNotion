"""
Tests for Flask logging configuration in Vercel API routes.
"""
import unittest.mock as mock
import pytest
import os
from flask import Flask

from deployments.vercel.api.hello_notion import app as hello_app
from deployments.vercel.api.run_daily_plan import app as daily_plan_app
from deployments.vercel.api.scheduled_daily_plan import app as scheduled_app

class TestFlaskLogging:
    """Test Flask logging configuration for Vercel API routes."""
    
    def test_logging_configuration_loaded(self):
        """Test that logging configuration is properly loaded."""
        # Test that the apps can be created without errors
        assert hello_app is not None
        assert daily_plan_app is not None
        assert scheduled_app is not None
    
    @mock.patch.dict(os.environ, {'SERVICE_LOG_LEVEL': 'DEBUG'})
    def test_logging_with_debug_level(self):
        """Test logging configuration with DEBUG level."""
        # Re-import to get the new environment variable
        import importlib
        import deployments.vercel.api.hello_notion
        importlib.reload(deployments.vercel.api.hello_notion)
        
        # Test that the app still works
        with deployments.vercel.api.hello_notion.app.test_client() as client:
            response = client.get('/')
            assert response.status_code == 200
    
    @mock.patch.dict(os.environ, {'SERVICE_LOG_LEVEL': 'ERROR'})
    def test_logging_with_error_level(self):
        """Test logging configuration with ERROR level."""
        # Re-import to get the new environment variable
        import importlib
        import deployments.vercel.api.run_daily_plan
        importlib.reload(deployments.vercel.api.run_daily_plan)
        
        # Test that the app still works
        with deployments.vercel.api.run_daily_plan.app.test_client() as client:
            response = client.post('/')
            assert response.status_code == 200
    
    def test_logging_fallback_without_env_var(self):
        """Test logging fallback when no environment variable is set."""
        # Remove the environment variable
        with mock.patch.dict(os.environ, {}, clear=True):
            # Re-import to get the fallback configuration
            import importlib
            import deployments.vercel.api.scheduled_daily_plan
            importlib.reload(deployments.vercel.api.scheduled_daily_plan)
            
            # Test that the app still works
            with deployments.vercel.api.scheduled_daily_plan.app.test_client() as client:
                response = client.post('/')
                assert response.status_code == 200
    
    def test_logging_config_file_not_found(self):
        """Test logging fallback when config file is not found."""
        with mock.patch('os.path.exists', return_value=False):
            # Re-import to test fallback configuration
            import importlib
            import deployments.vercel.api.hello_notion
            importlib.reload(deployments.vercel.api.hello_notion)
            
            # Test that the app still works
            with deployments.vercel.api.hello_notion.app.test_client() as client:
                response = client.get('/')
                assert response.status_code == 200
    
    def test_logging_invalid_config_file(self):
        """Test logging fallback when config file is invalid."""
        with mock.patch('os.path.exists', return_value=True), \
             mock.patch('builtins.open', mock.mock_open(read_data='invalid json')):
            # Re-import to test fallback configuration
            import importlib
            import deployments.vercel.api.run_daily_plan
            importlib.reload(deployments.vercel.api.run_daily_plan)
            
            # Test that the app still works
            with deployments.vercel.api.run_daily_plan.app.test_client() as client:
                response = client.post('/')
                assert response.status_code == 200

"""
Shared business logic for both Azure Functions and Vercel deployments.
This module contains the core Notion service logic that can be used by both platforms.
"""
import datetime
import logging
import logging.config
import os
import json
from autonotion.notion_registry_daily_plan import NotionDailyPlanner

# Configure logging
def setup_logging():
    """Setup logging configuration for the shared service."""
    # Try different possible locations for logging config
    possible_configs = [
        os.path.join(os.path.dirname(__file__), "..", "logging_config.json"),
        os.path.join(os.path.dirname(__file__), "..", "config", "logging.json"),
        os.path.join(os.path.dirname(__file__), "..", "config", "logging_config.json")
    ]
    
    config_loaded = False
    for config_file in possible_configs:
        if os.path.exists(config_file):
            try:
                with open(config_file, "rt") as f:
                    config = json.load(f)
                logging.config.dictConfig(config)
                config_loaded = True
                break
            except Exception as e:
                print(f"Error loading logging config from {config_file}: {e}")
    
    if not config_loaded:
        # Fallback to basic logging with environment variable level (business-specific logging)
        log_level = os.environ.get('SERVICE_LOG_LEVEL', 'INFO').upper()
        log_level_value = getattr(logging, log_level, logging.INFO)
        
        logging.basicConfig(
            level=log_level_value,
            format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
            handlers=[logging.StreamHandler()]
        )
        print(f"Shared service logging fallback configured with level: {log_level}")

class NotionService:
    """Shared service class that can be used by both Azure Functions and Vercel."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        setup_logging()
    
    def get_environment_variables(self):
        """Get required environment variables for Notion API."""
        api_key = os.environ.get("NOTION_API_KEY")
        registry_db_id = os.environ.get("NOTION_REGISTRY_DB_ID")
        tasks_db_id = os.environ.get("NOTION_TASKS_DB_ID")
        
        if not all([api_key, registry_db_id, tasks_db_id]):
            self.logger.error("Missing Notion environment variables.")
            return None, None, None
            
        return api_key, registry_db_id, tasks_db_id
    
    def run_daily_plan(self):
        """Execute the daily plan logic."""
        self.logger.info('Starting daily plan execution.')
        
        api_key, registry_db_id, tasks_db_id = self.get_environment_variables()
        if not all([api_key, registry_db_id, tasks_db_id]):
            return {"error": "Missing Notion environment variables.", "status_code": 400}
        
        try:
            notion_daily_planner = NotionDailyPlanner(api_key, registry_db_id, tasks_db_id)
            notion_daily_planner.run_daily_plan()
            self.logger.info("Successfully completed daily plan.")
            return {"message": "Daily plan executed successfully.", "status_code": 200}
        except Exception as e:
            self.logger.error(f"An error occurred during daily plan execution: {e}")
            return {"error": f"An error occurred: {e}", "status_code": 500}
    
    def hello_notion(self, name=None):
        """Hello Notion endpoint logic."""
        self.logger.info('Hello Notion endpoint called.')
        
        if name:
            return {
                "message": f"Hello, {name}. This HTTP triggered function executed successfully.",
                "status_code": 200
            }
        else:
            return {
                "message": "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
                "status_code": 200
            }

"""
Vercel API route for manual daily plan execution.
Equivalent to the Azure Function ManualNotionDailyPlan.
"""
import logging
import logging.config
import os
import json
from flask import Flask, jsonify
from shared.notion_service import NotionService

# Setup logging for Vercel
def setup_vercel_logging():
    """Setup logging configuration for Vercel."""
    # Get log level from environment variable (business-specific logging)
    log_level = os.environ.get('SERVICE_LOG_LEVEL', 'DEBUG').upper()
    log_level_value = getattr(logging, log_level, logging.INFO)
    
    # Try to load Vercel-specific logging config
    config_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "logging_vercel.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "rt") as f:
                config = json.load(f)
            
            # Override log levels with environment variable
            for logger_name in config.get('loggers', {}):
                config['loggers'][logger_name]['level'] = log_level
            
            # Override root level
            if 'root' in config:
                config['root']['level'] = log_level
            
            # Override handler level
            for handler_name in config.get('handlers', {}):
                if 'level' in config['handlers'][handler_name]:
                    config['handlers'][handler_name]['level'] = log_level
            
            logging.config.dictConfig(config)
            print(f"Vercel logging configured with level: {log_level}")
            return
        except Exception as e:
            print(f"Error loading Vercel logging config: {e}")
    
    # Fallback to basic logging with environment variable level
    logging.basicConfig(
        level=log_level_value,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )
    print(f"Vercel logging fallback configured with level: {log_level}")

# Initialize logging
setup_vercel_logging()
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
@app.route('/api/run-daily-plan', methods=['GET', 'POST'])
def run_daily_plan():
    """Vercel API handler for manual daily plan execution."""
    logger.info("Manual daily plan execution started")
    
    try:
        service = NotionService()
        logger.info("NotionService initialized successfully")
        
        result = service.run_daily_plan()
        logger.info(f"Daily plan execution result: {result}")
        
        status_code = result['status_code']
        body = result.get('message', result.get('error', 'Unknown error'))
        return jsonify({'body': body}), status_code
        
    except Exception as e:
        logger.error(f"Error in run_daily_plan handler: {e}", exc_info=True)
        return jsonify({'body': f"Internal server error: {str(e)}"}), 500

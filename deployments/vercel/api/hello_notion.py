"""
Vercel API route for Hello Notion endpoint.
Equivalent to the Azure Function HelloNotion.
"""
import json
import logging
import logging.config
import os
from flask import Flask, request as flask_request, jsonify
from shared.notion_service import NotionService

# Setup logging for Vercel
def setup_vercel_logging():
    """Setup logging configuration for Vercel."""
    # Get log level from environment variable (business-specific logging)
    log_level = os.environ.get('SERVICE_LOG_LEVEL', 'INFO').upper()
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
@app.route('/api/hello-notion', methods=['GET', 'POST'])
def hello_notion():
    """Vercel API handler for Hello Notion endpoint."""
    logger.info("Hello Notion endpoint called")
    
    try:
        service = NotionService()
        logger.debug("NotionService initialized successfully")
        
        # Get name from query parameters or request body
        name = flask_request.args.get('name')
        if not name and flask_request.method == 'POST':
            try:
                data = flask_request.get_json()
                name = data.get('name') if data else None
                logger.debug(f"Body name: {name}")
            except Exception as e:
                logger.warning(f"Error parsing body: {e}")
                pass
        
        # If no name provided, use default
        if not name:
            name = "World"
            logger.debug("No name provided, using default: World")
        
        logger.debug(f"Processing request for name: {name}")
        result = service.hello_notion(name)
        logger.info(f"Service result: status={result['status_code']}")
        
        return jsonify({'body': result['message']}), result['status_code']
        
    except Exception as e:
        logger.error(f"Error in hello_notion handler: {e}", exc_info=True)
        return jsonify({'body': f"Internal server error: {str(e)}"}), 500

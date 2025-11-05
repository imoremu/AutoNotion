"""
Vercel API route for Hello Notion endpoint.
Equivalent to the Azure Function HelloNotion.
"""
import json
import logging
from flask import Flask, request as flask_request, jsonify
from shared.notion_service import NotionService

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

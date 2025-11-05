"""
Vercel API route for manual daily plan execution.
Equivalent to the Azure Function ManualNotionDailyPlan.
"""
import logging
from flask import Flask, jsonify
from shared.notion_service import NotionService

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

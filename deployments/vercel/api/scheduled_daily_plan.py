"""
Vercel API route for scheduled daily plan execution.
Equivalent to the Azure Function ScheduledNotionDailyPlan.
This endpoint is triggered by Vercel cron jobs.
"""
import logging
from flask import Flask, jsonify
from shared.notion_service import NotionService

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
@app.route('/api/scheduled-daily-plan', methods=['GET', 'POST'])
def scheduled_daily_plan():
    """Vercel API handler for scheduled daily plan execution."""
    logger.info("Scheduled daily plan execution started")
    
    try:
        service = NotionService()
        logger.info("NotionService initialized successfully")
        
        result = service.run_daily_plan()
        logger.info(f"Scheduled daily plan execution result: {result}")
        
        # For cron jobs, we log the result
        status_code = result['status_code']
        if status_code == 200:
            message = result.get('message', 'Daily plan executed successfully')
            logger.info(f"Scheduled daily plan completed: {message}")
            return jsonify({'body': message}), 200
        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"Scheduled daily plan failed: {error}")
            return jsonify({'body': error}), status_code
        
    except Exception as e:
        logger.error(f"Error in scheduled_daily_plan handler: {e}", exc_info=True)
        return jsonify({'body': f"Internal server error: {str(e)}"}), 500

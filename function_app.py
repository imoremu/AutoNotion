import azure.functions as func
import json
import logging
import logging.config
import os

from autonotion.notion_registry_daily_plan import NotionDailyPlanner

# Load logging configuration from external file.
config_file = os.path.join(os.path.dirname(__file__), "logging_config.json")
if os.path.exists(config_file):
    with open(config_file, "rt") as f:
        config = json.load(f)
    logging.config.dictConfig(config)
else:
    logging.basicConfig(level=logging.INFO)

# Use a module-level logger based on the module name.
logger = logging.getLogger(__name__)
logger.info("Custom logger configured via external file.")

app = func.FunctionApp()

@app.route(route="HelloNotion", auth_level=func.AuthLevel.ANONYMOUS)
def HelloNotion(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('Python HTTP trigger function processed a request in HelloNotion.')
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

@app.schedule(schedule="0 5 2 * * 1-5", arg_name="myTimer", run_on_startup=False)
def ScheduledNotionDailyPlan(myTimer: func.TimerRequest) -> None:
    logger.info('Timer trigger for CreateDefaultDailyNotionPlan started execution.')

    api_key = os.environ.get("NOTION_API_KEY")
    registry_db_id = os.environ.get("NOTION_REGISTRY_DB_ID")
    tasks_db_id = os.environ.get("NOTION_TASKS_DB_ID")
        
    if not all([api_key, registry_db_id, tasks_db_id]):
        logger.error("Missing Notion environment variables. Function cannot run.")
        return

    try:
        notion_daily_planner = NotionDailyPlanner(api_key, registry_db_id, tasks_db_id)
        notion_daily_planner.run_daily_plan()
        logger.info("Successfully completed CreateDefaultDailyNotionPlan.")
    except Exception as e:
        logger.error(f"An error occurred during CreateDefaultDailyNotionPlan: {e}")

@app.route(route="run-daily-plan", auth_level=func.AuthLevel.FUNCTION)
def ManualNotionDailyPlan(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('HTTP trigger for ManualNotionDailyPlan started.')

    api_key = os.environ.get("NOTION_API_KEY")
    registry_db_id = os.environ.get("NOTION_REGISTRY_DB_ID")
    tasks_db_id = os.environ.get("NOTION_TASKS_DB_ID")
        
    if not all([api_key, registry_db_id, tasks_db_id]):
        logger.error("Missing Notion environment variables. Function cannot run.")
        return func.HttpResponse("Missing Notion environment variables.", status_code=400)

    try:
        notion_daily_planner = NotionDailyPlanner(api_key, registry_db_id, tasks_db_id)
        notion_daily_planner.run_daily_plan()
        logger.info("Successfully completed ManualNotionDailyPlan.")
        return func.HttpResponse("Daily plan executed successfully.", status_code=200)
    except Exception as e:
        logger.error(f"An error occurred during manual execution: {e}")
        return func.HttpResponse(f"An error occurred: {e}", status_code=500)
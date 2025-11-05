import datetime
import logging
import requests
import os
from tenacity import retry, wait_fixed, stop_after_attempt

logger = logging.getLogger(__name__)

RETRY_WAIT_SECONDS = int(os.environ.get("RETRY_WAIT_SECONDS", 5))
RETRY_ATTEMPTS = int(os.environ.get("RETRY_ATTEMPTS", 3))

class NotionDailyPlanner:
    def __init__(self, api_key: str, registry_db_id: str, tasks_db_id: str):
        logger.debug("Initializing NotionDailyPlanner.")
        self.registry_db_id = registry_db_id
        self.tasks_db_id = tasks_db_id
                    
        self.existing_tasks_names = {}

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        logger.debug(f"Headers set to: {self.headers}")
        
        # Fetch the properties of the target registry database to ensure we only copy valid properties.
        self.registry_db_properties = self._get_db_properties(self.registry_db_id)

    def _get_db_properties(self, db_id: str) -> set:
        """Retrieves the set of property names for a given database."""
        logger.debug(f"Retrieving schema for database {db_id}")
        try:
            response = requests.get(f"https://api.notion.com/v1/databases/{db_id}", headers=self.headers, timeout=15)
            response.raise_for_status()
            properties = response.json().get("properties", {})
            property_names = set(properties.keys())
            logger.info(f"Found properties for database {db_id}: {property_names}")
            return property_names
        except Exception as e:
            logger.error(f"Failed to retrieve database properties for {db_id}: {e}", exc_info=True)
            # Return an empty set on failure to prevent errors, though copying will likely fail.
            return set()

    @retry(wait=wait_fixed(RETRY_WAIT_SECONDS), stop=stop_after_attempt(RETRY_ATTEMPTS))
    def _query_database(self, db_id: str, query_filter: dict):
        """
        Queries a specified Notion database using a provided filter.
        Returns a list of matching pages.
        """
        logger.debug(f"Querying database [{db_id}] with filter: {query_filter}")
        try:
            response = requests.post(
                f"https://api.notion.com/v1/databases/{db_id}/query",
                headers=self.headers,
                json=query_filter,
                timeout=15
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error during database query: {e}", exc_info=True)
            raise e

        result = response.json().get("results", [])
        logger.debug(f"Received {len(result)} results from database [{db_id}].")
        return result

    @retry(wait=wait_fixed(RETRY_WAIT_SECONDS), stop=stop_after_attempt(RETRY_ATTEMPTS))
    def _create_page(self, payload: dict):
        """
        Creates a page in Notion using the provided payload.
        """
        logger.debug(f"Creating new page with payload: {payload}")
        try:
            create_response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=self.headers,
                json=payload,
                timeout=15
            )
            create_response.raise_for_status()
        except Exception as e:
            logger.error(f"Error during page creation: {e}", exc_info=True)
            raise e

        logger.debug("Page creation successful.")
        return create_response
    
    @staticmethod    
    def _remap_date_to_today(date_obj: dict, today_date: datetime.date) -> dict:
        """
        Takes a Notion date object and remaps its date part to today,
        keeping the original time of day and timezone.
        """
        logger.debug(f"Remapping date object {date_obj} to today's date {today_date.isoformat()}")
        if not date_obj:
            logger.warning("No date object provided for remapping.")
            return None
    
        new_date = {}
    
        start_str = date_obj.get("start")
        if start_str:
            # Parse the full ISO string to get a timezone-aware datetime object.
            start_dt = datetime.datetime.fromisoformat(start_str)
            # Create a new datetime object by replacing the date parts but keeping time and timezone.
            new_start_dt = start_dt.replace(year=today_date.year, month=today_date.month, day=today_date.day)
            new_date["start"] = new_start_dt.isoformat()
            logger.debug(f"Remapped start date: {new_date['start']}")
        else:
            new_date["start"] = today_date.isoformat()
            logger.debug("Start date was missing; using today's date.")
    
        end_str = date_obj.get("end")
        if end_str:
            end_dt = datetime.datetime.fromisoformat(end_str)
            new_end_dt = end_dt.replace(year=today_date.year, month=today_date.month, day=today_date.day)
            new_date["end"] = new_end_dt.isoformat()
            logger.debug(f"Remapped end date: {new_date['end']}")
            
        return new_date

    def _get_todays_scheduled_task_names(self, today_date_str: str) -> set:
        """
        Queries the registry for all tasks scheduled for today and returns a set of their names
        for efficient duplicate checking.
        """
        logger.debug(f"Querying for all tasks already scheduled for today: {today_date_str}")
        query_filter = {
            "filter": {
                "or": [
                    {"property": "Horario", "date": {"equals": today_date_str}},
                    {"property": "Horario Planificado", "date": {"equals": today_date_str}}
                ]
            }
        }
        
        todays_tasks = self._query_database(self.registry_db_id, query_filter)
        
        task_names = set()
        for task in todays_tasks:
            props = task.get("properties", {})
            task_title = props.get("Nombre", {}).get("title", [{}])
            if task_title and task_title[0].get("plain_text"):
                task_names.add(task_title[0]["plain_text"])
        
        logger.info(f"Found {len(task_names)} tasks already scheduled for today. Will skip duplicating these.")
        return task_names

    @staticmethod
    def _copy_writable_properties(source_properties: dict, target_properties: set) -> dict:
        """
        Copies properties from a source page, filtering out read-only types and 
        properties that do not exist in the target database. Also sanitizes values.
        """
        read_only_types = [
            "formula", "rollup", "created_by", "created_time", 
            "last_edited_by", "last_edited_time"
        ]

        new_properties = {}
        
        for key, prop in source_properties.items():
            if key not in target_properties:
                continue

            prop_type = prop.get("type")
            if prop_type in read_only_types:
                continue

            # Sanitize the property value to include only writable fields.
            # The Notion API response for a property contains read-only fields (like 'id')
            # that are invalid in a create/update request.
            if prop_type == "title" and prop.get("title"):
                new_properties[key] = {"title": [{"text": {"content": p["text"]["content"]}} for p in prop["title"]]}
            elif prop_type == "rich_text" and prop.get("rich_text"):
                 new_properties[key] = {"rich_text": [{"text": {"content": p["text"]["content"]}} for p in prop["rich_text"]]}
            elif prop_type == "number" and prop.get("number") is not None:
                new_properties[key] = {"number": prop["number"]}
            elif prop_type == "select" and prop.get("select"):
                new_properties[key] = {"select": {"name": prop["select"]["name"]}}
            elif prop_type == "multi_select" and prop.get("multi_select"):
                new_properties[key] = {"multi_select": [{"name": p["name"]} for p in prop["multi_select"]]}
            elif prop_type == "date" and prop.get("date"):
                # Sanitize the date object to remove read-only keys like 'time_zone'.
                date_value = prop["date"]
                sanitized_date = {"start": date_value.get("start")}
                if date_value.get("end"):
                    sanitized_date["end"] = date_value.get("end")
                new_properties[key] = {"date": sanitized_date}
            elif prop_type == "checkbox": # Checkbox can be null
                new_properties[key] = {"checkbox": prop["checkbox"]}
            elif prop_type == "url" and prop.get("url"):
                new_properties[key] = {"url": prop["url"]}
            elif prop_type == "email" and prop.get("email"):
                new_properties[key] = {"email": prop["email"]}
            # Add other property types here as needed (e.g., relation, files, etc.)

        return new_properties

    def _build_new_page_payload(self, source_task: dict, task_name: str, planned_date: dict = None) -> dict:
        """
        Builds the JSON payload for creating a new page in the registry database.

        This method centralizes the logic for:
        - Copying writable properties from a source task.
        - Setting the new task's name.
        - Creating a relation back to the source task.
        - Setting the planned date and time.
        """
        source_properties = source_task.get("properties", {})
        
        # First, copy all other matching writable properties from the source.
        new_properties = self._copy_writable_properties(source_properties, self.registry_db_properties)

        # Now, explicitly set or overwrite the core properties for the new task.
        new_properties["Nombre"] = {"title": [{"text": {"content": task_name}}]}
        
        # Handle the 'Tarea' relation intelligently.
        if "Tarea" in self.registry_db_properties:
            # If the source already has a 'Tarea' relation (i.e., it's an unfinished task from the registry), copy it.
            if "Tarea" in source_properties and source_properties["Tarea"].get("relation"):
                new_properties["Tarea"] = {"relation": source_properties["Tarea"]["relation"]}
            # Otherwise (i.e., it's a periodic task from the main tasks DB), create a new relation to it.
            else:
                new_properties["Tarea"] = {"relation": [{"id": source_task["id"]}]}

        if planned_date:
            new_properties["Horario Planificado"] = {"date": planned_date}

        # Ensure the old 'Horario' property is not carried over.
        new_properties.pop("Horario", None)

        return {"parent": {"database_id": self.registry_db_id}, "properties": new_properties}

    @staticmethod
    def _get_multi_select_values(prop: dict) -> list[str]:
        """Extracts all selected option names from a Notion multi-select property."""
        if not prop or "multi_select" not in prop:
            return []
        return [item.get("name") for item in prop["multi_select"]]

    @staticmethod
    def _get_week_of_month(date: datetime.date) -> int:
        """Calculates the week number of a day within its month (e.g., 1st, 2nd, 3rd...)."""
        return (date.day - 1) // 7 + 1

    def _is_task_scheduled_for_today(self, task_props: dict, today: datetime.date) -> bool:
        """
        Checks if a periodic task is scheduled to run today based on its properties.
        Handles multi-select properties for scheduling rules.
        """
        periodicities = self._get_multi_select_values(task_props.get("Periodicidad", {}))
        if not periodicities:
            return False

        task_name = task_props.get('Nombre', {}).get('title', [{}])[0].get('plain_text', 'Unknown Task')
        logger.debug(f"Checking periodicities {periodicities} for task '{task_name}'")

        for periodicity in periodicities:
            if periodicity == "Diaria":
                return True

            if periodicity == "Semanal":
                # Notion: Monday=1, Sunday=7. isoweekday() matches this.
                days_of_week = self._get_multi_select_values(task_props.get("Día de la semana", {}))
                if str(today.isoweekday()) in days_of_week:
                    return True

            if periodicity == "Mensual":
                days_of_month = self._get_multi_select_values(task_props.get("Día del mes", {}))
                # Case 1: Specific day of the month (e.g., "15")
                if str(today.day) in days_of_month:
                    return True

                # Case 2: Week-based scheduling (e.g., "first" "Monday")
                weeks_of_month = self._get_multi_select_values(task_props.get("Semana del mes", {}))
                days_of_week = self._get_multi_select_values(task_props.get("Día de la semana", {}))

                if weeks_of_month and days_of_week:
                    today_week_num = self._get_week_of_month(today)
                    week_map = {"1ª": 1, "2ª": 2, "3ª": 3, "4ª": 4}
                    
                    # Check for "last" week
                    if "Última" in weeks_of_month:
                        # Check if today is in the last 7 days of the month
                        last_day_of_month = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
                        if today.day > last_day_of_month.day - 7 and str(today.isoweekday()) in days_of_week:
                            return True

                    # Check for numbered weeks (1st, 2nd, 3rd, 4th)
                    for week_name, week_num in week_map.items():
                        if week_name in weeks_of_month and today_week_num == week_num and str(today.isoweekday()) in days_of_week:
                            return True

            if periodicity == "Anual":
                months = self._get_multi_select_values(task_props.get("Mes", {}))
                days_of_month = self._get_multi_select_values(task_props.get("Día del mes", {}))
                if str(today.month) in months and str(today.day) in days_of_month:
                    return True

        return False

    def generate_periodic_tasks(self):
        """
        Queries the main tasks DB for periodic tasks and creates them in the registry if they are scheduled for today.
        """
        logger.info("Starting periodic task generation.")
        today = datetime.date.today()
        today_str = today.isoformat()

        query_filter = {"filter": {"property": "Tipo", "select": {"equals": "Periódica"}}}
        
        periodic_tasks = self._query_database(self.tasks_db_id, query_filter)
        logger.info(f"Found {len(periodic_tasks)} periodic tasks in the main tasks database.")

        for task in periodic_tasks:
            props = task.get("properties", {})            
            
            task_title = props.get("Nombre", {}).get("title", [{}])
                        
            task_name = task_title[0].get("plain_text") if task_title else None

            logger.debug(f"Processing periodic task with title property: {task_name}")

            if not task_name or task_name in self.existing_tasks_names[today_str]:
                if task_name: logger.info(f"Skipping periodic task '{task_name}' as it already exists for today.")
                continue

            if self._is_task_scheduled_for_today(props, today):
                logger.info(f"Periodic task '{task_name}' is scheduled for today. Creating it.")

                # Check for an example time in the 'Hora' property.
                new_planned_date = None
                time_template_obj = props.get("Hora", {}).get("date")
                if time_template_obj:
                    logger.debug(f"Found time template for '{task_name}'. Remapping to today.")
                    new_planned_date = self._remap_date_to_today(time_template_obj, today)
                
                new_page_payload = self._build_new_page_payload(task, task_name, new_planned_date)
                self._create_page(new_page_payload)

    def duplicate_unfinished_tasks_for_today(self):
        """
        Queries Notion for unfinished tasks from yesterday
        and duplicates them for today with the original time.
        """        
        logger.info("Starting duplicate_unfinished_tasks_for_today.")
        today = datetime.date.today()
        today_str = today.isoformat()

        yesterday_str = (today - datetime.timedelta(days=1)).isoformat()
        logger.debug(f"Today's date: {today.isoformat()}, Yesterday's date: {yesterday_str}")

        query_filter = {
            "filter": {
                "and": [
                    {
                        "not": {
                            "or": [
                                {"property": "Estado", "status": {"equals": "Finalizada"}},
                                {"property": "Estado", "status": {"equals": "Cancelada"}}
                            ]
                        }
                    },
                    {
                        "or": [
                            {"property": "Horario", "date": {"equals": yesterday_str}},                            
                            {"property": "Horario Planificado", "date": {"equals": yesterday_str}}
                        ]
                    }
                ]
            }
        }
        
        logger.debug(f"Constructed query filter: {query_filter}")
        
        tasks_to_duplicate = self._query_database(self.registry_db_id, query_filter)
        
        logger.info(f"Found {len(tasks_to_duplicate)} tasks to duplicate.")

        if not tasks_to_duplicate:
            logger.info("No unfinished tasks from yesterday found to duplicate.")
            return
    
        for task in tasks_to_duplicate:
            props = task.get("properties", {})
            task_title = props.get("Nombre", {}).get("title", [{}])
            task_name = task_title[0].get("plain_text") if task_title else None
            logger.debug(f"Processing task: {task_name}")

            source_date_obj = None
            if props.get("Horario", {}).get("date"):
                source_date_obj = props["Horario"]["date"]
                logger.debug("Using 'Horario' date for remapping.")
            elif props.get("Horario Planificado", {}).get("date"):
                source_date_obj = props["Horario Planificado"]["date"]
                logger.debug("Using 'Horario Planificado' date for remapping.")

            if not task_name or not source_date_obj:
                logger.warning(f"Skipping task due to missing task name or date. Task name: {task_name}")
                continue            

            # Check against the in-memory set of today's tasks.
            if task_name in self.existing_tasks_names[today.isoformat()]:
                logger.info(f"Task '{task_name}' for today already exists. Skipping duplication.")
                continue

            new_planned_date = NotionDailyPlanner._remap_date_to_today(source_date_obj, today)
            logger.debug(f"New planned date for task [{task_name}]: {new_planned_date}")

            new_page_payload = self._build_new_page_payload(task, task_name, new_planned_date)
            
            self.existing_tasks_names[today.isoformat()].add(task_name)

            logger.info(f"Duplicating task from yesterday: '{task_name}'")
            self._create_page(new_page_payload)

    def add_alerted_objective_tasks(self):
        """
        Queries the main tasks DB for objetivo/puntual tasks that have an alert date
        less than or equal to today and are not completed, then adds them to today's registry.
        """
        logger.info("Starting add_alerted_objective_tasks.")
        today = datetime.date.today()
        today_str = today.isoformat()

        # Query for non-periodic tasks with alert date <= today and not completed
        query_filter = {
            "filter": {
                "and": [
                    {"property": "Tipo", "select": {"does_not_equal": "Periódica"}},
                    {"property": "Estado", "status": {"does_not_equal": "Completada"}},
                    {"property": "Fecha de Alerta", "date": {"on_or_before": today_str}}
                ]
            }
        }

        logger.debug(f"Constructed query filter for alerted tasks: {query_filter}")
        
        alerted_tasks = self._query_database(self.tasks_db_id, query_filter)
        
        logger.info(f"Found {len(alerted_tasks)} alerted objetivo/puntual tasks.")

        if not alerted_tasks:
            logger.info("No alerted objetivo/puntual tasks found.")
            return

        for task in alerted_tasks:
            props = task.get("properties", {})
            task_title = props.get("Nombre", {}).get("title", [{}])
            task_name = task_title[0].get("plain_text") if task_title else None
            
            if not task_name:
                logger.warning("Skipping task due to missing task name.")
                continue

            logger.debug(f"Processing alerted task: {task_name}")

            # Check against the in-memory set of today's tasks.
            if task_name in self.existing_tasks_names[today_str]:
                logger.info(f"Task '{task_name}' for today already exists. Skipping addition.")
                continue

            # Check for an example time in the 'Hora' property.
            new_planned_date = None
            time_template_obj = props.get("Hora", {}).get("date")
            if time_template_obj:
                logger.debug(f"Found time template for '{task_name}'. Remapping to today.")
                new_planned_date = self._remap_date_to_today(time_template_obj, today)
            else:
                logger.debug(f"No time template found for '{task_name}'. Setting to all-day.")
                new_planned_date = {"start": today_str}

            new_page_payload = self._build_new_page_payload(task, task_name, new_planned_date)

            self.existing_tasks_names[today_str].add(task_name)
            
            logger.info(f"Adding alerted objetivo/puntual task: '{task_name}'")
            self._create_page(new_page_payload)

    def run_daily_plan(self):
        """Orchestrates the execution of the full daily plan."""
        logger.info("--- Running Notion Daily Plan ---")
        # Run unfinished task duplication first to give it priority.
        
        today = datetime.date.today()
        today_str = today.isoformat()

        self.existing_tasks_names[today_str] = self._get_todays_scheduled_task_names(today_str)

        self.duplicate_unfinished_tasks_for_today()
        self.generate_periodic_tasks()
        self.add_alerted_objective_tasks()
        logger.info("--- Notion Daily Plan Finished ---")
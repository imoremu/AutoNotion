import datetime
import logging
import os

import requests
from tenacity import retry, wait_fixed, stop_after_attempt
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

RETRY_WAIT_SECONDS = int(os.environ.get("RETRY_WAIT_SECONDS", 5))
RETRY_ATTEMPTS = int(os.environ.get("RETRY_ATTEMPTS", 3))

class NotionDailyPlanner:
    def __init__(self, api_key: str, registry_db_id: str, tasks_db_id: str):
        logger.debug("Initializing NotionDailyPlanner.")
        self.registry_db_id = registry_db_id
        self.tasks_db_id = tasks_db_id
                    
        self.existing_tasks_names = {}

        tz_str = os.environ.get("NOTION_TIMEZONE")
        if tz_str:
            try:
                self.timezone = ZoneInfo(tz_str)
                logger.info(f"Using timezone from NOTION_TIMEZONE environment variable: {tz_str}")
            except Exception:
                logger.warning(f"NOTION_TIMEZONE variable '{tz_str}' is invalid. Falling back to server timezone.")
                self.timezone = datetime.datetime.now().astimezone().tzinfo
        else:
            logger.info("NOTION_TIMEZONE variable not set. Using server timezone.")
            self.timezone = datetime.datetime.now().astimezone().tzinfo

        logger.debug(f"Selected timezone: {self.timezone}")

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        logger.debug(f"Headers set to: {self.headers}")

        # Fetch the properties of the target registry database to ensure we only copy valid properties.
        self.registry_db_properties = self._get_db_properties(self.registry_db_id)

    def _build_planned_datetime(
        self,
        today: datetime.date,
        start_time_str: str | None,
        end_time_str: str | None,
        task_name: str,
    ) -> dict:
        planned = {}

        try:
            if start_time_str:
                start_time = datetime.time.fromisoformat(start_time_str)
                new_start_dt = datetime.datetime.combine(today, start_time, tzinfo=self.timezone)
                planned["start"] = new_start_dt.isoformat()
                logger.debug(f"Using start time '{start_time_str}' for '{task_name}'")

                if end_time_str:
                    end_time = datetime.time.fromisoformat(end_time_str)
                    new_end_dt = datetime.datetime.combine(today, end_time, tzinfo=self.timezone)
                    planned["end"] = new_end_dt.isoformat()
                    logger.debug(f"Using end time '{end_time_str}' for '{task_name}'")
            else:
                logger.debug(f"No start time found for '{task_name}'. Setting to 12:00.")
                start_of_day = datetime.datetime(today.year, today.month, today.day, 12, 0, 0, tzinfo=self.timezone)
                planned = {"start": start_of_day.isoformat()}
        except ValueError as e:
            logger.warning(
                f"Invalid time format in '{task_name}' (Start: '{start_time_str}', End: '{end_time_str}'). "
                f"Using 00:00. Error: {e}"
            )
            start_of_day = datetime.datetime(today.year, today.month, today.day, 12, 0, 0, tzinfo=self.timezone)
            planned = {"start": start_of_day.isoformat()}

        return planned

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
        except requests.HTTPError as e:
            try:
                error_body = e.response.json()
            except Exception:
                error_body = e.response.text if e.response is not None else "No response body"
            logger.error(
                "Error during database query: %s | status=%s | body=%s",
                e,
                e.response.status_code if e.response is not None else "unknown",
                error_body,
                exc_info=True,
            )
            raise e
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
    
    def _get_todays_scheduled_task_names(self, today_date_str: str) -> set:
        """
        Queries the registry for all tasks scheduled for today and returns a set of their names
        for efficient duplicate checking.
        """
        logger.debug(f"Querying for all tasks already scheduled for today: {today_date_str}")
        today_date = datetime.date.fromisoformat(today_date_str)
        today_start_dt = datetime.datetime.combine(today_date, datetime.time.min, tzinfo=self.timezone)
        tomorrow_start_dt = datetime.datetime.combine(today_date + datetime.timedelta(days=1), datetime.time.min, tzinfo=self.timezone)
        today_start_iso = today_start_dt.isoformat()
        tomorrow_start_iso = tomorrow_start_dt.isoformat()

        def _range_filter(property_name: str) -> dict:
            return {
                "and": [
                    {"property": property_name, "date": {"on_or_after": today_start_iso}},
                    {"property": property_name, "date": {"before": tomorrow_start_iso}}
                ]
            }

        query_filter = {
            "filter": {
                "or": [
                    _range_filter("Horario"),
                    _range_filter("Horario Planificado")
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

        if today_str not in self.existing_tasks_names:
            self.existing_tasks_names[today_str] = self._get_todays_scheduled_task_names(today_str)

        query_filter = {"filter": {"property": "Tipo", "select": {"equals": "Periódica"}}}
        
        periodic_tasks = self._query_database(self.tasks_db_id, query_filter)
        logger.info(f"Found {len(periodic_tasks)} periodic tasks in the main tasks database.")

        for task in periodic_tasks:
            props = task.get("properties", {})            
            
            task_title = props.get("Nombre", {}).get("title", [{}])
                        
            task_name = task_title[0].get("plain_text") if task_title else None

            logger.debug(f"Processing periodic task with title property: {task_name}")

            if not task_name or (today_str in self.existing_tasks_names and task_name in self.existing_tasks_names[today_str]):
                if task_name: logger.info(f"Skipping periodic task '{task_name}' as it already exists for today.")
                continue

            if self._is_task_scheduled_for_today(props, today):
                logger.info(f"Periodic task '{task_name}' is scheduled for today. Creating it.")

                start_prop = props.get("Hora Inicio", {}).get("rich_text", [])
                end_prop = props.get("Hora Fin", {}).get("rich_text", [])

                start_time_str = start_prop[0].get("plain_text") if start_prop else None
                end_time_str = end_prop[0].get("plain_text") if end_prop else None

                new_planned_date = self._build_planned_datetime(today, start_time_str, end_time_str, task_name)
                
                new_page_payload = self._build_new_page_payload(task, task_name, new_planned_date)
                self._create_page(new_page_payload)
                self.existing_tasks_names.setdefault(today_str, set()).add(task_name)

    def duplicate_unfinished_tasks_for_today(self):
        """
        Queries Notion for unfinished tasks from yesterday
        and duplicates them for today with the original time.
        """        
        logger.info("Starting duplicate_unfinished_tasks_for_today.")
        today = datetime.date.today()
        today_str = today.isoformat()

        yesterday_date = today - datetime.timedelta(days=1)
        yesterday_start_dt = datetime.datetime.combine(yesterday_date, datetime.time.min, tzinfo=self.timezone)
        today_start_dt = datetime.datetime.combine(today, datetime.time.min, tzinfo=self.timezone)
        yesterday_start_iso = yesterday_start_dt.isoformat()
        today_start_iso = today_start_dt.isoformat()
        logger.debug(f"Today's date: {today_start_iso}, Yesterday's date: {yesterday_start_iso}")

        if today_str not in self.existing_tasks_names:
            self.existing_tasks_names[today_str] = self._get_todays_scheduled_task_names(today_str)

        # Note: Notion does not support three level nesting in the filter object, so we have to use an 'or' with two 'and' objects.
        query_filter = {
            "filter": {
                "or": [
                    {
                        "and": [
                            {"property": "Estado", "status": {"does_not_equal": "Finalizada"}},
                            {"property": "Estado", "status": {"does_not_equal": "Cancelada"}},
                            {"property": "Horario", "date": {"on_or_after": yesterday_start_iso}},
                            {"property": "Horario", "date": {"before": today_start_iso}}
                        ]
                    },
                    {
                        "and": [
                            {"property": "Estado", "status": {"does_not_equal": "Finalizada"}},
                            {"property": "Estado", "status": {"does_not_equal": "Cancelada"}},
                            {"property": "Horario Planificado", "date": {"on_or_after": yesterday_start_iso}},
                            {"property": "Horario Planificado", "date": {"before": today_start_iso}}
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
            
            source_date_obj = None
            task_date_str = "No Date Found"

            horario_date = props.get("Horario", {}).get("date")
            planificado_date = props.get("Horario Planificado", {}).get("date")

            if horario_date:
                source_date_obj = horario_date
                task_date_str = horario_date.get("start", "No Start Date")
                logger.debug("Using 'Horario' date for remapping.")
            elif planificado_date:
                source_date_obj = planificado_date
                task_date_str = planificado_date.get("start", "No Start Date")
                logger.debug("Using 'Horario Planificado' date for remapping.")

            logger.debug(f"Processing task: {task_name} (Task Date: {task_date_str})")

            if not task_name or not source_date_obj:
                logger.warning(f"Skipping task due to missing task name or date. Task name: {task_name}")
                continue            

            # Check against the in-memory set of today's tasks.
            if today.isoformat() in self.existing_tasks_names and task_name in self.existing_tasks_names[today.isoformat()]:
                logger.info(f"Task '{task_name}' for today already exists. Skipping duplication.")
                continue

            start_dt = datetime.datetime.fromisoformat(source_date_obj["start"])
            if start_dt.tzinfo is None:
                start_time_str = start_dt.time().isoformat(timespec="minutes")
            else:
                start_time_str = start_dt.astimezone(self.timezone).time().isoformat(timespec="minutes")

            end_time_str = None
            if source_date_obj.get("end"):
                end_dt = datetime.datetime.fromisoformat(source_date_obj["end"])
                if end_dt.tzinfo is None:
                    end_time_str = end_dt.time().isoformat(timespec="minutes")
                else:
                    end_time_str = end_dt.astimezone(self.timezone).time().isoformat(timespec="minutes")

            new_planned_date = self._build_planned_datetime(today, start_time_str, end_time_str, task_name)

            logger.debug(f"New planned date for task [{task_name}]: {new_planned_date}")

            new_page_payload = self._build_new_page_payload(task, task_name, new_planned_date)
            
            # Update existing_tasks_names if it exists (e.g., when called from run_daily_plan)
            self.existing_tasks_names.setdefault(today.isoformat(), set()).add(task_name)

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

        if today_str not in self.existing_tasks_names:
            self.existing_tasks_names[today_str] = self._get_todays_scheduled_task_names(today_str)

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
            if today_str in self.existing_tasks_names and task_name in self.existing_tasks_names[today_str]:
                logger.info(f"Task '{task_name}' for today already exists. Skipping addition.")
                continue

            start_prop = props.get("Hora Inicio", {}).get("rich_text", [])
            end_prop = props.get("Hora Fin", {}).get("rich_text", [])

            start_time_str = start_prop[0].get("plain_text") if start_prop else None
            end_time_str = end_prop[0].get("plain_text") if end_prop else None

            new_planned_date = self._build_planned_datetime(today, start_time_str, end_time_str, task_name)

            new_page_payload = self._build_new_page_payload(task, task_name, new_planned_date)

            # Update existing_tasks_names if it exists (e.g., when called from run_daily_plan)
            self.existing_tasks_names.setdefault(today_str, set()).add(task_name)
            
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
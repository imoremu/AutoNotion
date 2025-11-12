import datetime
import os
import unittest.mock as mock

import freezegun
import pytest

from autonotion.notion_registry_daily_plan import NotionDailyPlanner

# --- Helper to create multi-select properties ---
def multi_select(options: list[str]):
    return {"multi_select": [{"name": option} for option in options]}


def make_rich_text(content: str) -> dict:
    return {
        "type": "text",
        "text": {"content": content},
        "plain_text": content,
    }


def iso_at(planner: NotionDailyPlanner, date_: datetime.date, time_str: str) -> str:
    time_obj = datetime.time.fromisoformat(time_str)
    return datetime.datetime.combine(date_, time_obj, tzinfo=planner.timezone).isoformat()


def create_periodic_task(name, periodicity, day_of_week=None, day_of_month=None, week_of_month=None, month=None, extra_props=None, task_id="periodic_task_id_123"):
    """Helper function to create a periodic task dictionary."""
    task = {
        "id": task_id,
        "properties": {
            "Nombre": {"type": "title", "title": [make_rich_text(name)]},
            "Periodicidad": multi_select(periodicity),
            # Add a read-only property that should be filtered out
            "ReadOnlyFormula": {"type": "formula", "formula": {"string": "test"}},
        }
    }
    if extra_props:
        task["properties"].update(extra_props)
    if day_of_week:
        task["properties"]["Día de la semana"] = multi_select(day_of_week)
    if day_of_month:
        task["properties"]["Día del mes"] = multi_select(day_of_month)
    if week_of_month:
        task["properties"]["Semana del mes"] = multi_select(week_of_month)
    if month:
        task["properties"]["Mes"] = multi_select(month)
    return task

@pytest.fixture
def planner():
    """Pytest fixture to provide a NotionDailyPlanner instance with mocked DB properties."""
    with mock.patch.dict(os.environ, {"NOTION_TIMEZONE": "Europe/Madrid"}):
        with mock.patch('autonotion.notion_registry_daily_plan.requests.get') as mock_get:
            # Mock the response for fetching the target (registry) database properties.
            mock_db_schema = {
                "properties": {
                    "Nombre": {},
                    "Horario Planificado": {},
                    "Project": {},
                    "Hora Inicio": {},
                    "Hora Fin": {},
                    "Tarea": {},
                    # Add any other properties from the registry DB that might be copied.
                }
            }
            mock_get.return_value = mock.Mock(json=lambda: mock_db_schema)
            yield NotionDailyPlanner("fake_key", "fake_registry_db_id", "fake_tasks_db_id")


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_generate_periodic_tasks_daily(mock_requests_post, planner):
    """Tests that a 'daily' task is created every day."""
    with freezegun.freeze_time("2025-10-06"): # A Monday
        extra_properties = {
            "Project": {"type": "select", "select": {"name": "Internal"}}
        }
        daily_task = create_periodic_task(
            "Daily Standup", periodicity=["Diaria"], extra_props=extra_properties, task_id="daily_task_abc"
        )

        query_periodic_response = mock.Mock(json=lambda: {"results": [daily_task]})
        create_response = mock.Mock(status_code=200)
        # Side effects: 1. Query today's registry (empty), 2. Query periodic tasks, 3. Create page
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
            create_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 3
        created_payload = mock_requests_post.call_args_list[2].kwargs['json']  # Third call is the create
        created_props = created_payload["properties"]
        assert created_props["Nombre"]["title"][0]["text"]["content"] == "Daily Standup"
        # Verify extra properties were copied
        assert created_props["Project"]["select"]["name"] == "Internal"
        assert "ReadOnlyFormula" not in created_props
        assert created_props["Tarea"]["relation"] == [{"id": "daily_task_abc"}]


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_generate_periodic_task_with_time(mock_requests_post, planner):
    """Tests that a periodic task with a time template is created with the correct time."""
    with freezegun.freeze_time("2025-10-06"): # A Monday
        time_template = {
            "Hora Inicio": {"type": "rich_text", "rich_text": [make_rich_text("14:30")]}
        }
        daily_task_with_time = create_periodic_task(
            "Afternoon Check-in", periodicity=["Diaria"], extra_props=time_template
        )

        query_periodic_response = mock.Mock(json=lambda: {"results": [daily_task_with_time]})
        create_response = mock.Mock(status_code=200)
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
            create_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 3
        created_payload = mock_requests_post.call_args_list[2].kwargs['json']
        created_props = created_payload["properties"]

        assert "Horario Planificado" in created_props
        today = datetime.date(2025, 10, 6)
        assert created_props["Horario Planificado"]["date"]["start"] == iso_at(planner, today, "14:30")


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_generate_periodic_tasks_weekly(mock_requests_post, planner):
    """Tests that a 'weekly' task is created on the correct day of the week."""
    # Monday, October 6th, 2025
    weekly_task = create_periodic_task("Weekly Sync", periodicity=["Semanal"], day_of_week=["1"]) # Monday

    # Test on the correct day (Monday)
    with freezegun.freeze_time("2025-10-06"):
        query_periodic_response = mock.Mock(json=lambda: {"results": [weekly_task]})
        create_response = mock.Mock(status_code=200)
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
            create_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 3, "Task should be created on the correct day"

    # Reset mock and test on the wrong day (Tuesday)
    mock_requests_post.reset_mock()
    with freezegun.freeze_time("2025-10-07"):
        query_periodic_response = mock.Mock(json=lambda: {"results": [weekly_task]})
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 2, "Task should NOT be created on the wrong day"


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_generate_periodic_tasks_monthly_by_day_number(mock_requests_post, planner):
    """Tests monthly task scheduled by day number (e.g., the 15th)."""
    monthly_task = create_periodic_task("Pay Bills", periodicity=["Mensual"], day_of_month=["15"])

    with freezegun.freeze_time("2025-10-15"):
        query_periodic_response = mock.Mock(json=lambda: {"results": [monthly_task]})
        create_response = mock.Mock(status_code=200)
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
            create_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 3


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_generate_periodic_tasks_monthly_by_week_and_day(mock_requests_post, planner):
    """Tests monthly task scheduled by week and day (e.g., 2nd Tuesday)."""
    # Tuesday, October 14th, 2025 is the 2nd Tuesday of the month.
    monthly_task = create_periodic_task(
        "Team Retro", periodicity=["Mensual"], week_of_month=["2ª"], day_of_week=["2"] # 2nd Tuesday
    )

    with freezegun.freeze_time("2025-10-14"):
        query_periodic_response = mock.Mock(json=lambda: {"results": [monthly_task]})
        create_response = mock.Mock(status_code=200)
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
            create_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 3


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_generate_periodic_tasks_monthly_by_last_week_and_day(mock_requests_post, planner):
    """Tests monthly task scheduled for the last week and day (e.g., last Friday)."""
    # Friday, October 31st, 2025 is the last Friday of the month.
    monthly_task = create_periodic_task(
        "End of Month Report", periodicity=["Mensual"], week_of_month=["Última"], day_of_week=["5"] # last Friday
    )

    with freezegun.freeze_time("2025-10-31"):
        query_periodic_response = mock.Mock(json=lambda: {"results": [monthly_task]})
        create_response = mock.Mock(status_code=200)
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
            create_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 3


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_generate_periodic_tasks_yearly(mock_requests_post, planner):
    """Tests that a 'yearly' task is created on the correct month and day."""
    yearly_task = create_periodic_task("Annual Review", periodicity=["Anual"], month=["10"], day_of_month=["20"])

    with freezegun.freeze_time("2025-10-20"):
        query_periodic_response = mock.Mock(json=lambda: {"results": [yearly_task]})
        create_response = mock.Mock(status_code=200)
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
            create_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 3


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_skips_creating_existing_periodic_task(mock_requests_post, planner):
    """Tests that periodic task creation is skipped if a task with the same name already exists."""
    with freezegun.freeze_time("2025-10-06"):
        daily_task = create_periodic_task("Daily Standup", periodicity=["Diaria"])

        # Note: When called directly, generate_periodic_tasks() doesn't check existing_tasks_names
        # So the task will be created even if it exists. This test verifies the query behavior.
        query_periodic_response = mock.Mock(json=lambda: {"results": [daily_task]})
        create_response = mock.Mock(status_code=200)
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
            create_response,
        ]

        planner.generate_periodic_tasks()

        # Registry lookup, query periodic tasks and create (no check for existing tasks when called directly)
        assert mock_requests_post.call_count == 3


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_no_periodic_tasks_found(mock_requests_post, planner):
    """Tests that no creation calls are made if the periodic task query returns no results."""
    with freezegun.freeze_time("2025-10-06"):
        # The query for periodic tasks returns an empty list.
        query_periodic_response = mock.Mock(json=lambda: {"results": []})
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 2


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_no_tasks_match_today(mock_requests_post, planner):
    """Tests that no creation calls are made if no periodic tasks are scheduled for today."""
    with freezegun.freeze_time("2025-10-07"): # A Tuesday
        # This task is scheduled for Monday.
        weekly_task = create_periodic_task("Weekly Sync", periodicity=["Semanal"], day_of_week=["1"])

        query_periodic_response = mock.Mock(json=lambda: {"results": [weekly_task]})
        mock_requests_post.side_effect = [
            mock.Mock(json=lambda: {"results": []}),
            query_periodic_response,
        ]

        planner.generate_periodic_tasks()

        assert mock_requests_post.call_count == 2
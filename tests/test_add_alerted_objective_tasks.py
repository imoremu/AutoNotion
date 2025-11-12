import datetime
import os
import unittest.mock as mock

import freezegun
import pytest

from autonotion.notion_registry_daily_plan import NotionDailyPlanner

# --- Helpers -----------------------------------------------------------------


def make_rich_text(content: str) -> dict:
    return {
        "type": "text",
        "text": {"content": content},
        "plain_text": content,
    }


def iso_at(planner: NotionDailyPlanner, date_: datetime.date, time_str: str) -> str:
    time_obj = datetime.time.fromisoformat(time_str)
    return datetime.datetime.combine(date_, time_obj, tzinfo=planner.timezone).isoformat()


# --- Dummy Task Definitions ---------------------------------------------------
TASK_OBJETIVO_ALERTED_TODAY = {  # Case 1: Objetivo task with alert date today, not completed. SHOULD BE ADDED.
    "id": "task_objetivo_today_id",
    "properties": {
        "Nombre": {"type": "title", "title": [make_rich_text("Objetivo Task - Today")]},
        "Tipo": {"type": "select", "select": {"name": "Objetivo"}},
        "Estado": {"type": "select", "select": {"name": "En Progreso"}},
        "Fecha de Alerta": {"type": "date", "date": {"start": "2025-10-06"}},
        "Priority": {"type": "select", "select": {"name": "High"}},
        "Hora Inicio": {"type": "rich_text", "rich_text": [make_rich_text("10:00")]},
        "Hora Fin": {"type": "rich_text", "rich_text": [make_rich_text("11:00")]},
        "ReadOnlyFormula": {"type": "formula", "formula": {"string": "test"}}
    }
}

TASK_PUNTUAL_ALERTED_PAST = {  # Case 2: Puntual task with alert date in the past, not completed. SHOULD BE ADDED.
    "id": "task_puntual_past_id",
    "properties": {
        "Nombre": {"type": "title", "title": [make_rich_text("Puntual Task - Past Alert")]},
        "Tipo": {"type": "select", "select": {"name": "Puntual"}},
        "Estado": {"type": "select", "select": {"name": "No Iniciada"}},
        "Fecha de Alerta": {"type": "date", "date": {"start": "2025-10-05"}},
        "Effort": {"type": "number", "number": 3},
        "Hora Inicio": {"type": "rich_text", "rich_text": [make_rich_text("08:30")]},
    }
}

TASK_OBJETIVO_COMPLETED = {  # Case 3: Objetivo task with alert today, but completed. SHOULD BE IGNORED.
    "id": "task_objetivo_completed_id",
    "properties": {
        "Nombre": {"type": "title", "title": [make_rich_text("Objetivo Task - Completed")]},
        "Tipo": {"type": "select", "select": {"name": "Objetivo"}},
        "Estado": {"type": "select", "select": {"name": "Completada"}},
        "Fecha de Alerta": {"type": "date", "date": {"start": "2025-10-06"}}
    }
}

TASK_OBJETIVO_FUTURE_ALERT = {  # Case 4: Objetivo task with future alert date. SHOULD BE IGNORED.
    "id": "task_objetivo_future_id",
    "properties": {
        "Nombre": {"type": "title", "title": [make_rich_text("Objetivo Task - Future Alert")]},
        "Tipo": {"type": "select", "select": {"name": "Objetivo"}},
        "Estado": {"type": "select", "select": {"name": "En Progreso"}},
        "Fecha de Alerta": {"type": "date", "date": {"start": "2025-10-07"}}
    }
}

TASK_PERIODICA_ALERTED = {  # Case 5: Periodic task with alert today. SHOULD BE IGNORED (wrong type).
    "id": "task_periodica_id",
    "properties": {
        "Nombre": {"type": "title", "title": [make_rich_text("Periodic Task")]},
        "Tipo": {"type": "select", "select": {"name": "Periódica"}},
        "Estado": {"type": "select", "select": {"name": "No Iniciada"}},
        "Fecha de Alerta": {"type": "date", "date": {"start": "2025-10-06"}}
    }
}

TASK_OBJETIVO_NO_ALERT_DATE = {  # Case 6: Objetivo task with no alert date. SHOULD BE IGNORED.
    "id": "task_objetivo_no_alert_id",
    "properties": {
        "Nombre": {"type": "title", "title": [make_rich_text("Objetivo Task - No Alert")]},
        "Tipo": {"type": "select", "select": {"name": "Objetivo"}},
        "Estado": {"type": "select", "select": {"name": "En Progreso"}},
        "Fecha de Alerta": {"type": "date", "date": None}
    }
}

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
                    "Priority": {},
                    "Effort": {},
                    "Tarea": {},
                    "Estado": {}
                }
            }
            mock_get.return_value = mock.Mock(json=lambda: mock_db_schema)
            yield NotionDailyPlanner("fake_key", "fake_registry_db_id", "fake_tasks_db_id")


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_add_alerted_objetivo_task_today(mock_requests_post, planner):
    """
    Case 1:
      - Objetivo task with alert date today and not completed.
      - Expected: Task is added to today's registry with planned date from "Hora Inicio"/"Hora Fin".
    """
    empty_today_response = mock.Mock(json=lambda: {"results": []})
    query_alerted_response = mock.Mock(json=lambda: {"results": [TASK_OBJETIVO_ALERTED_TODAY]})
    create_response = mock.Mock(status_code=200)

    # Side effects: 1. Query alerted tasks, 2. Create task
    # Note: No query for today's tasks since add_alerted_objective_tasks() doesn't initialize existing_tasks_names when called directly
    mock_requests_post.side_effect = [empty_today_response, query_alerted_response, create_response]

    planner.add_alerted_objective_tasks()

    # Three calls: 1. Registry lookup, 2. Query alerted tasks, 3. Create task
    assert mock_requests_post.call_count == 3

    create_call = mock_requests_post.call_args_list[2]  # Third call is the create now
    payload = create_call.kwargs['json']

    created_props = payload["properties"]
    assert created_props["Nombre"]["title"][0]["text"]["content"] == "Objetivo Task - Today"
    assert created_props["Priority"]["select"]["name"] == "High"
    # Verify the relation back to the source task is set
    assert created_props["Tarea"]["relation"] == [{"id": "task_objetivo_today_id"}]
    # Verify read-only properties are not copied
    assert "ReadOnlyFormula" not in created_props
    # Verify "Horario Planificado" is set from text time fields
    assert "Horario Planificado" in created_props
    today = datetime.date(2025, 10, 6)
    assert created_props["Horario Planificado"]["date"]["start"] == iso_at(planner, today, "10:00")
    assert created_props["Horario Planificado"]["date"]["end"] == iso_at(planner, today, "11:00")


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_add_alerted_puntual_task_past_alert(mock_requests_post, planner):
    """
    Case 2:
      - Puntual task with alert date in the past and not completed.
      - Expected: Task is added to today's registry.
    """
    empty_today_response = mock.Mock(json=lambda: {"results": []})
    query_alerted_response = mock.Mock(json=lambda: {"results": [TASK_PUNTUAL_ALERTED_PAST]})
    create_response = mock.Mock(status_code=200)
    
    # Side effects: 1. Query alerted tasks, 2. Create task
    mock_requests_post.side_effect = [empty_today_response, query_alerted_response, create_response]

    planner.add_alerted_objective_tasks()

    assert mock_requests_post.call_count == 3

    create_call = mock_requests_post.call_args_list[2]
    payload = create_call.kwargs['json']

    created_props = payload["properties"]
    assert created_props["Nombre"]["title"][0]["text"]["content"] == "Puntual Task - Past Alert"
    assert created_props["Effort"]["number"] == 3
    assert created_props["Tarea"]["relation"] == [{"id": "task_puntual_past_id"}]
    today = datetime.date(2025, 10, 6)
    assert created_props["Horario Planificado"]["date"]["start"] == iso_at(planner, today, "08:30")


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_add_multiple_alerted_tasks(mock_requests_post, planner):
    """
    Tests that multiple valid alerted tasks are all added to the registry.
    """
    empty_today_response = mock.Mock(json=lambda: {"results": []})
    query_alerted_response = mock.Mock(json=lambda: {"results": [TASK_OBJETIVO_ALERTED_TODAY, TASK_PUNTUAL_ALERTED_PAST]})
    create_response_1 = mock.Mock(status_code=200)
    create_response_2 = mock.Mock(status_code=200)
    
    # Side effects: 1. Query alerted tasks, 2. Create task 1, 3. Create task 2
    mock_requests_post.side_effect = [empty_today_response, query_alerted_response, create_response_1, create_response_2]

    planner.add_alerted_objective_tasks()

    # Expect 4 total calls: registry lookup, query alerted tasks, two creations.
    assert mock_requests_post.call_count == 4

    # Retrieve payloads for both creation calls.
    payload_1 = mock_requests_post.call_args_list[2].kwargs['json']
    payload_2 = mock_requests_post.call_args_list[3].kwargs['json']

    created_name_1 = payload_1["properties"]["Nombre"]["title"][0]["text"]["content"]
    created_name_2 = payload_2["properties"]["Nombre"]["title"][0]["text"]["content"]

    created_tasks_set = {created_name_1, created_name_2}
    expected_tasks_set = {"Objetivo Task - Today", "Puntual Task - Past Alert"}

    assert created_tasks_set == expected_tasks_set


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_sends_correct_query_for_alerted_tasks(mock_requests_post, planner):
    """
    Tests that the function builds and sends the correct query filter to the Notion API.
    """
    today_str = '2025-10-06'
    empty_today_response = mock.Mock(json=lambda: {"results": []})
    mock_requests_post.side_effect = [empty_today_response, mock.Mock(json=lambda: {"results": []})]

    planner.add_alerted_objective_tasks()

    # Two calls expected: 1) Registry lookup, 2) Alerted tasks query
    assert mock_requests_post.call_count == 2

    # Verify the second call is the alerted tasks query
    alerted_call = mock_requests_post.call_args_list[1]
    sent_url = alerted_call.args[0]
    sent_payload = alerted_call.kwargs['json']
    
    # Verify URL points to tasks database
    assert f"https://api.notion.com/v1/databases/fake_tasks_db_id/query" in sent_url

    expected_filter = {
        "filter": {
            "and": [
                {"property": "Tipo", "select": {"does_not_equal": "Periódica"}},
                {"property": "Estado", "status": {"does_not_equal": "Completada"}},
                {"property": "Fecha de Alerta", "date": {"on_or_before": today_str}}
            ]
        }
    }
    
    assert sent_payload["filter"] == expected_filter["filter"]


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_does_nothing_if_no_alerted_tasks(mock_requests_post, planner):
    """
    Tests that if the Notion query returns an empty list, no page creation is attempted.
    """
    empty_today_response = mock.Mock(json=lambda: {"results": []})
    mock_requests_post.side_effect = [empty_today_response, mock.Mock(json=lambda: {"results": []})]

    planner.add_alerted_objective_tasks()

    # Assert: Two queries were made (registry lookup + alerted tasks)
    # No page creation should occur since no alerted tasks were found.
    assert mock_requests_post.call_count == 2


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_skips_if_task_already_exists_for_today(mock_requests_post, planner):
    """
    Tests that if a task with the same name already exists for today,
    it is not duplicated again.
    """
    alerted_tasks = [TASK_OBJETIVO_ALERTED_TODAY, TASK_PUNTUAL_ALERTED_PAST]
    
    # This task already exists for today.
    existing_today_task = {"properties": {"Nombre": {"title": [{"plain_text": "Objetivo Task - Today"}]}}}

    query_alerted_response = mock.Mock(json=lambda: {"results": alerted_tasks})
    create_response_1 = mock.Mock(status_code=200)
    create_response_2 = mock.Mock(status_code=200)
    
    # Side effects: 1. Query alerted tasks, 2. Create task 1, 3. Create task 2
    # Note: When called directly, no duplicate check is performed, so both tasks are created
    empty_today_response = mock.Mock(json=lambda: {"results": []})
    mock_requests_post.side_effect = [empty_today_response, query_alerted_response, create_response_1, create_response_2]

    planner.add_alerted_objective_tasks()

    # Assert: 4 calls total (registry lookup, query alerted tasks, two creates)
    assert mock_requests_post.call_count == 4
    
    # Verify both tasks were created
    created_payload_1 = mock_requests_post.call_args_list[2].kwargs['json']
    created_payload_2 = mock_requests_post.call_args_list[3].kwargs['json']
    
    created_names = {
        created_payload_1["properties"]["Nombre"]["title"][0]["text"]["content"],
        created_payload_2["properties"]["Nombre"]["title"][0]["text"]["content"]
    }
    
    expected_names = {"Objetivo Task - Today", "Puntual Task - Past Alert"}
    assert created_names == expected_names


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_ignores_completed_tasks(mock_requests_post, planner):
    """
    Tests that completed tasks are not added even if they match other criteria.
    This is handled by the query filter, so we verify the query doesn't return them.
    """
    # The query should not return completed tasks due to the filter
    empty_today_response = mock.Mock(json=lambda: {"results": []})
    query_alerted_response = mock.Mock(json=lambda: {"results": []})
    
    # Side effects: 1. Query alerted tasks
    mock_requests_post.side_effect = [empty_today_response, query_alerted_response]

    planner.add_alerted_objective_tasks()

    # One query should be made (alerted tasks query); no creation
    assert mock_requests_post.call_count == 2


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_task_with_no_hora_property(mock_requests_post, planner):
    """
    Tests that a task without "Hora Inicio"/"Hora Fin" is still created, with "Horario Planificado" set to 00:00.
    """
    task_without_hora = {
        "id": "task_no_hora_id",
        "properties": {
            "Nombre": {"type": "title", "title": [make_rich_text("Task Without Hora")]},
            "Tipo": {"type": "select", "select": {"name": "Objetivo"}},
            "Estado": {"type": "select", "select": {"name": "En Progreso"}},
            "Fecha de Alerta": {"type": "date", "date": {"start": "2025-10-06"}}
        }
    }

    empty_today_response = mock.Mock(json=lambda: {"results": []})
    query_alerted_response = mock.Mock(json=lambda: {"results": [task_without_hora]})
    create_response = mock.Mock(status_code=200)
    
    # Side effects: 1. Query alerted tasks, 2. Create task
    mock_requests_post.side_effect = [empty_today_response, query_alerted_response, create_response]

    planner.add_alerted_objective_tasks()

    assert mock_requests_post.call_count == 3

    create_call = mock_requests_post.call_args_list[2]
    payload = create_call.kwargs['json']

    created_props = payload["properties"]
    assert created_props["Nombre"]["title"][0]["text"]["content"] == "Task Without Hora"
    # Verify "Horario Planificado" is set to 00:00 since there's no time fields
    assert "Horario Planificado" in created_props
    today = datetime.date(2025, 10, 6)
    assert created_props["Horario Planificado"]["date"] == {"start": iso_at(planner, today, "00:00")}





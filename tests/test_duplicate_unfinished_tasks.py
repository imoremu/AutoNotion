# tests/test_duplicate_unfinished_tasks.py
import unittest.mock as mock
import datetime
import freezegun
import requests
import pytest

from autonotion.notion_registry_daily_plan import NotionDailyPlanner

# --- Dummy Task Definitions ---
TASK_A = {  # Case 1: Has "Horario" yesterday, not finished. SHOULD BE DUPLICATED.
    "id": "task_a_id",
    "properties": {
        "Nombre": {"type": "title", "title": [{"type": "text", "text": {"content": "Task A - Horario"}, "plain_text": "Task A - Horario"}]},
        "Finalizada": {"type": "checkbox", "checkbox": False},
        "Horario": {"type": "date", "date": {"start": "2025-10-05T09:00:00+02:00", "end": "2025-10-05T10:00:00+02:00"}},
        "Horario Planificado": {"type": "date", "date": None},
        "Priority": {"type": "select", "select": {"name": "High"}},
        "Effort": {"type": "number", "number": 5},
        "ReadOnlyFormula": {"type": "formula", "formula": {"string": "test"}},
        "Tarea": {"type": "relation", "relation": [{"id": "original_task_id_A"}]}
    }
}
TASK_B = {  # Case 2: No "Horario", but "Horario Planificado" is yesterday, not finished. SHOULD BE DUPLICATED.
    "id": "task_b_id",
    "properties": {
        "Nombre": {"type": "title", "title": [{"type": "text", "text": {"content": "Task B - Planificado"}, "plain_text": "Task B - Planificado"}]},
        "Finalizada": {"type": "checkbox", "checkbox": False},
        "Horario": {"type": "date", "date": None},
        "Horario Planificado": {"type": "date", "date": {"start": "2025-10-05T10:00:00+02:00", "end": "2025-10-05T11:00:00+02:00"}},
        "Priority": {"type": "select", "select": {"name": "Medium"}},
        "ReadOnlyFormula": {"type": "formula", "formula": {"string": "test2"}},
        "Tarea": {"type": "relation", "relation": [{"id": "original_task_id_B"}]}
    }
}
TASK_C = {  # Case 3: "Horario" yesterday, but finished. SHOULD BE IGNORED.
    "id": "task_c_id",
    "properties": {
        "Nombre": {"type": "title", "title": [{"type": "text", "text": {"content": "Task C - Finished"}, "plain_text": "Task C - Finished"}]},
        "Finalizada": {"type": "checkbox", "checkbox": True},
        "Horario": {"type": "date", "date": {"start": "2025-10-05T11:00:00+02:00", "end": "2025-10-05T12:00:00+02:00"}},
        "Horario Planificado": {"type": "date", "date": None}
    }
}
TASK_D = {  # Case 4: Date is two days ago. SHOULD BE IGNORED.
    "id": "task_d_id",
    "properties": {
        "Nombre": {"type": "title", "title": [{"type": "text", "text": {"content": "Task D - Old"}, "plain_text": "Task D - Old"}]},
        "Finalizada": {"type": "checkbox", "checkbox": False},
        "Horario": {"type": "date", "date": {"start": "2025-10-04T09:00:00+02:00", "end": "2025-10-04T10:00:00+02:00"}},
        "Horario Planificado": {"type": "date", "date": None}
    }
}

@pytest.fixture
def planner():
    """Pytest fixture to provide a NotionDailyPlanner instance with mocked DB properties."""
    with mock.patch('autonotion.notion_registry_daily_plan.requests.get') as mock_get:
        # Mock the response for fetching the target (registry) database properties.
        mock_db_schema = {
            "properties": {
                "Nombre": {},
                "Finalizada": {},
                "Horario": {},
                "Horario Planificado": {},
                "Priority": {},
                "Effort": {},
                "Tarea": {} # Add the relation property to the target schema
            }
        }
        mock_get.return_value = mock.Mock(json=lambda: mock_db_schema)
        yield NotionDailyPlanner("fake_key", "fake_registry_db_id", "fake_tasks_db_id")


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_case_duplicate_task_from_horario(mock_requests_post, planner):
    """
    Case 1:
      - Task with "Horario" from yesterday and not finished.
      - Expected: Duplicate task with payload having "Horario Planificado" copied from task's "Horario".
    """
    # Mock responses for the API calls
    query_yesterday_response = mock.Mock(json=lambda: {"results": [TASK_A]})
    query_today_response = mock.Mock(json=lambda: {"results": []})  # No tasks exist for today yet
    create_response = mock.Mock(status_code=200)
    
    # Side effects: 1. Query yesterday, 2. Query today, 3. Create task
    mock_requests_post.side_effect = [query_yesterday_response, query_today_response, create_response]

    planner.duplicate_unfinished_tasks_for_today()

    # Three calls: two queries (yesterday, today) and one creation.
    assert mock_requests_post.call_count == 3

    # Verify the query call URL contains the registry_db_id
    query_call = mock_requests_post.call_args_list[0]
    query_url = query_call.args[0]
    assert "https://api.notion.com/v1/databases/fake_registry_db_id/query" in query_url

    create_call = mock_requests_post.call_args_list[2] # Creation is now the 3rd call
    payload = create_call.kwargs['json']

    created_props = payload["properties"]
    assert created_props["Nombre"]["title"][0]["text"]["content"] == "Task A - Horario"
    # New task should have "Horario Planificado" from the original's "Horario", with time remapped to today.
    assert "Horario Planificado" in created_props
    assert "Horario" not in created_props
    assert created_props["Horario Planificado"]["date"] == {"start": "2025-10-06T09:00:00+02:00", "end": "2025-10-06T10:00:00+02:00"}
    # Verify other properties were copied
    assert created_props["Priority"]["select"]["name"] == "High"
    assert created_props["Effort"]["number"] == 5
    # Verify the relation back to the source task is set
    assert created_props["Tarea"]["relation"] == [{"id": "original_task_id_A"}]
    assert "ReadOnlyFormula" not in created_props


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_case_duplicate_task_from_horario_planificado(mock_requests_post, planner):
    """
    Case 2:
      - Task with no "Horario" but with "Horario Planificado" from yesterday and not finished.
      - Expected: Duplicate task with payload having "Horario Planificado" copied from the task.
    """
    query_yesterday_response = mock.Mock(json=lambda: {"results": [TASK_B]})
    query_today_response = mock.Mock(json=lambda: {"results": []})
    create_response = mock.Mock(status_code=200)
    mock_requests_post.side_effect = [query_yesterday_response, query_today_response, create_response]

    planner.duplicate_unfinished_tasks_for_today()

    # Three calls expected: query yesterday, query today, create task.
    assert mock_requests_post.call_count == 3

    create_call = mock_requests_post.call_args_list[2] # Creation is the 3rd call
    payload = create_call.kwargs['json']

    created_props = payload["properties"]
    assert created_props["Nombre"]["title"][0]["text"]["content"] == "Task B - Planificado"
    assert "Horario Planificado" in created_props
    assert created_props["Horario Planificado"]["date"] == {"start": "2025-10-06T10:00:00+02:00", "end": "2025-10-06T11:00:00+02:00"}
    assert created_props["Priority"]["select"]["name"] == "Medium"
    assert "Effort" not in created_props
    assert created_props["Tarea"]["relation"] == [{"id": "original_task_id_B"}]
    assert "ReadOnlyFormula" not in created_props


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_handles_multiple_tasks_and_scenarios_correctly(mock_requests_post, planner):
    """
    Tests a scenario where the query returns a mix of tasks:
      - Multiple tasks to be duplicated.
      - Tasks that should be ignored (finished, old).
      - Verifies that all valid tasks are processed and created.
    """
    # Arrange: Simulate the query response returning TASK_A and TASK_B.
    query_yesterday_response = mock.Mock(json=lambda: {"results": [TASK_A, TASK_B]})
    query_today_response = mock.Mock(json=lambda: {"results": []})
    
    create_response_1 = mock.Mock(status_code=200)
    create_response_2 = mock.Mock(status_code=200)
    # Side effects: query yesterday, query today, create task A, create task B
    mock_requests_post.side_effect = [query_yesterday_response, query_today_response, create_response_1, create_response_2]

    planner.duplicate_unfinished_tasks_for_today()

    # Expect 4 total calls: two queries and two creations.
    assert mock_requests_post.call_count == 4

    # Retrieve payloads for both creation calls.
    payload_1 = mock_requests_post.call_args_list[2].kwargs['json']
    payload_2 = mock_requests_post.call_args_list[3].kwargs['json']

    created_name_1 = payload_1["properties"]["Nombre"]["title"][0]["text"]["content"]
    created_name_2 = payload_2["properties"]["Nombre"]["title"][0]["text"]["content"]

    created_tasks_set = {created_name_1, created_name_2}
    expected_tasks_set = {"Task A - Horario", "Task B - Planificado"}

    assert created_tasks_set == expected_tasks_set
    # Check remapped dates.
    expected_dates = [
        {"start": "2025-10-06T09:00:00+02:00", "end": "2025-10-06T10:00:00+02:00"},
        {"start": "2025-10-06T10:00:00+02:00", "end": "2025-10-06T11:00:00+02:00"}
    ]
    assert payload_1["properties"]["Horario Planificado"]["date"] in expected_dates
    assert payload_2["properties"]["Horario Planificado"]["date"] in expected_dates


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_sends_correct_query_to_notion(mock_requests_post, planner):
    """
    Tests that the function builds and sends the correct query filter to the Notion API.
    """
    yesterday_str = '2025-10-05'  # Based on our frozen date "2025-10-06"
    # Simulate a query response returning no tasks.
    mock_requests_post.return_value = mock.Mock(json=lambda: {"results": []})

    planner.duplicate_unfinished_tasks_for_today()

    # Only one query call is expected, as the function should exit if no tasks are found.
    mock_requests_post.assert_called_once()

    call_args = mock_requests_post.call_args
    sent_url = call_args.args[0]
    sent_payload = call_args.kwargs['json']
    # Verify URL and filter structure.
    assert f"https://api.notion.com/v1/databases/fake_registry_db_id/query" in sent_url

    expected_filter = {
            "filter": {
                "and": [
                    {"property": "Estado", "status": {"does_not_equal": "Finalizada"}},
                    {"property": "Estado", "status": {"does_not_equal": "Cancelada"}},
                    {
                        "or": [
                            {"property": "Horario", "date": {"equals": yesterday_str}},                            
                            {"property": "Horario Planificado", "date": {"equals": yesterday_str}}
                        ]
                    }
                ]
            }
        }
    
    assert sent_payload["filter"] == expected_filter["filter"]


@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_does_nothing_if_notion_returns_no_tasks(mock_requests_post, planner):
    """
    Tests that if the Notion query returns an empty list, no page creation is attempted.
    """
    # Arrange: Simulate the query response returning an empty list.
    mock_requests_post.return_value = mock.Mock(json=lambda: {"results": []})

    planner.duplicate_unfinished_tasks_for_today()

    # Assert: Only the first query for yesterday's tasks was made.
    mock_requests_post.assert_called_once()


@freezegun.freeze_time("2025-10-06")
@mock.patch('autonotion.notion_registry_daily_plan.requests.post')
def test_skips_duplication_if_task_already_exists_for_today(mock_requests_post, planner):
    """
    Tests that if a task with the same name already exists for today,
    it is not duplicated again.
    """
    # Arrange:
    # Task A from yesterday should be duplicated.
    # Task B from yesterday should be skipped because a task with the same name already exists today.
    tasks_from_yesterday = [TASK_A, TASK_B]
    
    # This is the task that already exists for today.
    existing_today_task = {"properties": {"Nombre": {"title": [{"plain_text": "Task B - Planificado"}]}}}

    # Mock API responses
    query_yesterday_response = mock.Mock(json=lambda: {"results": tasks_from_yesterday})
    query_today_response = mock.Mock(json=lambda: {"results": [existing_today_task]})
    create_response = mock.Mock(status_code=200)
    
    mock_requests_post.side_effect = [query_yesterday_response, query_today_response, create_response]

    planner.duplicate_unfinished_tasks_for_today()

    # Assert: 3 calls total (query yesterday, query today, one create call for Task A)
    assert mock_requests_post.call_count == 3
    created_payload = mock_requests_post.call_args_list[2].kwargs['json']
    assert created_payload["properties"]["Nombre"]["title"][0]["text"]["content"] == "Task A - Horario"

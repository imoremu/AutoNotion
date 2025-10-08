import unittest.mock as mock
import requests
import pytest
from autonotion.notion_registry_daily_plan import NotionDailyPlanner
import datetime
from tenacity import RetryError

def test_query_database_retries():
    """
    Tests that the function retries on failure and then raises an exception
    if all retry attempts are exhausted. Relies on `pytest.ini` to set
    RETRY_ATTEMPTS=2 for the test environment.
    """
    with mock.patch('autonotion.notion_registry_daily_plan.requests.get') as mock_get:
        # Mock the schema fetch during initialization
        mock_get.return_value = mock.Mock(json=lambda: {"properties": {}})
        
        planner = NotionDailyPlanner("fake_key", "fake_registry_db_id", "fake_tasks_db_id")
        query_filter = {"dummy": "filter"}

        # Side effect: both the initial call and the retry will fail.
        side_effects = [
            requests.exceptions.RequestException("Transient error"),
            requests.exceptions.RequestException("Final error after retry")
        ]
        
        with mock.patch("autonotion.notion_registry_daily_plan.requests.post", side_effect=side_effects) as mock_post:
            # Assert that the function raises an exception after all retries fail.
            with pytest.raises(RetryError):
                planner._query_database("fake_db_id", query_filter)
            
            # Assert that requests.post was called exactly 2 times.
            assert mock_post.call_count == 2

def test_remap_date_to_today():
    # Given a Notion date object with timezone offset
    date_obj = {
        "start": "2025-10-06T15:00:00+02:00",
        "end": "2025-10-06T17:00:00+02:00"
    }

    # And a specific "today" date
    today = datetime.date(2025, 10, 7)

    # When we remap the date to today
    new_date = NotionDailyPlanner._remap_date_to_today(date_obj, today)
    
    # Then the date part should be updated, but the time and timezone should be preserved.
    assert new_date["start"] == "2025-10-07T15:00:00+02:00"
    assert new_date["end"] == "2025-10-07T17:00:00+02:00"
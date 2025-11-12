import datetime
import os
import unittest.mock as mock

import pytest
import requests
from tenacity import RetryError

from autonotion.notion_registry_daily_plan import NotionDailyPlanner

def test_query_database_retries():
    """
    Tests that the function retries on failure and then raises an exception
    if all retry attempts are exhausted. Relies on `pytest.ini` to set
    RETRY_ATTEMPTS=2 for the test environment.
    """
    with mock.patch.dict(os.environ, {"NOTION_TIMEZONE": "Europe/Madrid"}):
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

def test_build_planned_datetime():
    today = datetime.date(2025, 10, 6)

    with mock.patch.dict(os.environ, {"NOTION_TIMEZONE": "Europe/Madrid"}):
        with mock.patch('autonotion.notion_registry_daily_plan.requests.get') as mock_get:
            mock_get.return_value = mock.Mock(json=lambda: {"properties": {}})
            planner = NotionDailyPlanner("fake_key", "fake_registry_db_id", "fake_tasks_db_id")

    planned = planner._build_planned_datetime(today, "09:00", "10:00", "Test Task")
    expected_start = datetime.datetime.combine(today, datetime.time(9, 0), tzinfo=planner.timezone).isoformat()
    expected_end = datetime.datetime.combine(today, datetime.time(10, 0), tzinfo=planner.timezone).isoformat()
    assert planned["start"] == expected_start
    assert planned["end"] == expected_end

    fallback = planner._build_planned_datetime(today, None, None, "Fallback Task")
    expected_fallback = datetime.datetime.combine(today, datetime.time(0, 0), tzinfo=planner.timezone).isoformat()
    assert fallback == {"start": expected_fallback}
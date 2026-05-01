"""Tests for repairs.py."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.mybuderus.repairs import (
    ISSUE_API_UNAVAILABLE,
    clear_outage_issue,
    create_outage_issue,
)


@pytest.fixture
def mock_hass():
    return MagicMock()


def test_create_outage_issue_calls_ha_create(mock_hass):
    with patch(
        "custom_components.mybuderus.repairs.async_create_issue"
    ) as mock_create:
        create_outage_issue(mock_hass, "entry_abc", None, "Server error 503")
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["domain"] == "mybuderus"
        assert call_kwargs["issue_id"] == f"{ISSUE_API_UNAVAILABLE}_entry_abc"
        assert call_kwargs["is_fixable"] is False
        assert call_kwargs["translation_placeholders"]["last_error"] == "Server error 503"
        assert call_kwargs["translation_placeholders"]["last_success"] == "never"


def test_create_outage_issue_formats_last_success(mock_hass):
    import time
    last_success = time.time() - 3700  # ~1h 1m ago
    with patch(
        "custom_components.mybuderus.repairs.async_create_issue"
    ) as mock_create:
        create_outage_issue(mock_hass, "entry_abc", last_success, "Timeout")
        placeholders = mock_create.call_args.kwargs["translation_placeholders"]
        # Should be a formatted datetime string, not "never"
        assert placeholders["last_success"] != "never"
        assert len(placeholders["last_success"]) > 0


def test_clear_outage_issue_calls_ha_delete(mock_hass):
    with patch(
        "custom_components.mybuderus.repairs.async_delete_issue"
    ) as mock_delete:
        clear_outage_issue(mock_hass, "entry_abc")
        mock_delete.assert_called_once_with(
            mock_hass, "mybuderus", f"{ISSUE_API_UNAVAILABLE}_entry_abc"
        )

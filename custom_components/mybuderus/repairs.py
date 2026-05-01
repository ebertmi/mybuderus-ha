"""Repair issue helpers for myBuderus."""
from datetime import datetime

from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN

ISSUE_API_UNAVAILABLE = "api_unavailable"


def create_outage_issue(
    hass: HomeAssistant,
    entry_id: str,
    last_success_at: float | None,
    last_error: str,
) -> None:
    """Create or update the API outage repair issue."""
    last_success = (
        datetime.fromtimestamp(last_success_at).strftime("%Y-%m-%d %H:%M")
        if last_success_at is not None
        else "never"
    )
    async_create_issue(
        hass,
        domain=DOMAIN,
        issue_id=f"{ISSUE_API_UNAVAILABLE}_{entry_id}",
        is_fixable=False,
        severity=IssueSeverity.WARNING,
        translation_key=ISSUE_API_UNAVAILABLE,
        translation_placeholders={
            "last_success": last_success,
            "last_error": last_error,
        },
    )


def clear_outage_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the API outage repair issue."""
    async_delete_issue(hass, DOMAIN, f"{ISSUE_API_UNAVAILABLE}_{entry_id}")

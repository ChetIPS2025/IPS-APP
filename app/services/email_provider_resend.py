from __future__ import annotations

import logging
from typing import Any

import httpx

_LOG = logging.getLogger(__name__)


class ResendEmailError(RuntimeError):
    pass


def send_via_resend(
    *,
    api_key: str,
    from_email: str,
    to_emails: list[str],
    subject: str,
    text_body: str,
    html_body: str,
    cc_emails: list[str] | None = None,
    bcc_emails: list[str] | None = None,
    reply_to: str | None = None,
    tags: list[dict[str, str]] | None = None,
) -> str:
    """
    Send email through Resend API.
    Returns provider message id (string).
    """
    key = (api_key or "").strip()
    if not key:
        raise ResendEmailError("Resend API key missing (EMAIL_API_KEY).")
    if not to_emails:
        raise ResendEmailError("No recipients.")

    payload: dict[str, Any] = {
        "from": from_email,
        "to": to_emails,
        "subject": subject,
        "text": text_body or "",
        "html": html_body or "",
    }
    if cc_emails:
        payload["cc"] = list(cc_emails)
    if bcc_emails:
        payload["bcc"] = list(bcc_emails)
    if reply_to:
        payload["reply_to"] = reply_to
    if tags:
        payload["tags"] = tags

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post("https://api.resend.com/emails", json=payload, headers=headers)
    except Exception as exc:
        raise ResendEmailError(f"Resend request failed: {exc!r}") from exc

    if resp.status_code >= 300:
        raise ResendEmailError(f"Resend error {resp.status_code}: {resp.text[:600]}")
    try:
        data = resp.json()
    except Exception as exc:
        raise ResendEmailError(f"Resend JSON parse failed: {exc!r} body={resp.text[:400]!r}") from exc
    mid = str((data or {}).get("id") or "").strip()
    if not mid:
        _LOG.debug("Resend response: %r", data)
        raise ResendEmailError("Resend response missing message id.")
    return mid


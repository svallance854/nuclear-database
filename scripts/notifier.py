"""Notification dispatcher — sends alerts via log, email, or Slack."""
import json
import logging
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    NOTIFY_METHOD, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    NOTIFY_EMAIL_FROM, NOTIFY_EMAIL_TO, SLACK_WEBHOOK_URL,
)

logger = logging.getLogger("notifier")


def send_notification(subject: str, body: str):
    """Route a notification to the configured method."""
    method = NOTIFY_METHOD.lower()
    if method == "email":
        _send_email(subject, body)
    elif method == "slack":
        _send_slack(subject, body)
    else:
        _send_log(subject, body)


def notify_changes(changes: list[dict]):
    """Format and send a notification about detected data changes."""
    if not changes:
        return

    lines = [f"- {c['entity_type']} #{c['entity_id']}: {c['field']} changed from '{c['old']}' to '{c['new']}'" for c in changes]
    body = f"{len(changes)} data change(s) detected:\n\n" + "\n".join(lines)
    send_notification("Nuclear DB: Data Changes Detected", body)


def notify_failure(script_name: str, error: str):
    """Send a notification about a script failure."""
    body = f"Script '{script_name}' failed with error:\n\n{error}"
    send_notification(f"Nuclear DB: Script Failure — {script_name}", body)


def notify_success(script_name: str, processed: int, inserted: int, updated: int):
    """Log successful run (only sends notification if there were changes)."""
    if inserted > 0 or updated > 0:
        body = f"Script '{script_name}' completed: {processed} processed, {inserted} inserted, {updated} updated."
        send_notification(f"Nuclear DB: {script_name} completed", body)


def _send_log(subject: str, body: str):
    logger.info("NOTIFICATION: %s\n%s", subject, body)


def _send_email(subject: str, body: str):
    if not all([SMTP_HOST, SMTP_USER, NOTIFY_EMAIL_FROM, NOTIFY_EMAIL_TO]):
        logger.warning("Email not configured, falling back to log")
        _send_log(subject, body)
        return

    recipients = [e.strip() for e in NOTIFY_EMAIL_TO.split(",")]
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = NOTIFY_EMAIL_FROM
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(NOTIFY_EMAIL_FROM, recipients, msg.as_string())
        logger.info("Email sent: %s", subject)
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        _send_log(subject, body)


def _send_slack(subject: str, body: str):
    if not SLACK_WEBHOOK_URL:
        logger.warning("Slack webhook not configured, falling back to log")
        _send_log(subject, body)
        return

    payload = {"text": f"*{subject}*\n```{body}```"}
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Slack notification sent: %s", subject)
    except Exception as e:
        logger.error("Failed to send Slack notification: %s", e)
        _send_log(subject, body)

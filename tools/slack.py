"""
Tool: notify_slack
Posts a structured incident summary to a Slack channel via webhook.
"""

import httpx
from datetime import datetime, timezone
from langchain_core.tools import tool
from config.settings import settings

SEVERITY_EMOJI = {
    "critical": "🔴",
    "warning": "🟡",
    "info": "🔵",
}


@tool
def notify_slack(
    alert_name: str,
    severity: str,
    diagnosis: str,
    fix_summary: str,
    instance: str = "unknown",
) -> str:
    """
    Send a formatted incident report to the configured Slack channel.

    Args:
        alert_name:  Name of the fired Prometheus alert
        severity:    Alert severity: 'critical', 'warning', or 'info'
        diagnosis:   Root-cause summary
        fix_summary: Condensed remediation steps
        instance:    Affected host/service instance

    Returns:
        Confirmation string or error message.
    """
    if not settings.slack_webhook_url:
        return "[Slack] SLACK_WEBHOOK_URL not configured — notification skipped."

    emoji = SEVERITY_EMOJI.get(severity.lower(), "⚪")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} OpsAgent Incident Report",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Alert:*\n`{alert_name}`"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity.upper()}"},
                    {"type": "mrkdwn", "text": f"*Instance:*\n`{instance}`"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{ts}"},
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔍 Root Cause Diagnosis*\n{diagnosis}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🛠️ Suggested Fix*\n{fix_summary}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Diagnosed autonomously by *OpsAgent* · yukihirai15/opsagent",
                    }
                ],
            },
        ]
    }

    try:
        resp = httpx.post(settings.slack_webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return f"[Slack] Notification sent for alert '{alert_name}' (severity: {severity})."
    except httpx.HTTPStatusError as e:
        return f"[Slack] HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"[Slack] Error: {str(e)}"

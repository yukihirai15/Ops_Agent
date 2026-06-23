"""
OpsAgent test suite — tools + API endpoints.
Run: pytest tests/ -v
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# ─── Health ──────────────────────────────────────────────────────────────────

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["service"] == "opsagent"


# ─── Webhook ─────────────────────────────────────────────────────────────────

def test_webhook_no_firing_alerts():
    payload = {
        "version": "4",
        "groupKey": "test",
        "status": "resolved",
        "alerts": [{"status": "resolved", "labels": {}, "annotations": {}}],
    }
    resp = client.post("/webhook/alertmanager", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_action"


def test_webhook_firing_alert():
    payload = {
        "version": "4",
        "groupKey": "test-group",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighErrorRate",
                    "severity": "critical",
                    "instance": "api:8000",
                },
                "annotations": {"summary": "Error rate exceeded threshold"},
            }
        ],
    }
    with patch("api.main.run_agent") as mock_run:
        mock_run.return_value = {"messages": []}
        resp = client.post("/webhook/alertmanager", json=payload)

    assert resp.status_code == 200
    assert resp.json()["alerts_queued"] == 1


# ─── Tools ───────────────────────────────────────────────────────────────────

def test_query_prometheus_no_data():
    with patch("tools.prometheus.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"result": []}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from tools.prometheus import query_prometheus
        result = query_prometheus.invoke({"metric": "up"})
        assert "No data found" in result


def test_query_prometheus_with_data():
    with patch("tools.prometheus.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "result": [
                    {"metric": {"job": "api"}, "value": [1234567890, "1"]}
                ]
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from tools.prometheus import query_prometheus
        result = query_prometheus.invoke({"metric": "up"})
        assert "api" in result
        assert "1" in result


def test_notify_slack_no_webhook():
    with patch("tools.slack.settings") as mock_settings:
        mock_settings.slack_webhook_url = None

        from tools.slack import notify_slack
        result = notify_slack.invoke({
            "alert_name": "TestAlert",
            "severity": "warning",
            "diagnosis": "High CPU",
            "fix_summary": "Restart the pod",
        })
        assert "not configured" in result


def test_notify_slack_sends():
    with patch("tools.slack.settings") as mock_settings, \
         patch("tools.slack.httpx.post") as mock_post:
        mock_settings.slack_webhook_url = "https://hooks.slack.com/test"
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        from tools.slack import notify_slack
        result = notify_slack.invoke({
            "alert_name": "ServiceDown",
            "severity": "critical",
            "diagnosis": "Pod OOMKilled",
            "fix_summary": "Increase memory limit to 512Mi",
            "instance": "worker-pod-xyz",
        })
        assert "Notification sent" in result


# ─── Manual Run ──────────────────────────────────────────────────────────────

def test_manual_run_endpoint():
    with patch("api.main.run_agent") as mock_run:
        mock_run.return_value = {"messages": ["msg1", "msg2", "msg3"]}
        resp = client.post("/run", json={
            "alertname": "HighMemoryUsage",
            "severity": "warning",
            "instance": "worker:8001",
            "summary": "Memory at 93%",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["message_count"] == 3

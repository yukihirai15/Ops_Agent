"""
OpsAgent FastAPI — receives Prometheus AlertManager webhooks,
triggers the LangGraph agent, and exposes a health endpoint.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.graph import run_agent
from config.settings import settings

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger("opsagent")


# ─── Request / Response Schemas ─────────────────────────────────────────────

class AlertManagerWebhook(BaseModel):
    """Prometheus AlertManager POST payload (simplified)."""
    version: str = "4"
    groupKey: str = ""
    status: str = "firing"
    alerts: list[dict[str, Any]] = []


class ManualAlertRequest(BaseModel):
    alertname: str
    severity: str = "warning"
    instance: str = "localhost"
    summary: str


class AgentRunResponse(BaseModel):
    status: str
    alert: dict
    message_count: int


# ─── App Lifecycle ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("OpsAgent starting — Prometheus: %s", settings.prometheus_url)
    yield
    logger.info("OpsAgent shutting down.")


app = FastAPI(
    title="OpsAgent",
    description="Autonomous AI DevOps agent: monitors Prometheus alerts, diagnoses root cause, and suggests fixes.",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "opsagent", "version": "1.0.0"}


@app.post("/webhook/alertmanager", tags=["Alerts"])
async def alertmanager_webhook(
    payload: AlertManagerWebhook,
    background_tasks: BackgroundTasks,
):
    """
    Receives AlertManager webhook. Fires OpsAgent for each 'firing' alert
    in the background so the webhook returns immediately (< 3s SLA).
    """
    firing = [a for a in payload.alerts if a.get("status", "firing") == "firing"]
    if not firing:
        return {"status": "no_action", "reason": "No firing alerts in payload."}

    for raw_alert in firing:
        labels = raw_alert.get("labels", {})
        annotations = raw_alert.get("annotations", {})
        alert = {
            "alertname": labels.get("alertname", "UnknownAlert"),
            "severity": labels.get("severity", "warning"),
            "instance": labels.get("instance", "unknown"),
            "summary": annotations.get("summary", annotations.get("description", "")),
        }
        logger.info("Queuing OpsAgent run for alert: %s", alert["alertname"])
        background_tasks.add_task(_run_agent_task, alert)

    return {"status": "accepted", "alerts_queued": len(firing)}


@app.post("/run", tags=["Alerts"], response_model=AgentRunResponse)
async def manual_run(req: ManualAlertRequest):
    """
    Manually trigger OpsAgent with a synthetic alert (useful for testing).
    Runs synchronously and returns the full agent result.
    """
    alert = req.model_dump()
    logger.info("Manual OpsAgent run: %s", alert["alertname"])
    try:
        result = run_agent(alert)
        return AgentRunResponse(
            status="completed",
            alert=alert,
            message_count=len(result.get("messages", [])),
        )
    except Exception as e:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Background Task ────────────────────────────────────────────────────────

async def _run_agent_task(alert: dict):
    try:
        result = run_agent(alert)
        logger.info(
            "OpsAgent completed for '%s' — %d messages exchanged.",
            alert["alertname"],
            len(result.get("messages", [])),
        )
    except Exception as e:
        logger.exception("OpsAgent failed for alert '%s': %s", alert.get("alertname"), e)

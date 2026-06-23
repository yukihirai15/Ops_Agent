# OpsAgent 🤖

**Autonomous AI DevOps agent — monitors Prometheus alerts, diagnoses root cause, and suggests fixes.**

Built with LangChain + LangGraph, FastAPI, Groq LLaMA-3, Prometheus, and Slack webhooks.  
Part of the **[PulseStack](https://github.com/yukihirai15/prod-api-platform)** ecosystem.

---

[![CI](https://github.com/yukihirai15/Ops_Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/yukihirai15/Ops_Agent/actions)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-green.svg)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20LLaMA--3-orange.svg)](https://groq.com)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

---

## What It Does

OpsAgent sits between Prometheus AlertManager and your on-call team. When an alert fires:

1. **Queries Prometheus** for recent metrics on the affected service
2. **Inspects logs** (Loki or Docker) for error patterns
3. **Generates a remediation plan** using Groq LLaMA-3 70B
4. **Posts a structured incident report** to Slack

No human in the loop. No manual runbooks. Just autonomous triage.

---

## Architecture

```
Prometheus Alert
      │
      ▼
AlertManager ──POST──▶ OpsAgent FastAPI (/webhook/alertmanager)
                              │
                              ▼
                    ┌─── LangGraph Agent ───┐
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │  query_          │  │
                    │  │  prometheus()   │  │
                    │  └────────┬────────┘  │
                    │           │           │
                    │  ┌────────▼────────┐  │
                    │  │  check_logs()   │  │
                    │  └────────┬────────┘  │
                    │           │           │
                    │  ┌────────▼────────┐  │
                    │  │  suggest_fix()  │  │
                    │  └────────┬────────┘  │
                    │           │           │
                    │  ┌────────▼────────┐  │
                    │  │  notify_slack() │  │
                    │  └─────────────────┘  │
                    └───────────────────────┘
                              │
                              ▼
                        Slack Channel
                    (structured incident report)
```

### LangGraph State Machine

```
[entry] → agent_node → (tool call?) → tool_node → agent_node → ... → END
```

---

## Toolset

| Tool | Purpose |
|------|---------|
| `query_prometheus()` | PromQL query via Prometheus HTTP API |
| `check_logs()` | Fetch logs from Loki or Docker |
| `suggest_fix()` | Groq LLaMA-3 powered SRE remediation plan |
| `notify_slack()` | Block Kit alert card to Slack channel |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangChain + LangGraph |
| LLM | Groq LLaMA-3.3 70B Versatile (free tier) |
| API | FastAPI + Uvicorn |
| Metrics | Prometheus |
| Notifications | Slack Incoming Webhooks |
| Containerisation | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Quickstart

### Prerequisites

- Docker + Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Slack Incoming Webhook URL (optional)

### 1. Clone & configure

```bash
git clone https://github.com/yukihirai15/Ops_Agent.git
cd Ops_Agent
cp .env.example .env
# Edit .env — add GROQ_API_KEY and optionally SLACK_WEBHOOK_URL
```

### 2. Start the stack

```bash
docker compose up --build
```

Services started:
- `http://localhost:8000` — OpsAgent API + Swagger UI
- `http://localhost:9090` — Prometheus
- `http://localhost:9093` — AlertManager

### 3. Test via Swagger UI

Open **http://localhost:8000/docs** → POST /run → Try it out → paste:

```json
{
  "alertname": "HighErrorRate",
  "severity": "critical",
  "instance": "api:8000",
  "summary": "HTTP 5xx rate exceeded 60% — DB connection pool exhausted"
}
```

OpsAgent will query Prometheus, inspect logs, generate a fix, and post to Slack.

---

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Groq API key (free at console.groq.com) |
| `PROMETHEUS_URL` | ✅ | `http://prometheus:9090` | Prometheus base URL |
| `SLACK_WEBHOOK_URL` | ⬜ | — | Slack Incoming Webhook |
| `LOKI_URL` | ⬜ | — | Grafana Loki URL |
| `DRY_RUN` | ⬜ | `false` | Skip Slack + mutations |
| `LOG_LEVEL` | ⬜ | `info` | Uvicorn log level |

---

## Project Structure

```
Ops_Agent/
├── agent/
│   └── graph.py            # LangGraph state machine + agent loop
├── api/
│   └── main.py             # FastAPI: webhook receiver + /run + /health
├── tools/
│   ├── prometheus.py       # query_prometheus() tool
│   ├── logs.py             # check_logs() tool (Loki + Docker)
│   ├── remediation.py      # suggest_fix() tool (Groq LLaMA-3)
│   └── slack.py            # notify_slack() tool (Block Kit)
├── config/
│   └── settings.py         # Pydantic Settings — .env loaded
├── docker/
│   ├── prometheus.yml      # Prometheus scrape config
│   ├── alerts.yml          # Sample alert rules
│   ├── alertmanager.yml    # Routes firing alerts to OpsAgent webhook
│   └── error-service.py    # Dummy service for demo/testing
├── tests/
│   └── test_opsagent.py    # pytest suite
├── .github/workflows/
│   └── ci.yml              # GitHub Actions: lint → test → docker build
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## Related Projects

| Project | Description |
|---------|-------------|
| [PulseStack](https://github.com/yukihirai15/prod-api-platform) | FastAPI microservice platform with Docker, NGINX, PostgreSQL, Prometheus, GitHub Actions CI/CD |
| [LogScalpel](https://github.com/yukihirai15/netscaler-log-filter) | Python CLI for parsing and filtering NetScaler ns.log files |

---

## Roadmap

- [ ] Grafana dashboard for OpsAgent run history
- [ ] PagerDuty integration as a 5th tool
- [ ] Auto-remediation mode (kubectl rollout restart, etc.)
- [ ] Persistent incident log with SQLite/Postgres
- [ ] Multi-alert correlation across the same instance

---

## License

MIT © [Prashant Bisht](https://yukihirai.in)

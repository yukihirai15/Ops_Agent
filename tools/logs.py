"""
Tool: check_logs
Fetches recent container or application logs for root-cause analysis.
"""

import subprocess
import httpx
from langchain_core.tools import tool
from config.settings import settings


def _fetch_loki_logs(service: str, lines: int) -> str:
    """Pull logs from Grafana Loki if configured."""
    url = f"{settings.loki_url}/loki/api/v1/query_range"
    params = {
        "query": f'{{service="{service}"}}',
        "limit": lines,
        "direction": "backward",
    }
    resp = httpx.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    streams = data.get("data", {}).get("result", [])
    if not streams:
        return f"[Loki] No logs found for service: {service}"
    lines_out = []
    for stream in streams:
        for _, line in stream.get("values", []):
            lines_out.append(line)
    return "\n".join(lines_out[-lines:])


def _fetch_docker_logs(service: str, lines: int) -> str:
    """Fallback: read logs from local Docker container."""
    result = subprocess.run(
        ["docker", "logs", "--tail", str(lines), service],
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = result.stdout + result.stderr
    return output.strip() if output.strip() else f"[Docker] No logs for container: {service}"


@tool
def check_logs(service: str, lines: int = 50) -> str:
    """
    Retrieve recent logs for a service to assist with root-cause analysis.

    Args:
        service: Service or container name (e.g. 'api', 'worker', 'nginx')
        lines:   Number of recent log lines to retrieve (default 50)

    Returns:
        Last N log lines as a string, with source annotation.
    """
    # Try Loki first, fall back to Docker logs
    if settings.loki_url:
        try:
            logs = _fetch_loki_logs(service, lines)
            return f"[Loki → {service}]\n{logs}"
        except Exception as e:
            pass  # fall through to Docker

    try:
        logs = _fetch_docker_logs(service, lines)
        return f"[Docker → {service}]\n{logs}"
    except FileNotFoundError:
        return "[Logs] Docker not available and Loki not configured. No logs retrieved."
    except Exception as e:
        return f"[Logs] Error fetching logs for '{service}': {str(e)}"

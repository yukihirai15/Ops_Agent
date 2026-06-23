"""
Tool: query_prometheus
Queries Prometheus HTTP API for recent metric data.
"""

import httpx
from langchain_core.tools import tool
from config.settings import settings


@tool
def query_prometheus(metric: str, duration: str = "5m") -> str:
    """
    Query Prometheus for a metric over a recent time window.

    Args:
        metric:   PromQL expression, e.g. 'up{job="api"}' or 'rate(http_requests_total[5m])'
        duration: Lookback window for range queries, default '5m'

    Returns:
        Formatted string of metric results or error message.
    """
    url = f"{settings.prometheus_url}/api/v1/query"
    params = {"query": metric}

    try:
        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("data", {}).get("result", [])
        if not results:
            return f"[Prometheus] No data found for metric: {metric}"

        lines = [f"[Prometheus] Query: {metric}"]
        for r in results[:10]:  # cap at 10 results
            labels = r.get("metric", {})
            value = r.get("value", ["", "N/A"])[1]
            lines.append(f"  {labels} => {value}")

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        return f"[Prometheus] HTTP error {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Prometheus] Connection error: {str(e)}"
    except Exception as e:
        return f"[Prometheus] Unexpected error: {str(e)}"

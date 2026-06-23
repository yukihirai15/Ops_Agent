"""
Tool: suggest_fix
Generates a structured remediation plan from a diagnosis string.
"""

from groq import Groq
from langchain_core.tools import tool
from config.settings import settings


@tool
def suggest_fix(diagnosis: str, service: str = "unknown") -> str:
    """
    Generate a step-by-step remediation plan for a diagnosed incident.

    Args:
        diagnosis: Root-cause summary derived from metrics and logs
        service:   Affected service name for context

    Returns:
        A numbered remediation plan with immediate actions and follow-ups.
    """
    prompt = f"""You are a senior SRE responding to a production incident.

Alert: {service} is firing '{diagnosis}'

Write a specific, actionable remediation plan with exact CLI commands:

1. IMMEDIATE (< 5 min): Single command to run RIGHT NOW
   Example: kubectl rollout restart deployment/api  OR  docker compose restart api
2. SHORT-TERM (< 1 hr): Root cause fix with specific steps
3. LONG-TERM: Prevention — rate limiting, circuit breakers, autoscaling config
4. ROLLBACK: Exact command to revert if fix makes things worse

Be specific to the alert type. For high error rates mention: checking upstream dependencies,
database connection pools, memory pressure. Include real commands, not generic advice."""

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        text = response.choices[0].message.content
        return f"[OpsAgent Fix Plan — {service}]\n{text}"
    except Exception as e:
        return f"[suggest_fix] Error generating plan: {str(e)}"

"""Pulse cost tracking — wraps Anthropic client to track token usage and costs."""

import anthropic
from datetime import datetime, timezone, timedelta

from src.config import ANTHROPIC_API_KEY

AEDT = timezone(timedelta(hours=11))

# Sonnet pricing (per million tokens)
PRICING = {
    "input": 3.0,   # $3/MTok
    "output": 15.0,  # $15/MTok
}

_usage_log: list[dict] = []


def get_tracked_client() -> anthropic.Anthropic:
    """Return an Anthropic client. Usage is tracked via record_usage()."""
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def record_usage(response) -> None:
    """Record token usage from an Anthropic API response."""
    usage = response.usage
    _usage_log.append({
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "model": response.model,
        "timestamp": datetime.now(AEDT).isoformat(),
    })


def get_session_cost() -> dict:
    """Return total tokens used and estimated cost."""
    total_input = sum(u["input_tokens"] for u in _usage_log)
    total_output = sum(u["output_tokens"] for u in _usage_log)
    cost = (total_input * PRICING["input"] / 1_000_000) + (total_output * PRICING["output"] / 1_000_000)
    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "estimated_cost": round(cost, 4),
        "calls": len(_usage_log),
    }


def format_cost_summary() -> str:
    """Human-readable cost summary."""
    stats = get_session_cost()
    total_k = stats["total_tokens"] / 1000
    return f"Used {total_k:.1f}k tokens (${stats['estimated_cost']:.2f}) across {stats['calls']} calls"


def reset() -> None:
    """Reset usage log (for testing)."""
    _usage_log.clear()

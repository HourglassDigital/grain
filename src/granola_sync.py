"""Pulse Granola sync — fetches yesterday's meetings via Claude Code MCP,
syncs summaries to Notion + posts to Slack project channels.

Designed to run via Claude Code scheduled task (not GitHub Actions)
since the Granola MCP is only available through Claude Code's OAuth.

Usage:
    Run via Claude Code: /schedule or RemoteTrigger
    Manual: claude -p "run the granola sync" (from pulse repo)
"""

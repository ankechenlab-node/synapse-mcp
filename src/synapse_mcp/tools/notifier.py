"""MCP Tools: Progress notification via webhooks.

Supports Telegram, Feishu (飞书), and generic JSON webhooks.
All optional — if webhook not configured, notifications are silently skipped.
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

# Config file: ~/.synapse/notifications.json
_CONFIG_PATH = Path.home() / ".synapse" / "notifications.json"


def _load_config() -> dict:
    """Load notification config, return empty dict if not found."""
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _send_webhook(url: str, payload: dict, timeout: int = 10) -> bool:
    """Send a POST webhook. Returns True on success."""
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 400
    except Exception:
        return False  # silently skip failures


def _format_telegram_message(text: str) -> dict:
    return {"text": f"Synapse:\n{text}", "parse_mode": "HTML"}


def _format_feishu_message(text: str) -> dict:
    return {
        "msg_type": "text",
        "content": {"text": f"Synapse: {text}"},
    }


def _send_notification(text: str, channel: str | None = None) -> str:
    """Send notification to all configured channels."""
    config = _load_config()
    if not config:
        return (
            "No notification channels configured.\n"
            f"Create {_CONFIG_PATH} with your webhook URLs.\n"
            "See: /synapse-notifier config"
        )

    channels = config.get("channels", {})
    results = []

    for name, cfg in channels.items():
        if channel and name != channel:
            continue

        url = cfg.get("url")
        if not url:
            results.append(f"  {name}: no URL configured")
            continue

        kind = cfg.get("type", "generic")
        if kind == "telegram":
            payload = _format_telegram_message(text)
        elif kind == "feishu":
            payload = _format_feishu_message(text)
        else:
            payload = {"message": text}

        success = _send_webhook(url, payload)
        results.append(f"  {name}: {'sent' if success else 'failed'}")

    return f"Notification results:\n" + "\n".join(results)


def register_notifier_tools(mcp: FastMCP):
    """Register notification tools."""

    @mcp.tool(annotations=ToolAnnotations(
        title="Send Notification",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ))
    def send_notification(text: str, channel: str | None = None) -> str:
        """Send a progress notification via configured webhooks.

        Args:
            text: Message to send
            channel: Specific channel name (optional, sends to all if omitted)
        """
        return _send_notification(text, channel)

    @mcp.tool(annotations=ToolAnnotations(
        title="Notifier Config",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ))
    def notifier_config() -> str:
        """Show current notification configuration."""
        config = _load_config()
        if not config:
            return (
                "No notification configuration found.\n\n"
                f"Create {_CONFIG_PATH}:\n\n"
                "{\n"
                '  "channels": {\n'
                '    "telegram": {\n'
                '      "type": "telegram",\n'
                '      "url": "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>"\n'
                "    },\n"
                '    "feishu": {\n'
                '      "type": "feishu",\n'
                '      "url": "https://open.feishu.cn/open-apis/bot/v2/hook/<HOOK_ID>"\n'
                "    }\n"
                "  }\n"
                "}"
            )
        channels = config.get("channels", {})
        lines = ["Notification channels:", ""]
        for name, cfg in channels.items():
            kind = cfg.get("type", "generic")
            url = cfg.get("url", "not set")
            # Mask URL for privacy
            masked = url[:20] + "..." if len(url) > 20 else url
            lines.append(f"  {name} ({kind}): {masked}")
        return "\n".join(lines)

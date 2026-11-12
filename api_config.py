import json
import logging
import random
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_ID
from emojis import PremiumEmoji as E

logger = logging.getLogger(__name__)
_CONFIG_PATH = Path(__file__).resolve().parent / "api_config.json"
_DEFAULT_ENDPOINT = ""
_DEFAULT_SITE_ENABLED = True

_current_endpoint = None
_current_site_enabled = None


def _load():
    global _current_endpoint, _current_site_enabled
    if _current_endpoint is not None:
        return _current_endpoint
    try:
        if _CONFIG_PATH.exists():
            d = json.loads(_CONFIG_PATH.read_text())
            _current_endpoint = d.get("endpoint", _DEFAULT_ENDPOINT)
            _current_site_enabled = bool(d.get("site_enabled", _DEFAULT_SITE_ENABLED))
        else:
            _current_endpoint = _DEFAULT_ENDPOINT
            _current_site_enabled = _DEFAULT_SITE_ENABLED
    except Exception:
        _current_endpoint = _DEFAULT_ENDPOINT
        _current_site_enabled = _DEFAULT_SITE_ENABLED
    return _current_endpoint


def _save():
    try:
        _CONFIG_PATH.write_text(json.dumps({
            "endpoint": _current_endpoint,
            "site_enabled": bool(_current_site_enabled),
        }, indent=2))
    except Exception:
        pass


def _normalize(url):
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url


def get_api_endpoint():
    """Priority:
    1. If any LB node is enabled → random pick from LB pool.
    2. Else → manual override from /capi (api_config.json).
    """
    try:
        from database import get_enabled_lb_nodes
        nodes = get_enabled_lb_nodes()
        if nodes:
            return random.choice(nodes)
    except Exception:
        pass
    return _load()


def get_api_endpoints():
    """All live endpoints in priority order (LB first, then manual)."""
    out = []
    try:
        from database import get_enabled_lb_nodes
        out = get_enabled_lb_nodes() or []
    except Exception:
        pass
    manual = _load()
    if manual:
        out.append(manual)
    return out or [_DEFAULT_ENDPOINT]


def is_site_enabled():
    _load()
    return bool(_current_site_enabled) if _current_site_enabled is not None else _DEFAULT_SITE_ENABLED


def _set(url):
    global _current_endpoint
    _current_endpoint = url
    _save()


def _set_site(enabled):
    global _current_site_enabled
    _current_site_enabled = bool(enabled)
    _save()


async def handle_capi(update, context):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        await update.message.reply_text(
            f"<blockquote>{E.ERROR} <b>Owner Only</b></blockquote>", parse_mode="HTML")
        return

    if not context.args:
        st = f"{E.APPROVED} ON" if is_site_enabled() else f"{E.ERROR} OFF"
        lb_info = ""
        try:
            from database import get_enabled_lb_nodes
            lb = get_enabled_lb_nodes()
            lb_info = f"\n{E.GLOBE} <b>LB nodes live:</b> <code>{len(lb)}</code>"
        except Exception:
            pass
        await update.message.reply_text(
            f"<blockquote>{E.GLOBE} <b>Global API</b></blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E.LINK} <b>Manual</b> ➠ <code>{get_api_endpoint()}</code>\n"
            f"{E.SETTINGS} <b>Site</b> ➠ {st}"
            f"{lb_info}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<code>/capi URL</code> — set manual\n"
            f"<code>/capi URL on</code> — set + site ON\n"
            f"<code>/capi URL off</code> — set + site OFF\n\n"
            f"<i>If LB pool is populated, manual URL is ignored unless LB is empty.</i>",
            parse_mode="HTML", disable_web_page_preview=True)
        return

    url = _normalize(context.args[0])
    if len(context.args) >= 2:
        flag = context.args[1].strip().lower()
        if flag not in ("on", "off"):
            await update.message.reply_text(
                f"{E.WARNING} Use <code>on</code> or <code>off</code>", parse_mode="HTML")
            return
        _set_site(flag == "on")
    _set(url)
    st = f"{E.APPROVED} ON" if is_site_enabled() else f"{E.ERROR} OFF"
    await update.message.reply_text(
        f"<blockquote>{E.SUCCESS} <b>Updated</b></blockquote>\n"
        f"{E.LINK} <b>URL</b> ➠ <code>{get_api_endpoint()}</code>\n"
        f"{E.SETTINGS} <b>Site</b> ➠ {st}",
        parse_mode="HTML", disable_web_page_preview=True)


async def handle_cafi(update, context):
    await handle_capi(update, context)


def register_capi(app):
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("capi", handle_capi))
    app.add_handler(CommandHandler("cafi", handle_cafi))

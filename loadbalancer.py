"""loadbalancer.py — LB node management + health monitor"""

import time
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import aiohttp

from config import OWNER_ID
from emojis import PremiumEmoji as E
from database import (
    add_lb_node, get_all_lb_nodes, get_lb_node,
    toggle_lb_node, delete_lb_node, update_lb_health,
)

logger = logging.getLogger(__name__)


async def _health(url, timeout=8):
    try:
        t = aiohttp.ClientTimeout(total=timeout, connect=timeout)
        async with aiohttp.ClientSession(timeout=t) as s:
            start = time.time()
            async with s.get(url, ssl=False) as r:
                ms = int((time.time() - start) * 1000)
                return {"ok": r.status < 500, "status": r.status, "ms": ms}
    except Exception as e:
        return {"ok": False, "error": str(e)[:60]}


async def lb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    nodes = get_all_lb_nodes()
    if not nodes:
        await update.message.reply_text(
            f"<blockquote>{E.INFO} <b>No Load Balancer Nodes</b></blockquote>\n\n"
            f"<code>/lbadd NAME URL</code>\n"
            f"<i>When ≥1 node is enabled, API calls rotate through them.</i>",
            parse_mode="HTML")
        return
    lines = []
    for n in nodes:
        status = "🟢 ON" if n["enabled"] else "🔴 OFF"
        lines.append(f"<b>{status}</b> · <code>{n['name']}</code>\n"
                     f"  ID: <code>{n['id']}</code> · {n['url'][:55]}")
    text = (
        f"<blockquote>{E.GLOBE} <b>Load Balancer Nodes</b></blockquote>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(lines) +
        f"\n━━━━━━━━━━━━━━━━━━\n"
        f"<code>/lbadd NAME URL</code>\n"
        f"<code>/lbtoggle ID</code>\n"
        f"<code>/lbdel ID</code>\n"
        f"<code>/lbmonitor</code>"
    )
    await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)


async def lbadd_command(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text(f"{E.INFO} <code>/lbadd NAME URL</code>", parse_mode="HTML")
        return
    name = context.args[0]
    url = context.args[1].strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    if add_lb_node(name, url):
        await update.message.reply_text(
            f"{E.SUCCESS} Added <code>{name}</code> → <code>{url}</code>",
            parse_mode="HTML", disable_web_page_preview=True)
    else:
        await update.message.reply_text(f"{E.ERROR} Failed or duplicate.", parse_mode="HTML")


async def lbtoggle_command(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text(f"{E.INFO} <code>/lbtoggle ID</code>", parse_mode="HTML")
        return
    try:
        nid = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"{E.ERROR} Invalid ID.", parse_mode="HTML")
        return
    node = get_lb_node(nid)
    if not node:
        await update.message.reply_text(f"{E.ERROR} Not found.", parse_mode="HTML")
        return
    new = toggle_lb_node(nid)
    await update.message.reply_text(
        f"{E.SUCCESS} <code>{node['name']}</code> → {'ON 🟢' if new else 'OFF 🔴'}",
        parse_mode="HTML")


async def lbdel_command(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text(f"{E.INFO} <code>/lbdel ID</code>", parse_mode="HTML")
        return
    try:
        nid = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"{E.ERROR} Invalid ID.", parse_mode="HTML")
        return
    if delete_lb_node(nid):
        await update.message.reply_text(f"{E.SUCCESS} Deleted.", parse_mode="HTML")
    else:
        await update.message.reply_text(f"{E.ERROR} Failed.", parse_mode="HTML")


async def lbmonitor_command(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    nodes = get_all_lb_nodes()
    if not nodes:
        await update.message.reply_text(f"{E.INFO} No nodes.", parse_mode="HTML")
        return
    msg = await update.message.reply_text(
        f"{E.FLY} Checking {len(nodes)} nodes...", parse_mode="HTML")
    results = []
    for n in nodes:
        r = await _health(n["url"])
        update_lb_health(n["id"], 1 if r["ok"] else 0)
        results.append((n, r))
    lines = []
    for n, r in results:
        if r["ok"]:
            lines.append(f"🟢 <code>{n['name']}</code> · {r['ms']}ms · HTTP {r['status']}")
        else:
            lines.append(f"🔴 <code>{n['name']}</code> · {r.get('error','?')[:50]}")
    text = (
        f"<blockquote>{E.STATS} <b>LB Health Monitor</b></blockquote>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(lines) +
        f"\n━━━━━━━━━━━━━━━━━━\n"
        f"<i>Checked at {datetime.now().strftime('%H:%M:%S')}</i>"
    )
    try:
        await msg.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)


def register_lb(app):
    app.add_handler(CommandHandler("lb", lb_command))
    app.add_handler(CommandHandler("lbadd", lbadd_command))
    app.add_handler(CommandHandler("lbtoggle", lbtoggle_command))
    app.add_handler(CommandHandler("lbdel", lbdel_command))
    app.add_handler(CommandHandler("lbmonitor", lbmonitor_command))
    logger.info("✅ /lb registered")

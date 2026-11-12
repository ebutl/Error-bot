"""redeem.py — Claim codes with 𒉼- prefix support"""

import logging
import random
import string
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (
    get_redeem_code_info, mark_redeem_code_as_used,
    save_redeem_code, update_user_plan, update_user_credits,
    has_user_active_plan, is_db_admin,
)
from config import OWNER_ID, OWNER_NAME, KEY_PREFIX
from emojis import PremiumEmoji as E

logger = logging.getLogger(__name__)
ADMIN_IDS = [OWNER_ID]

PLANS = {
    "Core":  {"tier": "Core",  "duration_days": 7,  "emoji": "🛠️"},
    "Elite": {"tier": "Elite", "duration_days": 15, "emoji": "👑"},
    "Root":  {"tier": "Root",  "duration_days": 30, "emoji": "⭐"},
    "X":     {"tier": "X",     "duration_days": 90, "emoji": "💎"},
}

active_requests = {}

PREFIXES = (KEY_PREFIX + "-", "CXGFT-", "SPITZ-")  # current + legacy


def is_admin(uid):
    if uid in ADMIN_IDS:
        return True
    try:
        return is_db_admin(uid)
    except Exception:
        return False


def _gen_code():
    alphabet = string.ascii_uppercase + string.digits
    b1 = ''.join(random.choices(alphabet, k=4))
    b2 = ''.join(random.choices(alphabet, k=4))
    return f"{KEY_PREFIX}-{b1}-{b2}"


async def handle_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            f"<blockquote>{E.INFO} <b>Claim Code</b></blockquote>\n\n"
            f"<code>/claim {KEY_PREFIX}-XXXX-XXXX</code>",
            parse_mode=ParseMode.HTML)
        return

    code = context.args[0].strip().upper()

    if not any(code.startswith(p) for p in PREFIXES):
        await update.message.reply_text(
            f"<blockquote>{E.ERROR} <b>Invalid Format</b></blockquote>\n\n"
            f"{E.INFO} <i>Codes start with</i> <code>{KEY_PREFIX}-</code>",
            parse_mode=ParseMode.HTML)
        return

    uid = update.effective_user.id

    if uid in active_requests and active_requests[uid]:
        await update.message.reply_text("⏳ Wait.", parse_mode=ParseMode.HTML)
        return

    active_requests[uid] = True
    proc = await update.message.reply_text(
        f"<blockquote>🔄 <b>Validating...</b></blockquote>\n<pre>{code}</pre>",
        parse_mode=ParseMode.HTML)

    try:
        info = get_redeem_code_info(code)
        if not info:
            await proc.edit_text(
                f"<blockquote>{E.ERROR} <b>Invalid Code</b></blockquote>\n"
                f"<code>{code}</code>",
                parse_mode=ParseMode.HTML)
            return

        tier = info["tier"]
        dur = info["duration_days"]

        if tier == "Credits":
            update_user_credits(uid, 100)
            mark_redeem_code_as_used(code, uid)
            await proc.edit_text(
                f"<blockquote>{E.SUCCESS} <b>Redeemed</b></blockquote>\n"
                f"{E.PREMIUM} <b>Type:</b> <code>100 Credits</code>",
                parse_mode=ParseMode.HTML)
            return

        if uid != OWNER_ID and has_user_active_plan(uid):
            await proc.edit_text(
                f"<blockquote>{E.ERROR} <b>Active Plan</b></blockquote>\n"
                f"<i>You already have an active plan.</i>",
                parse_mode=ParseMode.HTML)
            return

        exp = datetime.now() + timedelta(days=dur)
        success = update_user_plan(uid, tier, exp)

        if success:
            mark_redeem_code_as_used(code, uid)
            pi = PLANS.get(tier, {"emoji": "⭐"})
            await proc.edit_text(
                f"<blockquote>{E.SUCCESS} <b>Redeemed</b></blockquote>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E.KEY} <b>Code:</b> <code>{code}</code>\n"
                f"{E.STAR} <b>Tier:</b> {pi['emoji']} <code>{tier}</code>\n"
                f"{E.CLOCK} <b>Days:</b> <code>{dur}</code>\n"
                f"{E.CALANDER} <b>Expires:</b> <code>{exp.strftime('%Y-%m-%d %H:%M')}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E.APPROVED} <b>Unlimited credits</b>\n"
                f"{E.LINK} <b>Dev</b> ➠ {OWNER_NAME}",
                parse_mode=ParseMode.HTML)
        else:
            await proc.edit_text(
                f"<blockquote>{E.ERROR} <b>Failed</b></blockquote>",
                parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"claim: {e}")
        try:
            await proc.edit_text(f"{E.ERROR} {e}", parse_mode=ParseMode.HTML)
        except Exception:
            pass
    finally:
        active_requests[uid] = False


async def handle_gplan1(update, context): await _gen_plan(update, context, "Core")
async def handle_gplan2(update, context): await _gen_plan(update, context, "Elite")
async def handle_gplan3(update, context): await _gen_plan(update, context, "Root")
async def handle_gplan4(update, context): await _gen_plan(update, context, "X")


async def _gen_plan(update, context, tier):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(f"{E.ERROR} Admin only.", parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text("<code>/gplan N</code>", parse_mode=ParseMode.HTML)
        return
    try:
        count = int(context.args[0])
        if count <= 0 or count > 50:
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"{E.ERROR} Count 1-50.", parse_mode=ParseMode.HTML)
        return

    plan = PLANS.get(tier)
    if not plan:
        return

    codes = []
    for _ in range(count):
        c = _gen_code()
        if save_redeem_code(c, plan["tier"], plan["duration_days"]):
            codes.append(c)
    ct = "\n".join(f"<code>{c}</code>" for c in codes)
    await update.message.reply_text(
        f"<blockquote>{E.SUCCESS} <b>Codes Generated</b></blockquote>\n"
        f"{E.STAR} <b>Tier:</b> {plan['emoji']} {tier}\n"
        f"{E.STATS} <b>Count:</b> <code>{len(codes)}</code>\n\n"
        f"<pre>{ct}</pre>",
        parse_mode=ParseMode.HTML)


async def handle_gcodes(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(f"{E.ERROR} Admin only.", parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text("<code>/gcodes N</code>", parse_mode=ParseMode.HTML)
        return
    try:
        count = int(context.args[0])
        if count <= 0 or count > 50:
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"{E.ERROR} Count 1-50.", parse_mode=ParseMode.HTML)
        return
    codes = []
    for _ in range(count):
        c = _gen_code()
        if save_redeem_code(c, "Credits", 0):
            codes.append(c)
    ct = "\n".join(f"<code>{c}</code>" for c in codes)
    await update.message.reply_text(
        f"<blockquote>{E.SUCCESS} <b>Credits Codes</b></blockquote>\n"
        f"{E.PREMIUM} <b>Type:</b> <code>100 Credits</code>\n"
        f"{E.STATS} <b>Count:</b> <code>{len(codes)}</code>\n\n"
        f"<pre>{ct}</pre>",
        parse_mode=ParseMode.HTML)

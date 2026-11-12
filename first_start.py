"""first_start.py — Pinned welcome on first /start"""

import logging
from database import has_seen_first_start, mark_first_start_seen
from config import BOT_NAME, FIRST_START_IMAGE, OWNER_NAME
from emojis import PremiumEmoji as E

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    f"<blockquote><b>{BOT_NAME}</b> ✦ WELCOME</blockquote>\n"
    f"━━━━━━━━━━━━━━━━━━\n"
    f"• <b>BOT IS STEALER LESS</b>\n"
    f"• <b>SO IT'S PAID ONLY</b>\n"
    f"• <b>FUCK HATER'S</b>\n"
    f"━━━━━━━━━━━━━━━━━━\n"
    f"{E.STAR} <b>Buy Access</b> ➠ /pay\n"
    f"{E.INFO} <b>Contact Dev</b> ➠ /mdev &lt;message&gt;\n"
    f"━━━━━━━━━━━━━━━━━━\n"
    f"<i>This message was pinned for you.</i>"
)


async def send_first_start(bot, chat_id, user_id):
    try:
        if has_seen_first_start(user_id):
            return
    except Exception:
        return
    try:
        mark_first_start_seen(user_id)
    except Exception:
        pass
    try:
        try:
            msg = await bot.send_photo(
                chat_id=chat_id, photo=FIRST_START_IMAGE,
                caption=WELCOME_TEXT, parse_mode="HTML")
        except Exception:
            msg = await bot.send_message(
                chat_id=chat_id, text=WELCOME_TEXT, parse_mode="HTML")
        try:
            await bot.pin_chat_message(
                chat_id=chat_id, message_id=msg.message_id,
                disable_notification=True)
        except Exception as e:
            logger.warning(f"first_start pin: {e}")
    except Exception as e:
        logger.error(f"first_start send: {e}")

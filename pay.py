"""pay.py — /pay command + owner /setpay setup"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_bot_setting, set_bot_setting
from config import OWNER_ID, BOT_NAME, KEY_PREFIX
from emojis import PremiumEmoji as E

logger = logging.getLogger(__name__)


async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btc = get_bot_setting("pay_btc", "") or "Not set"
    ltc = get_bot_setting("pay_ltc", "") or "Not set"
    eth = get_bot_setting("pay_eth", "") or "Not set"
    usdt = get_bot_setting("pay_usdt", "") or "Not set"
    extra = get_bot_setting("pay_extra", "") or ""
    price = get_bot_setting("pay_price", "") or "$25 / 30d"

    text = (
        f"<blockquote>{E.MONEY} <b>{BOT_NAME} | PAYMENT</b></blockquote>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E.STAR} <b>Plan:</b> <code>{price}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>BTC:</b>\n<code>{btc}</code>\n\n"
        f"<b>LTC:</b>\n<code>{ltc}</code>\n\n"
        f"<b>ETH:</b>\n<code>{eth}</code>\n\n"
        f"<b>USDT (TRC20):</b>\n<code>{usdt}</code>\n"
    )
    if extra:
        text += f"━━━━━━━━━━━━━━━━━━\n{extra}\n"
    text += (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E.INFO} <b>After payment:</b>\n"
        f"1. Send screenshot proof via <code>/mdev</code>\n"
        f"2. Dev verifies and sends a key like:\n"
        f"   <code>{KEY_PREFIX}-ABCD-1234</code>\n"
        f"3. Redeem with <code>/claim {KEY_PREFIX}-ABCD-1234</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>No stealer. Paid only. Real usage.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def setpay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            f"<blockquote>{E.INFO} <b>Set Payment Details</b></blockquote>\n\n"
            f"<code>/setpay btc ADDRESS</code>\n"
            f"<code>/setpay ltc ADDRESS</code>\n"
            f"<code>/setpay eth ADDRESS</code>\n"
            f"<code>/setpay usdt ADDRESS</code>\n"
            f"<code>/setpay price $25 / 30d</code>\n"
            f"<code>/setpay extra any note</code>\n"
            f"<code>/setpay clear</code>",
            parse_mode="HTML")
        return
    key = context.args[0].lower()
    value = " ".join(context.args[1:])
    if key == "clear":
        for k in ["btc", "ltc", "eth", "usdt", "price", "extra"]:
            set_bot_setting(f"pay_{k}", "")
        await update.message.reply_text(f"{E.SUCCESS} Cleared.", parse_mode="HTML")
        return
    if key not in ("btc", "ltc", "eth", "usdt", "price", "extra"):
        await update.message.reply_text(f"{E.ERROR} Invalid key.", parse_mode="HTML")
        return
    set_bot_setting(f"pay_{key}", value)
    await update.message.reply_text(
        f"{E.SUCCESS} <code>pay_{key}</code> updated.", parse_mode="HTML")


def register_pay(app):
    app.add_handler(CommandHandler("pay", pay_command))
    app.add_handler(CommandHandler("setpay", setpay_command))
    logger.info("✅ /pay registered")

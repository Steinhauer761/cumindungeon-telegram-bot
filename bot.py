import asyncio
import logging
import os
import re

from supabase import Client, create_client
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
supabase: Client | None = None

WELCOME = (
    "🔥 *WELCOME TO CUMINDUNGEON*\n\n"
    "An adults-only virtual club is coming.\n\n"
    "Explore a dark, theatrical world of live entertainment, themed rooms, "
    "performers, private experiences, VIP access and social interaction.\n\n"
    "🏰 Virtual rooms\n🔥 Live entertainment\n👑 VIP experiences\n"
    "💬 Social & private interaction\n🎟️ Membership & exclusive access\n\n"
    "We're getting ready to open the doors.\n\n"
    "You must be 18+ to join the pre-launch list."
)


def referral_code(user_id: int) -> str:
    return f"u{user_id}"


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value.strip()))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["referral_code"] = context.args[0] if context.args else None
    keyboard = [
        [InlineKeyboardButton("🔞 I'm 18+ • Join Waitlist", callback_data="age_yes")],
        [InlineKeyboardButton("Learn About CumInDungeon", callback_data="about")],
    ]
    await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "about":
        keyboard = [[InlineKeyboardButton("🔞 I'm 18+ • Join Waitlist", callback_data="age_yes")]]
        await query.edit_message_text(
            "CumInDungeon is an adults-only virtual entertainment and social club built around live experiences, "
            "themed rooms, performers, private experiences and VIP access.\n\nThe site is preparing for launch. "
            "Join the list to hear when the doors open.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif query.data == "age_yes":
        context.user_data["age_confirmed"] = True
        context.user_data["state"] = "name"
        await query.edit_message_text("Perfect. Let's get you on the pre-launch list.\n\n👤 *What's your name?*", parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not context.user_data.get("age_confirmed"):
        await update.message.reply_text("Please use /start and confirm that you are 18+ before joining the list.")
        return

    text = update.message.text.strip()
    state = context.user_data.get("state")

    if state == "name":
        if not 2 <= len(text) <= 100:
            await update.message.reply_text("Please enter a valid name.")
            return
        context.user_data["name"] = text
        context.user_data["state"] = "email"
        await update.message.reply_text("📧 Now enter your email address:")
        return

    if state != "email":
        await update.message.reply_text("Use /start to begin.")
        return

    if not valid_email(text):
        await update.message.reply_text("❌ That doesn't look like a valid email. Please try again.")
        return

    user = update.effective_user
    payload = {
        "telegram_user_id": user.id,
        "telegram_username": user.username,
        "name": context.user_data["name"],
        "email": text.lower(),
        "referral_code": referral_code(user.id),
        "referred_by": context.user_data.get("referral_code"),
        "age_confirmed": True,
    }

    try:
        supabase.table("pre_signups").upsert(payload, on_conflict="telegram_user_id").execute()
    except Exception:
        logger.exception("Could not save signup")
        await update.message.reply_text("I couldn't save your signup right now. Please try again in a moment.")
        return

    bot = await context.bot.get_me()
    share_link = f"https://t.me/{bot.username}?start={referral_code(user.id)}"
    context.user_data.clear()
    await update.message.reply_text(
        "🎉 *You're on the list!*\n\n"
        "You're officially registered for early access to CumInDungeon.\n\n"
        "👥 *Invite friends*\n"
        f"{share_link}\n\n"
        "Share your link and help bring people through the doors.",
        parse_mode="Markdown",
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_TELEGRAM_ID or str(update.effective_user.id) != ADMIN_TELEGRAM_ID:
        return
    try:
        result = supabase.table("pre_signups").select("id", count="exact").execute()
        await update.message.reply_text(f"📊 Pre-signups: {result.count or 0}")
    except Exception:
        logger.exception("Stats failed")
        await update.message.reply_text("Couldn't retrieve stats.")


def main():
    global supabase
    missing = [k for k, v in {
        "TELEGRAM_BOT_TOKEN": TOKEN,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_KEY,
    }.items() if not v]
    if missing:
        raise RuntimeError("Missing environment variables: " + ", ".join(missing))

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("CumInDungeon bot starting")

    # Python 3.14 no longer creates a default event loop automatically.
    # python-telegram-bot's polling startup expects one to exist.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app.run_polling()


if __name__ == "__main__":
    main()

from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from src.config.settings import Config

TOKEN = Config.TELEGRAM_TOKEN

bot = Bot(TOKEN)
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

async def start(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id
    username = update.effective_user.username

    # Check if a referral user ID was provided as an argument
    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0])
            # Here you might validate if referrer_id exists in the database
            # If valid, save referral data; otherwise, ignore
        except ValueError:
            await update.message.reply_text("Invalid referral code.")

    # Generate a referral link with the current user's Telegram ID
    referral_link = f"https://t.me/{bot.username}?start={telegram_id}"

    # Reply to the user with a welcome message and their unique referral link
    await update.message.reply_text(
        f"Hello, {username}! Welcome to the FastAPI Chatbot.\n"
        f"Share this referral link to invite others: {referral_link}"
    )
    
    # Optionally, notify the referrer if this is a referral registration
    if referrer_id is not None:
        await update.message.reply_text(f"You were referred by user with ID {referrer_id}.")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

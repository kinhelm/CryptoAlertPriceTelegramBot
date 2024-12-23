import logging

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

coinmarketcap_api_key = os.getenv('COINMARKETCAP_API_KEY')
token = os.getenv('TELEGRAM_BOT_TOKEN')

from models.Alert import Alert
from models.User import User
from models.base import Base

logger = logging.getLogger(__name__)
reply_keyboard = [
    ["add"],
]
reply_direction = [
    ["greater", 'lower'],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
ACTION, TYPING_COIN, TYPING_DIRECTION, TYPING_PRICE, TYPING_REMOVE_ID = range(5)
engine = create_engine("sqlite:///mydb.db", echo=True)

Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

alert = Alert
coinmarketcap_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Register a user"""
    user = session.scalars(select(User).filter_by(id_telegram=update.message.from_user.id)).first()
    if user is None:
        user = User(
            id_telegram=update.message.from_user.id,
            firstname=update.message.from_user.first_name,
            chat_id=update.message.chat_id
        )
        session.add(user)
        session.commit()

    await update.message.reply_text(
        f"Hello {user.firstname} !",
    )


async def add_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global alert
    alert = Alert()
    user = session.scalars(select(User).filter_by(id_telegram=update.message.from_user.id)).first()
    alert.user_id = user.id
    await update.message.reply_text(
        "Enter the token's symbol (BTC, ETH etc...)"
    )

    return TYPING_COIN


async def add_coin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global alert
    alert.symbol = update.message.text
    await update.message.reply_text(
        "Choose condition (lower or greater)",
        reply_markup=ReplyKeyboardMarkup(reply_direction, one_time_keyboard=True),
    )

    return TYPING_DIRECTION


async def add_direction_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global alert
    alert.direction = update.message.text
    await update.message.reply_text(
        "Enter target price"
    )

    return TYPING_PRICE


async def add_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global alert
    alert.target_price = update.message.text
    await update.message.reply_text(
        "Alert created"
    )

    session.add(alert)
    session.commit()

    return ConversationHandler.END


async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job
    print(context.user_data)
    await context.bot.send_message(job.chat_id, text=f"Beep! {job.data} seconds are over!")


async def list_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the user's list of alarm ."""
    user = session.scalars(select(User).filter_by(id_telegram=update.message.chat_id)).first()
    await update.message.reply_text(
        ',\n'.join(map(str, user.alerts))
    )


async def delete_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Delete an alert by database ID."""
    command, alert_id = update.message.text.split()
    user = session.scalars(select(User).filter_by(id_telegram=update.message.from_user.id)).first()
    alert = session.scalars(select(Alert).filter_by(id=alert_id, user_id=user.id)).first()
    if alert is not None:
        session.delete(alert)
        session.commit()
        await update.message.reply_text("Alert deleted successfully")
    else:
        await update.message.reply_text("Alert not found")
    return ConversationHandler.END


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    if "choice" in user_data:
        del user_data["choice"]

    user_data.clear()
    return ConversationHandler.END


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def alerting(context: ContextTypes.DEFAULT_TYPE):
    alerts = session.query(Alert, User).join(User)

    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': coinmarketcap_api_key,
    }

    for alert_local, user in alerts:
        params = {
            'symbol': alert_local.symbol,
        }
        resp = requests.get(coinmarketcap_url, headers=headers, params=params)

        if resp.status_code == 200:
            data = resp.json()
            current_price = float(data['data'][alert_local.symbol]['quote']['USD']['price'])

            if alert_local.direction == 'lower':
                if current_price <= alert_local.target_price:
                    await context.bot.send_message(chat_id=user.chat_id,
                                                   text=f'{alert_local.symbol} <= {alert_local.target_price}')
                    session.query(Alert).filter(Alert.id == alert_local.id).delete()
            elif alert_local.direction == 'greater':
                if current_price >= alert_local.target_price:
                    await context.bot.send_message(chat_id=user.chat_id,
                                                   text=f'{alert_local.symbol} >= {alert_local.target_price}')
                    session.query(Alert).filter(Alert.id == alert_local.id).delete()

    session.commit()


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", register))
    application.add_handler(CommandHandler("list_alert", list_alert))
    application.add_handler(CommandHandler("delete_alert", delete_alert_command))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_alert", add_alert)],
        states={
            TYPING_COIN: [MessageHandler(filters.Regex("^(.*)$"), add_coin_command)],
            TYPING_DIRECTION: [MessageHandler(filters.Regex("^(greater|lower.*)$"), add_direction_command)],
            TYPING_PRICE: [MessageHandler(filters.Regex("^(.*)$"), add_price_command)],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)

    job_queue = application.job_queue
    job_queue.run_repeating(alerting, interval=300, first=0)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()

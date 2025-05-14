import os; os.environ["PORT"] = "10000"

import json
import logging
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from config import BOT_TOKEN, ADMIN_IDS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

DATA_FILE = "data.json"
scheduler = BackgroundScheduler()
scheduler.start()

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"tasks": {}, "streak": 0}
        save_data(data)
    await update.message.reply_text("Привет! Я помогу тебе фокусироваться каждый день.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("У тебя нет доступа к этой команде.")
        return
    data = load_data()
    message = "📊 Статистика всех пользователей:\n"
    for uid, user_data in data.items():
        streak = user_data.get("streak", 0)
        tasks_today = user_data.get("tasks", {}).get(today_str(), [])
        message += f"👤 {uid}: streak {streak}, задач сегодня: {len(tasks_today)}\n"
    await update.message.reply_text(message)

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    data = load_data()
    tasks = data.get(user_id, {}).get("tasks", {})
    today = today_str()
    if today not in tasks:
        tasks[today] = []
    if len(tasks[today]) < 3:
        tasks[today].append(text)
        data[user_id]["tasks"] = tasks
        save_data(data)
        await update.message.reply_text(f"Задача сохранена: {text}")
    else:
        await update.message.reply_text("Ты уже добавил 3 задачи на сегодня.")

def schedule_messages(app):
    async def send_morning():
        for user_id in load_data():
            try:
                await app.bot.send_message(chat_id=int(user_id),
                                           text="🕚 Утро! Введи 3 главные задачи дня:")
            except Exception as e:
                logging.error(f"Ошибка отправки: {e}")

    async def send_afternoon():
        data = load_data()
        for user_id, user_data in data.items():
            tasks = user_data.get("tasks", {}).get(today_str(), [])
            message = "🕑 Напоминание:\n" + "\n".join([f"{i+1}. {t}" for i, t in enumerate(tasks)])
            try:
                await app.bot.send_message(chat_id=int(user_id), text=message)
            except Exception as e:
                logging.error(f"Ошибка отправки: {e}")

    async def send_evening():
        for user_id in load_data():
            try:
                await app.bot.send_message(
                    chat_id=int(user_id),
                    text="🕗 День заканчивается. Что сделал сегодня?\n✔ Что сделал:\n⏳ Что не успел:\n📈 Вывод:"
                )
            except Exception as e:
                logging.error(f"Ошибка отправки: {e}")

    scheduler.add_job(lambda: app.create_task(send_morning()), "cron", hour=11)
    scheduler.add_job(lambda: app.create_task(send_afternoon()), "cron", hour=14)
    scheduler.add_job(lambda: app.create_task(send_evening()), "cron", hour=20)

def run_dummy_server():
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running.")
    server = HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), DummyHandler)
    server.serve_forever()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    schedule_messages(app)

    # Запускаем фоновый HTTP-сервер, чтобы Render видел "порт"
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # Запускаем Telegram-бота
    app.run_polling()

if __name__ == "__main__":
    main()

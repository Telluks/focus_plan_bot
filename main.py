import os; os.environ["PORT"] = "10000"

import json
import logging
import threading
import asyncio
import nest_asyncio
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from config import BOT_TOKEN, ADMIN_IDS

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

DATA_FILE = "data.json"
scheduler = BackgroundScheduler()
scheduler.start()

def today_str(offset=0):
    return (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

async def set_commands(app):
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("addmain", "Добавить основную задачу"),
        BotCommand("addextra", "Добавить дополнительную задачу"),
        BotCommand("mytasks", "Показать мои задачи"),
        BotCommand("complete_main", "Завершить основную задачу"),
        BotCommand("complete_extra", "Завершить дополнительную задачу"),
        BotCommand("delete_main", "Удалить основную задачу"),
        BotCommand("delete_extra", "Удалить дополнительную задачу"),
        BotCommand("reset", "Сбросить задачи"),
        BotCommand("stats", "Статистика"),
        BotCommand("admin", "Статистика по пользователям (только админ)")
    ]
    await app.bot.set_my_commands(commands)

# Остальной код тот же, можно добавить снова при необходимости
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await set_commands(app)
    run_dummy_server()
    await app.run_polling()

def run_dummy_server():
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running.")
    server = HTTPServer(("0.0.0.0", int(os.environ["PORT"])), DummyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())

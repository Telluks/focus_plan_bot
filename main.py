import os; os.environ["PORT"] = "10000"

import json
import logging
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"tasks": {}, "stats": {}}
        save_data(data)
    await update.message.reply_text("Привет! Я помогу тебе вести ежедневный план задач.\nНапиши до 3 основных задач и дополнительные через /добавить_доп.")

async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    tasks = data.get(user_id, {}).get("tasks", {}).get(today, {"main": [], "extra": []})
    msg = "📋 Твои задачи на сегодня:\n\n"
    msg += "🌟 Основные задачи:\n" + "\n".join([f"{i+1}. {'✅ ' if t['done'] else '❌ '} {t['text']}" for i, t in enumerate(tasks.get("main", []))]) or "—"
    msg += "\n\n➕ Дополнительные задачи:\n" + "\n".join([f"{i+1}. {'✅ ' if t['done'] else '❌ '} {t['text']}" for i, t in enumerate(tasks.get("extra", []))]) or "—"
    await update.message.reply_text(msg)

async def add_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    today = today_str()
    task_text = " ".join(context.args)
    if not task_text:
        await update.message.reply_text("Напиши дополнительную задачу после команды.")
        return
    task = {"text": task_text, "done": False}
    data.setdefault(user_id, {"tasks": {}, "stats": {}})
    data[user_id]["tasks"].setdefault(today, {"main": [], "extra": []})
    data[user_id]["tasks"][today]["extra"].append(task)
    save_data(data)
    await update.message.reply_text(f"Добавлена доп. задача: {task_text}")

async def complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    all_tasks = data.get(user_id, {}).get("tasks", {}).get(today, {"main": [], "extra": []})
    args = context.args
    if not args or len(args) < 2 or args[0] not in ("основные", "доп"):
        await update.message.reply_text("Формат: /завершить основные 2 или /завершить доп 1")
        return
    list_name = "main" if args[0] == "основные" else "extra"
    try:
        idx = int(args[1]) - 1
        all_tasks[list_name][idx]["done"] = True
        save_data(data)
        await update.message.reply_text("Задача отмечена как выполненная.")
    except:
        await update.message.reply_text("Неверный номер задачи.")

async def reset_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    if user_id in data and today in data[user_id]["tasks"]:
        data[user_id]["tasks"][today] = {"main": [], "extra": []}
        save_data(data)
    await update.message.reply_text("Все задачи на сегодня сброшены.")

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("Формат: /удалить основные 1 или /удалить доп 2")
        return
    list_name = "main" if args[0] == "основные" else "extra"
    try:
        idx = int(args[1]) - 1
        del data[user_id]["tasks"][today][list_name][idx]
        save_data(data)
        await update.message.reply_text("Задача удалена.")
    except:
        await update.message.reply_text("Неверный номер.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    count = 0
    done = 0
    for date, sets in data.get(user_id, {}).get("tasks", {}).items():
        for task in sets.get("main", []) + sets.get("extra", []):
            count += 1
            if task["done"]:
                done += 1
    await update.message.reply_text(f"📊 Выполнено {done} из {count} задач за всё время.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_IDS:
        await update.message.reply_text("Нет доступа.")
        return
    data = load_data()
    msg = "📋 Общая статистика:\n"
    for uid, val in data.items():
        total = 0
        done = 0
        for day in val["tasks"].values():
            for task in day["main"] + day["extra"]:
                total += 1
                if task["done"]:
                    done += 1
        msg += f"👤 {uid}: {done}/{total} задач\n"
    await update.message.reply_text(msg)

def transfer_tasks():
    data = load_data()
    yesterday = today_str(-1)
    today = today_str()
    for user, udata in data.items():
        if yesterday in udata["tasks"]:
            for list_name in ["main", "extra"]:
                for task in udata["tasks"][yesterday][list_name]:
                    if not task["done"]:
                        data[user]["tasks"].setdefault(today, {"main": [], "extra": []})
                        data[user]["tasks"][today][list_name].append(task)
    save_data(data)

def schedule_jobs(app):
    scheduler.add_job(lambda: app.create_task(send_morning(app)), "cron", hour=11)
    scheduler.add_job(lambda: app.create_task(send_afternoon(app)), "cron", hour=14)
    scheduler.add_job(lambda: app.create_task(send_evening(app)), "cron", hour=20)
    scheduler.add_job(transfer_tasks, "cron", hour=5)

async def send_morning(app):
    for user in load_data():
        try:
            await app.bot.send_message(chat_id=int(user), text="🌅 Доброе утро! Введи 3 основные задачи.")
        except:
            pass

async def send_afternoon(app):
    for user in load_data():
        try:
            await app.bot.send_message(chat_id=int(user), text="🕑 Напоминание о задачах. Проверь прогресс.")
        except:
            pass

async def send_evening(app):
    for user in load_data():
        try:
            await app.bot.send_message(chat_id=int(user), text="🌇 Вечерний отчёт: что удалось сделать? Отметь выполненные задачи командой /завершить")
        except:
            pass

def run_dummy_server():
    class DummyHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running.")
    server = HTTPServer(("0.0.0.0", int(os.environ["PORT"])), DummyHandler)
    server.serve_forever()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("мои_задачи", my_tasks))
    app.add_handler(CommandHandler("добавить_доп", add_extra))
    app.add_handler(CommandHandler("удалить", delete_task))
    app.add_handler(CommandHandler("завершить", complete))
    app.add_handler(CommandHandler("сброс", reset_tasks))
    app.add_handler(CommandHandler("статистика", stats))
    app.add_handler(CommandHandler("admin", admin))
    schedule_jobs(app)
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app.run_polling()

if __name__ == "__main__":
    main()
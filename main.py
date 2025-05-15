import os; os.environ["PORT"] = "10000"

import json
import logging
import threading
import asyncio
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"tasks": {}, "stats": {}}
        save_data(data)
    await update.message.reply_text(
        "Привет! Я помогу тебе вести ежедневный план задач.\n"
        "Добавляй основные задачи через /addmain или дополнительные через /addextra.\n"
        "Для просмотра задач используй /mytasks."
    )

async def add_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    today = today_str()
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Напиши текст задачи после команды.")
        return
    data = load_data()
    data.setdefault(user_id, {"tasks": {}, "stats": {}})
    data[user_id]["tasks"].setdefault(today, {"main": [], "extra": []})

    main_tasks = data[user_id]["tasks"][today]["main"]

    if len(main_tasks) < 3:
        main_tasks.append({"text": text, "done": False})
        save_data(data)
        await update.message.reply_text(f"Основная задача добавлена: {text}")
    else:
        await update.message.reply_text("Лимит основных задач на сегодня достигнут (3).")

async def add_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    today = today_str()
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Напиши текст задачи после команды.")
        return
    data = load_data()
    data.setdefault(user_id, {"tasks": {}, "stats": {}})
    data[user_id]["tasks"].setdefault(today, {"main": [], "extra": []})
    data[user_id]["tasks"][today]["extra"].append({"text": text, "done": False})
    save_data(data)
    await update.message.reply_text("Дополнительная задача добавлена.")

async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    tasks = data.get(user_id, {}).get("tasks", {}).get(today, {"main": [], "extra": []})

    msg = "\U0001F4CB Твои задачи на сегодня:\n\n"

    main_tasks = tasks.get("main", [])
    if main_tasks:
        msg += "\U0001F31F Основные задачи:\n" + "\n".join([
            f"{i+1}. {'✅' if t['done'] else '❌'} {t['text']}" for i, t in enumerate(main_tasks)
        ])
    else:
        msg += "\U0001F31F Основные задачи: —\n"

    extra_tasks = tasks.get("extra", [])
    if extra_tasks:
        msg += "\n\n➕ Дополнительные задачи:\n" + "\n".join([
            f"{i+1}. {'✅' if t['done'] else '❌'} {t['text']}" for i, t in enumerate(extra_tasks)
        ])
    else:
        msg += "\n\n➕ Дополнительные задачи: —"

    await update.message.reply_text(msg)

async def complete_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _complete(update, context, "main")

async def complete_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _complete(update, context, "extra")

async def delete_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete(update, context, "main")

async def delete_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete(update, context, "extra")

async def _complete(update: Update, context: ContextTypes.DEFAULT_TYPE, list_name: str):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    try:
        idx = int(context.args[0]) - 1
        data[user_id]["tasks"][today][list_name][idx]["done"] = True
        save_data(data)
        await update.message.reply_text("Задача отмечена как выполненная.")
    except:
        await update.message.reply_text("Ошибка: укажи правильный номер задачи.")

async def _delete(update: Update, context: ContextTypes.DEFAULT_TYPE, list_name: str):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    try:
        idx = int(context.args[0]) - 1
        del data[user_id]["tasks"][today][list_name][idx]
        save_data(data)
        await update.message.reply_text("Задача удалена.")
    except:
        await update.message.reply_text("Ошибка при удалении задачи.")

async def reset_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    data.setdefault(user_id, {"tasks": {}, "stats": {}})
    data[user_id]["tasks"][today] = {"main": [], "extra": []}
    save_data(data)
    await update.message.reply_text("Задачи на сегодня сброшены.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    total = 0
    done = 0
    for day in data.get(user_id, {}).get("tasks", {}).values():
        for t in day.get("main", []) + day.get("extra", []):
            total += 1
            if t["done"]:
                done += 1
    await update.message.reply_text(f"📊 Всего: {total}, выполнено: {done}")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Нет доступа.")
        return
    data = load_data()
    msg = "📋 Статистика всех пользователей:\n"
    for uid, user in data.items():
        total = 0
        done = 0
        for d in user.get("tasks", {}).values():
            for t in d.get("main", []) + d.get("extra", []):
                total += 1
                if t["done"]:
                    done += 1
        msg += f"👤 {uid}: {done}/{total}\n"
    await update.message.reply_text(msg)

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Я не понимаю это сообщение.\n"
        "Вот доступные команды:\n"
        "/addmain [текст] — добавить основную задачу\n"
        "/addextra [текст] — добавить дополнительную задачу\n"
        "/mytasks — показать задачи на сегодня\n"
        "/complete_main [номер] — завершить основную\n"
        "/complete_extra [номер] — завершить дополнительную\n"
        "/delete_main [номер] — удалить основную\n"
        "/delete_extra [номер] — удалить дополнительную\n"
        "/reset — сбросить задачи\n"
        "/stats — статистика\n"
        "/admin — статистика по пользователям (админ)"
    )
    await update.message.reply_text(help_text)

def transfer_unfinished_tasks():
    data = load_data()
    yday = today_str(-1)
    today = today_str()
    for user, udata in data.items():
        if yday in udata["tasks"]:
            for list_type in ["main", "extra"]:
                for task in udata["tasks"][yday].get(list_type, []):
                    if not task["done"]:
                        data[user]["tasks"].setdefault(today, {"main": [], "extra": []})
                        data[user]["tasks"][today][list_type].append(task)
    save_data(data)

def schedule_jobs(app):
    scheduler.add_job(lambda: app.create_task(send_morning(app)), "cron", hour=11)
    scheduler.add_job(lambda: app.create_task(send_afternoon(app)), "cron", hour=14)
    scheduler.add_job(lambda: app.create_task(send_evening(app)), "cron", hour=20)
    scheduler.add_job(transfer_unfinished_tasks, "cron", hour=5)

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
            await app.bot.send_message(chat_id=int(user), text="🌇 Вечерний отчёт: что удалось сделать?")
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

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await set_commands(app)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addmain", add_main))
    app.add_handler(CommandHandler("addextra", add_extra))
    app.add_handler(CommandHandler("mytasks", my_tasks))
    app.add_handler(CommandHandler("complete_main", complete_main))
    app.add_handler(CommandHandler("complete_extra", complete_extra))
    app.add_handler(CommandHandler("delete_main", delete_main))
    app.add_handler(CommandHandler("delete_extra", delete_extra))
    app.add_handler(CommandHandler("reset", reset_tasks))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    schedule_jobs(app)
    threading.Thread(target=run_dummy_server, daemon=True).start()
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())
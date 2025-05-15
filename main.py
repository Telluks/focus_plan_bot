import os
import json
import logging
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

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
DATA_FILE = "data.json"
WEBHOOK_URL = "https://focus-plan-bot.onrender.com/webhook"

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
        BotCommand("admin", "Статистика по пользователям (админ)")
    ]
    await app.bot.set_my_commands(commands)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе вести задачи.\n"
        "Основные команды:\n"
        "/addmain [текст] — основная задача\n"
        "/addextra [текст] — дополнительная задача\n"
        "/mytasks — список задач\n"
        "/complete_main [номер] — завершить основную\n"
        "/complete_extra [номер] — завершить доп\n"
        "/delete_main [номер] — удалить основную\n"
        "/delete_extra [номер] — удалить доп\n"
        "/stats — твоя статистика\n"
        "/admin — статистика всех пользователей\n"
    )


async def add_task(update, context, task_type):
    user_id = str(update.effective_user.id)
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Напиши текст задачи после команды.")
        return
    today = today_str()
    data = load_data()
    data.setdefault(user_id, {"tasks": {}, "stats": {}})
    data[user_id]["tasks"].setdefault(today, {"main": [], "extra": []})
    if task_type == "main" and len(data[user_id]["tasks"][today]["main"]) >= 3:
        await update.message.reply_text("Лимит: 3 основные задачи.")
        return
    data[user_id]["tasks"][today][task_type].append({"text": text, "done": False})
    save_data(data)
    await update.message.reply_text(f"{'Основная' if task_type == 'main' else 'Дополнительная'} задача добавлена.")


async def add_main(update, context):
    await add_task(update, context, "main")


async def add_extra(update, context):
    await add_task(update, context, "extra")


async def my_tasks(update, context):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    tasks = data.get(user_id, {}).get("tasks", {}).get(today, {"main": [], "extra": []})
    msg = "📋 Задачи на сегодня:\n\n"

    msg += "🌟 Основные:\n" + (
        "\n".join([f"{i+1}. {'✅' if t['done'] else '❌'} {t['text']}" for i, t in enumerate(tasks["main"])])
        if tasks["main"] else "—"
    )
    msg += "\n\n➕ Дополнительные:\n" + (
        "\n".join([f"{i+1}. {'✅' if t['done'] else '❌'} {t['text']}" for i, t in enumerate(tasks["extra"])])
        if tasks["extra"] else "—"
    )
    await update.message.reply_text(msg)


async def complete(update, context, list_name):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    try:
        idx = int(context.args[0]) - 1
        data[user_id]["tasks"][today][list_name][idx]["done"] = True
        save_data(data)
        await update.message.reply_text("Отмечено как выполнено.")
    except:
        await update.message.reply_text("Ошибка: укажи правильный номер задачи.")


async def delete(update, context, list_name):
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


async def reset(update, context):
    user_id = str(update.effective_user.id)
    today = today_str()
    data = load_data()
    data[user_id]["tasks"][today] = {"main": [], "extra": []}
    save_data(data)
    await update.message.reply_text("Задачи сброшены.")


async def stats(update, context):
    user_id = str(update.effective_user.id)
    data = load_data()
    total, done = 0, 0
    for tasks in data.get(user_id, {}).get("tasks", {}).values():
        for t in tasks["main"] + tasks["extra"]:
            total += 1
            if t["done"]:
                done += 1
    await update.message.reply_text(f"📊 Выполнено {done} из {total} задач.")


async def admin(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Нет доступа.")
        return
    data = load_data()
    msg = "📊 Статистика пользователей:\n"
    for uid, user in data.items():
        total = sum(len(t["main"]) + len(t["extra"]) for t in user["tasks"].values())
        done = sum(t["done"] for day in user["tasks"].values() for t in day["main"] + day["extra"])
        msg += f"{uid}: {done}/{total}\n"
    await update.message.reply_text(msg)


async def unknown(update, context):
    await update.message.reply_text("Я не понял. Введи команду из меню.")


def transfer_unfinished_tasks():
    data = load_data()
    yday = today_str(-1)
    today = today_str()
    for user, udata in data.items():
        if yday in udata["tasks"]:
            for list_type in ["main", "extra"]:
                for task in udata["tasks"][yday][list_type]:
                    if not task["done"]:
                        data[user]["tasks"].setdefault(today, {"main": [], "extra": []})
                        data[user]["tasks"][today][list_type].append(task)
    save_data(data)


def schedule_jobs(app):
    scheduler.add_job(lambda: app.create_task(send_reminder(app, "🌅 Доброе утро! Введи задачи.")), "cron", hour=11)
    scheduler.add_job(lambda: app.create_task(send_reminder(app, "🕑 Напоминание о задачах.")), "cron", hour=14)
    scheduler.add_job(lambda: app.create_task(send_reminder(app, "🌇 Вечерний отчёт: что сделано?")), "cron", hour=20)
    scheduler.add_job(transfer_unfinished_tasks, "cron", hour=5)


async def send_reminder(app, text):
    for user in load_data():
        try:
            await app.bot.send_message(chat_id=int(user), text=text)
        except:
            pass


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await set_commands(app)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addmain", add_main))
    app.add_handler(CommandHandler("addextra", add_extra))
    app.add_handler(CommandHandler("mytasks", my_tasks))
    app.add_handler(CommandHandler("complete_main", lambda u, c: complete(u, c, "main")))
    app.add_handler(CommandHandler("complete_extra", lambda u, c: complete(u, c, "extra")))
    app.add_handler(CommandHandler("delete_main", lambda u, c: delete(u, c, "main")))
    app.add_handler(CommandHandler("delete_extra", lambda u, c: delete(u, c, "extra")))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    schedule_jobs(app)
    await app.initialize()
    await app.bot.set_webhook(WEBHOOK_URL)
    await app.start()
    await app.updater.start_polling()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
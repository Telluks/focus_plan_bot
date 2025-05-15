import os

# Токен от @BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Админы: список ID через запятую, например "123456789,987654321"
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))

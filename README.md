# Бот "Дневной Фокус" (Telegram)

## Что делает бот
- Утром спрашивает 3 главные задачи
- Днем напоминает о фокусе
- Вечером собирает отчет
- Показывает статистику /admin

## Запуск на Render.com
1. Создайте новый Web Service
2. В переменных окружения укажите:
   - `BOT_TOKEN=7855842271:AAGo9dn1lQQEAWYvseTT7W48snTD7BQnJC4`
   - `ADMIN_IDS=5018948221`
3. Start command:
   ```
   python main.py
   ```

## Зависимости
- python-telegram-bot
- apscheduler

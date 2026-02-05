import aiohttp
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta

# Простой кэш для поисковых запросов
search_cache = {}
CACHE_DURATION = 300  # 5 минут в секундах


async def search_with_cache(query: str):
    """Поиск с кэшированием результатов"""
    current_time = datetime.now()

    # Проверяем кэш
    if query in search_cache:
        cached_data, timestamp = search_cache[query]
        if (current_time - timestamp).total_seconds() < CACHE_DURATION:
            return cached_data

    # Если нет в кэше или кэш устарел, делаем запрос
    result = await perform_search(query)

    # Сохраняем в кэш
    search_cache[query] = (result, current_time)

    # Очищаем старые записи из кэша
    cleanup_cache()

    return result


async def perform_search(query: str):
    """Выполнение поискового запроса"""
    async with aiohttp.ClientSession() as session:
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1'
        }

        async with session.get(url, params=params, timeout=10) as response:
            if response.status == 200:
                return await response.json()
    return None


def cleanup_cache():
    """Очистка устаревшего кэша"""
    current_time = datetime.now()
    expired_queries = []

    for query, (_, timestamp) in search_cache.items():
        if (current_time - timestamp).total_seconds() > CACHE_DURATION:
            expired_queries.append(query)

    for query in expired_queries:
        del search_cache[query]


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный поиск с кэшированием"""
    if not context.args:
        await update.message.reply_text("Введите запрос для поиска: /search <запрос>")
        return

    query = ' '.join(context.args)
    search_message = await update.message.reply_text(f"🔍 Ищу: {query}")

    try:
        data = await search_with_cache(query)

        if not data:
            await search_message.edit_text("❌ Не удалось получить результаты")
            return

        # Форматируем результат
        if data.get('Abstract'):
            result = f"📚 **{data.get('Heading', 'Результат')}**\n\n"
            result += data['Abstract'][:1000]
            if len(data['Abstract']) > 1000:
                result += "..."
            if data.get('AbstractURL'):
                result += f"\n\n🔗 {data['AbstractURL']}"

        elif data.get('RelatedTopics'):
            result = f"📖 По запросу *'{query}'*:\n\n"
            for i, topic in enumerate(data['RelatedTopics'][:3], 1):
                if 'Text' in topic:
                    result += f"{i}. {topic['Text'][:300]}\n\n"

        else:
            result = "😔 Ничего не найдено"

        await search_message.edit_text(result, parse_mode='Markdown')

    except Exception as e:
        await search_message.edit_text(f"⚠️ Ошибка: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку"""
    help_text = """
🤖 **Бот-поисковик**

Я помогаю искать информацию в интернете прямо из Telegram.

🔍 **Основные команды:**
/search <запрос> - найти информацию
Примеры:
  /search погода в Москве
  /search рецепт оливье
  /search Python документация
  /search новости технологии

📝 **Советы по поиску:**
• Используйте конкретные запросы
• Добавляйте ключевые слова для уточнения
• Проверяйте орфографию

🚀 **Быстрый старт:**
Просто отправьте /search и ваш вопрос!

❓ **Проблемы?**
Если поиск не работает, попробуйте:
1. Переформулировать запрос
2. Использовать английские слова
3. Подождать несколько минут
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений"""
    text = update.message.text

    # Если сообщение начинается не с команды, предлагаем помощь
    if not text.startswith('/'):
        await update.message.reply_text(
            "Чтобы начать поиск, используйте команду /search\n"
            "Например: /search " + text[:50] + ("..." if len(text) > 50 else "")
        )


def main(start=None):
    """Основная функция запуска бота"""
    # ⚠️ ВАЖНО: Замените на ваш реальный токен!
    TOKEN = "8130693503:AAFk_6mH5RGP46YmJqKTsLWr4BgmR1C5Jtk"

    # Создаем приложение
    app = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("help", help_command))

    # Запускаем бота
    print("🚀 Бот запущен! Ожидаю команды...")
    app.run_polling()


if __name__ == '__main__':
    main()
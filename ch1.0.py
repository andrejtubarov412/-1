import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы с ботом"""
    await update.message.reply_text(
        "👋 Привет! Я бот для поиска информации в интернете.\n\n"
        "📋 Доступные команды:\n"
        "/start - начать работу\n"
        "/search <запрос> - найти информацию\n"
        "/help - помощь\n\n"
        "Пример: /search как приготовить пасту"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск информации в интернете"""
    if not context.args:
        await update.message.reply_text(
            "❌ Пожалуйста, укажите запрос для поиска.\n"
            "Пример: /search рецепт борща"
        )
        return

    query = ' '.join(context.args)

    # Показываем пользователю, что поиск начат
    search_message = await update.message.reply_text(f"🔍 Ищу: _{query}_", parse_mode='Markdown')

    try:
        # Используем DuckDuckGo API (не требует ключа)
        async with aiohttp.ClientSession() as session:
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = ""

                    # Если есть краткое описание
                    if data.get('Abstract'):
                        result = f"📚 **{data['Heading'] if data['Heading'] else 'Результат поиска'}**\n\n"
                        result += f"{data['Abstract']}\n\n"
                        if data.get('AbstractURL'):
                            result += f"🔗 Подробнее: {data['AbstractURL']}"

                    # Если есть связанные темы
                    elif data.get('RelatedTopics'):
                        result = f"📖 Нашел по запросу *'{query}'*:\n\n"
                        count = 0
                        for topic in data['RelatedTopics']:
                            if 'Text' in topic:
                                count += 1
                                # Обрезаем длинный текст
                                text = topic['Text'][:200] + "..." if len(topic['Text']) > 200 else topic['Text']
                                result += f"{count}. {text}\n\n"

                                # Ограничиваем количество результатов
                                if count >= 5:
                                    result += "📎 И еще несколько результатов..."
                                    break

                    # Если ничего не найдено
                    else:
                        result = "😔 По вашему запросу ничего не найдено.\n\n"
                        result += "Попробуйте:\n"
                        result += "• Изменить формулировку запроса\n"
                        result += "• Использовать другие ключевые слова\n"
                        result += "• Проверить орфографию"

                    # Отправляем результат (Telegram ограничивает 4096 символов)
                    if len(result) > 4000:
                        result = result[:4000] + "...\n\n⚠️ Результат был обрезан"

                    await search_message.edit_text(result, parse_mode='Markdown')

                else:
                    await search_message.edit_text(
                        "❌ Не удалось получить результаты поиска.\n"
                        "Попробуйте еще раз через несколько минут."
                    )

    except aiohttp.ClientError:
        await search_message.edit_text(
            "🌐 Проблемы с подключением к интернету.\n"
            "Проверьте ваше соединение и попробуйте снова."
        )

    except Exception as e:
        await search_message.edit_text(
            "⚠️ Произошла непредвиденная ошибка.\n"
            "Попробуйте другой запрос или повторите позже."
        )
        print(f"Ошибка поиска: {e}")


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


def main():
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
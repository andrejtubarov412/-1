import aiohttp
import asyncio
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import urllib.parse
import random


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *Бот для поиска информации*\n\n"
        "Используйте команды:\n"
        "• /search <запрос> - поиск информации\n"
        "• /news - последние новости\n"
        "• /weather - погода (Москва)\n"
        "• /help - помощь\n\n"
        "Пример: `/search рецепт пиццы`",
        parse_mode='Markdown'
    )


async def search_google_scraper(query: str) -> str:
    """Поиск через Google (веб-скрапинг)"""
    try:
        # Создаем URL для поиска
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=ru"

        # Случайные User-Agent для обхода блокировки
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        ]

        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    results = []

                    # Парсим основные результаты
                    for g in soup.find_all('div', class_='g'):
                        # Название
                        title_element = g.find('h3')
                        if title_element:
                            title = title_element.get_text()
                        else:
                            continue

                        # Описание
                        desc_element = g.find('div', class_='VwiC3b') or g.find('div', class_='lyLwlc')
                        description = desc_element.get_text() if desc_element else "Нет описания"

                        # Ссылка
                        link_element = g.find('a')
                        link = link_element['href'] if link_element and 'href' in link_element.attrs else ""

                        if title and link:
                            results.append({
                                'title': title,
                                'description': description[:300],
                                'link': link
                            })

                    # Если не нашли обычные результаты, ищем быстрые ответы
                    if not results:
                        # Быстрый ответ (featured snippet)
                        quick_answer = soup.find('div', class_='BNeawe')
                        if quick_answer:
                            return f"📋 *Быстрый ответ:*\n\n{quick_answer.get_text()[:2000]}"

                        # Знания (knowledge graph)
                        knowledge = soup.find('div', class_='kno-rdesc')
                        if knowledge:
                            return f"📚 *Знания:*\n\n{knowledge.get_text()[:2000]}"

                    # Форматируем результаты
                    if results:
                        response_text = f"🔍 *Результаты по запросу:* `{query}`\n\n"
                        for i, result in enumerate(results[:5], 1):
                            response_text += f"*{i}. {result['title']}*\n"
                            response_text += f"{result['description']}\n"
                            if result['link']:
                                # Очищаем ссылку от мусора
                                clean_link = result['link'].split('&')[0].replace('/url?q=', '')
                                if clean_link.startswith('http'):
                                    response_text += f"🔗 {clean_link}\n"
                            response_text += "\n"

                        if len(response_text) > 4000:
                            response_text = response_text[:4000] + "...\n\n⚠️ Результаты обрезаны"

                        return response_text

                    return "❌ Не удалось найти информацию. Попробуйте другой запрос."

                return f"❌ Ошибка подключения: {response.status}"

    except asyncio.TimeoutError:
        return "⏰ Превышено время ожидания. Попробуйте позже."
    except Exception as e:
        return f"⚠️ Ошибка: {str(e)}"


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основная команда поиска"""
    if not context.args:
        await update.message.reply_text(
            "📝 *Формат:* `/search ваш запрос`\n\n"
            "📌 *Примеры:*\n"
            "• `/search погода Москва`\n"
            "• `/search рецепт борща`\n"
            "• `/search новости технологий`",
            parse_mode='Markdown'
        )
        return

    query = ' '.join(context.args)

    # Отправляем сообщение о начале поиска
    search_msg = await update.message.reply_text(f"🔍 *Ищу:* `{query}`\n\n⏳ Обработка...", parse_mode='Markdown')

    # Выполняем поиск
    result = await search_google_scraper(query)

    # Редактируем сообщение с результатом
    await search_msg.edit_text(result, parse_mode='Markdown')


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последние новости"""
    try:
        await update.message.reply_text("📰 *Ищу свежие новости...*", parse_mode='Markdown')

        async with aiohttp.ClientSession() as session:
            # Новости через RSS
            urls = [
                "https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru",
                "https://lenta.ru/rss/news",
                "https://ria.ru/export/rss2/index.xml"
            ]

            news_items = []

            for url in urls:
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            text = await response.text()
                            soup = BeautifulSoup(text, 'xml')

                            items = soup.find_all('item')[:3]  # Берем по 3 новости с каждого источника
                            for item in items:
                                title = item.title.get_text() if item.title else ""
                                link = item.link.get_text() if item.link else ""
                                pub_date = item.pubDate.get_text() if item.pubDate else ""

                                if title and link:
                                    news_items.append({
                                        'title': title[:200],
                                        'link': link,
                                        'source': url.split('/')[2]
                                    })
                except:
                    continue

            if news_items:
                response_text = "📰 *Последние новости:*\n\n"
                for i, news in enumerate(news_items[:10], 1):
                    response_text += f"*{i}. {news['title']}*\n"
                    response_text += f"🔗 {news['link']}\n"
                    response_text += f"📡 Источник: {news['source']}\n\n"

                await update.message.reply_text(response_text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Не удалось загрузить новости")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Погода"""
    try:
        city = ' '.join(context.args) if context.args else "Москва"

        await update.message.reply_text(f"🌤 *Запрашиваю погоду для:* {city}", parse_mode='Markdown')

        # Используем Яндекс.Погода (упрощенный вариант)
        async with aiohttp.ClientSession() as session:
            # Создаем поисковый запрос
            search_query = f"погода {city} сегодня"
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&hl=ru"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            async with session.get(search_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Ищем информацию о погоде
                    weather_info = soup.find('div', class_='BNeawe')

                    if weather_info:
                        temp = weather_info.get_text()
                        await update.message.reply_text(
                            f"🌤 *Погода в {city}:*\n\n"
                            f"{temp}\n\n"
                            f"ℹ️ Для точного прогноза используйте погодные приложения",
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            f"❌ Не удалось получить погоду для {city}\n\n"
                            f"Попробуйте: `/weather Санкт-Петербург`",
                            parse_mode='Markdown'
                        )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка"""
    help_text = """
🔍 *Поисковый бот*

*Доступные команды:*

🔎 *Поиск информации:*
`/search <запрос>` - поиск в интернете
Примеры:
• `/search рецепт блинов`
• `/search новости футбола`
• `/search что такое ИИ`
• `/search фильмы 2024`

📰 *Новости:*
`/news` - последние новости России и мира

🌤 *Погода:*
`/weather [город]` - погода (по умолчанию Москва)
Примеры:
• `/weather`
• `/weather Санкт-Петербург`
• `/weather Лондон`

ℹ️ *Другое:*
`/start` - начало работы
`/help` - эта справка

*Советы по поиску:*
• Используйте конкретные запросы
• На английском языке часто больше информации
• Для точного поиска используйте кавычки: `/search "Илон Маск"`

📱 *Ограничения:*
• Максимум 5 результатов на запрос
• Иногда поиск может не работать
• Нет 100% гарантии нахождения информации
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений"""
    text = update.message.text

    if text and not text.startswith('/'):
        # Если сообщение длинное, предлагаем поиск
        if len(text.split()) >= 3:
            await update.message.reply_text(
                f"💡 Хотите найти информацию?\n\n"
                f"Используйте: `/search {text[:50]}`",
                parse_mode='Markdown'
            )
        elif text.lower() in ['привет', 'hello', 'hi', 'здравствуйте']:
            await update.message.reply_text("👋 Привет! Используйте /help для списка команд")
        elif '?' in text:
            await update.message.reply_text(
                f"❓ Это вопрос? Попробуйте:\n"
                f"`/search {text}`",
                parse_mode='Markdown'
            )


def main():
    """Запуск бота"""
    # ⚠️ Замените токен на ваш!
    TOKEN = "ВАШ_ТОКЕН_БОТА"

    # Устанавливаем необходимые библиотеки (если их нет)
    try:
        import bs4
    except ImportError:
        print("❌ Установите BeautifulSoup4: pip install beautifulsoup4")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("news", news))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("help", help_command))

    # Обработчик обычных сообщений
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("🚀 Бот запущен!")
    print("✅ Команды:")
    print("  /search - поиск информации")
    print("  /news - последние новости")
    print("  /weather - погода")
    print("  /help - справка")

    app.run_polling()


if __name__ == '__main__':
    # Проверяем зависимости
    import sys

    required_packages = ['bs4', 'aiohttp']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("❌ Установите недостающие пакеты:")
        print(f"   pip install {' '.join(missing_packages)}")
        sys.exit(1)

    main()
import requests
import json
import logging
from typing import Dict, List
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация LM Studio
LM_STUDIO_URL = "http://localhost:1234/v1"  # URL по умолчанию в LM Studio
BOT_TOKEN = "8130693503:AAFk_6mH5RGP46YmJqKTsLWr4BgmR1C5Jtk"


# Проверяем доступность LM Studio
def check_lm_studio_available() -> bool:
    """Проверяет, запущен ли сервер LM Studio"""
    try:
        response = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False
    except Exception as e:
        logger.error(f"Ошибка проверки LM Studio: {e}")
        return False


# Получаем список доступных моделей
def get_available_models() -> List[str]:
    """Получает список моделей из LM Studio"""
    try:
        response = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            models = []
            for model in models_data.get("data", []):
                model_id = model.get("id")
                if model_id:
                    models.append(model_id)
            return models
    except Exception as e:
        logger.error(f"Ошибка получения моделей: {e}")
    return []


# Генерация текста через LM Studio
def generate_with_lm_studio(
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
) -> str:
    """
    Генерирует ответ через LM Studio API
    """
    try:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{LM_STUDIO_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120  # Долгий таймаут для больших моделей
        )

        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return "❌ Не получилось сгенерировать ответ."
        else:
            error_text = f"Ошибка API: {response.status_code}"
            try:
                error_detail = response.json()
                if "error" in error_detail:
                    error_text = f"Ошибка: {error_detail['error']}"
            except:
                pass
            return f"❌ {error_text}"

    except requests.exceptions.ConnectionError:
        return "❌ Не удалось подключиться к LM Studio. Убедитесь, что сервер запущен."
    except requests.exceptions.Timeout:
        return "⏰ Превышено время ожидания ответа от модели."
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        return f"⚠️ Ошибка при генерации ответа: {str(e)}"


# Хранилище контекста диалогов
user_conversations: Dict[int, Dict] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user

    # Проверяем доступность LM Studio
    if not check_lm_studio_available():
        await update.message.reply_text(
            "⚠️ *LM Studio не обнаружен!*\n\n"
            "Для работы бота необходимо:\n\n"
            "1. 📥 Скачать и установить LM Studio с https://lmstudio.ai/\n"
            "2. 🧠 Скачать модель (например, Llama 2, Mistral, Phi-2)\n"
            "3. ▶️ В LM Studio:\n"
            "   • Выберите модель\n"
            "   • Перейдите во вкладку 'Local Server'\n"
            "   • Нажмите 'Start Server'\n"
            "   • Убедитесь, что порт 1234 (по умолчанию)\n\n"
            "4. 🔄 Перезапустите этого бота\n\n"
            "📚 *Рекомендуемые модели:*\n"
            "• Mistral-7B-Instruct\n"
            "• Llama-2-7B-Chat\n"
            "• Phi-2\n"
            "• Zephyr-7B-beta",
            parse_mode='Markdown'
        )
    else:
        models = get_available_models()
        models_text = "\n".join([f"• `{m}`" for m in models[:5]]) if models else "*Нет загруженных моделей*"

        if len(models) > 5:
            models_text += f"\n\n... и еще {len(models) - 5} моделей"

        await update.message.reply_text(
            f"🤖 *Добро пожаловать, {user.first_name}!*\n\n"
            "✅ *LM Studio обнаружен и готов к работе!*\n\n"
            "🧠 *Доступные модели:*\n"
            f"{models_text}\n\n"
            "✨ *Возможности:*\n"
            "• 💬 Умные диалоги с локальной ИИ\n"
            "• 🔒 Полная приватность (все на вашем ПК)\n"
            "• 🚀 Быстрые ответы\n"
            "• 💾 Сохранение контекста беседы\n\n"
            "📋 *Команды:*\n"
            "`/start` - Начало работы\n"
            "`/help` - Помощь\n"
            "`/new` - Новый диалог\n"
            "`/models` - Список моделей\n"
            "`/mode` - Режимы общения\n"
            "`/settings` - Настройки\n"
            "`/status` - Статус системы\n\n"
            "💬 *Просто напишите мне сообщение!*",
            parse_mode='Markdown'
        )

    # Очищаем старый контекст
    user_id = user.id
    if user_id in user_conversations:
        del user_conversations[user_id]


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🆘 *Помощь по использованию бота*

🤖 *О технологии:*
Бот использует локальную ИИ через LM Studio.
Все обработки происходят на вашем компьютере.

⚡ *Основные команды:*
`/start` - Начать работу с ботом
`/help` - Эта справка
`/new` - Начать новый диалог
`/models` - Показать доступные модели
`/mode` - Изменить режим общения
`/settings` - Настройки генерации
`/status` - Статус системы

🎭 *Режимы общения (/mode):*
1. *Умный* - Баланс креативности и точности
2. *Креативный* - Более творческие ответы
3. *Точный* - Фактологические ответы
4. *Дружелюбный* - Неформальное общение

⚙️ *Настройки (/settings):*
• Температура (креативность)
• Длина ответа
• Системный промпт

💡 *Советы:*
• Задавайте конкретные вопросы
• Используйте `/new` для смены темы
• Начните с модели 7B параметров
• Для быстрых ответов используйте маленькие модели

🔧 *Устранение проблем:*
1. LM Studio не запущен - запустите сервер
2. Нет моделей - скачайте в LM Studio
3. Медленные ответы - используйте меньшую модель
4. Ошибки памяти - закройте другие приложения

📚 *Документация:*
• LM Studio: https://lmstudio.ai/docs
• Модели: https://huggingface.co/models
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /new - новый диалог"""
    user_id = update.effective_user.id
    if user_id in user_conversations:
        del user_conversations[user_id]

    await update.message.reply_text(
        "🔄 *Новый диалог начат!*\n"
        "История предыдущего разговора очищена.\n\n"
        "💭 Теперь я готов к новому разговору!",
        parse_mode='Markdown'
    )


async def list_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /models - список моделей"""
    if not check_lm_studio_available():
        await update.message.reply_text(
            "❌ *LM Studio не доступен*\n\n"
            "Запустите LM Studio и запустите сервер.",
            parse_mode='Markdown'
        )
        return

    try:
        models = get_available_models()

        if models:
            response_text = "🧠 *Доступные модели в LM Studio:*\n\n"

            for i, model in enumerate(models[:10], 1):
                # Укорачиваем длинные названия моделей
                short_name = model
                if len(short_name) > 50:
                    short_name = short_name[:47] + "..."

                response_text += f"{i}. `{short_name}`\n"

            if len(models) > 10:
                response_text += f"\n... и еще {len(models) - 10} моделей"

            response_text += "\n\n💡 *Совет:* Используйте модели с 'instruct' или 'chat' в названии для диалогов."
        else:
            response_text = (
                "📭 *Нет загруженных моделей*\n\n"
                "Чтобы добавить модели:\n"
                "1. Откройте LM Studio\n"
                "2. Перейдите во вкладку 'Search'\n"
                "3. Найдите и скачайте модель\n"
                "4. Перезапустите сервер\n\n"
                "🔥 *Рекомендуемые модели:*\n"
                "• mistral-7b-instruct\n"
                "• llama-2-7b-chat\n"
                "• phi-2\n"
                "• zephyr-7b-beta"
            )

        await update.message.reply_text(response_text, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка при получении списка моделей:\n`{str(e)}`",
            parse_mode='Markdown'
        )


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mode - выбор режима общения"""
    if context.args:
        mode = context.args[0]
        modes = {
            "1": {"name": "Умный", "temp": 0.7, "desc": "Баланс креативности и точности"},
            "2": {"name": "Креативный", "temp": 0.9, "desc": "Более творческие ответы"},
            "3": {"name": "Точный", "temp": 0.3, "desc": "Фактологические ответы"},
            "4": {"name": "Дружелюбный", "temp": 0.8, "desc": "Неформальное общение"}
        }

        if mode in modes:
            user_id = update.effective_user.id
            if user_id not in user_conversations:
                user_conversations[user_id] = {"mode": mode, "messages": []}
            else:
                user_conversations[user_id]["mode"] = mode

            await update.message.reply_text(
                f"✅ Режим изменен на: *{modes[mode]['name']}*\n\n"
                f"📝 {modes[mode]['desc']}\n"
                f"🌡 Температура: {modes[mode]['temp']}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Неверный номер режима. Используйте 1-4.\n"
                "Пример: `/mode 2`",
                parse_mode='Markdown'
            )
    else:
        mode_text = """
🎭 *Режимы общения*

Выберите режим для настройки стиля ответов:

1. *🧠 Умный* (по умолчанию)
   Температура: 0.7
   Баланс креативности и точности

2. *🎨 Креативный*
   Температура: 0.9
   Более творческие и развернутые ответы

3. *📚 Точный*
   Температура: 0.3
   Фактологические, краткие ответы

4. *😊 Дружелюбный*
   Температура: 0.8
   Неформальное, живое общение

Для выбора режима напишите: `/mode [номер]`
Пример: `/mode 2`
        """
        await update.message.reply_text(mode_text, parse_mode='Markdown')


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /settings - настройки"""
    user_id = update.effective_user.id

    # Получаем текущие настройки пользователя
    default_settings = {
        "temperature": 0.7,
        "max_tokens": 500,
        "system_prompt": "Ты полезный, дружелюбный ИИ-ассистент. Отвечай на русском языке."
    }

    if user_id in user_conversations and "settings" in user_conversations[user_id]:
        settings = user_conversations[user_id]["settings"]
    else:
        settings = default_settings

    if context.args:
        # Обработка изменения настроек
        if len(context.args) >= 2:
            setting = context.args[0]
            value = context.args[1]

            if setting == "temp" or setting == "temperature":
                try:
                    temp = float(value)
                    if 0 <= temp <= 2:
                        settings["temperature"] = temp
                        await update.message.reply_text(
                            f"✅ Температура изменена на: *{temp}*\n\n"
                            f"Чем выше температура, тем более креативны ответы.",
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text("❌ Температура должна быть от 0 до 2")
                except ValueError:
                    await update.message.reply_text("❌ Укажите число для температуры")

            elif setting == "tokens":
                try:
                    tokens = int(value)
                    if 50 <= tokens <= 2000:
                        settings["max_tokens"] = tokens
                        await update.message.reply_text(
                            f"✅ Максимальное количество токенов изменено на: *{tokens}*",
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text("❌ Количество токенов должно быть от 50 до 2000")
                except ValueError:
                    await update.message.reply_text("❌ Укажите число для токенов")

            else:
                await update.message.reply_text(
                    "❌ Неизвестная настройка\n\n"
                    "Доступные настройки:\n"
                    "• `temp <значение>` - температура (0-2)\n"
                    "• `tokens <значение>` - максимальное количество токенов (50-2000)\n\n"
                    "Пример: `/settings temp 0.8`",
                    parse_mode='Markdown'
                )

            # Сохраняем настройки
            if user_id not in user_conversations:
                user_conversations[user_id] = {"settings": settings, "messages": []}
            else:
                user_conversations[user_id]["settings"] = settings
    else:
        # Показываем текущие настройки
        settings_text = f"""
⚙️ *Текущие настройки*

🌡 *Температура:* `{settings['temperature']}`
📏 *Максимальная длина ответа:* `{settings['max_tokens']}` токенов
🤖 *Системный промпт:* {settings['system_prompt'][:100]}...

🛠 *Изменить настройки:*
`/settings temp 0.8` - изменить температуру
`/settings tokens 1000` - изменить длину ответа

📊 *Что означает температура:*
• 0.0-0.3: Очень детерминированные ответы
• 0.4-0.7: Баланс (рекомендуется)
• 0.8-1.2: Креативные ответы
• 1.3-2.0: Очень случайные, экспериментальные
        """
        await update.message.reply_text(settings_text, parse_mode='Markdown')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - статус системы"""
    try:
        status_text = "🖥️ *Статус системы*\n\n"

        # Проверяем LM Studio
        lm_status = check_lm_studio_available()
        if lm_status:
            status_text += "✅ *LM Studio доступен*\n"

            # Получаем информацию о моделях
            models = get_available_models()
            if models:
                status_text += f"📚 Загружено моделей: *{len(models)}*\n"
                if models:
                    current_model = models[0]
                    if len(current_model) > 40:
                        current_model = current_model[:37] + "..."
                    status_text += f"🧠 Текущая модель: `{current_model}`\n"
            else:
                status_text += "📭 *Нет загруженных моделей*\n"
        else:
            status_text += "❌ *LM Studio не доступен*\n"

        # Статистика пользователя
        user_id = update.effective_user.id
        if user_id in user_conversations:
            msg_count = len(user_conversations[user_id].get("messages", []))
            status_text += f"\n📊 *Ваша статистика:*\n"
            status_text += f"💬 Сообщений в диалоге: *{msg_count}*\n"

            settings = user_conversations[user_id].get("settings", {})
            if settings:
                status_text += f"🌡 Температура: *{settings.get('temperature', 0.7)}*\n"

        # Общая статистика
        status_text += f"\n👥 *Общая статистика:*\n"
        status_text += f"Активных диалогов: *{len(user_conversations)}*\n"

        # Информация о системе
        import psutil
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        status_text += f"\n⚡ *Системные ресурсы:*\n"
        status_text += f"CPU: *{cpu_percent}%*\n"
        status_text += f"Память: *{memory.percent}%* использовано\n"

        await update.message.reply_text(status_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Ошибка статуса: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при получении статуса:\n`{str(e)}`",
            parse_mode='Markdown'
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_message = update.message.text
    user_id = update.effective_user.id

    # Пропускаем команды
    if user_message.startswith('/'):
        return

    # Показываем статус "печатает"
    await update.message.chat.send_action(action="typing")

    logger.info(f"Сообщение от {update.effective_user.first_name}: {user_message[:50]}...")

    # Проверяем доступность LM Studio
    if not check_lm_studio_available():
        await update.message.reply_text(
            "❌ *LM Studio не доступен*\n\n"
            "Пожалуйста, убедитесь, что:\n"
            "1. LM Studio запущен\n"
            "2. Сервер запущен (вкладка Local Server → Start Server)\n"
            "3. Порт 1234 свободен\n\n"
            "Используйте `/status` для проверки.",
            parse_mode='Markdown'
        )
        return

    # Инициализируем или получаем контекст пользователя
    if user_id not in user_conversations:
        user_conversations[user_id] = {
            "messages": [],
            "settings": {
                "temperature": 0.7,
                "max_tokens": 500,
                "system_prompt": "Ты полезный, дружелюбный ИИ-ассистент. Отвечай на русском языке."
            },
            "mode": "1"
        }

    user_data = user_conversations[user_id]
    messages = user_data["messages"]
    settings = user_data["settings"]

    # Добавляем системный промпт если это первый запрос
    if not messages:
        messages.append({
            "role": "system",
            "content": settings["system_prompt"]
        })

    # Добавляем сообщение пользователя
    messages.append({
        "role": "user",
        "content": user_message
    })

    # Ограничиваем историю (оставляем системный промпт + последние 9 сообщений)
    if len(messages) > 10:
        messages = [messages[0]] + messages[-9:]
        user_data["messages"] = messages

    try:
        # Генерируем ответ
        ai_response = generate_with_lm_studio(
            messages=messages,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"]
        )

        # Очищаем ответ
        ai_response = ai_response.strip()

        # Добавляем ответ в историю
        messages.append({
            "role": "assistant",
            "content": ai_response
        })

        # Отправляем ответ
        if len(ai_response) > 4000:
            # Разбиваем длинные ответы
            chunks = [ai_response[i:i + 4000] for i in range(0, len(ai_response), 4000)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(chunk, parse_mode='Markdown')
                else:
                    await update.message.reply_text(chunk, parse_mode='Markdown')
        else:
            await update.message.reply_text(ai_response, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await update.message.reply_text(
            "❌ *Произошла ошибка при обработке запроса.*\n\n"
            "Возможные причины:\n"
            "• Не хватает памяти\n"
            "• Модель не загружена\n"
            "• Таймаут соединения\n\n"
            "Попробуйте:\n"
            "1. Использовать меньшую модель\n"
            "2. Уменьшить длину ответа (/settings tokens 300)\n"
            "3. Перезапустить LM Studio\n"
            "4. Использовать `/new` для нового диалога",
            parse_mode='Markdown'
        )


def main():
    """Запуск бота"""
    print("=" * 60)
    print("🤖 Запуск бота с локальной ИИ через LM Studio")
    print("=" * 60)

    # Проверяем доступность LM Studio
    if check_lm_studio_available():
        print("✅ LM Studio обнаружен и доступен")
        models = get_available_models()
        if models:
            print(f"📚 Найдено моделей: {len(models)}")
            for i, model in enumerate(models[:3], 1):
                print(f"   {i}. {model[:60]}...")
            if len(models) > 3:
                print(f"   ... и еще {len(models) - 3} моделей")
        else:
            print("⚠️ Нет загруженных моделей")
            print("   Загрузите модели в LM Studio")
    else:
        print("❌ LM Studio не доступен")
        print("\n📋 Инструкция по настройке:")
        print("1. Скачайте LM Studio: https://lmstudio.ai/")
        print("2. Установите и запустите программу")
        print("3. Скачайте модель (например, mistral-7b-instruct)")
        print("4. Перейдите во вкладку 'Local Server'")
        print("5. Нажмите 'Start Server'")
        print("6. Убедитесь, что порт 1234")

    print("\n⚡ Команды бота:")
    print("  /start    - Начало работы")
    print("  /help     - Помощь")
    print("  /new      - Новый диалог")
    print("  /models   - Список моделей")
    print("  /mode     - Режимы общения")
    print("  /settings - Настройки")
    print("  /status   - Статус системы")
    print("\n💬 Напишите любое сообщение для начала общения!")
    print("=" * 60)

    # Проверяем наличие psutil для статуса
    try:
        import psutil
    except ImportError:
        print("\n⚠️ Для расширенного статуса установите: pip install psutil")

    # Создаем приложение
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_chat))
    app.add_handler(CommandHandler("models", list_models))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("status", status_command))

    # Обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    try:
        app.run_polling()
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        print("Проверьте токен бота и соединение с Telegram.")


if __name__ == '__main__':
    # Проверяем наличие зависимостей
    try:
        import requests
    except ImportError:
        print("❌ Установите библиотеку requests:")
        print("   pip install requests")
        exit(1)

    main()
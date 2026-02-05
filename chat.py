from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой бот !")

if __name__ == '__main__':
    app = ApplicationBuilder().token("8130693503:AAFk_6mH5RGP46YmJqKTsLWr4BgmR1C5Jtk").build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
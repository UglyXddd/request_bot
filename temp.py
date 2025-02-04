import telebot

TOKEN = "7793677369:AAEw15axx4UMdqnIAYmPX6EvkwIuzTVfl1s"  # Вставь свой токен бота

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(func=lambda message: True)
def get_chat_id(message):
    print(f"Chat ID группы: {message.chat.id}")
    bot.send_message(message.chat.id, f"Ваш chat_id: {message.chat.id}")

bot.polling()

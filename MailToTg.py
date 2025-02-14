#7793677369:AAEw15axx4UMdqnIAYmPX6EvkwIuzTVfl1s
#838543272
import imaplib
import email
import telebot
import time
import chardet  # Библиотека для определения кодировки
from email.header import decode_header
import re

# Настройки
MAIL_SERVER = "imap.mail.ru"
MAIL_USER = "ant.mosco_w@mail.ru"
MAIL_PASS = "aWaVR6q6mpUgP3tuDUY8"
TELEGRAM_TOKEN = "7793677369:AAEw15axx4UMdqnIAYmPX6EvkwIuzTVfl1s"
CHAT_ID = "-1002284366831"


bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Подключение к серверу
mail = imaplib.IMAP4_SSL(MAIL_SERVER)
mail.login(MAIL_USER, MAIL_PASS)
mail.select("inbox")

# Поиск писем с темой, начинающейся на "[~"
status, messages = mail.search(None, 'SUBJECT "[~1358264"')

# Получаем последние 10 сообщений
message_ids = messages[0].split()[-100:]

# Обрабатываем каждое сообщение
for num in reversed(message_ids):
    status, msg_data = mail.fetch(num, "(RFC822)")

    for response_part in msg_data:
        if isinstance(response_part, tuple):
            # Разбираем email
            msg = email.message_from_bytes(response_part[1])

            # Декодируем тему
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")

            # Декодируем отправителя
            sender, encoding = decode_header(msg["From"])[0]
            if isinstance(sender, bytes):
                sender = sender.decode(encoding if encoding else "utf-8")

            # Получаем тело письма
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            # Выводим данные о письме
            print(f"Отправитель: {sender}")
            print(f"Тема: {subject}")
            print(f"Сообщение: {body[:10000]}")  # Ограничиваем вывод первых 500 символов
            print("=" * 100)

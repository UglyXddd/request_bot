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


def decode_email_header(header):
    """Функция для декодирования темы письма"""
    decoded_header = decode_header(header)
    subject = ""
    for part, encoding in decoded_header:
        if isinstance(part, bytes):  # Если закодировано в байтах
            encoding = encoding if encoding else "utf-8"
            try:
                subject += part.decode(encoding, errors="ignore")
            except:
                subject += part.decode("utf-8", errors="ignore")
        else:
            subject += part
    return subject.strip()


def get_latest_email():
    try:
        print("⏳ Подключаюсь к IMAP...")
        mail = imaplib.IMAP4_SSL(MAIL_SERVER)
        mail.login(MAIL_USER, MAIL_PASS)
        print("✅ Вход в почту успешен!")

        mail.select("inbox")
        result, data = mail.search(None, "UNSEEN")
        mail_ids = data[0].split()

        print(f"📩 Найдено новых писем: {len(mail_ids)}")

        messages = []
        for num in mail_ids:
            print(f"🔄 Обрабатываю письмо ID: {num}")

            result, msg_data = mail.fetch(num, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Декодируем тему письма
            subject = msg["subject"] if msg["subject"] else "(Без темы)"
            subject = decode_email_header(subject)

            from_email = msg["from"]
            body = ""

            # 🔍 ФИЛЬТРУЕМ ТОЛЬКО ЗАЯВКИ (если тема не начинается с "[~", письмо игнорируется)
            if not subject.startswith("[~"):
                print(f"🚫 Письмо проигнорировано (не заявка). Тема: {subject}")
                continue

            # Определяем кодировку и декодируем текст письма
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        encoding = part.get_content_charset()

                        if encoding is None:
                            detected_encoding = chardet.detect(payload)['encoding']
                            encoding = detected_encoding if detected_encoding else "utf-8"

                        body = payload.decode(encoding, errors="ignore").strip()
                        break
            else:
                payload = msg.get_payload(decode=True)
                encoding = msg.get_content_charset()

                if encoding is None:
                    detected_encoding = chardet.detect(payload)['encoding']
                    encoding = detected_encoding if detected_encoding else "utf-8"

                body = payload.decode(encoding, errors="ignore").strip()

            # Выводим информацию в консоль
            print(f"✅ Письмо обработано!")
            print(f"📌 Тема: {subject}")
            print(f"📄 Текст письма:\n{body[:1000]}")  # Ограничим вывод 500 символами в сосноль

            # Добавляем письмо в список сообщений для отправки в Telegram
            messages.append(f"📩 Новая заявка!\nОт: {from_email}\nТема: {subject}\n\n{body}")

        mail.logout()
        return messages

    except Exception as e:
        print(f"❌ Ошибка в get_latest_email: {e}")
        return []


def send_to_telegram(messages):
    for msg in messages:
        try:
            print("📤 Отправляю в Telegram...")
            clean_msg = clean_html_tags(msg)

            bot.send_message(CHAT_ID, clean_msg)
            print("✅ Отправлено!")
        except Exception as e:
            print(f"❌ Ошибка при отправке в Telegram: {e}")


def clean_html_tags(text):
    """Функция для удаления HTML-тегов"""
    return re.sub(r"<.*?>", "", text)


# Основной цикл с логами
while True:
    print("🔍 Проверяю почту...")
    emails = get_latest_email()

    if emails:
        print("📬 Найдены новые заявки, отправляю в Telegram...")
        send_to_telegram(emails)
    else:
        print("📭 Новых заявок нет.")

    time.sleep(599)
    print("😴 Поспал 10 минут...\n===================================================================")


import imaplib
import email
import telebot
import time
import chardet  # Определение кодировки
from email.header import decode_header
import re
import html

# Настройки
MAIL_SERVER = "imap.mail.ru"
MAIL_USER = "axer1998@mail.ru"
MAIL_PASS = "fdpZ7FHjnQnt4bDd8uwH"
TELEGRAM_TOKEN = "7793677369:AAEw15axx4UMdqnIAYmPX6EvkwIuzTVfl1s"
CHAT_ID = "-1002480536548"

bot = telebot.TeleBot(TELEGRAM_TOKEN)


def decode_email_header(header):
    """Функция для декодирования темы письма"""
    decoded_header = decode_header(header)
    subject = ""
    for part, encoding in decoded_header:
        if isinstance(part, bytes):
            encoding = encoding if encoding else "utf-8"
            subject += part.decode(encoding, errors="ignore")
        else:
            subject += part
    return subject.strip()


def clean_html_text(text):
    """Функция для удаления HTML-тегов, декодирования символов и форматирования"""

    text = html.unescape(text)  # Декодируем HTML-сущности (&nbsp; -> пробел, &quot; -> ")

    text = re.sub(r"<a\s+.*?>.*?</a>", "", text, flags=re.DOTALL)  # Убираем <a>
    text = re.sub(r"<hr\s+.*?>", "", text, flags=re.DOTALL)  # Убираем <hr>

    text = re.sub(r"<.*?>", "", text)  # Удаляем оставшиеся HTML-теги

    # Добавляем переносы строк перед важными полями
    text = re.sub(r"(?<!\n)(Запись от: \d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})", r"\n\1", text)
    text = re.sub(r"(?<!\n)(ID запроса: \d+)", r"\n\1", text)
    text = re.sub(r"(?<!\n)(Отдел: .+)", r"\n\1", text)
    text = re.sub(r"(?<!\n)(Тип: .+)", r"\n\1", text)
    text = re.sub(r"(?<!\n)(Статус: .+)", r"\n\1", text)
    text = re.sub(r"(?<!\n)(Приоритет: .+)", r"\n\1", text)

    # Теперь убираем только лишние пробелы, НЕ удаляя переносы строк!
    text = re.sub(r"[ \t]+", " ", text).strip()
    # Удаляем лишние пустые строки, оставляя максимум 1 подряд
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

    return text


def extract_relevant_info(body):
    """Фильтрует и оставляет только нужную информацию"""
    body = clean_html_text(body)

    # Извлекаем историю запроса
    history_match = re.search(r"Запись от:.*?(?=ID запроса:)", body, re.DOTALL)
    history = history_match.group(0).strip() if history_match else ""

    # Извлекаем детали запроса
    details_match = re.search(r"ID запроса:.*", body, re.DOTALL)
    details = details_match.group(0).strip() if details_match else ""

    return history, details


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

            if not subject.startswith("[~"):
                print(f"🚫 Письмо проигнорировано (не заявка). Тема: {subject}")
                continue

            body = ""
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

            # Фильтруем только нужную информацию
            history, details = extract_relevant_info(body)

            if history and details:
                clean_message = f"📩 Новая заявка!\nТема: {subject}\n\n{history}\n\n{details}"
                messages.append(clean_message)
                print(f"✅ Письмо обработано и готово к отправке!")

        mail.logout()
        return messages

    except Exception as e:
        print(f"❌ Ошибка в get_latest_email: {e}")
        return []


def send_to_telegram(messages):
    for msg in messages:
        try:
            print("📤 Отправляю в Telegram...")
            bot.send_message(CHAT_ID, msg)
            print("✅ Отправлено!")
        except Exception as e:
            print(f"❌ Ошибка при отправке в Telegram: {e}")


# Основной цикл
while True:
    print("🔍 Проверяю почту...")
    emails = get_latest_email()

    if emails:
        print("📬 Найдены новые заявки, отправляю в Telegram...")
        send_to_telegram(emails)
    else:
        print("📭 Новых заявок нет.")

    time.sleep(5)
    print("😴 Поспал 10 минут...\n===================================================================")



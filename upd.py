import imaplib
import email
import telebot
import time
import chardet
from email.header import decode_header
import re
import html
import json
from datetime import datetime

REQUESTS_COUNT_FILE = "requests_count.json"


def get_request_number():
    """Функция возвращает номер заявки за день и увеличивает его в файле"""
    today = datetime.now().strftime("%m%d")  # MMDD

    try:
        with open(REQUESTS_COUNT_FILE, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    request_number = data.get(today, 0) + 1
    data[today] = request_number

    with open(REQUESTS_COUNT_FILE, "w") as file:
        json.dump(data, file)

    return request_number


# Настройки
MAIL_SERVER = "imap.mail.ru"
MAIL_USER = "ant.mosco_w@mail.ru"
MAIL_PASS = "aWaVR6q6mpUgP3tuDUY8"
TELEGRAM_TOKEN = "7793677369:AAEw15axx4UMdqnIAYmPX6EvkwIuzTVfl1s"
CHAT_ID = "-1002284366831"

bot = telebot.TeleBot(TELEGRAM_TOKEN)


def decode_email_header(header):
    """Функция для корректного декодирования темы письма"""
    decoded_header = decode_header(header)
    subject = ""
    for part, encoding in decoded_header:
        if isinstance(part, bytes):
            encoding = encoding if encoding else "utf-8"
            try:
                subject += part.decode(encoding, errors="ignore")
            except:
                subject += part.decode("utf-8", errors="ignore")
        else:
            subject += part
    print(subject, "Название темы.\n")
    return subject.strip()


def clean_html_text(text):
    """Функция для удаления HTML-тегов, декодирования символов и форматирования"""

    text = html.unescape(text)

    text = re.sub(r"<a\s+.*?>.*?</a>", "", text, flags=re.DOTALL)
    text = re.sub(r"<hr\s+.*?>", "", text, flags=re.DOTALL)

    text = re.sub(r"<.*?>", "", text)

    text = re.sub(r"(?<!\n)(Запись от: \d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})", r"\n\1", text)

    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

    return text


def extract_relevant_info(body):
    """Фильтрует и оставляет только нужную информацию"""
    body = clean_html_text(body)

    history_match = re.search(r"Запись от:.*?(?=ID запроса:)", body, re.DOTALL)
    history = history_match.group(0).strip() if history_match else ""

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

            subject = msg["subject"] if msg["subject"] else "(Без темы)"
            subject = decode_email_header(subject)

            if not subject.strip().startswith("[~"):
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

            history, details = extract_relevant_info(body)

            if history:
                request_number = get_request_number()
                today_date = datetime.now().strftime("%m%d")  # MMDD

                ticket_id_match = re.search(r"\[~(\d+)\]", subject)
                ticket_id = ticket_id_match.group(1) if ticket_id_match else "0000"

                formatted_subject = f"{today_date}-{request_number} {subject.replace(f'[~{ticket_id}]', '').strip()} [~{ticket_id}]"

                print(f"🎯 Новая тема заявки: {formatted_subject}")

                # Создаём сообщение
                details = ""
                history = history.replace("Детали Запроса", '')
                clean_message = f"{formatted_subject}\n\n{history}\n\n{details}"
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

    time.sleep(599)
    print("😴 Поспал 10 минут...\n===================================================================")



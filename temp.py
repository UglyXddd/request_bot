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
from bs4 import BeautifulSoup

REQUESTS_COUNT_FILE = "requests_count.json"

print("Хороший день, чтобы поработать вместо Алёны!!! v0.10")


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
#TELEGRAM_TOKEN = "7793677369:AAEw15axx4UMdqnIAYmPX6EvkwIuzTVfl1s"
TELEGRAM_TOKEN = "5965866857:AAFUDbzZCgSPJWYOT5fp71c7PxBq6SFNBss"
#CHAT_ID = "-1002284366831"
CHAT_ID = "650065041"

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
    return subject.strip()


def extract_relevant_info(body):
    res = []
    soup = BeautifulSoup(body, 'html.parser')

    for tag in soup.find_all(True, recursive=True):
        client = []
        if tag.name == 'b':
            if 'клиент' in tag.next_sibling.text.lower():
                client.append(tag.text.strip())
                client.append(tag.next_sibling.text.strip())
                client.append('\n')
                next_font = tag.find_next('font')

                if next_font:
                    font_text = next_font.text.strip()
                    # Убираем строки с цитатами (начинаются с ">")
                    clean_lines = [line for line in font_text.splitlines() if not line.strip().startswith(">")]
                    client.append('\n'.join(clean_lines))
                    client.append('\n')

        res.append(''.join(client)) if client else None

    return '\n\n'.join(res)


def get_latest_email():
    try:
        print("⏳ Подключаюсь к IMAP...")
        mail = imaplib.IMAP4_SSL(MAIL_SERVER)
        mail.login(MAIL_USER, MAIL_PASS)
        print("✅ Вход в почту успешен!")

        mail.select("inbox")
        result, data = mail.search(None, "SEEN")  # Получаем ТОЛЬКО прочитанные письма
        mail_ids = data[0].split()

        print(f"📩 Всего прочитанных писем: {len(mail_ids)}")

        if len(mail_ids) == 0:
            print("📭 Нет прочитанных писем.")
            mail.logout()
            return []

        # Берем последние 100 прочитанных писем и разворачиваем список
        last_emails = mail_ids[-2000:][::-1]  # Берем 100(2000*) последних, но читаем с конца (от новых к старым)

        messages = []
        for num in last_emails:
            if len(messages) >= 150:  # Ограничиваем обработку 30(150*) заявками
                break

            print(f"🔄 Обрабатываю письмо ID: {num}")

            result, msg_data = mail.fetch(num, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = msg["subject"] if msg["subject"] else "(Без темы)"
            subject = decode_email_header(subject)

            if not re.match(r"^\[.*?\]:.*", subject.strip()):
                print(f"🚫 Письмо проигнорировано (не заявка). Тема: {subject}")
                continue  # Пропускаем письмо, если оно не является заявкой

            print(f"📌 Найдена заявка: {subject}")

            body = get_email_body(msg)
            history = extract_relevant_info(body)

            if history:
                request_number = get_request_number()
                today_date = datetime.now().strftime("%m%d")  # MMDD

                ticket_id_match = re.search(r"\[(.*?)\]", subject)
                ticket_id = ticket_id_match.group(1) if ticket_id_match else "0000"

                court_info = extract_court_info(body)
                subject_clean = re.sub(r'\[.*?\]', '', subject).strip()
                formatted_subject = f"{today_date}-{request_number} {subject_clean} [{ticket_id}] {court_info}"

                print(f"🎯 Новая тема заявки: {formatted_subject}")
                history = re.sub(r'<.*?>', '', history)  # Убираем HTML-теги

                clean_message = f"{formatted_subject}\n\n{history}"
                messages.append(clean_message)



        mail.logout()


        return messages

    except Exception as e:
        print(f"❌ Ошибка в get_latest_email: {e}")
        return []


def extract_court_info(body):
    """Функция для извлечения кода и названия суда из тела письма"""
    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text("\n", strip=True)  # Преобразуем HTML в чистый текст

    match = re.search(r"\((\w+)\)([^\n]+)", text)  # Регулярка для поиска кода суда и его названия
    if match:
        court_code = match.group(1).strip()
        court_name = match.group(2).strip()
        court_name = re.sub(r"<.*?>", "", court_name)
        court_code = re.sub(r"<.*?>", "", court_code)

        return f"({court_code}) {court_name}"

    return ""


def get_email_body(msg):
    """Функция получает текст тела письма (любого формата)"""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Игнорируем вложения (файлы)
                if "attachment" in content_disposition:
                    continue

                # Берём первую часть, содержащую текст
                if content_type in ["text/html", "text/plain"]:
                    return part.get_payload(decode=True).decode(errors="ignore")

        # Если письмо не multipart, просто получаем текст
        return msg.get_payload(decode=True).decode(errors="ignore")

    except Exception as e:
        return ""


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

    time.sleep(10)
    print("😴 Поспал 10 минут...\n===================================================================")

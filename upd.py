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

print("Хороший день, чтобы поработать вместо Алёны!!!")

time.sleep(5)


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
    return subject.strip()


def extract_relevant_info(body):
    """Функция извлекает нужную информацию из HTML-сообщения"""
    soup = BeautifulSoup(body, 'html.parser')

    # Разбираем HTML и преобразуем в чистый текст
    plain_text = soup.get_text("\n", strip=True)

    # Разделяем текст на строки
    lines = plain_text.split("\n")

    # Переменная для хранения результата
    result = []
    current_entry = []
    is_collecting = False

    for i, line in enumerate(lines):
        # Прекращаем обработку, если встречаем "Детали Запроса"
        if "Детали Запроса" in line:
            break

        # Если строка содержит "(Клиент)", начинаем сбор
        if "(Клиент)" in line:
            if current_entry:
                result.append("\n".join(current_entry))  # Завершаем предыдущий блок
            current_entry = [line]  # Начинаем новый блок
            is_collecting = True
            continue

        # Если строка содержит "(Персонал)", прекращаем сбор
        if "(Персонал)" in line:
            if current_entry:
                result.append("\n".join(current_entry))  # Завершаем текущий блок
            current_entry = []
            is_collecting = False
            continue

        # Если в блоке клиента, добавляем содержимое, исключая лишние имена перед "(Персонал)"
        if is_collecting and line.strip():
            # Проверяем, что следующая строка не является именем перед "(Персонал)"
            if i + 1 < len(lines) and "(Персонал)" in lines[i + 1]:
                continue  # Пропускаем эту строку, чтобы избежать вывода лишних имен
            current_entry.append(line.strip())

    # Добавляем последний блок, если есть
    if current_entry:
        result.append("\n".join(current_entry))

    # Объединяем все записи в переменную result
    return "\n\n".join(result)


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
            print("\nТЕма:\n\n ", subject.strip(), "\n\n\n")
            if not re.match(r"^\[.*?\]:.*", subject.strip()):
                print(f"🚫 Письмо проигнорировано (не заявка). Тема: {subject}")
                continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
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

            history = extract_relevant_info(body)
            if history:
                request_number = get_request_number()
                today_date = datetime.now().strftime("%m%d")  # MMDD

                ticket_id_match = re.search(r"\[~(\d+)\]", subject)
                ticket_id = ticket_id_match.group(1) if ticket_id_match else "0000"

                court_info = extract_court_info(body)

                formatted_subject = f"{today_date}-{request_number} {subject.replace(f'[~{ticket_id}]', '').strip()} [~{ticket_id}] {court_info}"

                print(f"🎯 Новая тема заявки: {formatted_subject}")
                history = re.sub(r'<.*?>', '', history)
                # Создаём сообщение
                clean_message = f"{formatted_subject}\n\n{history}"
                messages.append(clean_message)
                print(f"✅ Письмо обработано и готово к отправке!")

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

        print("\n\n", court_code, "\n\n", court_name)
        return f"({court_code}) {court_name}"

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

    time.sleep(599)
    print("😴 Поспал 10 минут...\n===================================================================")

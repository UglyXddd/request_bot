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

print("Хороший день, чтобы поработать вместо Алёны!!! v0.9")


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
    res = []
    soup = BeautifulSoup(body, 'html.parser')

    for tag in soup.find_all(True, recursive=True):
        print(f"{tag}  трай по тэгу")
        client = []
        print(f"Промежуточный вывод клиент {client}")
        if tag.name == 'b':
            if 'клиент' in tag.next_sibling.text.lower():
                client.append(tag.text.strip())
                client.append(tag.next_sibling.text.strip())
                client.append('\n')
                client.append(tag.find_next('font').text.strip())
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
            print("\nТема: ", subject.strip(), "\n\n\n")
            if not re.match(r"^\[.*?\]:.*", subject.strip()):
                print(f"🚫 Письмо проигнорировано (не заявка). Тема: {subject}")
                continue

            body = ""
            print(f"\n\n\n Проверка на мультипарт ")
            if msg.is_multipart():
                print(f"\n\n\n Письмо мультипарт ")
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
                print(f"\n\n\n Письмо НЕ мультипарт ")
                payload = msg.get_payload(decode=True)
                encoding = msg.get_content_charset()

                if encoding is None:
                    detected_encoding = chardet.detect(payload)['encoding']
                    encoding = detected_encoding if detected_encoding else "utf-8"

                body = payload.decode(encoding, errors="ignore").strip()
            print(f"\n\n\n Промежуточный вывод ")

            print(f"\n++++\n+++++\n\n++++\n+++++\n\n++++\n+++++\n\n++++\n+++++\n {body}, \n++++\n+++++\n\n++++\n+++++\n\n++++\n+++++\n\n++++\n+++++\n")
            body = get_email_body(msg)

            history = extract_relevant_info(body)
            print(f"\n История: {history}")
            if history:
                request_number = get_request_number()
                today_date = datetime.now().strftime("%m%d")  # MMDD

                ticket_id_match = re.search(r"\[(.*?)\]", subject)
                ticket_id = ticket_id_match.group(1) if ticket_id_match else "0000"

                court_info = extract_court_info(body)
                # Удаляем строку в квадратных скобках с ~ и ticket_id
                subject_clean = re.sub(r'\[.*?\]', '', subject).strip()
                formatted_subject = f"{today_date}-{request_number} {subject_clean} [{ticket_id}] {court_info}"

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
        print(f"❌ Ошибка при получении текста письма: {e}")
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

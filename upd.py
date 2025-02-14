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
import gspread
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

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
TELEGRAM_TOKEN = "7793677369:AAEw15axx4UMdqnIAYmPX6EvkwIuzTVfl1s"
CHAT_ID = "-1002284366831"
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

        result, data = mail.search(None, "SEEN") #для тестов
        #result, data = mail.search(None, "UNSEEN")
        mail_ids = data[0].split()[-10:]  # Для тестов
        #mail_ids = data[0].split()

        print(f"📩 Найдено писем для теста: {len(mail_ids)}")

        processed_emails = []  # Список всех заявок

        for num in mail_ids:
            print(f"🔄 Обрабатываю письмо ID: {num}")

            result, msg_data = mail.fetch(num, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = msg["subject"] if msg["subject"] else "(Без темы)"
            subject = decode_email_header(subject)
            print("\nТема: ", subject.strip(), "\n")

            if not re.match(r"^\[.*?\]:.*", subject.strip()):
                print(f"🚫 Письмо проигнорировано (не заявка). Тема: {subject}")
                continue

            body = get_email_body(msg)  # Получаем HTML-тело письма

            # 🔥 Извлекаем НУЖНЫЕ ДАННЫЕ ДО обработки
            court_name, ticket_id, request_date, request_text = extract_request_data(body)

            # Проверяем, есть ли в письме полезная информация
            if court_name != "Не найдено" and ticket_id != "Не найдено" and request_text:
                processed_emails.append((court_name, ticket_id, request_date, request_text))
                print(f"✅ Заявка добавлена в список!")

        mail.logout()
        return processed_emails  # Возвращаем СПИСОК ВСЕХ ЗАЯВОК

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


# Файл сервисного аккаунта
SERVICE_ACCOUNT_FILE = "requestbot-449717-0fbe05e908c6.json"

# ID Google таблицы
SPREADSHEET_ID = "1lh8woEj_U4WCRpvzWUzGVARFt80KpM27W2dLc8bul2g"

#SPREADSHEET_ID = "1J__mJm9JNu5KWugecueHUNqE7XY3lnHDuSNI8DcvGc4" #тест


def connect_to_sheets():
    """Функция для подключения к Google Sheets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1  # Берем первый лист


def extract_request_data(email_body):
    """Функция для извлечения данных из оригинального письма"""
    soup = BeautifulSoup(email_body, 'html.parser')

    # 1️⃣ Извлекаем ID заявки (из конца письма)
    request_id_match = re.search(r"ID запроса:\s*(\d+)", email_body)
    request_id = request_id_match.group(1) if request_id_match else "Не найдено"

    # 2️⃣ Извлекаем дату создания заявки (из "Запись от: ...")
    date_match = re.search(r"Запись от:\s*(\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})", email_body)
    request_date = date_match.group(1) if date_match else "Не найдено"

    # 3️⃣ Извлекаем название суда
    court_name = "Не найдено"
    court_match = soup.find_all("font", color="#45991c")
    for tag in court_match:
        if re.search(r"\(\w+\)", tag.text):  # Если в тексте есть код суда (пример: (77GV0006))
            court_name = re.sub(r"\(.*?\)", "", tag.text).strip()  # Убираем код, оставляем только название суда
            break

    # 4️⃣ Извлекаем текст заявки (весь текст от клиента)
    request_text = ""
    history_match = soup.find("legend", string="История Запроса")
    if history_match:
        history_fieldset = history_match.find_parent("fieldset")
        if history_fieldset:
            request_text = history_fieldset.get_text("\n", strip=True)

    return court_name, request_id, request_date, request_text


def write_to_google_sheets(court_name, ticket_id, request_date, request_text, engineer_name="Не назначен"):
    """Функция записи данных в Google Sheets"""
    sheet = connect_to_sheets()

    # Формируем строку данных
    new_row = ["", "", "", "", court_name, ticket_id, request_date, request_text, "", "", "", engineer_name]

    # Добавляем строку в таблицу
    sheet.append_row(new_row, value_input_option="RAW")

    print("✅ Данные добавлены в Google Sheets!")


# Основной цикл
while True:
    print("🔍 Проверяю почту...")
    processed_emails = get_latest_email()  # Берем ВСЕ заявки

    if processed_emails:
        print(f"📬 Найдено {len(processed_emails)} новых заявок, отправляю в Telegram...")

        for court_name, ticket_id, request_date, request_text in processed_emails:
            send_to_telegram([f"Заявка {ticket_id}:\n{request_text}"])  # Отправляем каждую заявку

        print("📊 Добавляю заявки в Google Sheets...")
        for court_name, ticket_id, request_date, request_text in processed_emails:
            write_to_google_sheets(court_name, ticket_id, request_date, request_text)  # Запись каждой заявки

        print("✅ Все данные успешно записаны в Google Sheets!")
    else:
        print("📭 Новых заявок нет.")

    time.sleep(599)
    print("😴 Поспал 10 минут...\n===================================================================")

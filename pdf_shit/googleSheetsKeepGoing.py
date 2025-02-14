import os
import re
import gspread
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
from datetime import datetime

# Определяем текущую директорию, где запущен скрипт
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Файл с ключами для Google Sheets (должен лежать рядом со скриптом)
GOOGLE_SHEETS_JSON = os.path.join(CURRENT_DIRECTORY, "../requestbot-449717-0fbe05e908c6.json")

# URL таблицы (оставляем как есть)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1J__mJm9JNu5KWugecueHUNqE7XY3lnHDuSNI8DcvGc4/edit"

# Авторизация в Google Sheets
creds = Credentials.from_service_account_file(GOOGLE_SHEETS_JSON, scopes=["https://spreadsheets.google.com/feeds",
                                                                          "https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(SPREADSHEET_URL)
worksheet = spreadsheet.sheet1

# Получаем уже существующие вторичные коды (чтобы избежать дубликатов)
existing_codes = set(row[1] for row in worksheet.get_all_values()[1:])  # Пропускаем заголовок


# Функция для извлечения метаданных файла
def extract_pdf_metadata(file_path):
    try:
        reader = PdfReader(file_path)
        metadata = reader.metadata
        if metadata and "/CreationDate" in metadata:
            creation_date = metadata["/CreationDate"]
            match = re.search(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", creation_date)
            if match:
                return datetime(
                    int(match.group(1)),  # Год
                    int(match.group(2)),  # Месяц
                    int(match.group(3)),  # День
                    int(match.group(4)),  # Часы
                    int(match.group(5)),  # Минуты
                    int(match.group(6))  # Секунды
                ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Ошибка при чтении {file_path}: {e}")
    return "Неизвестно"


# Функция для обработки PDF
def process_pdfs():
    new_entries = []

    for filename in os.listdir(CURRENT_DIRECTORY):
        if filename.lower().endswith(".pdf"):
            match = re.match(r"([СсОо]+-\d+)[ _-](\d+)[ _-]([\wА-Яа-я]+)\.pdf", filename)
            if match:
                first_code = match.group(1)
                second_code = match.group(2)
                court_name = match.group(3)

                # Проверяем, есть ли уже этот код в таблице
                if second_code in existing_codes:
                    print(f"⏭ Пропускаем {filename}, так как он уже в таблице")
                    continue

                file_path = os.path.join(CURRENT_DIRECTORY, filename)
                creation_datetime = extract_pdf_metadata(file_path)

                # Добавляем в список для загрузки
                new_entries.append([first_code, second_code, court_name, creation_datetime])
                print(f"✅ Добавляем: {first_code}, {second_code}, {court_name}, {creation_datetime}")

    # Записываем в Google Sheets, если есть новые данные
    if new_entries:
        worksheet.append_rows(new_entries)
        print(f"📌 Добавлено {len(new_entries)} записей в Google Sheets.")
    else:
        print("🔍 Новых записей нет.")


# Запускаем обработку
if __name__ == "__main__":
    process_pdfs()

import logging
import json
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# Настройки API Google Sheets
GOOGLE_SHEETS_FILE = "requestbot-449717-5cf6a48a0ed7.json"  # Укажи путь к JSON-файлу ключа
SPREADSHEET_ID = "1J__mJm9JNu5KWugecueHUNqE7XY3lnHDuSNI8DcvGc4"  # Новый ID таблицы
SHEET_NAME = "Лист1"  # Название листа (поменяй, если другое)


# Функция подключения к Google Sheets
def connect_to_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_FILE, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    except Exception as e:
        print(f"Ошибка подключения к Google Sheets: {e}")
        return None


# Функция сохранения заявки в Google Таблицу
def save_to_google_sheets(data):
    try:
        sheet = connect_to_sheets()
        if not sheet:
            return False

        sheet.append_row([
            data['full_name'],
            data['position'],
            data['inventory_number'],
            data['serial_number'],
            data['problem_description']
        ])
        return True
    except Exception as e:
        print(f"Ошибка записи в Google Sheets: {e}")
        return False

    
# Читаем токен из файла
def read_token():
    with open("token.txt", "r") as file:
        return file.read().strip()


token = read_token()
bot = telebot.TeleBot(token)

# Заглушка для проверки пароля
PASSWORDS = {
    "1234": "Отдел разработки",
    "5678": "Отдел поддержки"
}

# Файлы для хранения данных
USER_DATA_FILE = "user_data.json"
IAC_FILE = "iac.json"
UNISERVER_FILE = "uniserver.json"

# Состояния пользователей
user_data = {}


# Функция загрузки данных
def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_user_data():
    with open(USER_DATA_FILE, "w") as file:
        json.dump(user_data, file, indent=4)


# Функция сохранения заявок
def save_request(data, filename):
    try:
        with open(filename, "r") as file:
            requests = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        requests = []
    requests.append(data)
    with open(filename, "w") as file:
        json.dump(requests, file, indent=4)


# Загрузка данных при старте
user_data = load_user_data()


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Привет! Введите пароль для авторизации:")
    user_data[message.chat.id] = {}


@bot.message_handler(
    func=lambda message: message.chat.id in user_data and 'department' not in user_data[message.chat.id])
def check_password(message):
    password = message.text.strip()
    if password in PASSWORDS:
        user_data[message.chat.id]['department'] = PASSWORDS[password]
        bot.send_message(message.chat.id, f"Пароль верный! Ваше подразделение: {PASSWORDS[password]}")
        if message.chat.id in user_data and 'full_name' in user_data[message.chat.id]:
            confirm_data(message)
        else:
            request_full_name(message)
    else:
        bot.send_message(message.chat.id, "Неверный пароль. Попробуйте снова:")


# Функции для запроса данных

def request_full_name(message):
    bot.send_message(message.chat.id, "Введите ваше ФИО:")
    bot.register_next_step_handler(message, request_position)


def request_position(message):
    user_data[message.chat.id]['full_name'] = message.text.strip()
    bot.send_message(message.chat.id, "Введите вашу должность:")
    bot.register_next_step_handler(message, request_inventory_number)


def request_inventory_number(message):
    user_data[message.chat.id]['position'] = message.text.strip()
    bot.send_message(message.chat.id, "Введите ваш инвентарный номер:")
    bot.register_next_step_handler(message, request_serial_number)


def request_serial_number(message):
    user_data[message.chat.id]['inventory_number'] = message.text.strip()
    bot.send_message(message.chat.id, "Введите ваш серийный номер:")
    bot.register_next_step_handler(message, request_problem_description)


def request_problem_description(message):
    user_data[message.chat.id]['serial_number'] = message.text.strip()
    bot.send_message(message.chat.id, "Опишите вашу проблему:")
    bot.register_next_step_handler(message, confirm_data)


def confirm_data(message):
    if message.text != "Назад":
        user_data[message.chat.id]['problem_description'] = message.text.strip()
    save_user_data()
    data = user_data[message.chat.id]
    summary = (f"Ваши данные:\nФИО: {data['full_name']}\n"
               f"Должность: {data['position']}\n"
               f"Инвентарный номер: {data['inventory_number']}\n"
               f"Серийный номер: {data['serial_number']}\n"
               f"Описание проблемы: {data['problem_description']}\n"
               "Всё верно?")

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Всё верно"), KeyboardButton("Изменить данные"))
    bot.send_message(message.chat.id, summary, reply_markup=markup)
    bot.register_next_step_handler(message, edit_data_options)


def edit_data_options(message):
    if message.text == "Изменить данные":
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("Изменить ФИО"), KeyboardButton("Изменить должность"))
        markup.add(KeyboardButton("Изменить инвентарный номер"), KeyboardButton("Изменить серийный номер"))
        markup.add(KeyboardButton("Изменить описание проблемы"), KeyboardButton("Назад"))
        bot.send_message(message.chat.id, "Выберите, что хотите изменить:", reply_markup=markup)
        bot.register_next_step_handler(message, edit_selected_field)
    elif message.text == "Всё верно":
        send_final_options(message)


def edit_selected_field(message):
    fields = {
        "Изменить ФИО": lambda msg: update_field(msg, "full_name", "Введите ваше ФИО:"),
        "Изменить должность": lambda msg: update_field(msg, "position", "Введите вашу должность:"),
        "Изменить инвентарный номер": lambda msg: update_field(msg, "inventory_number",
                                                               "Введите ваш инвентарный номер:"),
        "Изменить серийный номер": lambda msg: update_field(msg, "serial_number", "Введите ваш серийный номер:"),
        "Изменить описание проблемы": lambda msg: update_field(msg, "problem_description", "Опишите вашу проблему:")
    }

    if message.text in fields:
        fields[message.text](message)
    elif message.text == "Назад":
        confirm_data(message)


def send_final_options(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Подать заявку в Юнисервис"), KeyboardButton("Подать заявку в ИАЦ"))
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_application_choice)


def handle_application_choice(message):
    user_id = message.chat.id
    if user_id not in user_data:
        bot.send_message(message.chat.id, "Ошибка: нет данных для заявки. Попробуйте снова.")
        return

    if message.text == "Подать заявку в Юнисервис":
        save_request(user_data[user_id], UNISERVER_FILE)  # Сохраняем в JSON
        success = save_to_google_sheets(user_data[user_id])  # Записываем в Google Sheets

        if success:
            bot.send_message(message.chat.id, "✅ Заявка успешно отправлена в Юнисервис и сохранена в Google Таблице!")
        else:
            bot.send_message(message.chat.id, "❌ Ошибка при записи в Google Таблицу, но заявка сохранена в Юнисервис.")

    elif message.text == "Подать заявку в ИАЦ":
        save_request(user_data[user_id], IAC_FILE)

    # Добавляем кнопку для новой заявки
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Новая заявка"))
    bot.send_message(message.chat.id, "Заявка подана! Хотите создать новую?", reply_markup=markup)
    bot.register_next_step_handler(message, start_new_request)


def start_new_request(message):
    user_id = message.chat.id

    # Проверяем, есть ли данные пользователя в памяти
    if user_id in user_data and 'full_name' in user_data[user_id]:
        bot.send_message(user_id, "Введите описание проблемы:")
        bot.register_next_step_handler(message, confirm_data)  # <-- исправлено
    else:
        bot.send_message(user_id, "Для создания новой заявки нужно ввести данные заново.")
        request_full_name(message)


def create_new_request(message):
    user_id = message.chat.id

    if user_id in user_data and 'full_name' in user_data[user_id]:
        bot.send_message(user_id, "Введите описание проблемы:")
        bot.register_next_step_handler(message, confirm_data)  # <-- исправлено
    else:
        bot.send_message(user_id, "Для создания новой заявки нужно ввести данные заново.")
        request_full_name(message)


def update_field(message, field, prompt):
    user_data[message.chat.id][field] = message.text.strip()
    save_user_data()  # Сохраняем изменения сразу
    bot.send_message(message.chat.id, "Данные обновлены.")
    confirm_data(message)  # Возвращаем пользователя к подтверждению данных


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot.polling(none_stop=True)

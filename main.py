import logging
import json
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


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
        "Изменить ФИО": request_full_name,
        "Изменить должность": request_position,
        "Изменить инвентарный номер": request_inventory_number,
        "Изменить серийный номер": request_serial_number,
        "Изменить описание проблемы": request_problem_description
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
    if message.text == "Подать заявку в Юнисервис":
        save_request(user_data[message.chat.id], UNISERVER_FILE)
    elif message.text == "Подать заявку в ИАЦ":
        save_request(user_data[message.chat.id], IAC_FILE)

    # Добавляем кнопку для создания новой заявки
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Новая заявка"))
    bot.send_message(message.chat.id, "Заявка подана! Хотите создать новую?", reply_markup=markup)
    bot.register_next_step_handler(message, start_new_request)


def start_new_request(message):
    user_id = message.chat.id

    # Проверяем, есть ли данные пользователя в памяти
    if user_id in user_data and 'full_name' in user_data[user_id]:
        data = user_data[user_id]
        summary = (f"Ваши данные:\nФИО: {data['full_name']}\n"
                   f"Должность: {data['position']}\n"
                   f"Инвентарный номер: {data['inventory_number']}\n"
                   f"Серийный номер: {data['serial_number']}\n"
                   "Введите описание проблемы:")
        bot.send_message(user_id, summary)
        # Регистрация только одного шага для описания проблемы
        bot.register_next_step_handler(message, request_problem_description)
    else:
        bot.send_message(user_id, "Для создания новой заявки нужно ввести данные заново.")
        request_full_name(message)



def create_new_request(message):
    user_id = message.chat.id
    if user_id in user_data and 'full_name' in user_data[user_id]:
        data = user_data[user_id]
        summary = (f"Ваши данные:\nФИО: {data['full_name']}\n"
                   f"Должность: {data['position']}\n"
                   f"Инвентарный номер: {data['inventory_number']}\n"
                   f"Серийный номер: {data['serial_number']}\n"
                   "Введите описание проблемы:")
        bot.send_message(user_id, summary)
        bot.register_next_step_handler(message, request_problem_description)
    else:
        bot.send_message(user_id, "Для создания новой заявки нужно ввести данные заново.")
        request_full_name(message)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot.polling(none_stop=True)

import imaplib

MAIL_SERVER = "imap.mail.ru"  # IMAP-сервер Mail.ru
MAIL_USER = "axer1998@mail.ru"  # Введи свою почту
MAIL_PASS = "fdpZ7FHjnQnt4bDd8uwH"  # Введи свой обычный пароль

try:
    # Подключаемся к IMAP-серверу
    mail = imaplib.IMAP4_SSL(MAIL_SERVER, 993)
    mail.login(MAIL_USER, MAIL_PASS)

    print("✅ Подключение успешно!")

    # Завершаем сессию
    mail.logout()

except Exception as e:
    print(f"❌ Ошибка: {e}")

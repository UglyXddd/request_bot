from bs4 import BeautifulSoup
import re

html_message = """<font face="Verdana, Arial, Helvetica" size="2">
<font color="#F07D18">Никита</font><br />
<font color="#F07D18">(50RS0009)Егорьевский городской суд</font><br />
<font color="#F07D18">(49640)2-97-17</font><br />
<font color="#F07D18">egorievsk.mo@sudrf.ru</font><br />
<br />
<font face="Verdana, Arial, Helvetica" size="2">=-=-=-=-=- Пожалуйста, напишите ответ выше этого сообщения -=-=-=-=-=<br />
<br />
Добрый день, коллеги.<br />
Направляю заявку. Свяжитесь пожалуйста с заявителем для решения проблемы. Вы можете самостоятельно закрыть данную заявку, если при ответе на данное письмо в ТЕМУ письма добавите ==closed== сразу после номера заявки. Например [~XXXXX]: ==closed==<br />
Текст из данного письма будет выводиться в отчете для судебного департамента как признак закрытия. Как правило там указывается &quot;Выполнено силами филиала&quot;. Рекомендую в тексте описать, какие работы были выполнены для закрытия заявки.<br />
Просьба пользоваться данной функцией только для закрытия уже существующих заявок.<br />
<br />
БУДЬТЕ ВНИМАТЕЛЬНЫ! В ТЕМЕ письма обязательно должен присутствовать номер заявки вида [~XXXXX].<br />
<br />
<br /><br />
<fieldset style="margin-bottom: 6px; color: #333333;FONT: 11px Verdana, Tahoma;PADDING:3px;">
<legend>История Запроса</legend>

<b>Никита</b> (Клиент) Запись от: 05-02-2025 15:56:05
<hr style="margin-bottom: 6px; height: 1px; BORDER: none; color: #cfcfcf; background-color: #cfcfcf;" />
<br />
<font color="#F07D18">Добрый день! Прошу дать ответ по заявке, будет ли производится ремонт/замена жесткого диска и в какие сроки нам этого ожидать? Ответ ждём очень долго. Просим хотя бы проинформировать по данному вопросу.</font>

<br /><br />

<b>Ирина Полякова</b> (Персонал) Запись от: 19-12-2024 12:12:26
<hr style="margin-bottom: 6px; height: 1px; BORDER: none; color: #cfcfcf; background-color: #cfcfcf;" />
<br />
<font color="#F07D18">=-=-=-=-=- Пожалуйста, напишите ответ выше этого сообщения -=-=-=-=-=<br />
<br />
Добрый день, коллеги. <br />
Направляю заявку. Свяжитесь пожалуйста с заявителем для решения проблемы. Вы можете самостоятельно закрыть данную заявку, если при ответе на данное письмо в ТЕМУ письма добавите ==closed== сразу после номера заявки. Например [~XXXXX]: ==closed==<br />
Текст из данного письма будет выводиться в отчете для судебного департамента как признак закрытия. Как правило там указывается &quot;Выполнено силами филиала&quot;. Рекомендую в тексте описать, какие работы были выполнены для закрытия заявки.<br />
Просьба пользоваться данной функцией только для закрытия уже существующих заявок.<br />
<br />
БУДЬТЕ ВНИМАТЕЛЬНЫ! В ТЕМЕ письма обязательно должен присутствовать номер заявки вида [~XXXXX]. Вместо XXXXX номер заявки.<br />
<br />
</font>

<br /><br />

<b>Никита</b> (Клиент) Запись от: 19-12-2024 11:58:52
<hr style="margin-bottom: 6px; height: 1px; BORDER: none; color: #cfcfcf; background-color: #cfcfcf;" />
<br />
<font color="#F07D18">Прошу отремотировать АРМ Инвент. номер 9000153861304, сер. номер 59MASPXFS9WG, год выпуска 2019, вышел из строя жесткий диск Toshiba PC P300 1TB</font>

<br /><br />

<b>Ирина Полякова</b> (Персонал) Запись от: 27-11-2024 10:27:43
<hr style="margin-bottom: 6px; height: 1px; BORDER: none; color: #cfcfcf; background-color: #cfcfcf;" />
<br />
<font color="#F07D18">=-=-=-=-=- Пожалуйста, напишите ответ выше этого сообщения -=-=-=-=-=<br />
<br />
Добрый день, коллеги,<br />
Направляю заявку. Свяжитесь пожалуйста с заявителем для решения проблемы. Вы можете самостоятельно закрыть данную заявку, если при ответе на данное письмо в ТЕМУ письма добавите ==closed== сразу после номера заявки. Например [~XXXXX]: ==closed==<br />
Текст из данного письма будет выводиться в отчете для судебного департамента как признак закрытия. Как правило там указывается &quot;Выполнено силами филиала&quot;. Рекомендую в тексте описать, какие работы были выполнены для закрытия заявки.<br />
Просьба пользоваться данной функцией только для закрытия уже существующих заявок.<br />
<br />
БУДЬТЕ ВНИМАТЕЛЬНЫ! В ТЕМЕ письма обязательно должен присутствовать номер заявки вида [~XXXXX].<br />
<br />
</font>

<br /><br />

<b>Никита</b> (Клиент) Запись от: 27-11-2024 09:35:50
<hr style="margin-bottom: 6px; height: 1px; BORDER: none; color: #cfcfcf; background-color: #cfcfcf;" />
<br />
<font color="#F07D18">самому жесткому диску инвентарный номер не присваивается, вот инвентарный номер компьютера: 9000153861304</font>

<br /><br />

<b>Гульмира Сулима</b> (Персонал) Запись от: 08-11-2024 15:00:56
<hr style="margin-bottom: 6px; height: 1px; BORDER: none; color: #cfcfcf; background-color: #cfcfcf;" />
<br />
<font color="#F07D18">=-=-=-=-=- Пожалуйста, напишите ответ выше этого сообщения -=-=-=-=-=<br />
<br />
Добрый день.<br />
<br />
Просьба указать инвентарный номер. <br />
<br />
БУДЬТЕ ВНИМАТЕЛЬНЫ! При дальнейшей переписке НЕ ИЗМЕНЯЙТЕ тему (Subject) письма, так как она содержит техническую информацию для Системы!<br />
<br />
Служба технической поддержки ГАС «Правосудие»<br />
<br />
<br />
<br />
</font>

<br /><br />

<b>Даниил</b> (Клиент) Запись от: 08-11-2024 14:53:37
<hr style="margin-bottom: 6px; height: 1px; BORDER: none; color: #cfcfcf; background-color: #cfcfcf;" />
<br />
<font color="#F07D18">Прошу произвести осмотр и ремонт жесткого диска модели Toshiba PC P300 1TB, сер№ 59MASPXFS9WG, 2019 года выпуска, в виду технической неисправности жесткого диска.</font>

<br /><br />


</fieldset>


Детали Запроса<br />
<hr style="margin-bottom: 6px; height: 1px; BORDER: none; color: #cfcfcf; background-color: #cfcfcf;" />
ID запроса: 1358264<br />
Отдел: Обслуживание программных и технических средств<br />
Тип: Выезд<br />
Статус: <font color="">Передана соисполнителю</font><br />
Приоритет: <font color="#F07D18">Высокий</font><br />

<br />
Центральная служба технической поддержки  ГАС Правосудие<br />
</font>
"""

print("\n\n\n========================= Вход: \n\n\n", html_message, "\n\n\n\n\n УЛЮЛЮ\n\n\n")

# Парсим HTML
soup = BeautifulSoup(html_message, 'html.parser')


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
result_text = "\n\n".join(result)

# Выводим итоговый результат
print(result_text)


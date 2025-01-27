import telebot, sqlite3, schedule, requests, time, threading, datetime, pytz, wikipedia, os, random
from telebot import types
from token import token
bot = telebot.TeleBot(token)
ukr_time = pytz.timezone('Europe/Kiev')

current_directory = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_directory, 'JOHN NEGRETO.db')

def init_db():
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS employers (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                city TEXT NOT NULL,
                age INTEGER NOT NULL,
                phone TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()
def get_db_connection():
    conn = sqlite3.connect('JOHN NEGRETO.db', check_same_thread=False)
    return conn

def is_registered(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employers WHERE user_id = ?", (user_id,))
    return cur.fetchone() is not None

def message_reminder():
    API_KEY = 'b938e155c496afc5197c2923cc273eb1'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employers")
    users = cur.fetchall()

    for user in users:
        try:
            user_id = user[0]
            user_name = user[1]
            city_name = user[2]

            if not city_name:
                print(f"Пропущено користувача {user_name} без міста.")
                continue

            url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={API_KEY}&units=metric&lang=uk"
            response = requests.get(url)

            if response.status_code == 200:
                weather_data = response.json()
                temp = weather_data['main']['temp']
                description = weather_data['weather'][0]['description']
                bot.send_message(user_id, f"Добрий ранок, {user_name}! Сьогодні у місті {city_name} буде {description}, "
                                          f"{temp}°C, тому одягніться відповідно.")
            else:
                print(f"Не вдалося отримати погоду для міста {city_name}")
                bot.send_message(user_id, f"Добрий ранок, {user_name}! Не вдалося отримати дані про погоду для міста {city_name}.")

        except Exception as e:
            print(f"Помилка при відправці повідомлення користувачу {user_name}: {e}")

def message_planner():
    schedule.every().day.at("06:00").do(message_reminder)
    while True:
        schedule.run_pending()
        time.sleep(60)

def task_reminder():
    now = datetime.datetime.now(ukr_time).strftime('%d-%m-%Y %H:%M')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employers")
    users = cur.fetchall()
    for user in users:
        user_id = user[0]
        user_name = user[1]
        table_name = f'tasks_{user_name}'
        cur.execute(f"SELECT * FROM {table_name} WHERE date = ?", (now,))
        task = cur.fetchone()
        if task:
            bot.send_message(user_id, f'Не забудьте про {task[2]}')
            cur.execute(f"DELETE FROM {table_name} WHERE date = ?", (now,))
    conn.commit()
    conn.close()

def task_planner():
    schedule.every(1).minute.do(task_reminder)
    while True:
        schedule.run_pending()
        time.sleep(60)

@bot.message_handler(commands=["start"])
def registration(message):
    if is_registered(message.from_user.id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Завдання")
        button2 = types.KeyboardButton("Футбол")
        button3 = types.KeyboardButton("Інформація")
        button4 = types.KeyboardButton("Робота")
        button5 = types.KeyboardButton("Книги")
        button6 = types.KeyboardButton("Фільми")
        keyboard.add(button1, button2, button3, button6, button5, button4)
        bot.send_message(message.chat.id,
                         f"Чим Вам допомогти {message.from_user.first_name}?",
                         reply_markup=keyboard)
    else:
        starting = types.ReplyKeyboardMarkup(resize_keyboard=True)
        go = types.KeyboardButton("Зареєструватись")
        starting.add(go)
        bot_message = bot.send_message(message.chat.id, 'Привіт, я John Negreto.'
                                                        'Можу допомогти тобі, але спочатку ти маєш зареєструватись.',
                                        reply_markup=starting)
        bot.register_next_step_handler_by_chat_id(message.chat.id, creation_1)

def creation_1(message):
    if message.text == "Зареєструватись":
        bot.send_message(message.chat.id, 'В якому місті Ви проживаєте?')
        bot.register_next_step_handler(message, creation_2)
    else:
        bot.send_message(message.chat.id, 'Будь ласка, натисніть "Зареєструватись".')
        bot.register_next_step_handler(message, handle_registration)

def creation_2(message):
    user_city = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("Надіслати номер телефону", request_contact=True)
    keyboard.add(button)
    bot.send_message(message.chat.id, 'Уведіть Ваш телефон, натиснувши на кнопку.', reply_markup=keyboard)
    bot.register_next_step_handler_by_chat_id(message.chat.id, lambda msg: creation_3(msg, user_city))
def creation_3(message, user_city):
    if message.content_type == 'contact':
        user_number = message.contact.phone_number
        bot_message = bot.send_message(message.chat.id, 'Скільки Вам років?')
        bot.register_next_step_handler(bot_message, creation_over, user_city, user_number)
    else:
        bot.send_message(message.chat.id, 'Будь ласка, надішліть номер телефону, натиснувши кнопку.')
        bot.register_next_step_handler(message, lambda msg: creation_3(msg, user_city))

def creation_over(message, user_city, user_number):
    user_age = message.text
    name_is = message.from_user.username
    if name_is:
        user_name = name_is
    else:
        rand_number = random.randint(1, 9999)
        user_name = f"user_N{rand_number}"
    user_id = message.from_user.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO employers (user_id, username, city, age, phone) VALUES (?, ?, ?, ?, ?)',
                    (user_id, user_name, user_city, user_age, user_number))
    conn.commit()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton("Завдання")
    button2 = types.KeyboardButton("Футбол")
    button3 = types.KeyboardButton("Інформація")
    button4 = types.KeyboardButton("Робота")
    button5 = types.KeyboardButton("Книги")
    button6 = types.KeyboardButton("Фільми")
    keyboard.add(button1, button2, button3, button6, button5, button4)
    bot.send_message(message.chat.id, f"{user_name}, Ви зареєстровані!", reply_markup=keyboard)

@bot.message_handler(func= lambda message: message.text == 'Завдання')
def tasks(message):
    if is_registered(message.from_user.id):
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton("Створити", callback_data='button_1')
        button2 = types.InlineKeyboardButton("Переглянути", callback_data='button_2')
        button3 = types.InlineKeyboardButton("Видалити", callback_data='button_3')
        keyboard.add(button1, button2, button3)
        bot.send_message(message.chat.id, f"Виберіть відповідну кнопку", reply_markup=keyboard)
    else:
        starting = types.ReplyKeyboardMarkup(resize_keyboard=True)
        go = types.KeyboardButton("Зареєструватись")
        starting.add(go)
        bot.send_message(message.chat.id, 'Натисніть "Зареєструватись", щоб почати.', reply_markup=starting)

@bot.message_handler(func=lambda message: message.text == 'Футбол')
def football(message):
    if not is_registered(message.from_user.id):
        bot.send_message(message.chat.id, "Вам потрібно зареєструватися, щоб використовувати цю функцію.")
        return
    API_KEY = '8a051e4e4d0f44f2b653fb55248199f7'
    API_URL = 'https://api.football-data.org/v4/matches'
    today = datetime.datetime.now().date()

    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(f"{API_URL}?date={today}", headers=headers)

    if response.status_code == 200:
        matches = response.json().get('matches', [])
        leagues = {}

        kyiv_tz = pytz.timezone('Europe/Kiev')

        for match in matches:
            league = match.get('competition')
            if league:
                league_id = league.get('id')
                if league_id in [2002, 2014, 2021, 2019]:
                    home_team = match['homeTeam']['name']
                    away_team = match['awayTeam']['name']
                    match_time = match['utcDate']

                    utc_time = datetime.datetime.strptime(match_time, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                    local_time = utc_time.astimezone(kyiv_tz)
                    date_str = local_time.strftime('%H:%M')

                    league_name = league['name']
                    if league_name not in leagues:
                        leagues[league_name] = []
                    leagues[league_name].append(f"{home_team} vs {away_team}, {date_str}")

        for league_name, match_list in leagues.items():
            if match_list:
                bot.reply_to(message, f"{league_name}:\n\n" + "\n".join(match_list))

        if not leagues:
            bot.reply_to(message, "Сьогодні немає матчів у вибраних лігах.")
    else:
        bot.reply_to(message, f"Помилка: {response.status_code} - {response.text}")

@bot.message_handler(func=lambda message: message.text == 'Інформація')
def question(message):
    bot.send_message(message.chat.id, 'Що саме Вас цікавить?')
    bot.register_next_step_handler(message, answer)
def answer(message):
    wikipedia.set_lang("uk")
    topic = message.text
    try:
        summary = wikipedia.summary(topic, sentences=10)
        bot.send_message(message.chat.id, summary)
    except wikipedia.exceptions.DisambiguationError as e:
        bot.send_message(message.chat.id, f"Виберіть одну з цих тем: {e.options}")
    except Exception as e:
        bot.send_message(message.chat.id, 'Вибачте, не вдалося знайти інформацію про цю тему.')

@bot.message_handler(func=lambda message: message.text == 'Робота')
def work(message):
    if is_registered(message.from_user.id):
        keyboard = types.InlineKeyboardMarkup()
        button4 = types.InlineKeyboardButton("Операційний", callback_data='button_4')
        button5 = types.InlineKeyboardButton("Документи", callback_data='button_5')
        button6 = types.InlineKeyboardButton("Відеонагляд", callback_data='button_6')
        keyboard.add(button4, button5, button6)
        bot.send_message(message.chat.id, f'{message.from_user.first_name}, Що ви шукаєте ?', reply_markup=keyboard)
    else:
        starting = types.ReplyKeyboardMarkup(resize_keyboard=True)
        go = types.KeyboardButton("Зареєструватись")
        starting.add(go)
        bot.send_message(message.chat.id, 'Натисніть "Зареєструватись", щоб почати.', reply_markup=starting)

@bot.message_handler(func= lambda message: message.text == 'Фільми')
def films(message):
    if is_registered(message.from_user.id):
        keyboard = types.InlineKeyboardMarkup()
        button7 = types.InlineKeyboardButton("Додати", callback_data='button_7')
        button8 = types.InlineKeyboardButton("Переглянути", callback_data='button_8')
        button9 = types.InlineKeyboardButton("Видалити", callback_data='button_9')
        keyboard.add(button7, button8, button9)
        bot.send_message(message.chat.id, f"Виберіть відповідну кнопку", reply_markup=keyboard)
    else:
        starting = types.ReplyKeyboardMarkup(resize_keyboard=True)
        go = types.KeyboardButton("Зареєструватись")
        starting.add(go)
        bot.send_message(message.chat.id, 'Натисніть "Зареєструватись", щоб почати.', reply_markup=starting)

@bot.message_handler(func= lambda message: message.text == 'Книги')
def books(message):
    if is_registered(message.from_user.id):
        keyboard = types.InlineKeyboardMarkup()
        button10 = types.InlineKeyboardButton("Прочитані", callback_data='button_10')
        button11 = types.InlineKeyboardButton("Нові", callback_data='button_11')
        keyboard.add(button10, button11)
        bot.send_message(message.chat.id, f"Виберіть відповідну кнопку", reply_markup=keyboard)
    else:
        starting = types.ReplyKeyboardMarkup(resize_keyboard=True)
        go = types.KeyboardButton("Зареєструватись")
        starting.add(go)
        bot.send_message(message.chat.id, 'Натисніть "Зареєструватись", щоб почати.', reply_markup=starting)

@bot.callback_query_handler(func=lambda call: True)
def buttons_task(call):
    if call.message:
        user_name = call.from_user.username

        if call.data == "button_1":
            handle_task_creation(call, user_name)

        elif call.data == 'button_2':
            show_tasks(call, user_name)

        elif call.data == 'button_3':
            prompt_task_deletion(call, user_name)

        elif call.data == 'button_4':
            send_checklist(call)

        elif call.data == 'button_5':
            send_documents(call)

        elif call.data == 'button_6':
            send_google_drive_links(call)

        elif call.data == 'button_7':
            prompt_add_film(call, user_name)

        elif call.data == 'button_8':
            show_films(call)

        elif call.data == 'button_9':
            prompt_film_deletion(call, user_name)

        elif call.data == 'button_11':
            manage_books(call, user_name)

        elif call.data == 'button_10':
            my_books(call, user_name)

def handle_task_creation(call, user_name):
    table_name = f'tasks_{user_name}'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (number INTEGER PRIMARY KEY AUTOINCREMENT, "
                f"date TEXT NOT NULL, task TEXT NOT NULL)")
    conn.commit()

    bot_message = bot.send_message(call.message.chat.id, 'Уведіть дату у форматі ДД-ММ-РРРР ГГ:ХХ, і я вам нагадаю про нього.')
    bot.register_next_step_handler(bot_message, lambda msg: deadline(msg, table_name))

def deadline(message, table_name):
    deadline = message.text
    bot_message = bot.send_message(message.chat.id, 'Опишіть Ваше завдання')
    bot.register_next_step_handler(bot_message, lambda msg: task_over(msg, deadline, table_name))

def task_over(message, deadline, table_name):
    task = message.text.lower()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {table_name} (date, task) VALUES (?, ?)", (deadline, task))
    conn.commit()
    bot.send_message(message.chat.id, 'Завдання створено!')

def show_tasks(call, user_name):
    table_name = f'tasks_{user_name}'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    tasks = cur.fetchall()

    if tasks:
        elements = ""
        for element in tasks:
            elements += f"N{element[0]}) {element[1]} - {element[2]}\n"
        conn.commit()
        bot.send_message(call.message.chat.id, f'Ось Ваші зафіксовані завдання...')
        bot.send_message(call.message.chat.id, elements)
    else:
        bot.send_message(call.message.chat.id, 'У Вас немає завдань.')

def prompt_task_deletion(call, user_name):
    bot_message = bot.send_message(call.message.chat.id, 'Уведіть номер завдання')
    bot.register_next_step_handler(bot_message, lambda msg: delete_task(msg, user_name))

def delete_task(message, user_name):
    number = message.text
    table_name = f'tasks_{user_name}'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table_name} WHERE number = ?", (number,))
    conn.commit()
    bot.send_message(message.chat.id, 'Завдання видалено!')

def send_checklist(call):
    message_text = (
        "Чек-лист РЦ:\n"
        "https://docs.google.com/forms/d/e/1FAIpQLSeCUmyt0Xc4jHNJ9ez2gwLzobneIw2LibMJ4InTtJoC_Cc8hg/viewform\n\n"
        "Чек-лист магазину:\n"
        "https://forms.gle/QEEZLcPM9iJjb6Lp7\n"
        "https://docs.google.com/spreadsheets/d/181RYCpcl5_QKJ7WHyyjQ50ef_uJzU24P0IDC5ZbIYQg/edit#gid=2022098910\n\n"
        "Чек-лист менеджер:\n"
        "https://forms.gle/3JdwaWUnAPnQab849\n"
        "https://docs.google.com/spreadsheets/d/1zITMg2BaRNvXZpR0Q4dCp-tBSyXVCE-qGwR2rJfB5S8/edit?resourcekey#gid=1097342196\n\n"
        "Чек-лист менеджера Тімірязєва-12б:\n"
        "https://forms.gle/RuMnMbYJDE3JVpeb8\n"
        "https://docs.google.com/spreadsheets/d/1QZdLLkbhbhlYkeZ40yuCOz5UCTJ6l4QcbjgK2inD9c8/edit?resourcekey#gid=219982839\n\n"
        "Чек-лист магазину Тімірязєва-12б:\n"
        "https://forms.gle/r3fsLNMxmZYUaxY36\n"
        "https://docs.google.com/spreadsheets/d/1QZdLLkbhbhlYkeZ40yuCOz5UCTJ6l4QcbjgK2inD9c8/edit?resourcekey#gid=219982839\n\n"
        "Чек-лист пекарні:\n"
        "https://forms.gle/r3fsLNMxmZYUaxY36\n"
        "https://docs.google.com/spreadsheets/d/1QZdLLkbhbhlYkeZ40yuCOz5UCTJ6l4QcbjgK2inD9c8/edit?resourcekey#gid=219982839\n"
    )
    bot.send_message(call.message.chat.id, message_text)

def send_documents(call):
    file_1 = open('списання.xlsx', 'rb')
    file_2 = open('службова (дорога).docx', 'rb')
    file_3 = open('протерміновка.xlsx', 'rb')
    bot.send_document(call.message.chat.id, file_1)
    bot.send_document(call.message.chat.id, file_2)
    bot.send_document(call.message.chat.id, file_3)

def send_google_drive_links(call):
    message_text = (
        "Гугл диск СБ:\n"
        "https://drive.google.com/drive/my-drive\n\n"
        "Чек-лист магазину:\n"
        "https://docs.google.com/spreadsheets/d/17oXUoBVZ2YzGn9Urnb1S1zfKBP8ISt_tcBHCfAeBn_s/edit?gid=1262384048#gid=1262384048\n\n"
        "Зловживання працівників:\n"
        "https://docs.google.com/spreadsheets/d/13yAl_IVZ8EQmnH0QDUZhCAG4059_ntWCuqegP5EYNe4/edit#gid=1882209401\n\n"
        "Графіки роботи магазинів:\n"
        "https://drive.google.com/drive/folders/1-4XhgndS2oH_HDHc9UHF521raijsFnpE\n\n"
    )
    bot.send_message(call.message.chat.id, message_text)

def prompt_add_film(call, user_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS films (number INTEGER PRIMARY KEY AUTOINCREMENT, names TEXT NOT NULL)")
    conn.commit()
    bot_message = bot.send_message(call.message.chat.id,
                                   'Якщо ви знайшли якийсь гарний фільм, напишіть мені, я запамятаю.')
    bot.register_next_step_handler(bot_message, lambda msg: films(msg, user_name))

def films(message, user_name):
    film = message.text
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO films (names) VALUES (?)", (film,))
    conn.commit()
    bot.send_message(message.chat.id, "Супер, я запам'ятав цей шедевр!")

def show_films(call):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM films")
    films = cur.fetchall()

    if films:
        elements = ""
        for element in films:
            elements += f"{element[0]}. {element[1]}\n"
        conn.commit()
        bot.send_message(call.message.chat.id, f'Ось фільми, які варто Вам переглянути!')
        bot.send_message(call.message.chat.id, elements)
    else:
        bot.send_message(call.message.chat.id,
                         'У Вас немає фільмів, які треба переглянути.\nЙдіть працюйте, а не фільми дивіться!')

def prompt_film_deletion(call, user_name):
    bot_message = bot.send_message(call.message.chat.id, 'Уведіть номер фільма.., і я його видалю.')
    bot.register_next_step_handler(bot_message, lambda msg: delete_film(msg, user_name))

def delete_film(message, user_name):
    number = message.text
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM films WHERE number = ?", (number,))
    conn.commit()
    bot.send_message(message.chat.id, 'Фільм видалено!')

def manage_books(call, user_name):
    table_name = f'books_{user_name}'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (number INTEGER PRIMARY KEY AUTOINCREMENT, "
                f"author TEXT NOT NULL, book TEXT NOT NULL)")
    cur.execute(f"SELECT * FROM {table_name}")
    books = cur.fetchall()

    if books:
        elements = ""
        for element in books:
            elements += f"{element[0]}) {element[1]} - {element[2]}\n"
        conn.commit()
        bot.send_message(call.message.chat.id, f'Ось Ваші нові книги...')
        bot.send_message(call.message.chat.id, elements)

    bot_message = bot.send_message(call.message.chat.id, f'Бажаєте додати ще?')
    bot.register_next_step_handler(bot_message, lambda msg: yes_or_no(msg, user_name))

def yes_or_no(message, user_name):
    if message.text.lower() == 'так' or message.text.lower() == 'да':
        bot_message = bot.send_message(message.chat.id, 'Уведіть автора, назву книги.')
        bot.register_next_step_handler(bot_message, lambda msg: add_book(msg, user_name))
    else:
        bot.send_message(message.chat.id, 'Добре, до наступного разу!')

def add_book(message, user_name):
    try:
        book_data = message.text.split(",")
        if len(book_data) == 2:
            author = book_data[0].strip()
            book = book_data[1].strip()
            table_name = f'books_{user_name}'
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"INSERT INTO {table_name} (author, book) VALUES (?, ?)", (author, book))
            conn.commit()
            bot.send_message(message.chat.id, "Супер! Книга додана.")
        else:
            bot.send_message(message.chat.id,
                             "Будь ласка, введіть автора та назву книги через кому.")
            bot.register_next_step_handler(message, lambda msg: add_book(msg, user_name))
    except Exception as e:
        bot.send_message(message.chat.id, f"Сталася помилка: {e}")

def my_books(message, user_name):
    table_name = f'mybooks_{user_name}'
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (number INTEGER PRIMARY KEY AUTOINCREMENT, "
                    f"author TEXT NOT NULL, book TEXT NOT NULL)")
    except sqlite3.Error as e:
        bot.send_message(message.message.chat.id, f"Помилка при створенні таблиці: {e}")
        return
    cur.execute(f"SELECT * FROM {table_name}")
    books = cur.fetchall()
    if books:
        elements = ""
        for element in books:
            elements += f"{element[0]}) {element[1]} - {element[2]}\n"
        bot.send_message(message.message.chat.id, 'Ось список Ваших прочитаних книг...')
        bot.send_message(message.message.chat.id, elements)
    else:
        bot.send_message(message.message.chat.id, 'У Вас нема прочитаних книг!')
    bot_message = bot.send_message(message.message.chat.id, 'Ви вже прочитали щось нове ?')
    bot.register_next_step_handler(bot_message, lambda msg: yes_or_no2(msg, user_name))

def yes_or_no2(message, user_name):
    if message.text.lower() == 'так' or message.text.lower() == 'да':
        bot_message = bot.send_message(message.chat.id, 'Уведіть номер книги, яку Ви прочитали, я внесу її у список прочитаних.')
        bot.register_next_step_handler(bot_message, lambda msg: add_mybook(msg, user_name))
    else:
        bot.send_message(message.chat.id, 'Добре, до наступного разу!')

def add_mybook(message, user_name):
    number_book = message.text
    newbooks = f'books_{user_name}'
    mybooks = f'mybooks_{user_name}'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {newbooks} WHERE number = ?", (number_book,))
    mybook = cur.fetchone()
    cur.execute(f"INSERT INTO {mybooks} (author, book) VALUES (?, ?)", (mybook[1], mybook[2]))
    cur.execute(f"DELETE FROM {newbooks} WHERE number = ?", (number_book,))
    conn.commit()
    bot.send_message(message.chat.id, 'Ого, ви молодець..')
    bot.send_message(message.chat.id, f"Швидко прочитали '{mybook[2]}'")



if __name__ == "__main__":
    threading.Thread(target=task_planner, daemon=True).start()
    threading.Thread(target=message_planner, daemon=True).start()
    bot.polling(none_stop=True)

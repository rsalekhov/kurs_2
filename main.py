
import random
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from config import DATABASE_CONFIG, TELEGRAM_TOKEN
import psycopg2

print('Start telegram bot...')

state_storage = StateMemoryStorage()
bot = TeleBot(TELEGRAM_TOKEN, state_storage=state_storage)

known_users = set()  # Используем множество для быстрого поиска
userStep = {}
buttons = []

conn = psycopg2.connect(**DATABASE_CONFIG)
cursor = conn.cursor()

def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"

def get_random_word_from_user(user_id):
    cursor.execute(f"""
        SELECT target_word, translate_word, other_words
        FROM user_words{user_id}
        ORDER BY RANDOM() LIMIT 1;
    """)
    result = cursor.fetchone()
    return result

def create_user_tables(user_id):
    # Создаем таблицу user_info, если ее еще нет
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_info
        (
            user_id bigint NOT NULL,
            CONSTRAINT user_info_pkey PRIMARY KEY (user_id)
        )
        TABLESPACE pg_default;
    """)

    # Добавляем пользователя в user_info, если его еще нет
    cursor.execute("""
        INSERT INTO user_info (user_id)
        VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING;
    """, (user_id,))

    # Создаем таблицу user_words*user_id*, если ее еще нет
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS user_words{user_id}
        (
            id serial NOT NULL,
            user_id bigint NOT NULL,
            target_word character varying(255) COLLATE pg_catalog."default" NOT NULL,
            translate_word character varying(255) COLLATE pg_catalog."default" NOT NULL,
            other_words text[] COLLATE pg_catalog."default",
            CONSTRAINT user_words_{user_id}_pkey PRIMARY KEY (id),  -- Изменилось здесь
            CONSTRAINT user_words_user_id_fkey FOREIGN KEY (user_id)
                REFERENCES public.user_info (user_id) MATCH SIMPLE
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        TABLESPACE pg_default;
    """)

    conn.commit()


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'

class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()

def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        return 0

def get_random_words_from_other_words():
    cursor.execute("SELECT word FROM other_words ORDER BY RANDOM() LIMIT 3;")
    result = cursor.fetchall()
    return [row[0] for row in result]

@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id

    # Проверяем наличие пользователя в базе данных
    cursor.execute("SELECT EXISTS (SELECT 1 FROM user_info WHERE user_id = %s)", (cid,))
    user_exists = cursor.fetchone()[0]

    # Создаем/регистрируем пользователя и его таблицы при первом запуске
    if not user_exists:
        create_user_tables(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Hello, stranger, let's study English...")

    markup = types.ReplyKeyboardMarkup(row_width=2)
    # ... (остальной код без изменений)


    global buttons
    buttons = []

    user_id = message.from_user.id
    cursor.execute(f"SELECT COUNT(*) FROM user_words{user_id}")
    user_words_count = cursor.fetchone()[0]

    if user_words_count == 0:
        # Если таблица пользователя пуста, копируем слова из общей таблицы
        cursor.execute(f"""
                    INSERT INTO user_words{user_id} (user_id, target_word, translate_word)
                    SELECT {user_id}, target_word, translate_word
                    FROM words_table;
                """)
        conn.commit()

        # Продолжаем обычный процесс создания карточек
    target_word, translate, _ = get_random_word_from_user(user_id)
    random_words = get_random_words_from_other_words()

    target_word_btn = types.KeyboardButton(translate)
    buttons.append(target_word_btn)

    other_words_btns = [types.KeyboardButton(word) for word in random_words]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)

    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {target_word}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = random_words

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    cid = message.chat.id
    user_id = message.from_user.id
    userStep[cid] = 2

    # Попросим пользователя ввести слово для удаления
    bot.send_message(cid, "Введите слово для удаления:")
    bot.register_next_step_handler(message, process_delete_word, user_id)

def process_delete_word(message, user_id):
    cid = message.chat.id
    word_to_delete = message.text.strip()

    if word_to_delete:
        # Здесь происходит удаление строки, если слово совпадает с target_word
        cursor.execute("""
            DELETE FROM user_words{} WHERE user_id = %s AND target_word = %s;
        """.format(user_id), (user_id, word_to_delete))

        if cursor.rowcount > 0:
            conn.commit()
            print(f"Word '{word_to_delete}' deleted from the database.")
            bot.send_message(cid, f"Слово '{word_to_delete}' успешно удалено.")
        else:
            bot.send_message(cid, f"Слово '{word_to_delete}' не найдено. Попробуйте еще раз.")
    else:
        bot.send_message(cid, "Вы не ввели слово для удаления. Пожалуйста, попробуйте еще раз.")


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    user_id = message.from_user.id
    userStep[cid] = 1

    # Попросим пользователя ввести новое слово на английском
    bot.send_message(cid, "Введите новое слово на русском:")
    bot.register_next_step_handler(message, process_new_word_english, user_id)

def process_new_word_english(message, user_id):
    cid = message.chat.id
    new_word_english = message.text.strip()

    if new_word_english:
        # Сохраняем английское слово в контексте для использования при добавлении в базу данных
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['new_word_english'] = new_word_english

        # Просим пользователя ввести перевод на русском
        bot.send_message(cid, "Теперь введите перевод на английском:")
        bot.register_next_step_handler(message, process_new_word_russian, user_id)
    else:
        bot.send_message(cid, "Вы не ввели новое слово. Пожалуйста, попробуйте еще раз.")

def process_new_word_russian(message, user_id):
    cid = message.chat.id
    new_word_russian = message.text.strip()

    if new_word_russian:
        # Сохраняем русское слово в контексте для использования при добавлении в базу данных
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            new_word_english = data['new_word_english']

        # Здесь происходит запись нового слова во все столбцы в новой строке
        cursor.execute("""
            INSERT INTO user_words{} (user_id, target_word, translate_word)
            VALUES (%s, %s, %s);
        """.format(user_id), (user_id, new_word_english, new_word_russian))

        conn.commit()
        print("Word added to the database:", new_word_english, new_word_russian)

        # Отправим пользователю сообщение о том, что слово получено и в процессе перевода
        bot.send_message(cid, "Мы получили ваше слово. Спасибо за добавление!")

        # После добавления слова, предоставим новые карточки пользователю
        create_cards(message)
    else:
        bot.send_message(cid, "Вы не ввели перевод на русском. Пожалуйста, попробуйте еще раз.")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        translate_word = data['translate_word']
        others = data['other_words']

        if text == translate_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        elif text in others:
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{target_word}")
        else:
            hint = show_hint("Неверный выбор. Попробуйте еще раз.")

    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)
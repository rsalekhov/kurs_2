import random
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from config import DATABASE_CONFIG, TELEGRAM_TOKEN
import psycopg2

print('Start telegram bot...')

state_storage = StateMemoryStorage()
bot = TeleBot(TELEGRAM_TOKEN, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []

conn = psycopg2.connect(**DATABASE_CONFIG)
cursor = conn.cursor()

def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"

def get_random_word_from_db():
    cursor.execute("SELECT target_word, translate_word, other_words FROM words_table ORDER BY RANDOM() LIMIT 1;")
    result = cursor.fetchone()
    return result

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
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0

@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Hello, stranger, let study English...")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    target_word, translate, others = get_random_word_from_db()
    target_word_btn = types.KeyboardButton(translate)  # Исправлено здесь
    buttons.append(target_word_btn)
    other_words_btns = [types.KeyboardButton(word) for word in others]
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
        data['other_words'] = others

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    cid = message.chat.id
    userStep[cid] = 2

    # Попросим пользователя ввести слово для удаления
    bot.send_message(cid, "Введите слово для удаления:")
    bot.register_next_step_handler(message, process_delete_word)

def process_delete_word(message):
    cid = message.chat.id
    word_to_delete = message.text.strip()

    if word_to_delete:
        # Здесь происходит удаление строки, если слово совпадает с target_word
        cursor.execute("""
            DELETE FROM user_words
            WHERE user_id = %s AND target_word = %s;
        """, (cid, word_to_delete))

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
    userStep[cid] = 1

    # Попросим пользователя ввести новое слово
    bot.send_message(cid, "Введите новое слово:")
    bot.register_next_step_handler(message, process_new_word)

def process_new_word(message):
    cid = message.chat.id
    new_word = message.text.strip()

    if new_word:
        # Здесь происходит запись нового слова во все столбцы в новой строке
        cursor.execute("""
            INSERT INTO user_words (user_id, target_word, translate_word, other_words)
            VALUES (%s, %s, %s, %s);
        """, (cid, new_word, new_word, [new_word, new_word, new_word]))

        conn.commit()
        print("Word added to the database:", new_word)

        # Отправим пользователю сообщение о том, что слово получено и в процессе перевода
        bot.send_message(cid, "Мы получили ваше слово. Наши специалисты занимаются его переводом. Скоро вы сможете его использовать в карточках.")

        # После добавления слова, предоставим новые карточки пользователю
        create_cards(message)
    else:
        bot.send_message(cid, "Вы не ввели новое слово. Пожалуйста, попробуйте еще раз.")



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
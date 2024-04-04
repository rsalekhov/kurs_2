import psycopg2
from config import DATABASE_CONFIG


def create_tables():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()

    # Создание таблицы user_info, если ее еще нет
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_info
        (
            user_id BIGINT PRIMARY KEY
        )
    """)

    # Создание таблицы user_words, если ее еще нет
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_words
        (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES user_info(user_id),
            target_word VARCHAR(255) NOT NULL,
            translate_word VARCHAR(255) NOT NULL,
            other_words TEXT[]
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def get_random_word_from_user(user_id):
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT target_word, translate_word, other_words
        FROM user_words
        WHERE user_id = %s
        ORDER BY RANDOM() LIMIT 1;
    """, (user_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result


def create_user_tables(user_id):
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()

    # Добавляем пользователя в user_info, если его еще нет
    cursor.execute("""
        INSERT INTO user_info (user_id)
        VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING;
    """, (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

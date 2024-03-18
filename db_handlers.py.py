# db_handlers.py

import psycopg2
from config import DATABASE_CONFIG


def create_tables():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()

    # Создание таблиц user_info и user_words
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_info
        (
            user_id bigint NOT NULL,
            CONSTRAINT user_info_pkey PRIMARY KEY (user_id)
        )
        TABLESPACE pg_default;
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_words
        (
            id serial NOT NULL,
            user_id bigint NOT NULL,
            target_word character varying(255) COLLATE pg_catalog."default" NOT NULL,
            translate_word character varying(255) COLLATE pg_catalog."default" NOT NULL,
            other_words text[] COLLATE pg_catalog."default",
            CONSTRAINT user_words_pkey PRIMARY KEY (id),
            CONSTRAINT user_words_user_id_fkey FOREIGN KEY (user_id)
                REFERENCES public.user_info (user_id) MATCH SIMPLE
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
        TABLESPACE pg_default;
    """)

    conn.commit()
    cursor.close()
    conn.close()


def get_random_word_from_user(user_id):
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT target_word, translate_word, other_words
        FROM user_words{user_id}
        ORDER BY RANDOM() LIMIT 1;
    """)
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result


def create_user_tables(user_id):
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()

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
    cursor.close()
    conn.close()

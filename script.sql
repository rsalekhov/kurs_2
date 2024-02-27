-- Table: public.words_table

-- DROP TABLE IF EXISTS public.words_table;

CREATE TABLE IF NOT EXISTS public.words_table
(
    id integer NOT NULL DEFAULT nextval('words_table_id_seq'::regclass),
    target_word character varying(255) COLLATE pg_catalog."default",
    translate_word character varying(255) COLLATE pg_catalog."default",
    other_words character varying(255)[] COLLATE pg_catalog."default",
    CONSTRAINT words_table_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.words_table
    OWNER to postgres;



-- Table: public.user_info

-- DROP TABLE IF EXISTS public.user_info;

CREATE TABLE IF NOT EXISTS public.user_info
(
    id integer NOT NULL DEFAULT nextval('user_info_id_seq'::regclass),
    user_id integer,
    CONSTRAINT user_info_pkey PRIMARY KEY (id),
    CONSTRAINT user_info_user_id_key UNIQUE (user_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.user_info
    OWNER to postgres;



-- Table: public.other_words

-- DROP TABLE IF EXISTS public.other_words;

CREATE TABLE IF NOT EXISTS public.other_words
(
    id integer NOT NULL DEFAULT nextval('other_words_id_seq'::regclass),
    word character varying(255) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT other_words_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.other_words
    OWNER to postgres;


-- Пример таблицы для каждого пользователя (замените user_id на фактическое значение)

-- Table: public.user_words164236627

-- DROP TABLE IF EXISTS public.user_words164236627;

CREATE TABLE IF NOT EXISTS public.user_words164236627
(
    id integer NOT NULL DEFAULT nextval('user_words164236627_id_seq'::regclass),
    user_id bigint NOT NULL,
    target_word character varying(255) COLLATE pg_catalog."default" NOT NULL,
    translate_word character varying(255) COLLATE pg_catalog."default" NOT NULL,
    other_words text[] COLLATE pg_catalog."default",
    CONSTRAINT user_words_164236627_pkey PRIMARY KEY (id),
    CONSTRAINT user_words_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.user_info (user_id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.user_words164236627
    OWNER to postgres;

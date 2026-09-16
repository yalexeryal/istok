-- Делаем istok_user полным владельцем схемы public
ALTER SCHEMA public OWNER TO istok_user;

-- Выдаем все права на схему
GRANT ALL ON SCHEMA public TO istok_user;

-- Выдаем права на все существующие и будущие таблицы и последовательности
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO istok_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO istok_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO istok_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO istok_user;
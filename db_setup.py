import sqlite3

# Подключение к базе данных
conn = sqlite3.connect("store_snap.db")
cursor = conn.cursor()

# Удаление старой таблицы, если она существует (опционально)
cursor.execute("DROP TABLE IF EXISTS users")

# Создание новой таблицы users
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    appstore_url TEXT,
    rustore_url TEXT,
    googleplay_url TEXT,
    appgallery_url TEXT,
    interval INTEGER DEFAULT 10,
    last_monitoring TEXT,
    next_monitoring TEXT
)
""")

conn.commit()
conn.close()
print("Таблица успешно создана!")
import time
import sqlite3
import json
import argparse
from datetime import datetime, timedelta, timezone
from stores.rustore import get_version_rustore
from stores.appstore import get_version_appstore
from stores.googleplay import get_version_googleplay
from stores.appgallery import get_version_appgallery
from telegram_utils import send_telegram_notification


def get_db_connection():
    """
    Подключение к базе данных SQLite.
    """
    return sqlite3.connect("store_snap.db")


def get_user_data(user_id=None):
    """
    Получает данные пользователей из базы данных.
    Если указан user_id, возвращает данные только для этого пользователя.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute(
            "SELECT user_id, appstore_url, rustore_url, googleplay_url, appgallery_url, interval, last_monitoring, next_monitoring "
            "FROM users WHERE user_id = ?", (user_id,)
        )
    else:
        cursor.execute(
            "SELECT user_id, appstore_url, rustore_url, googleplay_url, appgallery_url, interval, last_monitoring, next_monitoring "
            "FROM users"
        )

    users = cursor.fetchall()
    conn.close()
    return users


def get_current_time(offset_hours=0):
    """
    Возвращает текущее время с учетом смещения в часах (по умолчанию +3 часа).
    """
    return (datetime.now(timezone.utc) + timedelta(hours=offset_hours)).strftime("%Y-%m-%d %H:%M:%S")


def process_user_monitoring(user_id, config):
    """
    Обрабатывает мониторинг приложений для конкретного пользователя.
    """
    user = get_user_data(user_id=user_id)[0]  # Получаем данные конкретного пользователя

    user_id, appstore_url, rustore_url, googleplay_url, appgallery_url, interval, last_monitoring, next_monitoring = user

    # Пропускаем, если ни один стор не указан
    if not any([appstore_url, rustore_url, googleplay_url, appgallery_url]):
        send_telegram_notification(
            config["telegram_bot_token"],
            user_id,
            "Вы не указали ни одно приложение для мониторинга :("
        )
        return

    # Сопоставляем магазины и функции для получения версий
    stores = {
        "AppStore": (appstore_url, get_version_appstore),
        "RuStore": (rustore_url, get_version_rustore),
        "GooglePlay": (googleplay_url, get_version_googleplay),
        "AppGallery": (appgallery_url, get_version_appgallery),
    }

    # Храним текущие версии для пользователя
    current_versions = {}

    while True:
        # Получаем текущее время для логирования
        execution_time_str = get_current_time(offset_hours=3)

        # Проверяем, наступило ли время следующего мониторинга
        if next_monitoring and execution_time_str < next_monitoring:
            time.sleep(10)  # Ждем, если время не наступило
            continue

        # Выполняем мониторинг для каждого магазина
        for store_name, (store_url, get_version_func) in stores.items():
            if not store_url:
                continue

            try:
                # Получение данных о версиях и обновлениях
                if store_name == "AppGallery":
                    new_version, last_updated, changelog = get_version_func(store_url)
                else:
                    new_version, changelog, last_updated = get_version_func(store_url)

                # Проверяем, обновилась ли версия
                # Проверяем, обновилась ли версия
                if store_name not in current_versions:
                    # Первая проверка — новая версия
                    current_versions[store_name] = new_version
                    send_telegram_notification(
                        config["telegram_bot_token"],
                        user_id,
                        f"🎉 Новая версия в {store_name}!\n"
                        f"Версия: {new_version}\n"
                        f"Дата обновления: {last_updated}\n"
                        f"Изменения:\n{changelog}"
                    )
                    print(
                        f"Выполнен мониторинг для пользователя {user_id} в {get_current_time(offset_hours=3)}. "
                        f"Первая проверка — версия найдена, сообщение отправлено."
                    )
                else:
                    # Всегда выводим лог — обновилась ли версия или нет
                    if current_versions[store_name] != new_version:
                        # Найдена новая версия
                        current_versions[store_name] = new_version
                        send_telegram_notification(
                            config["telegram_bot_token"],
                            user_id,
                            f"🎉 Новая версия в {store_name}!\n"
                            f"Версия: {new_version}\n"
                            f"Дата обновления: {last_updated}\n"
                            f"Изменения:\n{changelog}"
                        )
                        print(
                            f"Выполнен мониторинг для пользователя {user_id} в {get_current_time(offset_hours=3)}. "
                            f"Найдена новая версия, сообщение отправлено."
                        )
                    else:
                        # Версия не изменилась
                        print(
                            f"Выполнен мониторинг для пользователя {user_id} в {get_current_time(offset_hours=3)}. "
                            f"Новая версия не найдена, сообщение не отправлено."
                        )

            except Exception as e:
                print(f"Ошибка при обработке {store_name} для пользователя {user_id}: {e}")

        # Обновляем last_monitoring и next_monitoring в UTC
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE users 
            SET last_monitoring = ?, 
                next_monitoring = datetime('now', '+{interval} minutes', '+3 hours')
            WHERE user_id = ?
            """,
            (execution_time_str, user_id)
        )
        conn.commit()
        conn.close()

        time.sleep(interval * 60)  # Ждем интервал перед следующим циклом


if __name__ == "__main__":
    with open("config.json", "r") as file:
        config = json.load(file)  # Загружаем токен бота из конфигурации

    try:
        # Получаем user_id из аргументов
        parser = argparse.ArgumentParser()
        parser.add_argument("--user_id", type=int, required=True, help="ID пользователя для мониторинга")
        args = parser.parse_args()

        # Выполняем мониторинг для конкретного пользователя
        process_user_monitoring(args.user_id, config)

    except KeyboardInterrupt:
        print("\nСкрипт остановлен пользователем.")
import subprocess
import sys
import os
import threading
import json
import time
import sqlite3
from telebot import TeleBot, types
from datetime import datetime, timezone
from stores.rustore import get_version_rustore
from stores.appstore import get_version_appstore
from stores.googleplay import get_version_googleplay
from stores.appgallery import get_version_appgallery

# Загрузка конфигурации
with open("config.json", "r") as file:
    config = json.load(file)

# Токен вашего Telegram-бота
bot = TeleBot(config["telegram_bot_token"])

# Путь к основному боту
BOT_SCRIPT = "bot.py"

# Переменные для хранения состояния
bot_process = None
lock = threading.Lock()

# Словари для хранения процессов
user_sessions = {}
check_sessions = {}


def get_db_connection():
    """
    Подключение к базе данных SQLite.
    """
    return sqlite3.connect("store_snap.db")


def main_menu_keyboard():
    """
    Главное меню с кнопками Reply Keyboard.
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        types.KeyboardButton("Запустить мониторинг"),
        types.KeyboardButton("Разовая проверка")
    )
    keyboard.row(
        types.KeyboardButton("Отзывы"),
        types.KeyboardButton("Руководство")
    )
    keyboard.row(
        types.KeyboardButton("Настройки"),
        types.KeyboardButton("О проекте")
    )
    return keyboard


def stop_monitoring_keyboard():
    """
    Клавиатура с одной кнопкой "Остановить мониторинг".
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(types.KeyboardButton("Остановить мониторинг"))
    return keyboard


def stop_check_keyboard():
    """
    Клавиатура с одной кнопкой "Остановить проверку".
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(types.KeyboardButton("Остановить проверку"))
    return keyboard


def back_keyboard():
    """
    Клавиатура с одной кнопкой "⏪ Назад".
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(types.KeyboardButton("⏪ Назад"))
    return keyboard


def back_to_main_menu_keyboard():
    """
    Клавиатура с одной кнопкой "↩️ Назад в меню".
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(types.KeyboardButton("↩️ Назад в меню"))
    return keyboard


def only_back_keyboard():
    """
    Клавиатура с одной кнопкой "⏪ Назад".
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(types.KeyboardButton("⏪ Назад"))
    return keyboard


def cancel_keyboard():
    """
    Клавиатура с одной кнопкой "Отмена".
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(types.KeyboardButton("Отмена"))
    return keyboard


def settings_menu_keyboard():
    """
    Клавиатура для настроек с кнопками "Магазины", "Частота обновлений" и "↩️ Назад в меню".
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(types.KeyboardButton("Магазины"), types.KeyboardButton("Частота обновлений"))
    keyboard.add(types.KeyboardButton("↩️ Назад в меню"))  # Обновлено
    return keyboard


def has_stores(user_id):
    """
    Проверяет, указал ли пользователь хотя бы один стор.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT appstore_url, rustore_url, googleplay_url, appgallery_url FROM users WHERE user_id = ?",
        (user_id,)
    )
    user_stores = cursor.fetchone()
    conn.close()

    return user_stores and any(store is not None and store.strip() != "" for store in user_stores)


def app_selection_keyboard():
    """
    Клавиатура с кнопками для выбора сторов и кнопкой "⏪ Назад".
    """
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        types.KeyboardButton("App Store"),
        types.KeyboardButton("RuStore")
    )
    keyboard.row(
        types.KeyboardButton("Google Play"),
        types.KeyboardButton("AppGallery")
    )
    keyboard.add(types.KeyboardButton("⏪ Назад"))  # Кнопка "⏪ Назад"
    return keyboard


@bot.message_handler(commands=['start'])
def start_command(message):
    """
    Команда /start: приветствие с созданием записи в БД.
    """
    user_id = message.chat.id
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, есть ли строка для пользователя
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        # Если строки нет, создаем новую с `full_name`
        cursor.execute(
            """
            INSERT INTO users (user_id, appstore_url, rustore_url, googleplay_url, appgallery_url, interval, full_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, None, None, None, None, 10, full_name)  # Дефолтный интервал — 10 минут
        )
        conn.commit()
        bot.send_message(user_id, "Вы успешно зарегистрированы в боте!🎉")

    else:
        # Обновляем `full_name` на случай изменения имени пользователя
        cursor.execute(
            "UPDATE users SET full_name = ? WHERE user_id = ?",
            (full_name, user_id)
        )
        conn.commit()

    # Приветственное сообщение
    bot.send_message(
        user_id,
        f"Добро пожаловать в Store Snap! ❤️",
        reply_markup=main_menu_keyboard()
    )

    # Закрытие соединения
    conn.close()


def utc_to_local(utc_dt):
    """
    Преобразует время UTC в локальный часовой пояс.
    """
    local_tz = datetime.now().astimezone().tzinfo
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(local_tz)

def get_current_utc_time():
    """
    Возвращает текущее время в UTC.
    """
    return datetime.now(timezone.utc)


@bot.message_handler(commands=['check'])
def check_command(message):
    """
    Обработка команды /check.
    Если у пользователя не указано ни одно приложение, отправляется предупреждение.
    """
    user_id = message.chat.id

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, указаны ли приложения для пользователя
    cursor.execute(
        "SELECT appstore_url, rustore_url, googleplay_url, appgallery_url FROM users WHERE user_id = ?",
        (user_id,)
    )
    user_stores = cursor.fetchone()
    conn.close()

    # Проверяем, есть ли хотя бы одно указанное приложение
    if not user_stores or all(store is None or store.strip() == "" for store in user_stores):
        bot.send_message(
            user_id,
            "Вы не указали ни одно приложение для проверки :("
        )
        return

    # Если хотя бы одно приложение указано
    bot.send_message(user_id, "Начинаю проверку сторов...⏳")
    try:
        results = perform_single_check(user_id)
        if not results or not results.strip():  # Если результат None или пустой
            bot.send_message(user_id, "Не удалось получить данные о сторах.")
        else:
            bot.send_message(user_id, results)
    except Exception as e:
        bot.send_message(user_id, f"Ошибка при выполнении проверки: {str(e)}")


@bot.message_handler(func=lambda message: message.text == "Запустить мониторинг")
def start_monitoring_handler(message):
    """
    Обработчик кнопки "Запустить мониторинг".
    Проверяет, указаны ли сторы перед началом мониторинга и запускает мониторинг только для текущего пользователя.
    """
    user_id = message.chat.id

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем ссылки на приложения из БД для текущего пользователя
    cursor.execute(
        "SELECT appstore_url, rustore_url, googleplay_url, appgallery_url, interval FROM users WHERE user_id = ?",
        (user_id,)
    )
    user_stores = cursor.fetchone()
    conn.close()

    # Проверяем, есть ли хотя бы один указанный стор
    if not user_stores or all(store is None or store.strip() == "" for store in user_stores[:4]):
        bot.send_message(
            user_id,
            "Вы не указали ни одно приложение для мониторинга :("
        )
        return

    # Если хотя бы одно приложение указано, запускаем мониторинг
    with lock:
        if user_id in user_sessions and user_sessions[user_id].poll() is None:
            bot.send_message(user_id, "Мониторинг уже запущен!", reply_markup=stop_monitoring_keyboard())
            return

        # Формируем аргументы для subprocess с конкретным пользователем
        args = ["python3", BOT_SCRIPT, f"--user_id={user_id}"]
        try:
            process = subprocess.Popen(args)
            user_sessions[user_id] = process

            # Логируем запуск мониторинга
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"Пользователь {user_id} запустил мониторинг в {current_time}")

            bot.send_message(user_id, "Мониторинг успешно запущен! 🚀", reply_markup=stop_monitoring_keyboard())
        except Exception as e:
            bot.send_message(user_id, f"Ошибка при запуске мониторинга: {str(e)}")


@bot.message_handler(func=lambda message: message.text == "Остановить мониторинг")
def stop_monitoring_handler(message):
    """
    Обработчик кнопки "Остановить мониторинг".
    """
    global bot_process
    with lock:
        user_id = message.chat.id
        if user_id in user_sessions and user_sessions[user_id].poll() is None:
            # Завершаем процесс мониторинга
            user_sessions[user_id].terminate()
            del user_sessions[user_id]

            # Обнуляем next_monitoring в базе данных
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET next_monitoring = NULL WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            conn.close()

            # Логируем остановку мониторинга
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"Пользователь {user_id} остановил мониторинг в {current_time}")

            bot.send_message(user_id, "Мониторинг остановлен! 🛑", reply_markup=main_menu_keyboard())
        else:
            bot.send_message(user_id, "Мониторинг не запущен", reply_markup=main_menu_keyboard())


@bot.message_handler(func=lambda message: message.text == "Настройки")
def bot_settings_handler(message):
    """
    Обработчик кнопки "Настройки".
    Переход в раздел настроек.
    """
    bot.send_message(
        message.chat.id,
        "Выберите, что хотите настроить ⚙️",
        reply_markup=settings_menu_keyboard()  # Клавиатура для настроек
    )


@bot.message_handler(func=lambda message: message.text == "Магазины")
def set_app_button_handler(message):
    """
    Обработчик кнопки "Магазины".
    Переходит к выбору стора.
    """
    bot.send_message(
        message.chat.id,
        "Добавьте или измените магазины приложений 🛍️",
        reply_markup=app_selection_keyboard()  # Клавиатура с кнопкой "⏪ Назад"
    )


@bot.message_handler(func=lambda message: message.text in ["App Store", "RuStore", "Google Play", "AppGallery", "Отмена"])
def store_selection_handler(message):
    """
    Обработчик выбора конкретного стора или выхода из меню.
    """
    if message.text == "Отмена":
        bot.send_message(
            message.chat.id,
            "Добавьте или измените магазины приложений 🛍️",
            reply_markup=app_selection_keyboard()  # Клавиатура с кнопками магазинов
        )
        # Убираем временные данные из user_sessions, если есть
        if message.chat.id in user_sessions:
            del user_sessions[message.chat.id]
        return

    store_mapping = {
        "App Store": "appstore",
        "RuStore": "rustore",
        "Google Play": "googleplay",
        "AppGallery": "appgallery"
    }
    selected_store = store_mapping[message.text]

    user_sessions[message.chat.id] = {"store": selected_store}

    bot.send_message(
        message.chat.id,
        f"Введите ссылку для {message.text}",
        reply_markup=cancel_keyboard()
    )


@bot.message_handler(func=lambda message: message.chat.id in user_sessions and "store" in user_sessions[message.chat.id])
def set_app_link_handler(message):
    """
    Обработчик ввода ссылки для выбранного стора.
    """
    # Если пользователь нажимает "⏪ Назад", возвращаем его в меню настроек
    if message.text == "⏪ Назад":
        bot.send_message(
            message.chat.id,
            "Выберите, что хотите настроить ⚙️",
            reply_markup=settings_menu_keyboard()
        )
        # Убираем выбор из сессии
        del user_sessions[message.chat.id]
        return

    user_data = user_sessions[message.chat.id]
    selected_store = user_data["store"]
    store_mapping = {
        "appstore": "App Store",
        "rustore": "RuStore",
        "googleplay": "Google Play",
        "appgallery": "AppGallery"
    }

    # Проверяем валидность ссылки (примитивная проверка на наличие протокола)
    if not message.text.startswith("http"):
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите корректную ссылку, начинающуюся с 'http'"
        )
        return

    # Сохраняем ссылку в базе данных
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE users SET {selected_store}_url = ? WHERE user_id = ?",
            (message.text, message.chat.id)
        )
        conn.commit()
        conn.close()

        bot.send_message(
            message.chat.id,
            f"Ссылка для {store_mapping[selected_store]} успешно сохранена! 🎉",
            reply_markup=settings_menu_keyboard()
        )

        # Убираем выбор из сессии
        del user_sessions[message.chat.id]

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Ошибка при сохранении ссылки: {e}"
        )


@bot.message_handler(func=lambda message: message.text == "Частота обновлений")
def set_interval_button_handler(message):
    """
    Обработчик кнопки "Частота обновлений".
    """
    bot.send_message(
        message.chat.id,
        "Укажите интервал обновления в минутах (по умолчанию 10) ⏱️",
        reply_markup=only_back_keyboard()
    )
    user_sessions[message.chat.id] = {"awaiting_interval": True}


@bot.message_handler(func=lambda message: message.chat.id in user_sessions and user_sessions[message.chat.id].get("awaiting_interval"))
def set_interval_handler(message):
    """
    Обработчик ввода интервала обновления.
    """
    if message.text == "⏪ Назад":
        bot.send_message(
            message.chat.id,
            "Выберите, что хотите настроить ⚙️",
            reply_markup=settings_menu_keyboard()
        )
        del user_sessions[message.chat.id]
        return

    if not message.text.isdigit():
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите целое число от 1 до 1440"
        )
        return

    interval = int(message.text)
    if interval < 1 or interval > 1440:
        bot.send_message(
            message.chat.id,
            "Интервал должен быть в диапазоне от 1 до 1440 минут"
        )
        return

    # Сохраняем интервал в базе данных
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET interval = ? WHERE user_id = ?",
        (interval, message.chat.id)
    )
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        f"Интервал обновления успешно установлен: {interval} минут",
        reply_markup=settings_menu_keyboard()
    )
    del user_sessions[message.chat.id]


@bot.message_handler(func=lambda message: message.text == "О проекте")
def about_project_handler(message):
    """
    Обработчик кнопки "О проекте".
    """
    bot.send_message(
        message.chat.id,
        "Store Snap — это бот для мониторинга обновлений приложений в RuStore, App Store, Google Play и AppGallery 🚀\n\n"
        "Обратная связь: @vanyabooo",
        reply_markup=back_to_main_menu_keyboard()  # Клавиатура с кнопкой "↩️ Назад в меню"
    )


@bot.message_handler(func=lambda message: message.text == "Отзывы")
def reviews_handler(message):
    """
    Обработчик кнопки "Отзывы".
    Выводит сообщение о том, что раздел в разработке, и добавляет кнопку для возврата в главное меню.
    """
    bot.send_message(
        message.chat.id,
        "Еще в разработке, не все так быстро, бро 🛠️",
        reply_markup=back_to_main_menu_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "↩️ Назад в меню")
def back_to_main_menu_handler(message):
    """
    Обработчик кнопки "↩️ Назад в меню".
    Возвращает пользователя в главное меню из любого подменю.
    """
    bot.send_message(
        message.chat.id,
        "Возвращаемся в главное меню",
        reply_markup=main_menu_keyboard()  # Возвращает клавиатуру главного меню
    )


@bot.message_handler(func=lambda message: message.text == "Руководство")
def show_guide_handler(message):
    """
    Обработчик кнопки "Руководство".
    Выводит инструкцию по работе с ботом и кнопку для возврата в главное меню.
    """
    bot.send_message(
        message.chat.id,
        guide_text,
        reply_markup=back_to_main_menu_keyboard(),  # Клавиатура с кнопкой "↩️ Назад в меню"
        parse_mode="HTML"  # Форматирование текста с помощью HTML
    )


@bot.message_handler(func=lambda message: message.text == "⏪ Назад")
def back_to_settings_handler(message):
    """
    Обработчик кнопки "⏪ Назад" из раздела выбора стора.
    Возвращает пользователя в раздел "Настройки".
    """
    bot.send_message(
        message.chat.id,
        "Выберите, что хотите настроить ⚙️",
        reply_markup=settings_menu_keyboard()  # Возвращение в "Настройки"
    )


@bot.message_handler(func=lambda message: message.text == "Разовая проверка")
def check_stores_handler(message):
    """
    Обработчик кнопки "Разовая проверка".
    Если у пользователя не указано ни одно приложение, отправляется предупреждение.
    """
    user_id = message.chat.id

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, указаны ли приложения для пользователя
    cursor.execute(
        "SELECT appstore_url, rustore_url, googleplay_url, appgallery_url FROM users WHERE user_id = ?",
        (user_id,)
    )
    user_stores = cursor.fetchone()
    conn.close()

    # Проверяем, есть ли хотя бы одно указанное приложение
    if not user_stores or all(store is None or store.strip() == "" for store in user_stores):
        bot.send_message(
            user_id,
            "Вы не указали ни одно приложение для проверки :("
        )
        return

    # Если хотя бы одно приложение указано
    bot.send_message(user_id, "Начинаю проверку сторов...⏳")
    try:
        results = perform_single_check(user_id)
        if not results or not results.strip():  # Если результат None или пустой
            bot.send_message(user_id, "Не удалось получить данные о сторах.")
        else:
            bot.send_message(user_id, results)
            # Добавляем сообщение после успешной проверки
            bot.send_message(user_id, "Проверка успешно завершена! ✅")
    except Exception as e:
        bot.send_message(user_id, f"Ошибка при выполнении проверки: {str(e)}")


@bot.message_handler(func=lambda message: message.text == "Остановить проверку")
def stop_check_handler(message):
    """
    Обработчик кнопки "Остановить проверку".
    """
    global check_sessions
    with lock:
        if message.chat.id in check_sessions:
            del check_sessions[message.chat.id]
            bot.send_message(message.chat.id, "Проверка остановлена!🛑", reply_markup=main_menu_keyboard())
        else:
            bot.send_message(message.chat.id, "Проверка уже завершена.", reply_markup=main_menu_keyboard())


@bot.message_handler(commands=['set_app'])
def set_app_command(message):
    """
    Устанавливает ссылку на приложение для указанного стора.
    Пример: /set_app appstore https://apps.apple.com/ru/app/example
    """
    args = message.text.split(maxsplit=2)  # Разделяем команду на части

    if len(args) != 3:  # Если недостаточно аргументов
        bot.send_message(
            message.chat.id,
            "Пожалуйста, укажите стор и ссылку на приложение. Пример:\n"
            "/set_app appstore https://apps.apple.com/ru/app/example"
        )
        return

    store_name, store_url = args[1], args[2]

    # Проверяем, что указано корректное имя стора
    valid_stores = ["appstore", "rustore", "googleplay", "appgallery"]
    if store_name not in valid_stores:
        bot.send_message(
            message.chat.id,
            f"Недопустимый стор: {store_name}. Пожалуйста, используйте одно из следующих значений:\n"
            f"{', '.join(valid_stores)}"
        )
        return

    # Сохраняем данные в базу
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем, существует ли пользователь
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (message.chat.id,))
        user = cursor.fetchone()

        if user:
            # Обновляем ссылку для указанного стора
            cursor.execute(
                f"UPDATE users SET {store_name}_url = ? WHERE user_id = ?",
                (store_url, message.chat.id)
            )
        else:
            # Если пользователя нет в БД, создаём запись с указанным стором
            cursor.execute(
                f"""
                INSERT INTO users (user_id, appstore_url, rustore_url, googleplay_url, appgallery_url, interval)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message.chat.id,
                    store_url if store_name == "appstore" else None,
                    store_url if store_name == "rustore" else None,
                    store_url if store_name == "googleplay" else None,
                    store_url if store_name == "appgallery" else None,
                    10  # Дефолтный интервал — 10 минут
                )
            )

        conn.commit()
        bot.send_message(
            message.chat.id,
            f"Стор {store_name} успешно обновлён! 🎉"
        )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Ошибка при сохранении данных: {e}"
        )
    finally:
        conn.close()


@bot.message_handler(commands=['set_interval'])
def set_interval_command(message):
    """
    Команда для установки интервала обновления.
    """
    user_id = message.chat.id
    args = message.text.split()

    # Проверка аргумента
    if len(args) != 2 or not args[1].isdigit():
        bot.send_message(user_id, "Пожалуйста, укажите интервал в минутах (например: /set_interval 10).")
        return

    interval = int(args[1])
    if interval < 1 or interval > 1440:
        bot.send_message(user_id, "Интервал должен быть от 1 до 1440 минут.")
        return

    # Обновление интервала в БД
    conn = sqlite3.connect("store_snap.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET interval = ? WHERE user_id = ?",
        (interval, user_id)
    )
    conn.commit()
    conn.close()

    bot.send_message(user_id, f"Интервал обновления успешно установлен: {interval} минут")


def perform_single_check(chat_id):
    """
    Логика однократной проверки всех сторов для конкретного пользователя.
    """
    try:
        # Логирование выполнения проверки
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Пользователь {chat_id} выполнил проверку сторов в {current_time}")

        # Подключение к базе данных
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем ссылки на приложения из БД для текущего пользователя
        cursor.execute(
            "SELECT appstore_url, rustore_url, googleplay_url, appgallery_url FROM users WHERE user_id = ?",
            (chat_id,)
        )
        user_stores = cursor.fetchone()
        conn.close()

        if not user_stores or all(store is None or store.strip() == "" for store in user_stores):
            return "Вы не указали ни одно приложение для проверки :("

        # Список доступных функций для проверки
        store_functions = {
            "appstore": get_version_appstore,
            "rustore": get_version_rustore,
            "googleplay": get_version_googleplay,
            "appgallery": get_version_appgallery
        }

        store_names = ["AppStore", "RuStore", "GooglePlay", "AppGallery"]

        results = []

        # Проверяем сторы только для текущего пользователя
        for store_name, store_url, store_function in zip(store_names, user_stores, store_functions.values()):
            if store_url and store_url.strip():  # Если стор указан
                try:
                    # Получаем данные о версии, дате обновления и changelog
                    data = store_function(store_url)
                    if store_name in ["AppStore", "RuStore", "GooglePlay"]:
                        version, changelog, last_updated = data
                    elif store_name == "AppGallery":
                        version, last_updated, changelog = data

                    results.append(
                        f"🎉 {store_name}\n"
                        f"Версия: {version}\n"
                        f"Дата обновления: {last_updated}\n"
                        f"Изменения:\n{changelog}"
                    )
                except Exception as e:
                    results.append(f"Ошибка при проверке {store_name}: {str(e)}")

        if not results:
            return "Нет данных о сторах."

        # Возвращаем результат проверки
        return "\n\n".join(results)

    except Exception as e:
        return f"Ошибка при выполнении проверки: {str(e)}"


guide_text = (
    "<b>📖 Инструкция по работе с ботом Store Snap</b>\n\n"
    "Добро пожаловать в Store Snap! Этот бот поможет вам удобно отслеживать обновления ваших приложений в популярных магазинах.\n\n"
    "<b>🚀 Основные функции:</b>\n"
    "1. <b>Запустить мониторинг</b>:\n"
    "   Бот начнет отслеживать обновления приложений, которые вы указали. Вы будете получать уведомления о новых версиях.\n\n"
    "2. <b>Разовая проверка</b>:\n"
    "   Узнайте актуальные версии ваших приложений прямо сейчас.\n\n"
    "3. <b>Отзывы (в разработке)</b>:\n"
    "   В будущем вы сможете получать новые отзывы о ваших приложениях.\n\n"
    "4. <b>Настройки</b>:\n"
    "   - Добавьте или измените ссылки на приложения.\n"
    "   - Укажите интервал обновления для мониторинга.\n\n"
    "5. <b>О проекте</b>:\n"
    "   Узнайте больше о возможностях и целях бота.\n\n"
    "6. <b>Руководство</b>:\n"
    "   Вы всегда можете вернуться к этой инструкции.\n\n"
    "---\n\n"
    "<b>⚙️ Как настроить бота:</b>\n"
    "1. <b>Добавьте ссылки на приложения</b>:\n"
    "   В разделе <b>Настройки → Магазины</b> выберите магазин (App Store, Google Play и др.) и введите ссылку на приложение.\n\n"
    "2. <b>Установите интервал обновления</b>:\n"
    "   В разделе <b>Настройки → Частота обновлений</b> выберите, как часто бот должен проверять обновления (например, каждые 10 минут).\n\n"
    "3. <b>Запустите мониторинг</b>:\n"
    "   Нажмите <b>Запустить мониторинг</b> — бот начнет проверять указанные вами приложения.\n\n"
    "4. <b>Остановите мониторинг</b>:\n"
    "   Если мониторинг больше не нужен, нажмите <b>Остановить мониторинг</b>.\n\n"
    "---\n\n"
    "<b>💬 Часто задаваемые вопросы:</b>\n"
    "- <b>Как узнать, есть ли обновления?</b>\n"
    "  Вы получите уведомление от бота, если выйдет новая версия приложения.\n\n"
    "- <b>Могу ли я изменить ссылки на приложения?</b>\n"
    "  Да, это можно сделать в разделе <b>Настройки → Магазины</b>.\n\n"
    "- <b>Как изменить интервал проверки?</b>\n"
    "  Перейдите в <b>Настройки → Частота обновлений</b> и укажите новый интервал.\n\n"
    "---\n\n"
    "Теперь вы готовы использовать Store Snap! 🎉\n"
    "Если у вас есть вопросы или предложения, свяжитесь с разработчиком 😊"
)

#Polling + restart
def restart_bot():
    print("Перезапуск бота...")
    os.execv(sys.executable, ['python'] + sys.argv)

while True:
    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=30)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(5)
        restart_bot()
import sqlite3
import requests


def send_telegram_notification(bot_token, chat_id, message):
    """
    Отправляет уведомление пользователю через Telegram.
    """
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Проверяем статус ответа
    except requests.exceptions.HTTPError as e:
        if response.status_code == 403 and "Forbidden: the group chat was deleted" in response.text:
            print(f"Ошибка отправки: {e}, пользователь {chat_id} недоступен.")
            remove_invalid_user(chat_id)
        else:
            print(f"Ошибка отправки: {e}")

def remove_invalid_user(chat_id):
    """
    Удаляет пользователя с недействительным chat_id из базы данных.
    """
    conn = sqlite3.connect("store_snap.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (chat_id,))
    conn.commit()
    conn.close()
    print(f"Пользователь {chat_id} удален из базы данных.")
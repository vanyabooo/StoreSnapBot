import requests
from datetime import datetime
from urllib.parse import urlparse, parse_qs


def extract_app_id_from_url(url):
    """
    Извлекает app_id из URL App Store.
    Пример URL: https://apps.apple.com/ru/app/some-app-name/id6443942006
    Возвращает: 6443942006
    """
    try:
        parsed_url = urlparse(url)
        if "id" in parsed_url.path:
            return parsed_url.path.split("id")[-1].split("?")[0]
        else:
            raise ValueError("Некорректный URL App Store.")
    except Exception as e:
        raise ValueError(f"Ошибка извлечения app_id из URL: {e}")


def get_version_appstore(url, country="ru"):
    """
    Получает последнюю версию, changelog и дату обновления приложения в App Store.

    :param url: URL или app_id приложения в App Store.
    :param country: Код страны для локализации данных (по умолчанию 'ru').
    :return: Версия, описание изменений (changelog), дата обновления.
    """
    try:
        # Если передан полный URL, извлекаем app_id
        if url.startswith("http"):
            app_id = extract_app_id_from_url(url)
        else:
            app_id = url  # Если передан только app_id

        # Формируем URL для API
        api_url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"

        # Отправляем запрос к API
        response = requests.get(api_url, timeout=10)  # Указываем таймаут для надёжности
        response.raise_for_status()
        data = response.json()

        # Проверяем наличие данных
        results = data.get("results", [])
        if not results:
            raise ValueError("Данные о приложении не найдены.")

        # Извлекаем нужные данные
        app_data = results[0]
        version = app_data.get("version", "Версия не найдена.")
        changelog = app_data.get("releaseNotes", "Нет описания изменений.")

        # Обрабатываем дату обновления
        last_updated_raw = app_data.get("currentVersionReleaseDate")
        if last_updated_raw:
            try:
                # Преобразуем дату из ISO 8601 в формат ДД.ММ.ГГГГ
                last_updated = datetime.fromisoformat(last_updated_raw.replace("Z", "")).strftime("%d.%m.%Y")
            except ValueError:
                last_updated = "Дата обновления не распознана."
        else:
            last_updated = "Дата обновления не найдена."

        return version, changelog, last_updated

    except requests.RequestException as req_err:
        raise RuntimeError(f"Ошибка сети при обращении к App Store: {req_err}")
    except ValueError as val_err:
        raise RuntimeError(f"Ошибка обработки данных App Store: {val_err}")
    except Exception as e:
        raise RuntimeError(f"Непредвиденная ошибка: {e}")
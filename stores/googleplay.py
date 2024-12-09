from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
import locale
import re
import time


def add_language_parameter(url, lang="ru"):
    url_parts = urlparse(url)
    query = parse_qs(url_parts.query)
    query['hl'] = lang
    updated_query = urlencode(query, doseq=True)
    return urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path, url_parts.params, updated_query, url_parts.fragment))


def format_date_googleplay(raw_date):
    try:
        locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
        raw_date = raw_date.replace("\u202f", " ").strip()
        raw_date = re.sub(r"[^\w\s.]", "", raw_date)

        months = {
            "янв.": "января",
            "февр.": "февраля",
            "мар.": "марта",
            "апр.": "апреля",
            "мая": "мая",
            "июн.": "июня",
            "июл.": "июля",
            "авг.": "августа",
            "сент.": "сентября",
            "окт.": "октября",
            "нояб.": "ноября",
            "дек.": "декабря"
        }
        for short_month, full_month in months.items():
            raw_date = raw_date.replace(short_month, full_month)

        raw_date = raw_date.replace(" г.", "").strip()
        date_obj = datetime.strptime(raw_date, "%d %B %Y")
        return date_obj.strftime("%d.%m.%Y")
    except Exception:
        return "Дата обновления не найдена"


def get_version_googleplay(base_url):
    driver = None
    try:
        # Настройка Chrome WebDriver с headless-режимом
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)

        localized_url = add_language_parameter(base_url)
        driver.get(localized_url)
        wait = WebDriverWait(driver, 10)

        # Извлечение ченджлога
        whats_new_block = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@itemprop, 'description')]")))
        whats_new = whats_new_block.text.strip() if whats_new_block else "Изменения не найдены"

        # Извлечение даты обновления
        last_updated_block = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'xg1aie')]")))
        raw_last_updated = last_updated_block.text.strip() if last_updated_block else "Дата обновления не найдена"
        last_updated = format_date_googleplay(raw_last_updated)

        # Клик по кнопке описания
        try:
            description_button = wait.until(EC.presence_of_element_located(
                (By.XPATH, ".//button[contains(@class, 'VfPpkd-Bz112c-LgbsSe yHy1rc eT1oJ QDwDD mN1ivc VxpoF')]")))
            driver.execute_script("arguments[0].scrollIntoView(true);", description_button)
            driver.execute_script("arguments[0].click();", description_button)
        except Exception:
            pass

        time.sleep(2)

        # Извлечение версии
        try:
            version_block = wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Версия')]/following-sibling::div")))
            version = version_block.text.strip() if version_block and version_block.text else "Версия не найдена"
        except Exception:
            version = "Версия не найдена"

        driver.quit()
        return version, whats_new, last_updated
    except Exception as e:
        if driver:
            driver.quit()
        raise RuntimeError(f"Ошибка при парсинге Google Play: {e}")
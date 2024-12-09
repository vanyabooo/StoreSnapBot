from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_version_rustore(base_url):
    """
    Получает последнюю версию приложения, changelog и дату обновления из RuStore с использованием Selenium в headless режиме.
    """
    driver = None
    try:
        # Добавляем путь `/versions` к URL
        versions_url = f"{base_url}/versions"

        # Настраиваем headless режим
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Инициализация Selenium WebDriver
        driver = webdriver.Chrome(options=options)
        driver.get(versions_url)

        # Используем WebDriverWait вместо time.sleep
        wait = WebDriverWait(driver, 10)

        # Ждём загрузки первого блока с версией
        latest_version_block = wait.until(EC.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'zzIZRzwc')]/li[1]")))

        # Извлекаем версию
        try:
            version_element = latest_version_block.find_element(By.XPATH, ".//p[contains(@class, 'c0TuZspB')]")
            version = version_element.text.strip()
            # Убираем лишний текст, если начинается с "Версия:"
            if version.lower().startswith("версия:"):
                version = version.split(":", 1)[-1].strip()
        except Exception:
            version = "Версия не найдена"

        # Извлекаем changelog
        try:
            changelog_elements = latest_version_block.find_elements(By.XPATH, ".//p[contains(@class, 'fHq7weSI')]")
            changelog = "\n".join([elem.text.strip() for elem in changelog_elements]) if changelog_elements else "Changelog не найден"
        except Exception:
            changelog = "Changelog не найден"

        # Извлекаем дату обновления
        try:
            last_updated_raw = latest_version_block.find_element(By.XPATH, ".//p[contains(@class, 'e_S0KJFo')]")
            last_updated = last_updated_raw.text.strip().replace("Дата: ", "").strip() if last_updated_raw else "Дата обновления не найдена"
        except Exception:
            last_updated = "Дата обновления не найдена"

        driver.quit()
        return version, changelog, last_updated
    except Exception as e:
        if driver:
            driver.quit()
        raise RuntimeError(f"Ошибка при парсинге RuStore: {e}")
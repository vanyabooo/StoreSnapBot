from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def get_version_appgallery(url):
    """
    Получение версии приложения, даты обновления и changelog из AppGallery.
    """
    try:
        # Настройки Chrome для headless режима
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Запуск в headless режиме
        chrome_options.add_argument("--disable-gpu")  # Отключение GPU (ускоряет headless режим)
        chrome_options.add_argument("--no-sandbox")  # Защита от сбоев в средах без интерфейса
        chrome_options.add_argument("--disable-dev-shm-usage")  # Улучшение для ограниченных ресурсов

        # Инициализация драйвера
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        driver.get(url)

        # Установка времени ожидания
        wait = WebDriverWait(driver, 10)

        def get_text(xpath):
            """
            Вспомогательная функция для извлечения текста по XPath с ожиданием.
            """
            try:
                return wait.until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                ).text.strip()
            except TimeoutException:
                return None

        # Определяем XPaths
        xpaths = {
            "version": '//div[@class="appSingleInfo" and .//div[text()="Версия"]]/div[@class="info_val"]',
            "updated": '//div[@class="appSingleInfo" and .//div[text()="Обновлено"]]/div[@class="info_val"]',
            "changelog": '//div[@class="detailprizecard"]//div[@class="openAndHide"]/div[@class="left"]',
        }

        # Получаем данные
        version_element = get_text(xpaths["version"])
        updated_element = get_text(xpaths["updated"])
        changelog_element = get_text(xpaths["changelog"])

        return version_element, updated_element, changelog_element

    except Exception as e:
        raise RuntimeError(f"Ошибка Selenium: {str(e)}")
    finally:
        driver.quit()
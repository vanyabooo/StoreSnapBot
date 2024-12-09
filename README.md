# **StoreSnap Bot**

**StoreSnap Bot** — это телеграм-бот для мониторинга обновлений мобильных приложений в популярных магазинах: Google Play, App Store, RuStore и Huawei AppGallery. Бот автоматически проверяет версии приложений, уведомляет пользователей о новых обновлениях, дате выхода и изменениях в приложении.

---

## **📦 Основные возможности**

- **Мониторинг магазинов приложений**:
  - Google Play Store
  - App Store (iOS)
  - Huawei AppGallery
  - RuStore
- **Уведомления о новых версиях** — бот отправляет актуальную информацию о версиях приложений.
- **Информация об изменениях** — бот предоставляет детальные ченджлоги, если они доступны.
- **Поддержка нескольких пользователей** — каждый пользователь получает свои персонализированные уведомления.

---

## **🛠 Установка**

### **Требования:**
- **Python 3.13** или выше
- **Git** (по желанию)

### **Шаги установки:**

1. **Клонируйте репозиторий** (или загрузите его вручную):
   ```bash
   git clone https://github.com/ВашПользователь/StoreSnapBot.git
   cd StoreSnapBot
   ```

2. **Создайте виртуальное окружение** (рекомендуется):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # MacOS/Linux
   .\venv\Scripts\activate   # Windows
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте бота:**
   - Откройте файл `config.json` и укажите свой **Telegram Bot Token**.

---

## **🚀 Запуск**

1. **Создайте базу данных (если необходимо):**
   ```bash
   python db_setup.py
   ```

2. **Запустите бота:**
   ```bash
   python new.py
   ```

---

## **📂 Структура проекта**

```
StoreSnapBot/
├── bot.py               # Основная логика бота
├── new.py               # Точка входа
├── db_setup.py          # Настройка базы данных
├── telegram_utils.py    # Вспомогательные функции для Telegram
├── config.json          # Конфигурация бота (токен)
├── requirements.txt     # Список зависимостей
├── store_snap.db        # База данных SQLite
└── stores/              # Модули магазинов приложений
    ├── appgallery.py
    ├── googleplay.py
    ├── appstore.py
    └── rustore.py
```

---

## **📦 Зависимости**

- `python-telegram-bot`
- `requests`
- `beautifulsoup4`
- `selenium`
- `chromedriver-autoinstaller`
- `telebot`
- `webdriver-manager`

---

## **⚠️ Важные замечания**

- **Храните `config.json` в безопасности!** Никогда не публикуйте свой **Telegram Bot Token** в открытых репозиториях.
- **Добавьте `.gitignore`** — чтобы исключить файлы, содержащие конфиденциальную информацию, такие как `config.json` и `store_snap.db`.

---

## **📜 Лицензия**

Проект лицензирован в соответствии с **MIT License**.
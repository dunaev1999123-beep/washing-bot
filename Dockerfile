# ========== ОСНОВНОЙ ОБРАЗ ==========
# Используем официальный образ Python 3.11
FROM python:3.11-slim

# ========== МЕТАДАННЫЕ ==========
LABEL maintainer="Ваше Имя <ваш.email@example.com>"
LABEL description="Telegram Bot for automatic laundry booking"
LABEL version="1.0"

# ========== УСТАНОВКА СИСТЕМНЫХ ЗАВИСИМОСТЕЙ ==========
# Устанавливаем системные пакеты для Chrome и Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libxss1 \
    libxtst6 \
    --no-install-recommends

# ========== УСТАНОВКА GOOGLE CHROME ==========
# Добавляем репозиторий Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ========== УСТАНОВКА CHROMEDRIVER ==========
# Устанавливаем ChromeDriver (совместимую версию)
# Проверяем последнюю стабильную версию на: https://googlechromelabs.github.io/chrome-for-testing/
RUN CHROME_DRIVER_VERSION="128.0.6613.84" \
    && wget -q -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_DRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

# ========== НАСТРОЙКА РАБОЧЕЙ ДИРЕКТОРИИ ==========
# Создаем рабочую директорию в контейнере
WORKDIR /app

# ========== КОПИРОВАНИЕ ФАЙЛОВ ==========
# Сначала копируем requirements.txt для кэширования зависимостей
COPY requirements.txt .

# ========== УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ ==========
RUN pip install --no-cache-dir -r requirements.txt

# ========== КОПИРОВАНИЕ ОСТАЛЬНЫХ ФАЙЛОВ ==========
# Копируем весь остальной код
COPY . .

# ========== СОЗДАНИЕ ДИРЕКТОРИЙ ==========
# Создаем папку для скриншотов
RUN mkdir -p /app/screenshots

# ========== НАСТРОЙКА ПРАВ ДОСТУПА ==========
# Даем права на запись в папку скриншотов
RUN chmod -R 755 /app/screenshots

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
# Устанавливаем переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# ========== ПОРТ ДЛЯ HEALTHCHECK ==========
# Открываем порт для HTTP сервера (нужен для Amvera healthcheck)
EXPOSE 8080

# ========== КОМАНДА ЗАПУСКА ==========
# Команда запуска приложения
CMD ["python", "bot.py"]
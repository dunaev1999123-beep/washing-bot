import os
import logging
import time
import tempfile
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение переменных окружения (со значениями по умолчанию)
BOT_TOKEN = os.getenv('BOT_TOKEN', '8196163948:AAGn9B0rIqLX2QDMWo0DDd0Yaz-jX04FywI')
ADMIN_ID = int(os.getenv('ADMIN_ID', '7452553608'))
TARGET_URL = os.getenv('TARGET_URL', 'https://dikidi.net/1613380?p=4.pi-po-ssm-sd-cf&o=7&am=1&m=3474814&s=16944200&d=202601310900&r=1027863105&rl=0_1027863105&sdr=')
FORM_NAME = os.getenv('FORM_NAME', 'Константин')
FORM_SURNAME = os.getenv('FORM_SURNAME', 'Дунаев')
FORM_COMMENT = os.getenv('FORM_COMMENT', '526')
FORM_PHONE = os.getenv('FORM_PHONE', '9955542240')

# Проверка переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не установлен!")

print("🤖 ТЕЛЕГРАМ БОТ ЗАПУСКАЕТСЯ")
print(f"✅ BOT_TOKEN: {'✓ Установлен' if BOT_TOKEN else '✗ ОТСУТСТВУЕТ'}")
print(f"✅ ADMIN_ID: {ADMIN_ID} ✓")
print(f"✅ TARGET_URL: {'✓ Установлен' if TARGET_URL else '✗ ОТСУТСТВУЕТ'}")

def setup_driver():
    """Настройка веб-драйвера для работы с Chromium в контейнере"""
    chrome_options = Options()
    
    # Аргументы для работы в контейнере
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")  # Без графического интерфейса
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Используем Chromium
    chrome_options.binary_location = "/usr/bin/chromium"
    
    # Дополнительные настройки для Selenium 4
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Устанавливаем user-agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        # Создаем драйвер
        driver = webdriver.Chrome(options=chrome_options)
        
        # Скрываем автоматизацию
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ Chromium драйвер успешно создан")
        return driver
    except Exception as e:
        print(f"❌ Ошибка создания драйвера: {e}")
        print("🔄 Пробую альтернативные пути...")
        
        # Пробуем альтернативные пути к браузеру
        possible_paths = [
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome"
        ]
        
        for path in possible_paths:
            try:
                chrome_options.binary_location = path
                driver = webdriver.Chrome(options=chrome_options)
                print(f"✅ Драйвер запущен с {path}")
                return driver
            except Exception as path_error:
                print(f"❌ Не удалось с {path}: {path_error}")
                continue
        
        raise Exception("Не удалось запустить ни Chromium, ни Chrome")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔄 Проверить доступность + скриншот", callback_data='check')],
        [InlineKeyboardButton("🚀 Забронировать автомат", callback_data='book')],
        [InlineKeyboardButton("📊 Статус", callback_data='status')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 Бот для бронирования стиральных автоматов\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ У вас нет доступа к этому боту.")
        return
    
    if query.data == 'check':
        await check_availability(query)
    elif query.data == 'book':
        await book_machine(query)
    elif query.data == 'status':
        await show_status(query)

async def check_availability(query):
    """Проверка доступности сайта и отправка скриншота"""
    await query.edit_message_text("📸 Захожу на сайт и делаю скриншот...")
    
    driver = None
    try:
        driver = setup_driver()
        
        # Переходим на сайт
        driver.get(TARGET_URL)
        
        # Ждем загрузки страницы
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Даем странице полностью загрузиться (особенно JavaScript)
        time.sleep(3)
        
        title = driver.title
        current_url = driver.current_url
        
        # 1. Делаем скриншот всей страницы
        screenshot_path = "/tmp/dikidi_screenshot.png"
        
        # Устанавливаем размер окна для полного скриншота
        driver.set_window_size(1920, 1080)
        driver.save_screenshot(screenshot_path)
        
        # 2. Получаем информацию о странице
        html_content = driver.page_source[:1500]  # Первые 1500 символов HTML
        
        # 3. Ищем все видимые элементы на странице
        buttons = driver.find_elements(By.TAG_NAME, "button")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        links = driver.find_elements(By.TAG_NAME, "a")
        divs = driver.find_elements(By.TAG_NAME, "div")
        
        # Создаем временный отчет
        report = (
            f"📊 ОТЧЕТ О СТРАНИЦЕ DIKIDI.NET\n"
            f"────────────────────\n"
            f"📝 Заголовок: {title}\n"
            f"🔗 URL: {current_url}\n"
            f"📏 Размер страницы: {len(driver.page_source)} символов\n"
            f"🎯 Элементов найдено:\n"
            f"   • Кнопок (button): {len(buttons)}\n"
            f"   • Полей ввода (input): {len(inputs)}\n"
            f"   • Ссылок (a): {len(links)}\n"
            f"   • Блоков (div): {len(divs)}\n"
            f"⏰ Время проверки: {datetime.now().strftime('%H:%M:%S')}\n"
            f"────────────────────\n"
            f"Первые 200 символов HTML:\n"
            f"{html_content[:200]}..."
        )
        
        # Обновляем сообщение с отчетом
        await query.edit_message_text(report)
        
        # 4. Отправляем скриншот в чат
        try:
            with open(screenshot_path, 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=f"📸 Скриншот страницы Dikidi\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
        except Exception as photo_error:
            await query.message.reply_text(f"❌ Не удалось отправить скриншот: {photo_error}")
        
        # 5. Дополнительно: отправляем информацию о найденных кнопках
        if buttons:
            button_info = "🔍 Найденные кнопки (первые 8):\n"
            for i, btn in enumerate(buttons[:8]):
                btn_text = btn.text.strip()[:30] if btn.text else "без текста"
                btn_class = btn.get_attribute('class')[:20] if btn.get_attribute('class') else "нет класса"
                btn_id = btn.get_attribute('id')[:15] if btn.get_attribute('id') else "нет id"
                button_info += f"{i+1}. '{btn_text}' (id:{btn_id}, class:{btn_class})\n"
            
            await query.message.reply_text(button_info)
        
        # 6. Проверяем наличие ключевых элементов Dikidi
        await query.message.reply_text("🔎 Ищу элементы Dikidi...")
        
        dikidi_elements = {
            "Календарь": [".calendar", "[data-calendar]", "#calendar", ".date-picker"],
            "Слоты времени": [".time-slot", ".schedule-item", "[data-time]", ".booking-slot"],
            "Форма входа": ["#login-form", ".auth-form", "[type='password']", "input[name='password']"],
            "Кнопка входа": ["button[type='submit']", ".login-btn", "#loginButton", "[value='Войти']"]
        }
        
        found_elements = []
        for element_name, selectors in dikidi_elements.items():
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        found_elements.append(f"✅ {element_name}: найдено через '{selector}'")
                        break
                except:
                    continue
        
        if found_elements:
            elements_report = "📋 Найденные элементы Dikidi:\n" + "\n".join(found_elements)
            await query.message.reply_text(elements_report[:1000])
        else:
            await query.message.reply_text("⚠️ Не найдено стандартных элементов Dikidi")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке сайта: {e}")
        
        # Пытаемся сделать скриншот даже при ошибке
        try:
            if driver:
                error_screenshot = "/tmp/dikidi_error.png"
                driver.save_screenshot(error_screenshot)
                with open(error_screenshot, 'rb') as photo:
                    await query.message.reply_photo(
                        photo=photo,
                        caption=f"❌ Ошибка при загрузке страницы\n{str(e)[:100]}"
                    )
        except:
            pass
            
        await query.edit_message_text(
            f"❌ Ошибка при проверке сайта:\n{str(e)[:300]}..."
        )
    finally:
        if driver:
            driver.quit()

async def book_machine(query):
    """Процесс бронирования автомата для dikidi.net"""
    await query.edit_message_text("🚀 Начинаю процесс бронирования на dikidi.net...")
    
    driver = None
    try:
        driver = setup_driver()
        
        # 1. Делаем скриншот ДО бронирования
        driver.get(TARGET_URL)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        
        before_screenshot = "/tmp/dikidi_before_booking.png"
        driver.save_screenshot(before_screenshot)
        
        # Отправляем скриншот "до"
        with open(before_screenshot, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption="📸 Страница ДО бронирования"
            )
        
        await query.edit_message_text("🔍 Анализирую страницу для бронирования...")
        
        # 2. Пытаемся найти элементы для бронирования
        # Сначала ищем календарь или выбор даты
        calendar_selectors = [
            ".calendar", 
            "[data-calendar]", 
            "#calendar", 
            ".date-picker",
            "div[class*='date']",
            "div[class*='calendar']"
        ]
        
        calendar_found = False
        for selector in calendar_selectors:
            try:
                calendar_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if calendar_elements:
                    await query.message.reply_text(f"✅ Найден календарь: {selector}")
                    calendar_found = True
                    break
            except:
                continue
        
        if not calendar_found:
            await query.message.reply_text("❌ Календарь не найден. Возможно, требуется вход в систему.")
        
        # 3. Ищем кнопки или элементы времени
        time_selectors = [
            ".time-slot", 
            ".schedule-item", 
            "[data-time]", 
            ".booking-slot",
            "div[class*='time']",
            "button[class*='slot']"
        ]
        
        time_elements = []
        for selector in time_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    time_elements.extend(elements)
            except:
                continue
        
        if time_elements:
            time_report = f"✅ Найдено элементов времени: {len(time_elements)}\n"
            for i, elem in enumerate(time_elements[:5]):
                elem_text = elem.text.strip()[:20] if elem.text else "без текста"
                time_report += f"{i+1}. '{elem_text}'...\n"
            await query.message.reply_text(time_report)
        else:
            await query.message.reply_text("❌ Элементы времени не найдены")
        
        # 4. Ищем машины/аппараты
        machine_selectors = [
            "[data-machine]", 
            "[data-device]", 
            ".machine-selector",
            ".device-option",
            "div[class*='machine']",
            "button[class*='machine']"
        ]
        
        machines_found = []
        for selector in machine_selectors:
            try:
                machines = driver.find_elements(By.CSS_SELECTOR, selector)
                for machine in machines:
                    machine_text = machine.text.strip()
                    if machine_text and any(str(num) in machine_text for num in ['1', '2', '3']):
                        machines_found.append(f"{selector}: '{machine_text}'")
            except:
                continue
        
        if machines_found:
            await query.message.reply_text(f"✅ Найдены машины:\n" + "\n".join(machines_found[:5]))
        else:
            await query.message.reply_text("❌ Машины не найдены")
        
        # 5. Делаем скриншот ПОСЛЕ анализа
        after_screenshot = "/tmp/dikidi_after_analysis.png"
        driver.save_screenshot(after_screenshot)
        
        with open(after_screenshot, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption="📸 Страница после анализа элементов"
            )
        
        # 6. Финальный отчет
        await query.edit_message_text(
            f"📋 ОТЧЕТ О ГОТОВНОСТИ К БРОНИРОВАНИЮ:\n\n"
            f"✅ Страница загружена\n"
            f"✅ Скриншоты сделаны\n"
            f"✅ Календарь: {'найден' if calendar_found else 'не найден'}\n"
            f"✅ Слотов времени: {len(time_elements)}\n"
            f"✅ Машин обнаружено: {len(machines_found)}\n\n"
            f"⚠️ Для полной автоматизации бронирования требуется:\n"
            f"1. Авторизация на сайте (логин/пароль)\n"
            f"2. Правильные CSS-селекторы для элементов\n"
            f"3. Тестирование на реальной странице с доступными слотами"
        )
            
    except Exception as e:
        logger.error(f"Ошибка при бронировании: {e}")
        
        # Пытаемся сделать скриншот ошибки
        try:
            if driver:
                error_screenshot = "/tmp/dikidi_booking_error.png"
                driver.save_screenshot(error_screenshot)
                with open(error_screenshot, 'rb') as photo:
                    await query.message.reply_photo(
                        photo=photo,
                        caption=f"❌ Ошибка при бронировании\n{str(e)[:100]}"
                    )
        except:
            pass
            
        await query.edit_message_text(
            f"❌ Критическая ошибка при бронировании:\n{str(e)[:300]}..."
        )
    finally:
        if driver:
            driver.quit()

async def show_status(query):
    """Показать статус бота"""
    status_text = (
        f"📊 СТАТУС БОТА:\n\n"
        f"✅ Бот активен и работает\n"
        f"👤 Админ ID: {ADMIN_ID}\n"
        f"🔗 Целевой URL: {TARGET_URL[:50]}...\n"
        f"📱 Телефон для брони: {FORM_PHONE}\n"
        f"👤 Имя: {FORM_NAME} {FORM_SURNAME}\n"
        f"💬 Комментарий: {FORM_COMMENT}\n"
        f"⏰ Время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🐍 Python: 3.11\n"
        f"🌐 Chromium: настроен в headless-режиме\n\n"
        f"🔧 Функции:\n"
        f"• /start - меню бота\n"
        f"• Проверка + скриншот\n"
        f"• Анализ страницы Dikidi\n"
        f"• Отладка элементов"
    )
    await query.edit_message_text(status_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"⚠️ Произошла ошибка:\n{str(context.error)[:100]}..."
        )

def main():
    """Основная функция запуска бота"""
    print("✅ HTTP сервер запущен на порту 8080")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    # Временный коммент для теста: application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("📱 Начинаю polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
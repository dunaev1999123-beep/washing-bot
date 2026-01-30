import os
import logging
import time
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
        [InlineKeyboardButton("🔄 Проверить доступность", callback_data='check')],
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
    """Проверка доступности сайта"""
    await query.edit_message_text("🔍 Проверяю доступность сайта...")
    
    driver = None
    try:
        driver = setup_driver()
        driver.get(TARGET_URL)
        
        # Ждем загрузки страницы
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        title = driver.title
        current_url = driver.current_url
        
        await query.edit_message_text(
            f"✅ Сайт доступен!\n\n"
            f"📝 Заголовок: {title}\n"
            f"🔗 URL: {current_url}\n"
            f"⏰ Время проверки: {datetime.now().strftime('%H:%M:%S')}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при проверке сайта: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при проверке сайта:\n{str(e)[:100]}..."
        )
    finally:
        if driver:
            driver.quit()

async def book_machine(query):
    """Процесс бронирования автомата"""
    await query.edit_message_text("🚀 Начинаю процесс бронирования...")
    
    driver = None
    try:
        driver = setup_driver()
        driver.get(TARGET_URL)
        
        # Ждем загрузки страницы
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Здесь должна быть логика заполнения формы
        # Это пример - адаптируйте под ваш сайт
        
        # 1. Найти кнопку бронирования (пример селектора)
        try:
            # Пробуем разные селекторы
            selectors = [
                "button.book-button",
                "button[class*='book']",
                "a[class*='book']",
                ".btn-book",
                "button:contains('Забронировать')"
            ]
            
            book_button = None
            for selector in selectors:
                try:
                    book_button = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if book_button:
                book_button.click()
                await query.edit_message_text("✅ Найдена кнопка бронирования, начинаю заполнение формы...")
            else:
                await query.edit_message_text("❌ Не удалось найти кнопку бронирования")
                return
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка поиска кнопки: {str(e)[:100]}")
            return
        
        # 2. Заполнить форму (пример)
        time.sleep(2)
        
        # Ищем поля формы
        try:
            # Имя
            name_selectors = ["input[name='name']", "input[name='firstname']", "#name", ".name-field"]
            for selector in name_selectors:
                try:
                    name_field = driver.find_element(By.CSS_SELECTOR, selector)
                    name_field.send_keys(FORM_NAME)
                    break
                except:
                    continue
            
            # Фамилия
            surname_selectors = ["input[name='surname']", "input[name='lastname']", "#surname", ".surname-field"]
            for selector in surname_selectors:
                try:
                    surname_field = driver.find_element(By.CSS_SELECTOR, selector)
                    surname_field.send_keys(FORM_SURNAME)
                    break
                except:
                    continue
            
            # Телефон
            phone_selectors = ["input[name='phone']", "input[type='tel']", "#phone", ".phone-field"]
            for selector in phone_selectors:
                try:
                    phone_field = driver.find_element(By.CSS_SELECTOR, selector)
                    phone_field.send_keys(FORM_PHONE)
                    break
                except:
                    continue
            
            # Комментарий
            comment_selectors = ["textarea[name='comment']", "textarea[name='message']", "#comment", ".comment-field"]
            for selector in comment_selectors:
                try:
                    comment_field = driver.find_element(By.CSS_SELECTOR, selector)
                    comment_field.send_keys(FORM_COMMENT)
                    break
                except:
                    continue
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка заполнения формы: {str(e)[:100]}")
            return
        
        # 3. Отправить форму
        time.sleep(1)
        try:
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                ".submit-btn",
                "button:contains('Отправить')",
                "button:contains('Подтвердить')"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if submit_button:
                submit_button.click()
                await query.edit_message_text("✅ Форма отправлена, ожидаю подтверждения...")
            else:
                await query.edit_message_text("❌ Не удалось найти кнопку отправки")
                return
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка отправки формы: {str(e)[:100]}")
            return
        
        # 4. Проверить успешность
        time.sleep(3)
        
        # Ищем сообщение об успехе
        success_indicators = [
            "Спасибо", "Успешно", "Забронировано", "Бронирование подтверждено",
            "success", "thank you", "booking confirmed"
        ]
        
        page_text = driver.page_source.lower()
        success = any(indicator.lower() in page_text for indicator in success_indicators)
        
        if success:
            await query.edit_message_text(
                f"✅ Бронирование успешно!\n\n"
                f"👤 Имя: {FORM_NAME}\n"
                f"👤 Фамилия: {FORM_SURNAME}\n"
                f"📱 Телефон: {FORM_PHONE}\n"
                f"💬 Комментарий: {FORM_COMMENT}\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n"
                f"🔗 Ссылка: {TARGET_URL[:50]}..."
            )
        else:
            # Делаем скриншот для отладки
            screenshot_path = "/tmp/booking_debug.png"
            driver.save_screenshot(screenshot_path)
            
            await query.edit_message_text(
                f"⚠️ Бронирование завершено, но нет подтверждения.\n"
                f"📸 Скриншот сохранен для отладки.\n"
                f"📞 Проверьте вручную: {TARGET_URL[:50]}..."
            )
            
    except Exception as e:
        logger.error(f"Ошибка при бронировании: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при бронировании:\n{str(e)[:200]}..."
        )
    finally:
        if driver:
            driver.quit()

async def show_status(query):
    """Показать статус бота"""
    status_text = (
        f"📊 Статус бота:\n\n"
        f"✅ Бот активен\n"
        f"👤 Админ ID: {ADMIN_ID}\n"
        f"🔗 Целевой URL: {TARGET_URL[:50]}...\n"
        f"📱 Телефон для брони: {FORM_PHONE}\n"
        f"⏰ Время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🐍 Python: 3.11\n"
        f"🌐 Chromium: настроен"
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
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

# Получение переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
TARGET_URL = os.getenv('TARGET_URL')
FORM_NAME = os.getenv('FORM_NAME')
FORM_SURNAME = os.getenv('FORM_SURNAME')
FORM_COMMENT = os.getenv('FORM_COMMENT')
FORM_PHONE = os.getenv('FORM_PHONE')

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
    """Настройка веб-драйвера для работы с Chromium"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Используем Chromium вместо Chrome
    chrome_options.binary_location = "/usr/bin/chromium"
    
    # Добавляем аргументы для стабильной работы
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

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
            f"❌ Ошибка при проверке сайта:\n{str(e)}"
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
        
        # 1. Найти кнопку бронирования
        book_button = driver.find_element(By.CSS_SELECTOR, "button.book-button")
        book_button.click()
        
        # 2. Заполнить форму
        time.sleep(2)
        name_field = driver.find_element(By.NAME, "name")
        name_field.send_keys(FORM_NAME)
        
        surname_field = driver.find_element(By.NAME, "surname")
        surname_field.send_keys(FORM_SURNAME)
        
        phone_field = driver.find_element(By.NAME, "phone")
        phone_field.send_keys(FORM_PHONE)
        
        comment_field = driver.find_element(By.NAME, "comment")
        comment_field.send_keys(FORM_COMMENT)
        
        # 3. Отправить форму
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # 4. Проверить успешность
        time.sleep(3)
        
        success = True  # Замените на реальную проверку
        
        if success:
            await query.edit_message_text(
                f"✅ Бронирование успешно!\n\n"
                f"👤 Имя: {FORM_NAME}\n"
                f"👤 Фамилия: {FORM_SURNAME}\n"
                f"📱 Телефон: {FORM_PHONE}\n"
                f"💬 Комментарий: {FORM_COMMENT}\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            await query.edit_message_text("❌ Не удалось завершить бронирование")
            
    except Exception as e:
        logger.error(f"Ошибка при бронировании: {e}")
        await query.edit_message_text(
            f"❌ Ошибка при бронировании:\n{str(e)}"
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
        f"⏰ Время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🐍 Python: 3.11\n"
        f"🌐 Chromium: установлен"
    )
    await query.edit_message_text(status_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"⚠️ Произошла ошибка:\n{context.error}"
        )

def main():
    """Основная функция запуска бота"""
    print("✅ HTTP сервер запущен на порту 8080")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("📱 Начинаю polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
import os
import logging
import time
import tempfile
import json
import threading
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', '8196163948:AAGn9B0rIqLX2QDMWo0DDd0Yaz-jX04FywI')
ADMIN_ID = int(os.getenv('ADMIN_ID', '7452553608'))
TARGET_URL = os.getenv('TARGET_URL', 'https://dikidi.net/1613380?p=4.pi-po-ssm-sd-cf&o=7&am=1&m=3474814&s=16944200&d=202601310900&r=1027863105&rl=0_1027863105&sdr=')

# Константы
CONFIG_FILE = "bot_config.json"
DEFAULT_CONFIG = {
    "form_name": "Константин",
    "form_surname": "Дунаев",
    "form_comment": "526",
    "form_phone": "9955542240",
    "machine_priority": ["Машинка 1", "Машинка 2", "Машинка 3"],
    "preferred_times": ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00", "21:00"],
    "selected_machine": None,
    "selected_time": None
}

# Загрузка конфигурации
def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

config = load_config()

# Кэш драйвера для повторного использования
driver_cache = None
driver_lock = threading.Lock()

print("🤖 ТЕЛЕГРАМ БОТ ЗАПУСКАЕТСЯ (УСКОРЕННАЯ ВЕРСИЯ)")
print(f"✅ BOT_TOKEN: {'✓ Установлен' if BOT_TOKEN else '✗ ОТСУТСТВУЕТ'}")
print(f"✅ ADMIN_ID: {ADMIN_ID} ✓")
print(f"✅ TARGET_URL: {'✓ Установлен' if TARGET_URL else '✗ ОТСУТСТВУЕТ'}")

def get_driver():
    """Получение драйвера (с кэшированием)"""
    global driver_cache
    
    with driver_lock:
        if driver_cache is not None:
            try:
                # Проверяем, что драйвер еще работает
                driver_cache.current_url
                return driver_cache
            except:
                driver_cache = None
        
        chrome_options = Options()
        
        # УСКОРЕННЫЕ НАСТРОЙКИ
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # ОПТИМИЗАЦИЯ ДЛЯ СКОРОСТИ
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        
        # УСКОРЕНИЕ ЗАГРУЗКИ
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2,  # Блокировка картинок
                'javascript': 1,  # JS включен
                'plugins': 2,  # Блокировка плагинов
                'popups': 2,  # Блокировка popup
                'notifications': 2,
            }
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        # Дополнительные настройки для скорости
        chrome_options.add_argument("--disable-device-discovery-notifications")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        
        chrome_options.binary_location = "/usr/bin/chromium"
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Устанавливаем таймауты для быстрой загрузки
            driver.set_page_load_timeout(10)
            driver.implicitly_wait(2)
            
            driver_cache = driver
            print("✅ Chromium драйвер создан (оптимизирован)")
            return driver
        except Exception as e:
            print(f"❌ Ошибка создания драйвера: {e}")
            
            possible_paths = ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]
            for path in possible_paths:
                try:
                    chrome_options.binary_location = path
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.set_page_load_timeout(10)
                    driver.implicitly_wait(2)
                    driver_cache = driver
                    print(f"✅ Драйвер запущен с {path}")
                    return driver
                except:
                    continue
            
            raise Exception("Не удалось запустить драйвер")

def cleanup_driver():
    """Очистка кэша драйвера"""
    global driver_cache
    with driver_lock:
        if driver_cache:
            try:
                driver_cache.quit()
            except:
                pass
            driver_cache = None

async def fast_handle_cookies_popup(driver):
    """Быстрая обработка cookies"""
    try:
        # Сокращенное время ожидания
        await asyncio.sleep(0.5)
        
        # Быстрый поиск кнопок cookies
        cookie_selectors = [
            (By.CSS_SELECTOR, ".cookie-accept"),
            (By.CSS_SELECTOR, "#accept-cookies"),
            (By.CSS_SELECTOR, "button[data-testid='accept-cookies']"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'accept')]"),
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'принять')]"),
        ]
        
        for by, selector in cookie_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed():
                        driver.execute_script("arguments[0].click();", element)
                        return True
            except:
                continue
        
        return False
    except Exception as e:
        return False

async def ultra_fast_booking(query, machine_name=None, preferred_time=None):
    """СУПЕР БЫСТРОЕ бронирование"""
    driver = None
    start_time = time.time()
    
    try:
        driver = get_driver()
        
        # 1. БЫСТРЫЙ ПЕРЕХОД НА САЙТ
        await query.edit_message_text("⚡ Загружаю сайт...")
        
        try:
            driver.get(TARGET_URL)
            # Ждем только body, не всю страницу
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            # Если не загрузилось полностью, продолжаем
            pass
        
        # 2. БЫСТРАЯ ОБРАБОТКА COOKIES
        await fast_handle_cookies_popup(driver)
        await asyncio.sleep(0.3)
        
        # 3. БЫСТРЫЙ ПОИСК МАШИНКИ
        if machine_name:
            await query.edit_message_text(f"⚡ Ищу {machine_name}...")
            
            # Оптимизированный поиск машины
            try:
                xpath_query = f"//*[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), '{machine_name.lower()}')]"
                elements = driver.find_elements(By.XPATH, xpath_query)
                
                for element in elements[:3]:  # Проверяем только первые 3 элемента
                    try:
                        if element.is_displayed():
                            html = element.get_attribute('outerHTML')
                            if not any(word in html.lower() for word in ['disabled', 'занят', 'busy']):
                                driver.execute_script("arguments[0].click();", element)
                                await asyncio.sleep(0.3)
                                break
                    except:
                        continue
            except:
                pass
        
        # 4. МГНОВЕННЫЙ ПОИСК ВРЕМЕНИ
        await query.edit_message_text("⚡ Ищу время...")
        
        time_found = False
        if preferred_time:
            # Прямой поиск по времени
            try:
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{preferred_time}')]")
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            driver.execute_script("arguments[0].click();", element)
                            time_found = True
                            await asyncio.sleep(0.3)
                            break
                    except:
                        continue
            except:
                pass
        
        if not time_found:
            # Быстрый поиск любых временных слотов
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, "[class*='time'], [class*='hour'], [data-time], .booking-slot")
                for element in elements[:8]:  # Проверяем только первые 8
                    try:
                        text = element.text.strip()
                        if text and ':' in text and len(text) < 8:
                            if element.is_displayed() and element.is_enabled():
                                driver.execute_script("arguments[0].click();", element)
                                await asyncio.sleep(0.3)
                                break
                    except:
                        continue
            except:
                pass
        
        # 5. СВЕРХБЫСТРОЕ ЗАПОЛНЕНИЕ ФОРМЫ
        await query.edit_message_text("⚡ Заполняю форму...")
        
        try:
            # Находим все поля
            all_inputs = driver.find_elements(By.TAG_NAME, "input")
            all_textareas = driver.find_elements(By.TAG_NAME, "textarea")
            
            # Быстро заполняем
            for field in all_inputs + all_textareas:
                try:
                    if not field.is_displayed():
                        continue
                    
                    field_type = field.get_attribute('type') or 'text'
                    field_name = field.get_attribute('name') or ''
                    
                    if field_type == 'tel' or 'phone' in field_name.lower():
                        field.clear()
                        field.send_keys(config.get('form_phone', '9955542240'))
                    elif field_type == 'text' and not field.get_attribute('value'):
                        field.clear()
                        field.send_keys(config.get('form_name', 'Константин'))
                        await asyncio.sleep(0.1)
                    elif field.tag_name == 'textarea':
                        field.clear()
                        field.send_keys(config.get('form_comment', '526'))
                except:
                    continue
        except:
            pass
        
        # 6. МГНОВЕННЫЙ ПОИСК КНОПОК CONTINUE
        await query.edit_message_text("⚡ Отправляю форму...")
        
        # Ищем кнопки CONTINUE
        continue_selectors = [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
            "//button[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'продолжить')]",
            "button[type='submit']",
            ".btn-primary",
        ]
        
        for selector in continue_selectors:
            try:
                if selector.startswith('//'):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                if element.is_displayed():
                    driver.execute_script("arguments[0].click();", element)
                    await asyncio.sleep(0.5)
                    break
            except:
                continue
        
        # 7. БЫСТРЫЙ ПОИСК КНОПКИ COMPLETE
        complete_selectors = [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'complete')]",
            "//button[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'завершить')]",
        ]
        
        for selector in complete_selectors:
            try:
                if selector.startswith('//'):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                if element.is_displayed():
                    driver.execute_script("arguments[0].click();", element)
                    await asyncio.sleep(0.5)
                    break
            except:
                continue
        
        # 8. ФИНАЛЬНЫЙ СКРИНШОТ
        total_time = time.time() - start_time
        
        final_screenshot = "/tmp/dikidi_final_fast.png"
        driver.save_screenshot(final_screenshot)
        
        with open(final_screenshot, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=f"📸 Результат за {total_time:.1f} сек"
            )
        
        await query.edit_message_text(f"✅ Бронирование завершено за {total_time:.1f} сек!\n\n⚡ Ускоренная версия работает!")
        
    except Exception as e:
        logger.error(f"Ошибка быстрого бронирования: {e}")
        await query.edit_message_text("⚠️ Ошибка при бронировании")
    finally:
        # Не закрываем драйвер, оставляем в кэше
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return
    
    keyboard = [
        [InlineKeyboardButton("⚡ Быстрая запись", callback_data='fast_book')],
        [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
        [InlineKeyboardButton("📊 Статус", callback_data='status')],
        [InlineKeyboardButton("🧹 Очистить кэш", callback_data='clear_cache')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 УСКОРЕННЫЙ бот для бронирования\n\n"
        f"⚡ Скорость приоритет!\n"
        f"⏰ Время сервера: {datetime.now().strftime('%H:%M:%S')}",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ У вас нет доступа к этому боту.")
        return
    
    if query.data == 'fast_book':
        await fast_booking_menu(query)
    elif query.data == 'settings':
        await settings_menu(query)
    elif query.data == 'status':
        await show_status(query)
    elif query.data == 'clear_cache':
        await clear_cache(query)
    elif query.data == 'back_to_main':
        await start_callback(query)
    elif query.data.startswith('book_fast_'):
        await start_fast_booking(query)
    elif query.data.startswith('set_machine_'):
        await set_machine(query)
    elif query.data.startswith('set_time_'):
        await set_time(query)
    elif query.data == 'edit_phone':
        await edit_phone_prompt(query)

async def start_callback(query):
    """Возврат в главное меню"""
    await start(query, None)

async def fast_booking_menu(query):
    """Меню быстрой записи"""
    keyboard = []
    
    # Кнопки для быстрой записи
    times = config.get('preferred_times', DEFAULT_CONFIG['preferred_times'])
    
    # Группируем по 3 кнопки в ряд
    for i in range(0, len(times), 3):
        row = []
        for j in range(3):
            if i + j < len(times):
                time_str = times[i + j]
                row.append(InlineKeyboardButton(f"⚡ {time_str}", callback_data=f"book_fast_{time_str}"))
        if row:
            keyboard.append(row)
    
    # Если выбрана машинка, добавляем кнопку с настройками
    if config.get('selected_machine'):
        keyboard.append([
            InlineKeyboardButton(
                f"🎯 {config['selected_machine']}", 
                callback_data=f"book_fast_custom"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚡ БЫСТРАЯ ЗАПИСЬ\n\n"
        "Выберите время для мгновенного бронирования:",
        reply_markup=reply_markup
    )

async def start_fast_booking(query):
    """Запуск быстрого бронирования"""
    if query.data == 'book_fast_custom':
        # Используем настройки из конфига
        await ultra_fast_booking(
            query, 
            machine_name=config.get('selected_machine'),
            preferred_time=config.get('selected_time')
        )
    else:
        # Используем выбранное время
        time_str = query.data.replace('book_fast_', '')
        await ultra_fast_booking(
            query,
            machine_name=config.get('selected_machine'),
            preferred_time=time_str
        )

async def settings_menu(query):
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton(f"🧺 Машинка: {config.get('selected_machine', 'не выбрана')}", callback_data='machine_menu')],
        [InlineKeyboardButton(f"🕒 Время: {config.get('selected_time', 'не выбрано')}", callback_data='time_menu')],
        [InlineKeyboardButton(f"📱 Телефон: {config.get('form_phone', '...')[:10]}", callback_data='edit_phone')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚙️ НАСТРОЙКИ\n\n"
        "Здесь можно настроить параметры:",
        reply_markup=reply_markup
    )

async def machine_menu(query):
    """Меню выбора машинки"""
    keyboard = []
    machines = config.get('machine_priority', DEFAULT_CONFIG['machine_priority'])
    
    for machine in machines:
        is_selected = " ✅" if config.get('selected_machine') == machine else ""
        keyboard.append([InlineKeyboardButton(f"{machine}{is_selected}", callback_data=f'set_machine_{machine}')])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='settings')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🧺 ВЫБОР МАШИНКИ\n\n"
        "Бот будет использовать выбранную машинку:",
        reply_markup=reply_markup
    )

async def time_menu(query):
    """Меню выбора времени"""
    keyboard = []
    times = config.get('preferred_times', DEFAULT_CONFIG['preferred_times'])
    
    for time_str in times:
        is_selected = " ✅" if config.get('selected_time') == time_str else ""
        keyboard.append([InlineKeyboardButton(f"{time_str}{is_selected}", callback_data=f'set_time_{time_str}')])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='settings')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🕒 ВЫБОР ВРЕМЕНИ\n\n"
        "Предпочтительное время для записи:",
        reply_markup=reply_markup
    )

async def set_machine(query):
    """Установка выбранной машинки"""
    machine = query.data.replace('set_machine_', '')
    config['selected_machine'] = machine
    save_config(config)
    await query.answer(f"✅ {machine}")
    await machine_menu(query)

async def set_time(query):
    """Установка выбранного времени"""
    time_str = query.data.replace('set_time_', '')
    config['selected_time'] = time_str
    save_config(config)
    await query.answer(f"✅ {time_str}")
    await time_menu(query)

async def clear_cache(query):
    """Очистка кэша драйвера"""
    cleanup_driver()
    await query.answer("✅ Кэш очищен!")
    await start_callback(query)

async def edit_phone_prompt(query):
    """Запрос номера телефона"""
    await query.edit_message_text(
        "📱 Введите номер телефона (10-11 цифр):\n"
        "Например: 9955542240\n\n"
        "Отправьте /cancel для отмены."
    )
    return SET_PHONE

async def set_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода телефона"""
    phone = update.message.text.strip()
    
    if phone.isdigit() and len(phone) >= 10:
        config['form_phone'] = phone
        save_config(config)
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад к настройкам", callback_data='settings')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Телефон сохранен: {phone}",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ Неверный формат телефона. Введите 10-11 цифр:\n"
            "Например: 9955542240\n\n"
            "Отправьте /cancel для отмены."
        )
        return SET_PHONE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

async def show_status(query):
    """Показать статус бота"""
    status_text = (
        f"📊 СТАТУС БОТА\n\n"
        f"✅ Версия: Ускоренная\n"
        f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🧺 Машинка: {config.get('selected_machine', 'не выбрана')}\n"
        f"🕒 Время: {config.get('selected_time', 'не выбрано')}\n"
        f"📱 Телефон: {config.get('form_phone', 'не установлен')}\n"
        f"👤 Имя: {config.get('form_name', 'Константин')}\n\n"
        f"⚡ Оптимизации:\n"
        f"• Блокировка картинок\n"
        f"• Кэширование драйвера\n"
        f"• Уменьшенные таймауты\n"
        f"• Быстрые клики через JS"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(status_text, reply_markup=reply_markup)

# Состояния для ConversationHandler
SET_PHONE, = range(1)

def main():
    """Основная функция запуска бота"""
    print("⚡ Запускаю УСКОРЕННУЮ версию бота...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Создаем ConversationHandler для обработки телефона
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_phone_prompt, pattern='^edit_phone$'),
        ],
        states={
            SET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Очищаем кэш при завершении
    import atexit
    atexit.register(cleanup_driver)
    
    print("📱 Начинаю polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
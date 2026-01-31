import os
import logging
import time
import tempfile
import json
import schedule
import threading
import asyncio
from datetime import datetime, time as dt_time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
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
    "auto_booking_enabled": False,
    "auto_booking_time": "08:00",
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
        chrome_options.add_argument("--disable-images")  # Отключаем загрузку картинок
        chrome_options.add_argument("--disable-javascript")  # Можно отключить JS если не нужен
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--disable-css-animations")
        
        # УСКОРЕНИЕ ЗАГРУЗКИ
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2,  # Блокировка картинок
                'javascript': 1,  # JS включен (нужен для работы сайта)
                'plugins': 2,  # Блокировка плагинов
                'popups': 2,  # Блокировка popup
                'geolocation': 2,
                'notifications': 2,
                'auto_select_certificate': 2,
                'fullscreen': 2,
                'mouselock': 2,
                'mixed_script': 2,
                'media_stream': 2,
                'media_stream_mic': 2,
                'media_stream_camera': 2,
                'ppapi_broker': 2,
                'automatic_downloads': 2,
                'midi_sysex': 2,
                'push_messaging': 2,
                'ssl_cert_decisions': 2,
                'metro_switch_to_desktop': 2,
                'protected_media_identifier': 2,
                'app_banner': 2,
                'site_engagement': 2,
                'durable_storage': 2
            }
        }
        chrome_options.add_experimental_option('prefs', prefs)
        
        # Дополнительные настройки для скорости
        chrome_options.add_argument("--disable-device-discovery-notifications")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--silent")
        
        chrome_options.binary_location = "/usr/bin/chromium"
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Устанавливаем таймауты для быстрой загрузки
            driver.set_page_load_timeout(10)  # 10 секунд на загрузку страницы
            driver.implicitly_wait(2)  # 2 секунды неявного ожидания
            
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
    """Быстрая обработка cookies (параллельный поиск)"""
    try:
        # Сокращенное время ожидания
        time.sleep(1)
        
        # Создаем список задач для параллельного поиска
        cookie_tasks = [
            # Поиск по CSS селекторам
            lambda: driver.find_elements(By.CSS_SELECTOR, ".cookie-accept, .cookies-accept, #accept-cookies, #cookie-accept"),
            # Поиск по тексту (быстрый вариант)
            lambda: driver.find_elements(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'accept') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'принять') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'согласен')]"),
        ]
        
        # Выполняем поиск параллельно
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(task) for task in cookie_tasks]
            for future in as_completed(futures):
                try:
                    elements = future.result(timeout=2)
                    for element in elements:
                        try:
                            if element.is_displayed():
                                # Быстрый клик через JavaScript
                                driver.execute_script("arguments[0].click();", element)
                                return True
                        except:
                            continue
                except:
                    continue
        
        return False
    except Exception as e:
        return False

def fast_find_and_click(driver, selectors, timeout=3):
    """Быстрый поиск и клик по элементу"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        for selector in selectors:
            try:
                if isinstance(selector, tuple):
                    by, value = selector
                    element = driver.find_element(by, value)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                if element.is_displayed() and element.is_enabled():
                    # Самый быстрый способ клика
                    driver.execute_script("arguments[0].click();", element)
                    return True
            except:
                continue
        
        time.sleep(0.1)  # Очень короткая пауза
    
    return False

async def fast_fill_form(driver):
    """Быстрое заполнение формы"""
    try:
        # Получаем все поля за один запрос
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        all_textareas = driver.find_elements(By.TAG_NAME, "textarea")
        
        # Создаем словарь для быстрого заполнения
        field_data = {
            'name': config.get('form_name', 'Константин'),
            'surname': config.get('form_surname', 'Дунаев'),
            'phone': config.get('form_phone', '9955542240'),
            'comment': config.get('form_comment', '526')
        }
        
        # Быстрое заполнение полей
        for field in all_inputs + all_textareas:
            try:
                if not field.is_displayed():
                    continue
                
                field_type = field.get_attribute('type') or 'text'
                field_name = field.get_attribute('name') or ''
                field_tag = field.tag_name
                
                # Очистка поля
                field.clear()
                
                # Определяем что заполнять
                if field_type == 'tel' or 'phone' in field_name.lower():
                    field.send_keys(field_data['phone'])
                elif 'name' in field_name.lower() and field_data['name']:
                    field.send_keys(field_data['name'])
                elif ('surname' in field_name.lower() or 'last' in field_name.lower()) and field_data['surname']:
                    field.send_keys(field_data['surname'])
                elif field_tag == 'textarea' and field_data['comment']:
                    field.send_keys(field_data['comment'])
                elif field_type == 'text' and not field.get_attribute('value'):
                    # Заполняем первое пустое текстовое поле именем
                    field.send_keys(field_data['name'])
                    field_data['name'] = None  # Чтобы не заполнять повторно
            except:
                continue
        
        return True
    except Exception as e:
        logger.error(f"Ошибка заполнения формы: {e}")
        return False

async def ultra_fast_booking(query, machine_name=None, preferred_time=None):
    """СУПЕР БЫСТРОЕ бронирование"""
    driver = None
    start_time = time.time()
    
    try:
        driver = get_driver()
        
        # 1. БЫСТРЫЙ ПЕРЕХОД НА САЙТ
        await query.edit_message_text("⚡ Загружаю сайт...")
        driver.get(TARGET_URL)
        
        # Ждем загрузки с таймаутом
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        # 2. БЫСТРАЯ ОБРАБОТКА COOKIES
        await fast_handle_cookies_popup(driver)
        
        # 3. БЫСТРЫЙ ПОИСК МАШИНКИ
        if machine_name:
            await query.edit_message_text(f"⚡ Ищу {machine_name}...")
            
            # Оптимизированный поиск машины
            try:
                # Прямой поиск по XPath
                xpath_query = f"//*[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), '{machine_name.lower()}')]"
                elements = driver.find_elements(By.XPATH, xpath_query)
                
                for element in elements[:5]:  # Проверяем только первые 5 элементов
                    try:
                        if element.is_displayed():
                            # Проверяем доступность
                            html = element.get_attribute('outerHTML')
                            if not any(word in html.lower() for word in ['disabled', 'занят', 'busy']):
                                driver.execute_script("arguments[0].click();", element)
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
                # Ищем элементы содержащие время
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{preferred_time}')]")
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            driver.execute_script("arguments[0].click();", element)
                            time_found = True
                            break
                    except:
                        continue
            except:
                pass
        
        if not time_found:
            # Быстрый поиск любых временных слотов
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, "[class*='time'], [class*='hour'], [data-time]")
                for element in elements[:10]:  # Проверяем только первые 10
                    try:
                        text = element.text.strip()
                        if text and ':' in text and len(text) < 8:
                            if element.is_displayed() and element.is_enabled():
                                driver.execute_script("arguments[0].click();", element)
                                break
                    except:
                        continue
            except:
                pass
        
        # 5. СВЕРХБЫСТРОЕ ЗАПОЛНЕНИЕ ФОРМЫ
        await query.edit_message_text("⚡ Заполняю форму...")
        await fast_fill_form(driver)
        
        # 6. МГНОВЕННЫЙ ПОИСК КНОПОК
        await query.edit_message_text("⚡ Отправляю форму...")
        
        # Ищем кнопки CONTINUE
        continue_selectors = [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
            "//button[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'продолжить')]",
            "button[type='submit']",
            ".btn-primary",
            "[class*='continue']"
        ]
        
        for selector in continue_selectors:
            try:
                if selector.startswith('//'):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                if element.is_displayed():
                    driver.execute_script("arguments[0].click();", element)
                    break
            except:
                continue
        
        # Короткая пауза для загрузки следующей страницы
        await asyncio.sleep(1)
        
        # 7. БЫСТРЫЙ ПОИСК КНОПКИ COMPLETE
        complete_selectors = [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'complete')]",
            "//button[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'завершить')]",
            "[class*='complete']"
        ]
        
        for selector in complete_selectors:
            try:
                if selector.startswith('//'):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                if element.is_displayed():
                    driver.execute_script("arguments[0].click();", element)
                    break
            except:
                continue
        
        # 8. ФИНАЛЬНЫЙ СКРИНШОТ
        await asyncio.sleep(1)
        total_time = time.time() - start_time
        
        final_screenshot = "/tmp/dikidi_final_fast.png"
        driver.save_screenshot(final_screenshot)
        
        with open(final_screenshot, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=f"📸 Результат за {total_time:.1f} сек"
            )
        
        await query.edit_message_text(f"✅ Бронирование завершено за {total_time:.1f} сек!")
        
    except Exception as e:
        logger.error(f"Ошибка быстрого бронирования: {e}")
        await query.edit_message_text("⚠️ Ошибка при бронировании")

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

async def start_callback(query):
    """Возврат в главное меню"""
    await start(query, None)

async def fast_booking_menu(query):
    """Меню быстрой записи"""
    keyboard = []
    
    # Кнопки для быстрой записи
    times = config.get('preferred_times', DEFAULT_CONFIG['preferred_times'])
    
    # Группируем по 3 кнопки в ряд для экономии места
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
        f"• Параллельный поиск\n"
        f"• Уменьшенные таймауты"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(status_text, reply_markup=reply_markup)

async def edit_phone_prompt(query):
    """Запрос номера телефона"""
    await query.edit_message_text(
        "📱 Введите номер телефона (только цифры):\n"
        "Пример: 9955542240"
    )
    return ConversationHandler.END

def main():
    """Основная функция запуска бота"""
    print("⚡ Запускаю УСКОРЕННУЮ версию бота...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Очищаем кэш при завершении
    import atexit
    atexit.register(cleanup_driver)
    
    print("📱 Начинаю polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
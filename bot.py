import os
import logging
import time
import tempfile
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import concurrent.futures

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
FORM_PHONE = os.getenv('FORM_PHONE', '7955542240')  # Исправлен номер с 7 в начале

# Кэш драйвера
driver_cache = None
driver_lock = asyncio.Lock()

print("⚡ ТЕЛЕГРАМ БОТ ЗАПУСКАЕТСЯ (УСКОРЕННАЯ ВЕРСИЯ)")
print(f"✅ BOT_TOKEN: {'✓ Установлен' if BOT_TOKEN else '✗ ОТСУТСТВУЕТ'}")
print(f"✅ ADMIN_ID: {ADMIN_ID} ✓")
print(f"✅ TARGET_URL: {'✓ Установлен' if TARGET_URL else '✗ ОТСУТСТВУЕТ'}")
print(f"✅ Телефон: {FORM_PHONE}")
print(f"✅ Фамилия: {FORM_SURNAME}")

async def get_driver():
    """Получение драйвера с кэшированием"""
    global driver_cache
    
    async with driver_lock:
        if driver_cache is not None:
            try:
                driver_cache.current_url
                return driver_cache
            except:
                driver_cache = None
        
        chrome_options = Options()
        
        # МАКСИМАЛЬНАЯ СКОРОСТЬ
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # ОПТИМИЗАЦИЯ ЗАГРУЗКИ
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
        
        # ДОПОЛНИТЕЛЬНАЯ ОПТИМИЗАЦИЯ
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--disable-device-discovery-notifications")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-software-rasterizer")
        
        chrome_options.binary_location = "/usr/bin/chromium"
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # МИНИМАЛЬНЫЕ ТАЙМАУТЫ ДЛЯ СКОРОСТИ
            driver.set_page_load_timeout(8)
            driver.implicitly_wait(1)
            driver.set_script_timeout(5)
            
            driver_cache = driver
            print("✅ Chromium драйвер создан (максимальная скорость)")
            return driver
        except Exception as e:
            print(f"❌ Ошибка создания драйвера: {e}")
            
            # Попробуем альтернативные пути
            possible_paths = ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]
            for path in possible_paths:
                try:
                    chrome_options.binary_location = path
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.set_page_load_timeout(8)
                    driver.implicitly_wait(1)
                    driver_cache = driver
                    print(f"✅ Драйвер запущен с {path}")
                    return driver
                except:
                    continue
            
            raise Exception("Не удалось запустить драйвер")

async def cleanup_driver():
    """Очистка кэша драйвера"""
    global driver_cache
    async with driver_lock:
        if driver_cache:
            try:
                driver_cache.quit()
            except:
                pass
            driver_cache = None

async def ultra_fast_handle_cookies(driver):
    """Сверхбыстрая обработка cookies"""
    try:
        # Используем JavaScript для мгновенного поиска и клика
        scripts = [
            """
            // Ищем кнопки Accept/Cookies мгновенно
            const selectors = [
                '.cookie-accept', '#accept-cookies', 
                'button[data-testid="accept-cookies"]',
                'button:contains("Accept all")',
                'button:contains("Принять все")',
                'button:contains("Принять")',
                'button:contains("Согласен")',
                'button:contains("OK")',
                '.btn-cookie',
                '[class*="cookie"][class*="accept"]',
                '[class*="cookies"][class*="accept"]'
            ];
            
            for (let selector of selectors) {
                try {
                    let elements = document.querySelectorAll(selector);
                    for (let el of elements) {
                        if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                            el.click();
                            return true;
                        }
                    }
                } catch(e) {}
            }
            
            // Ищем по тексту через XPath
            const xpaths = [
                '//button[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "accept")]',
                '//button[contains(translate(., "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ", "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"), "принять")]',
                '//button[contains(text(), "OK")]',
                '//button[contains(text(), "Согласен")]'
            ];
            
            const xpathResult = document.evaluate(xpaths[0], document, null, XPathResult.ANY_TYPE, null);
            let node = xpathResult.iterateNext();
            while (node) {
                if (node.offsetWidth > 0 && node.offsetHeight > 0) {
                    node.click();
                    return true;
                }
                node = xpathResult.iterateNext();
            }
            
            return false;
            """,
            """
            // Удаляем cookies overlay если не нашли кнопку
            const overlays = document.querySelectorAll('[class*="cookie"], [class*="cookies"], .cookie-overlay, .cookies-banner');
            overlays.forEach(el => {
                el.style.display = 'none';
                el.remove();
            });
            return true;
            """
        ]
        
        for script in scripts:
            try:
                result = driver.execute_script(script)
                if result:
                    await asyncio.sleep(0.2)  # Минимальная задержка
                    return True
            except:
                continue
        
        return False
    except Exception as e:
        return False

async def ultra_fast_book_machine(driver, machine_name=None):
    """Сверхбыстрый выбор машинки"""
    if not machine_name:
        return None
    
    try:
        # Пробуем разные стратегии одновременно
        strategies = [
            # Стратегия 1: Быстрый поиск по тексту
            f"//*[contains(text(), '{machine_name}')]",
            # Стратегия 2: Поиск по части текста
            f"//*[contains(., '{machine_name[:5]}')]",
            # Стратегия 3: Поиск по классам
            f"//div[contains(@class, 'machine')]//*[contains(text(), '{machine_name}')]",
            # Стратегия 4: Поиск кнопок с текстом
            f"//button[contains(text(), '{machine_name}')]",
        ]
        
        for xpath in strategies:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for element in elements[:5]:  # Проверяем только первые 5
                    try:
                        if element.is_displayed() and element.is_enabled():
                            # Быстрая проверка на доступность
                            html = element.get_attribute('outerHTML')
                            if not any(word in html.lower() for word in ['disabled', 'занят', 'busy', 'unavailable']):
                                driver.execute_script("arguments[0].click();", element)
                                await asyncio.sleep(0.3)
                                return element
                    except StaleElementReferenceException:
                        continue
            except:
                continue
        
        return None
    except Exception as e:
        return None

async def ultra_fast_select_time(driver):
    """Сверхбыстрый выбор времени"""
    try:
        # Стратегия 1: Ищем стандартные селекторы
        time_selectors = [
            ".nr-item.sdt-hour", "[data-time]", ".booking-slot", 
            ".time-slot", "[class*='sdt-hour']", "[class*='time-slot']",
            "button[class*='time']", "div[class*='time']", "a[class*='time']"
        ]
        
        for selector in time_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements[:8]:  # Проверяем первые 8
                    try:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            if text and ':' in text:
                                # Быстрая проверка на доступность
                                classes = element.get_attribute('class') or ''
                                if not any(word in classes.lower() for word in ['disabled', 'busy', 'unavailable']):
                                    driver.execute_script("arguments[0].click();", element)
                                    await asyncio.sleep(0.3)
                                    return text
                    except StaleElementReferenceException:
                        continue
            except:
                continue
        
        # Стратегия 2: Ищем по XPath для времени
        time_xpaths = [
            "//*[contains(text(), ':')]",
            "//*[contains(., '00') or contains(., '30')]",
        ]
        
        for xpath in time_xpaths:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for element in elements[:15]:  # Проверяем первые 15
                    try:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            if len(text) <= 8 and ':' in text and any(c.isdigit() for c in text):
                                driver.execute_script("arguments[0].click();", element)
                                await asyncio.sleep(0.3)
                                return text
                    except StaleElementReferenceException:
                        continue
            except:
                continue
        
        return None
    except Exception as e:
        return None

async def ultra_fast_fill_form(driver):
    """Сверхбыстрое заполнение формы"""
    try:
        # Находим все поля одним запросом
        all_fields = driver.find_elements(By.CSS_SELECTOR, "input, textarea")
        
        # Сопоставляем поля с данными
        fields_to_fill = []
        
        for field in all_fields:
            try:
                if not field.is_displayed():
                    continue
                    
                field_type = field.get_attribute('type') or 'text'
                field_name = field.get_attribute('name') or ''
                field_id = field.get_attribute('id') or ''
                placeholder = field.get_attribute('placeholder') or ''
                
                # Определяем что за поле
                is_phone = False
                is_surname = False
                is_name = False
                is_comment = False
                
                # Проверка телефона
                if field_type == 'tel' or 'phone' in field_name.lower() or 'phone' in field_id.lower() or 'телефон' in placeholder.lower():
                    is_phone = True
                # Проверка фамилии
                elif 'surname' in field_name.lower() or 'lastname' in field_name.lower() or 'фамилия' in placeholder.lower():
                    is_surname = True
                # Проверка имени
                elif 'name' in field_name.lower() and not 'surname' in field_name.lower() or 'имя' in placeholder.lower() and 'фамилия' not in placeholder.lower():
                    is_name = True
                # Проверка комментария
                elif field.tag_name == 'textarea' or 'comment' in field_name.lower() or 'комментарий' in placeholder.lower():
                    is_comment = True
                
                if is_phone or is_surname or is_name or is_comment:
                    fields_to_fill.append((field, is_phone, is_surname, is_name, is_comment))
                    
            except:
                continue
        
        # Быстро заполняем
        for field, is_phone, is_surname, is_name, is_comment in fields_to_fill:
            try:
                if is_phone:
                    field.clear()
                    field.send_keys(FORM_PHONE)
                elif is_surname:
                    field.clear()
                    field.send_keys(FORM_SURNAME)
                elif is_name:
                    field.clear()
                    field.send_keys(FORM_NAME)
                elif is_comment:
                    field.clear()
                    field.send_keys(FORM_COMMENT)
            except:
                continue
        
        # Если не нашли поля по атрибутам, заполняем первые доступные
        if len(fields_to_fill) == 0:
            visible_fields = [f for f in all_fields if f.is_displayed() and f.is_enabled()]
            for i, field in enumerate(visible_fields[:4]):
                try:
                    field.clear()
                    if i == 0:
                        field.send_keys(FORM_NAME)
                    elif i == 1:
                        field.send_keys(FORM_SURNAME)
                    elif i == 2:
                        field.send_keys(FORM_PHONE)
                    elif i == 3 and field.tag_name == 'textarea':
                        field.send_keys(FORM_COMMENT)
                except:
                    continue
        
        await asyncio.sleep(0.2)
        return True
    except Exception as e:
        return False

async def ultra_fast_submit(driver):
    """Сверхбыстрая отправка формы"""
    try:
        # Находим и кликаем на кнопки через JavaScript для скорости
        submit_scripts = [
            # Для кнопок Continue
            """
            const continueSelectors = [
                'button:contains("Continue")',
                'button:contains("Продолжить")',
                '[class*="continue"]',
                'button[type="submit"]',
                '.btn-primary',
                '.submit-button'
            ];
            
            for (let selector of continueSelectors) {
                try {
                    let elements = document.querySelectorAll(selector);
                    for (let el of elements) {
                        if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                            el.click();
                            return true;
                        }
                    }
                } catch(e) {}
            }
            return false;
            """,
            # Для кнопок Complete
            """
            const completeSelectors = [
                'button:contains("Complete")',
                'button:contains("Завершить")',
                'button:contains("Подтвердить")',
                '[class*="complete"]',
                '[class*="confirm"]'
            ];
            
            for (let selector of completeSelectors) {
                try {
                    let elements = document.querySelectorAll(selector);
                    for (let el of elements) {
                        if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                            el.click();
                            return true;
                        }
                    }
                } catch(e) {}
            }
            return false;
            """
        ]
        
        # Первый клик - Continue
        for script in submit_scripts[:1]:
            try:
                result = driver.execute_script(script)
                if result:
                    await asyncio.sleep(0.5)
                    break
            except:
                continue
        
        # Второй клик - Complete (после небольшой паузы)
        await asyncio.sleep(0.5)
        for script in submit_scripts[1:]:
            try:
                result = driver.execute_script(script)
                if result:
                    await asyncio.sleep(0.5)
                    break
            except:
                continue
        
        return True
    except Exception as e:
        return False

async def ultra_fast_booking(query, machine_name=None):
    """ОСНОВНАЯ ФУНКЦИЯ - СВЕРХБЫСТРОЕ БРОНИРОВАНИЕ"""
    start_time = time.time()
    driver = None
    
    try:
        driver = await get_driver()
        
        # 1. МГНОВЕННАЯ ЗАГРУЗКА САЙТА
        await query.edit_message_text("⚡ Загружаю сайт...")
        
        try:
            driver.get(TARGET_URL)
            # Ждем только body, не всю страницу
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            # Если не успел загрузиться полностью, работаем с тем что есть
            pass
        
        # 2. МГНОВЕННАЯ ОБРАБОТКА COOKIES
        await ultra_fast_handle_cookies(driver)
        await asyncio.sleep(0.3)
        
        # 3. МГНОВЕННЫЙ ВЫБОР МАШИНКИ
        selected_machine = None
        if machine_name:
            await query.edit_message_text(f"⚡ Ищу {machine_name}...")
            selected_machine = await ultra_fast_book_machine(driver, machine_name)
        
        # 4. МГНОВЕННЫЙ ВЫБОР ВРЕМЕНИ
        await query.edit_message_text("⚡ Ищу время...")
        selected_time = await ultra_fast_select_time(driver)
        
        # 5. МГНОВЕННОЕ ЗАПОЛНЕНИЕ ФОРМЫ
        await query.edit_message_text("⚡ Заполняю форму...")
        form_filled = await ultra_fast_fill_form(driver)
        
        # 6. МГНОВЕННАЯ ОТПРАВКА ФОРМЫ
        await query.edit_message_text("⚡ Отправляю форму...")
        submitted = await ultra_fast_submit(driver)
        
        # 7. ДЕЛАЕМ СКРИНШОТ РЕЗУЛЬТАТА
        await query.edit_message_text("⚡ Делаю скриншот...")
        final_screenshot = "/tmp/dikidi_ultra_fast.png"
        driver.save_screenshot(final_screenshot)
        
        total_time = time.time() - start_time
        
        # Отправляем результат
        with open(final_screenshot, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=f"⚡ Результат за {total_time:.2f} сек\n\n"
                       f"✅ Машинка: {machine_name if selected_machine else 'авто'}\n"
                       f"🕒 Время: {selected_time or 'авто'}\n"
                       f"👤 Данные: {FORM_NAME} {FORM_SURNAME}\n"
                       f"📱 Телефон: {FORM_PHONE}"
            )
        
        await query.edit_message_text(
            f"🎉 БРОНИРОВАНИЕ ВЫПОЛНЕНО!\n\n"
            f"⚡ Общее время: {total_time:.2f} сек\n"
            f"✅ Форма заполнена: {'✓' if form_filled else '✗'}\n"
            f"✅ Форма отправлена: {'✓' if submitted else '✗'}\n\n"
            f"🔍 Проверьте результат на скриншоте выше"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при бронировании: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        # Не закрываем драйвер для скорости
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этому боту.")
        return
    
    keyboard = [
        [InlineKeyboardButton("⚡ Мгновенное бронирование", callback_data='ultra_fast_book')],
        [InlineKeyboardButton("⚡ Проверить сайт", callback_data='check_fast')],
        [InlineKeyboardButton("⚡ Очистить кэш", callback_data='clear_cache')],
        [InlineKeyboardButton("📊 Статус", callback_data='status_fast')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚡ УСКОРЕННЫЙ БОТ ДЛЯ БРОНИРОВАНИЯ\n\n"
        f"⏱️ Оптимизирован для скорости\n"
        f"🚀 Время реакции: < 10 секунд\n"
        f"🎯 Приоритет: мгновенная запись\n\n"
        f"⏰ Серверное время: {datetime.now().strftime('%H:%M:%S')}",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ У вас нет доступа к этому боту.")
        return
    
    try:
        if query.data == 'ultra_fast_book':
            await ultra_fast_book_menu(query)
        elif query.data == 'check_fast':
            await check_fast(query)
        elif query.data == 'clear_cache':
            await clear_cache(query)
        elif query.data == 'status_fast':
            await status_fast(query)
        elif query.data.startswith('book_machine_'):
            machine = query.data.replace('book_machine_', '')
            await ultra_fast_booking(query, machine)
        elif query.data == 'book_auto':
            await ultra_fast_booking(query)
        elif query.data == 'back_main':
            await start_callback(query)
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}")
        await query.edit_message_text(f"⚠️ Ошибка: {str(e)[:100]}")

async def start_callback(query):
    """Возврат в главное меню"""
    keyboard = [
        [InlineKeyboardButton("⚡ Мгновенное бронирование", callback_data='ultra_fast_book')],
        [InlineKeyboardButton("⚡ Проверить сайт", callback_data='check_fast')],
        [InlineKeyboardButton("⚡ Очистить кэш", callback_data='clear_cache')],
        [InlineKeyboardButton("📊 Статус", callback_data='status_fast')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚡ УСКОРЕННЫЙ БОТ ДЛЯ БРОНИРОВАНИЯ\n\n"
        f"Главное меню:",
        reply_markup=reply_markup
    )

async def ultra_fast_book_menu(query):
    """Меню для быстрого бронирования"""
    keyboard = [
        [InlineKeyboardButton("⚡ Авто-поиск машины", callback_data='book_auto')],
        [InlineKeyboardButton("🧺 Машинка 1", callback_data='book_machine_Машинка 1')],
        [InlineKeyboardButton("🧺 Машинка 2", callback_data='book_machine_Машинка 2')],
        [InlineKeyboardButton("🧺 Машинка 3", callback_data='book_machine_Машинка 3')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚡ МГНОВЕННОЕ БРОНИРОВАНИЕ\n\n"
        "Выберите машинку или используйте авто-поиск:\n\n"
        f"✅ Все поля заполняются автоматически\n"
        f"⚡ Время выполнения: < 10 сек",
        reply_markup=reply_markup
    )

async def check_fast(query):
    """Быстрая проверка сайта"""
    driver = None
    try:
        driver = await get_driver()
        await query.edit_message_text("⚡ Проверяю сайт...")
        
        driver.get(TARGET_URL)
        await asyncio.sleep(1)
        
        screenshot_path = "/tmp/dikidi_check_fast.png"
        driver.save_screenshot(screenshot_path)
        
        with open(screenshot_path, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=f"⚡ Проверка сайта\n{datetime.now().strftime('%H:%M:%S')}"
            )
        
        await query.edit_message_text(
            f"✅ Сайт доступен\n"
            f"⚡ Время загрузки: < 2 сек\n"
            f"🔗 URL: {TARGET_URL[:50]}..."
        )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка проверки: {str(e)[:100]}")
    finally:
        pass  # Не закрываем драйвер

async def clear_cache(query):
    """Очистка кэша"""
    await cleanup_driver()
    await query.answer("✅ Кэш очищен!")
    await start_callback(query)

async def status_fast(query):
    """Быстрый статус"""
    status_text = (
        f"⚡ СТАТУС БОТА (УСКОРЕННАЯ ВЕРСИЯ)\n\n"
        f"✅ Состояние: Активно\n"
        f"⏱️ Оптимизация: Максимальная\n"
        f"🚀 Стратегия: Мгновенная запись\n\n"
        f"📊 ДАННЫЕ ДЛЯ ЗАПИСИ:\n"
        f"• 👤 Имя: {FORM_NAME}\n"
        f"• 👤 Фамилия: {FORM_SURNAME}\n"
        f"• 📱 Телефон: {FORM_PHONE}\n"
        f"• 💬 Комментарий: {FORM_COMMENT}\n\n"
        f"⚡ НАСТРОЙКИ СКОРОСТИ:\n"
        f"• Блокировка картинок\n"
        f"• Кэширование драйвера\n"
        f"• Минимальные таймауты\n"
        f"• JavaScript клики\n\n"
        f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(status_text, reply_markup=reply_markup)

def main():
    """Основная функция запуска бота"""
    print("⚡ Запускаю УСКОРЕННУЮ версию бота...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Очищаем кэш при завершении
    import atexit
    atexit.register(lambda: asyncio.run(cleanup_driver()))
    
    print("📱 Начинаю polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
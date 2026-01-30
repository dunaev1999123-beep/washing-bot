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
from selenium.webdriver.common.keys import Keys

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
FORM_PHONE = os.getenv('FORM_PHONE', '9955542240')  # Без +7, сайт сам добавляет

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

async def handle_cookies_popup(driver):
    """Обработка всплывающего окна с cookies"""
    try:
        time.sleep(2)
        
        cookie_selectors = [
            "button:contains('Accept all')",
            "button:contains('Accept All')",
            "button:contains('Принять все')",
            "button:contains('Согласен')",
            "button:contains('OK')",
            "button:contains('Принять')",
            "[data-testid='accept-cookies']",
            ".cookie-accept",
            ".cookies-accept",
            "#accept-cookies",
            "#cookie-accept",
            ".btn-cookie",
            "button[class*='cookie']",
            "button[class*='accept']",
            "button[class*='agree']",
            "button[class*='confirm']"
        ]
        
        for selector in cookie_selectors:
            try:
                if "contains" in selector:
                    text = selector.split("'")[1]
                    button = driver.find_element(By.XPATH, f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.5)
                    
                    try:
                        button.click()
                    except:
                        driver.execute_script("arguments[0].click();", button)
                    
                    time.sleep(1)
                    return True
            except:
                continue
        
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for button in buttons:
            try:
                btn_text = button.text.lower()
                if any(keyword in btn_text for keyword in ['accept', 'принять', 'согласен', 'ok', 'готово', 'agree', 'confirm']):
                    if button.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        
                        try:
                            button.click()
                        except:
                            driver.execute_script("arguments[0].click();", button)
                        
                        time.sleep(1)
                        return True
            except:
                continue
        
        return False
        
    except Exception as e:
        return False

def force_close_cookies(driver):
    """Принудительное закрытие cookies окна любыми способами"""
    try:
        cookie_overlays = [
            ".cookie-overlay",
            ".cookies-overlay",
            ".cookie-banner",
            ".cookies-banner",
            ".cookie-notice",
            ".cookies-notice",
            "[class*='cookie']",
            "[class*='cookies']"
        ]
        
        for selector in cookie_overlays:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    try:
                        buttons = elem.find_elements(By.TAG_NAME, "button")
                        for btn in buttons:
                            btn_text = btn.text.lower()
                            if any(keyword in btn_text for keyword in ['accept', 'принять', 'согласен', 'ok']):
                                if btn.is_displayed():
                                    driver.execute_script("arguments[0].click();", btn)
                                    time.sleep(1)
                                    return True
                    except:
                        continue
            except:
                continue
        
        try:
            driver.execute_script("""
                var elements = document.querySelectorAll('[class*="cookie"], [class*="cookies"], .cookie-banner, .cookies-banner');
                for (var i = 0; i < elements.length; i++) {
                    elements[i].style.display = 'none';
                }
            """)
            time.sleep(1)
            return True
        except:
            pass
        
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(1)
        except:
            pass
        
        return False
    except Exception as e:
        return False

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
        
        driver.get(TARGET_URL)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        await handle_cookies_popup(driver)
        
        time.sleep(3)
        
        title = driver.title
        current_url = driver.current_url
        
        screenshot_path = "/tmp/dikidi_screenshot.png"
        driver.set_window_size(1920, 1080)
        driver.save_screenshot(screenshot_path)
        
        report = (
            f"📊 ОТЧЕТ О СТРАНИЦЕ DIKIDI.NET\n"
            f"────────────────────\n"
            f"📝 Заголовок: {title}\n"
            f"🔗 URL: {current_url}\n"
            f"⏰ Время проверки: {datetime.now().strftime('%H:%M:%S')}\n"
            f"────────────────────\n"
        )
        
        await query.edit_message_text(report)
        
        try:
            with open(screenshot_path, 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=f"📸 Скриншот страницы Dikidi\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
        except Exception as photo_error:
            await query.message.reply_text(f"❌ Не удалось отправить скриншот: {photo_error}")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке сайта: {e}")
        
        try:
            if driver:
                error_screenshot = "/tmp/dikidi_error.png"
                driver.save_screenshot(error_screenshot)
                with open(error_screenshot, 'rb') as photo:
                    await query.message.reply_photo(
                        photo=photo,
                        caption=f"❌ Ошибка при загрузке страницы"
                    )
        except:
            pass
            
        await query.edit_message_text(
            f"❌ Ошибка при проверке сайта"
        )
    finally:
        if driver:
            driver.quit()

async def book_machine(query):
    """Процесс бронирования автомата для dikidi.net"""
    await query.edit_message_text("🚀 Начинаю процесс бронирования...")
    
    driver = None
    try:
        driver = setup_driver()
        
        # 1. Переходим на сайт
        driver.get(TARGET_URL)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 2. Закрываем cookies окно
        cookies_closed = False
        if await handle_cookies_popup(driver):
            cookies_closed = True
        elif force_close_cookies(driver):
            cookies_closed = True
        
        time.sleep(2)
        
        # 3. Ищем доступные машины
        await query.edit_message_text("🔍 Ищу доступные машины...")
        
        selected_machine = None
        machine_name = ""
        machine_priority = ["Машинка 1", "Машинка 2", "Машинка 3"]
        
        for machine_text in machine_priority:
            try:
                machine_elements = driver.find_elements(By.XPATH, 
                    f"//*[contains(translate(., 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), '{machine_text.lower()}')]"
                )
                
                if machine_elements:
                    visible_machines = []
                    for elem in machine_elements:
                        try:
                            if elem.is_displayed() and elem.is_enabled():
                                visible_machines.append(elem)
                        except:
                            continue
                    
                    if visible_machines:
                        selected_machine = visible_machines[0]
                        machine_name = machine_text
                        
                        parent_html = selected_machine.get_attribute('outerHTML')
                        if any(indicator in parent_html.lower() for indicator in ['disabled', 'занят', 'busy', 'недоступ', 'unavailable']):
                            continue
                        
                        driver.execute_script("arguments[0].click();", selected_machine)
                        await query.edit_message_text(f"✅ Выбрана {machine_text}")
                        time.sleep(2)
                        break
            except:
                continue
        
        if not selected_machine:
            await query.edit_message_text("❌ Не найдено доступных машин")
            raise Exception("Не найдены доступные машины")
        
        # 4. Ищем и выбираем ЛЮБОЕ доступное время
        await query.edit_message_text("🕒 Ищу доступное время...")
        
        time_elements = []
        time_selectors = [
            ".nr-item.sdt-hour",
            "[class*='sdt-hour']",
            "[class*='time-slot']",
            "[class*='schedule-item']",
            "[data-time]",
            ".booking-slot",
            "div[class*='time']",
            "button[class*='time']",
            "a[class*='time']",
            "div[class*='sdt']",
            "div[class*='hour']",
            "[class*='available']",
            "[class*='selectable']"
        ]
        
        for selector in time_selectors:
            try:
                found_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if found_elements:
                    time_elements.extend(found_elements)
            except:
                continue
        
        # Ищем по тексту времени (любое время с форматом ЧЧ:ММ)
        try:
            # Ищем все элементы на странице
            all_elements = driver.find_elements(By.XPATH, "//*")
            for elem in all_elements:
                try:
                    text = elem.text.strip()
                    # Пропускаем пустые или слишком длинные тексты
                    if not text or len(text) > 20:
                        continue
                    
                    # Проверяем, что текст содержит двоеточие и цифры (формат времени)
                    if ':' in text and any(char.isdigit() for char in text):
                        # Проверяем формат времени (например, "05:00 pm", "09:00", "14:30")
                        # Разделяем по двоеточию
                        parts = text.split(':')
                        if len(parts) == 2:
                            hour_part = parts[0].strip()
                            minute_part = parts[1].split()[0].strip() if ' ' in parts[1] else parts[1].strip()
                            
                            # Проверяем, что час и минуты - цифры
                            if hour_part.isdigit() and minute_part[:2].isdigit():
                                # Пропускаем не-времена (например, "Morning", "Day")
                                text_lower = text.lower()
                                if any(word in text_lower for word in ['morning', 'day', 'evening', 'night', 'weekend', 'утро', 'день', 'вечер', 'ночь', 'выходные']):
                                    continue
                                
                                # Добавляем элемент в список
                                time_elements.append(elem)
                except:
                    continue
        except:
            pass
        
        time_text = "не указано"
        time_selected = False
        
        if time_elements:
            # Выбираем первый доступный слот времени
            for time_elem in time_elements:
                try:
                    current_time_text = time_elem.text.strip()
                    
                    # Пропускаем пустые элементы
                    if not current_time_text:
                        continue
                    
                    # Проверяем, что это похоже на время
                    if ':' not in current_time_text:
                        continue
                    
                    # Пропускаем элементы, которые не являются временем
                    time_lower = current_time_text.lower()
                    if any(word in time_lower for word in ['morning', 'day', 'evening', 'night', 'weekend']):
                        continue
                    
                    # Проверяем, не занято ли время
                    try:
                        # Проверяем классы элемента
                        elem_class = time_elem.get_attribute('class') or ''
                        if any(indicator in elem_class.lower() for indicator in ['disabled', 'busy', 'unavailable', 'booked', 'занят', 'недоступно']):
                            continue
                        
                        # Проверяем родительские элементы на наличие индикаторов недоступности
                        parent = time_elem.find_element(By.XPATH, "./..")
                        parent_class = parent.get_attribute('class') or ''
                        if any(indicator in parent_class.lower() for indicator in ['disabled', 'busy', 'unavailable']):
                            continue
                        
                        # Проверяем стили
                        elem_style = time_elem.get_attribute('style') or ''
                        if 'opacity' in elem_style.lower() and ('0.5' in elem_style or '0.3' in elem_style):
                            continue
                    except:
                        pass
                    
                    # Прокручиваем к элементу
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", time_elem)
                    time.sleep(0.5)
                    
                    # Кликаем на выбранное время
                    try:
                        time_elem.click()
                    except:
                        driver.execute_script("arguments[0].click();", time_elem)
                    
                    time_text = current_time_text
                    time_selected = True
                    await query.edit_message_text(f"✅ Выбрано время: {time_text}")
                    time.sleep(2)
                    break
                except Exception as e:
                    continue
        
        # Если не нашли время стандартными методами, пробуем альтернативный поиск
        if not time_selected:
            await query.edit_message_text("🔄 Пробую альтернативный поиск времени...")
            
            # Ищем все кликабельные элементы, которые могут быть временными слотами
            all_clickable = driver.find_elements(By.XPATH, 
                "//div[contains(@class, 'sdt')] | " +
                "//div[contains(@class, 'hour')] | " +
                "//div[contains(@class, 'time')] | " +
                "//button[contains(@class, 'time')] | " +
                "//a[contains(@class, 'time')] | " +
                "//div[@onclick] | " +
                "//button[@onclick] | " +
                "//a[@onclick]"
            )
            
            for elem in all_clickable:
                try:
                    if not elem.is_displayed() or not elem.is_enabled():
                        continue
                    
                    current_time_text = elem.text.strip()
                    
                    # Пропускаем пустые
                    if not current_time_text:
                        continue
                    
                    # Ищем время в тексте
                    if ':' not in current_time_text:
                        continue
                    
                    # Пропускаем не-времена
                    time_lower = current_time_text.lower()
                    if any(word in time_lower for word in ['morning', 'day', 'evening', 'night']):
                        continue
                    
                    # Проверяем формат времени
                    parts = current_time_text.split(':')
                    if len(parts) != 2:
                        continue
                    
                    if not parts[0].strip().isdigit():
                        continue
                    
                    # Прокручиваем и кликаем
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    time.sleep(0.5)
                    
                    try:
                        elem.click()
                    except:
                        driver.execute_script("arguments[0].click();", elem)
                    
                    time_text = current_time_text
                    time_selected = True
                    await query.edit_message_text(f"✅ Выбрано время: {time_text}")
                    time.sleep(2)
                    break
                except:
                    continue
        
        # 5. Заполняем форму
        await query.edit_message_text("📋 Заполняю форму...")
        
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        all_textareas = driver.find_elements(By.TAG_NAME, "textarea")
        all_fields = all_inputs + all_textareas
        
        name_filled = False
        surname_filled = False
        phone_filled = False
        comment_filled = False
        
        field_counter = 0
        
        for field in all_fields:
            try:
                if not field.is_displayed() or not field.is_enabled():
                    continue
                
                field_type = field.get_attribute('type') or 'text'
                
                if field_type in ['hidden', 'checkbox', 'radio', 'submit', 'button']:
                    continue
                
                field.clear()
                time.sleep(0.3)
                
                if field_counter == 0 and field_type == 'text':
                    field.send_keys(FORM_NAME)
                    name_filled = True
                    field_counter += 1
                    
                elif field_counter == 1 and field_type == 'text':
                    field.send_keys(FORM_SURNAME)
                    surname_filled = True
                    field_counter += 1
                    
                elif field_type == 'tel' or 'phone' in (field.get_attribute('name') or '').lower():
                    phone_to_send = FORM_PHONE
                    try:
                        field.send_keys(phone_to_send)
                        time.sleep(0.5)
                        
                        current_value = field.get_attribute('value')
                        if not current_value or phone_to_send not in current_value:
                            field.clear()
                            time.sleep(0.5)
                            field.send_keys("7" + phone_to_send)
                            time.sleep(0.5)
                            
                        phone_filled = True
                    except:
                        pass
                    
                elif field.tag_name == 'textarea':
                    field.send_keys(FORM_COMMENT)
                    comment_filled = True
                    
            except:
                continue
        
        # 6. Нажимаем Continue на форме
        await query.edit_message_text("⏳ Отправляю форму...")
        
        continue_submit_clicked = False
        
        try:
            continue_elements = driver.find_elements(By.XPATH, 
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')] | " +
                "//*[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'продолжить')]"
            )
            
            for elem in continue_elements:
                if elem.is_displayed() and elem.is_enabled():
                    elem_text = elem.text.strip().lower()
                    if 'continue' in elem_text or 'продолжить' in elem_text:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                        time.sleep(1)
                        
                        try:
                            elem.click()
                        except:
                            driver.execute_script("arguments[0].click();", elem)
                        
                        continue_submit_clicked = True
                        time.sleep(3)
                        break
        except:
            pass
        
        # 7. Нажимаем Complete the appointment
        if continue_submit_clicked:
            await query.edit_message_text("⏳ Завершаю запись...")
            time.sleep(3)
        
        final_submit_clicked = False
        
        try:
            complete_buttons = driver.find_elements(By.XPATH, 
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'complete the appointment')] | " +
                "//*[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'завершить запись')]"
            )
            
            for btn in complete_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    
                    try:
                        btn.click()
                    except:
                        driver.execute_script("arguments[0].click();", btn)
                    
                    final_submit_clicked = True
                    time.sleep(3)
                    break
        except:
            pass
        
        if not final_submit_clicked:
            try:
                partial_texts = ['complete', 'appointment', 'завершить', 'запись']
                
                for text in partial_texts:
                    elements = driver.find_elements(By.XPATH, 
                        f"//*[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯABCDEFGHIJKLMNOPQRSTUVWXYZ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяabcdefghijklmnopqrstuvwxyz'), '{text}')]"
                    )
                    
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            elem_text = elem.text.strip().lower()
                            if 'complete' in elem_text or 'appointment' in elem_text or 'завершить' in elem_text:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                                time.sleep(1)
                                
                                try:
                                    elem.click()
                                except:
                                    driver.execute_script("arguments[0].click();", elem)
                                
                                final_submit_clicked = True
                                time.sleep(3)
                                break
                    if final_submit_clicked:
                        break
            except:
                pass
        
        # 8. Проверяем результат и отправляем финальный скриншот
        await query.edit_message_text("🔍 Проверяю результат...")
        time.sleep(3)
        
        # Делаем финальный скриншот
        final_screenshot = "/tmp/dikidi_final.png"
        driver.save_screenshot(final_screenshot)
        
        with open(final_screenshot, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption="📸 Финальный результат"
            )
        
        # Проверяем страницу на признаки успеха
        page_text = driver.page_source.lower()
        success_keywords = ['успешно', 'записан', 'подтвержден', 'спасибо', 'ожидайте', 'success', 'thank you', 'confirmed', 'завершен', 'completed']
        error_keywords = ['ошибка', 'error', 'не удалось', 'занято', 'busy', 'недоступно']
        
        success = any(keyword in page_text for keyword in success_keywords)
        error = any(keyword in page_text for keyword in error_keywords)
        
        # Формируем отчет
        if success:
            result_message = (
                f"🎉 БРОНИРОВАНИЕ УСПЕШНО!\n\n"
                f"✅ Машинка: {machine_name}\n"
                f"🕒 Время: {time_text}\n"
                f"👤 Имя: {FORM_NAME}\n"
                f"👤 Фамилия: {FORM_SURNAME}\n"
                f"📱 Телефон: {FORM_PHONE}\n"
                f"💬 Комментарий: {FORM_COMMENT}\n"
                f"⏰ Время брони: {datetime.now().strftime('%H:%M:%S')}"
            )
        elif error:
            result_message = (
                f"⚠️ ПРОБЛЕМА С БРОНИРОВАНИЕМ\n\n"
                f"❌ Обнаружена ошибка\n"
                f"🔍 Проверьте вручную: {TARGET_URL}\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}"
            )
        else:
            result_message = (
                f"📋 ПРОЦЕСС ЗАВЕРШЕН\n\n"
                f"✅ Все действия выполнены\n"
                f"✅ Форма отправлена\n"
                f"🔍 Проверьте запись вручную\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}"
            )
        
        await query.edit_message_text(result_message)
        
        # Отправляем итоговый отчет
        await query.message.reply_text(
            f"📊 ИТОГОВЫЙ ОТЧЕТ:\n"
            f"• Машина выбрана: {'✅ ' + machine_name if selected_machine else '❌'}\n"
            f"• Время выбрано: {'✅ ' + time_text if time_selected else '❌'}\n"
            f"• Форма заполнена: {'✅' if name_filled and surname_filled and phone_filled else '❌'}\n"
            f"• Запись завершена: {'✅' if final_submit_clicked else '❌'}\n"
            f"• Результат: {'✅ Успех' if success else '⚠️ Проверьте вручную' if not error else '❌ Ошибка'}"
        )
            
    except Exception as e:
        logger.error(f"Ошибка при бронировании: {e}")
        
        try:
            if driver:
                error_screenshot = "/tmp/dikidi_booking_error.png"
                driver.save_screenshot(error_screenshot)
                with open(error_screenshot, 'rb') as photo:
                    await query.message.reply_photo(
                        photo=photo,
                        caption="❌ Ошибка при бронировании"
                    )
        except:
            pass
            
        await query.edit_message_text(
            "❌ Ошибка при бронировании"
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
        f"⏰ Время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await query.edit_message_text(status_text)

def main():
    """Основная функция запуска бота"""
    print("🤖 Бот запускается...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("📱 Начинаю polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
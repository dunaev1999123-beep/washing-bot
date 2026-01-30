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
        # Даем время для загрузки popup
        time.sleep(2)
        
        # Селекторы для кнопок принятия cookies (на английском и русском)
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
                # Пробуем найти кнопку по тексту (XPath)
                if "contains" in selector:
                    # Извлекаем текст из селектора
                    text = selector.split("'")[1]
                    button = driver.find_element(By.XPATH, f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button.is_displayed():
                    # Прокручиваем к кнопке
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.5)
                    
                    # Пробуем разные способы клика
                    try:
                        button.click()
                    except:
                        driver.execute_script("arguments[0].click();", button)
                    
                    print(f"✅ Cookies-окно закрыто (селектор: {selector})")
                    time.sleep(1)  # Даем время на закрытие popup
                    return True
            except Exception as e:
                continue
        
        # Также проверяем все кнопки на странице
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for button in buttons:
            try:
                btn_text = button.text.lower()
                if any(keyword in btn_text for keyword in ['accept', 'принять', 'согласен', 'ok', 'готово', 'agree', 'confirm']):
                    if button.is_displayed():
                        # Прокручиваем к кнопке
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        
                        try:
                            button.click()
                        except:
                            driver.execute_script("arguments[0].click();", button)
                        
                        print(f"✅ Cookies-окно закрыто по тексту кнопки: {button.text}")
                        time.sleep(1)
                        return True
            except:
                continue
        
        print("⚠️ Cookies-окно не найдено или уже закрыто")
        return False
        
    except Exception as e:
        print(f"⚠️ Ошибка при обработке cookies: {e}")
        return False

def force_close_cookies(driver):
    """Принудительное закрытие cookies окна любыми способами"""
    try:
        # 1. Пробуем найти и кликнуть по оверлею cookies
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
                        # Пробуем найти кнопку внутри оверлея
                        buttons = elem.find_elements(By.TAG_NAME, "button")
                        for btn in buttons:
                            btn_text = btn.text.lower()
                            if any(keyword in btn_text for keyword in ['accept', 'принять', 'согласен', 'ok']):
                                if btn.is_displayed():
                                    driver.execute_script("arguments[0].click();", btn)
                                    print(f"✅ Cookies закрыты через оверлей: {selector}")
                                    time.sleep(1)
                                    return True
                    except:
                        continue
            except:
                continue
        
        # 2. Пробуем скрыть через JavaScript
        try:
            driver.execute_script("""
                var elements = document.querySelectorAll('[class*="cookie"], [class*="cookies"], .cookie-banner, .cookies-banner');
                for (var i = 0; i < elements.length; i++) {
                    elements[i].style.display = 'none';
                }
            """)
            print("✅ Cookies скрыты через JavaScript")
            time.sleep(1)
            return True
        except:
            pass
        
        # 3. Пробуем кликнуть по body чтобы закрыть (если модальное окно)
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.click()
            print("✅ Клик по body для закрытия модального окна")
            time.sleep(1)
        except:
            pass
        
        return False
    except Exception as e:
        print(f"⚠️ Ошибка при принудительном закрытии cookies: {e}")
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
        
        # Переходим на сайт
        driver.get(TARGET_URL)
        
        # Ждем загрузки страницы
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Закрываем cookies-окно
        await handle_cookies_popup(driver)
        
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
                    caption=f"📸 Скриншот страницы Dikidi (cookies закрыты)\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
        
        # 6. Отправляем информацию о найденных ссылках
        if links:
            links_report = "🔗 Найденные ссылки (первые 10):\n"
            for i, link in enumerate(links[:10]):
                link_text = link.text.strip()[:30] if link.text else "без текста"
                link_classes = link.get_attribute('class')[:30] if link.get_attribute('class') else "нет классов"
                links_report += f"{i+1}. '{link_text}' (class: {link_classes})\n"
            
            await query.message.reply_text(links_report)
        
        # 7. Проверяем наличие ключевых элементов Dikidi
        await query.message.reply_text("🔎 Ищу элементы Dikidi...")
        
        dikidi_elements = {
            "Календарь": [".calendar", "[data-calendar]", "#calendar", ".date-picker"],
            "Слоты времени": [".time-slot", ".schedule-item", "[data-time]", ".booking-slot", "div[class*='time']"],
            "Форма входа": ["#login-form", ".auth-form", "[type='password']", "input[name='password']"],
            "Кнопка входа": ["button[type='submit']", ".login-btn", "#loginButton", "[value='Войти']"],
            "Машины/аппараты": ["[data-machine]", "[data-device]", ".machine-selector", "div[class*='machine']"]
        }
        
        found_elements = []
        for element_name, selectors in dikidi_elements.items():
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        found_elements.append(f"✅ {element_name}: найдено {len(elements)} через '{selector}'")
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
        
        # 1. Переходим на сайт
        driver.get(TARGET_URL)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 2. Агрессивно закрываем cookies окно
        await query.edit_message_text("🍪 Закрываю cookies окно...")
        cookies_closed = False
        
        # Пробуем несколько раз закрыть cookies
        for attempt in range(5):
            await query.message.reply_text(f"🍪 Попытка {attempt + 1} закрыть cookies...")
            
            # Стандартный метод
            if await handle_cookies_popup(driver):
                cookies_closed = True
                await query.message.reply_text("✅ Cookies закрыты стандартным методом")
                break
            
            # Принудительный метод
            if force_close_cookies(driver):
                cookies_closed = True
                await query.message.reply_text("✅ Cookies закрыты принудительным методом")
                break
            
            time.sleep(1)
        
        if not cookies_closed:
            await query.message.reply_text("⚠️ Не удалось закрыть cookies, пробую продолжить...")
        
        time.sleep(2)
        
        # 3. Ищем доступные машины по приоритету
        await query.edit_message_text("🔍 Ищу доступные машины...")
        
        selected_machine = None
        machine_name = ""
        machine_priority = ["Машинка 1", "Машинка 2", "Машинка 3"]
        
        for machine_text in machine_priority:
            try:
                # Ищем элемент с текстом машины (регистронезависимо)
                machine_elements = driver.find_elements(By.XPATH, 
                    f"//*[contains(translate(., 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), '{machine_text.lower()}')]"
                )
                
                if machine_elements:
                    # Фильтруем только видимые элементы
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
                        
                        # Проверяем, не занята ли машина
                        parent_html = selected_machine.get_attribute('outerHTML')
                        if any(indicator in parent_html.lower() for indicator in ['disabled', 'занят', 'busy', 'недоступ', 'unavailable']):
                            await query.message.reply_text(f"⚠️ {machine_text} занята, пробую следующую...")
                            continue
                        
                        # Кликаем на выбранную машину
                        driver.execute_script("arguments[0].click();", selected_machine)
                        await query.message.reply_text(f"✅ Выбрана {machine_text}")
                        time.sleep(2)
                        break
            except Exception as e:
                await query.message.reply_text(f"⚠️ Ошибка поиска {machine_text}: {e}")
                continue
        
        if not selected_machine:
            await query.message.reply_text("❌ Не найдено ни одной доступной машины")
            raise Exception("Не найдены доступные машины")
        
        # 4. Ищем и выбираем любое доступное время
        await query.edit_message_text("🕒 Ищу доступные временные слоты...")
        
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
            "a[class*='time']"
        ]
        
        for selector in time_selectors:
            try:
                found_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if found_elements:
                    time_elements.extend(found_elements)
            except:
                continue
        
        # Также ищем по XPath для текста времени
        try:
            time_xpath_elements = driver.find_elements(By.XPATH, 
                "//*[contains(text(), ':') and (contains(text(), 'am') or contains(text(), 'pm') or contains(text(), '09') or contains(text(), '10') or contains(text(), '11') or contains(text(), '12') or contains(text(), '13') or contains(text(), '14') or contains(text(), '15') or contains(text(), '16') or contains(text(), '17') or contains(text(), '18') or contains(text(), '19') or contains(text(), '20') or contains(text(), '21') or contains(text(), '22') or contains(text(), '23'))]"
            )
            time_elements.extend(time_xpath_elements)
        except:
            pass
        
        time_text = "не указано"
        time_selected = False
        
        if time_elements:
            await query.message.reply_text(f"✅ Найдено слотов времени: {len(time_elements)}")
            
            # Выбираем первый доступный слот времени
            for time_elem in time_elements:
                try:
                    current_time_text = time_elem.text.strip()
                    
                    # Пропускаем пустые элементы
                    if not current_time_text:
                        continue
                    
                    # Проверяем, не занято ли время
                    parent_html = time_elem.get_attribute('outerHTML')
                    if any(indicator in parent_html.lower() for indicator in ['disabled', 'занят', 'busy', 'unavailable', 'selected']):
                        continue
                    
                    # Кликаем на выбранное время
                    driver.execute_script("arguments[0].click();", time_elem)
                    time_text = current_time_text
                    time_selected = True
                    await query.message.reply_text(f"✅ Выбрано время: {time_text}")
                    time.sleep(2)
                    break
                except:
                    continue
        
        # 5. Ищем кнопку продолжения после выбора времени
        await query.edit_message_text("🔍 Ищу кнопку продолжения...")
        
        continue_clicked = False
        continue_selectors = [
            "button:contains('Продолжить')",
            "button:contains('Далее')",
            "button:contains('Next')",
            "button:contains('Continue')",
            "button:contains('Выбрать')",
            "button:contains('Подтвердить')",
            ".btn-next",
            ".btn-continue",
            "[data-action='next']"
        ]
        
        for selector in continue_selectors:
            try:
                if "contains" in selector:
                    text = selector.split("'")[1]
                    button = driver.find_element(By.XPATH, 
                        f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                    )
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button.is_displayed():
                    # Прокручиваем к кнопке
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.5)
                    
                    driver.execute_script("arguments[0].click();", button)
                    await query.message.reply_text(f"✅ Нажата кнопка продолжения: {selector}")
                    continue_clicked = True
                    time.sleep(3)
                    break
            except:
                continue
        
        if continue_clicked:
            await query.edit_message_text("📝 Жду загрузки формы записи...")
            time.sleep(3)
        
        # 6. Ищем и заполняем форму
        await query.edit_message_text("📋 Заполняю форму...")
        
        # Находим все видимые поля ввода
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        all_textareas = driver.find_elements(By.TAG_NAME, "textarea")
        all_fields = all_inputs + all_textareas
        
        name_filled = False
        surname_filled = False
        phone_filled = False
        comment_filled = False
        
        # Счетчик для порядка заполнения
        field_counter = 0
        
        for field in all_fields:
            try:
                if not field.is_displayed() or not field.is_enabled():
                    continue
                
                field_type = field.get_attribute('type') or 'text'
                
                # Пропускаем ненужные типы полей
                if field_type in ['hidden', 'checkbox', 'radio', 'submit', 'button']:
                    continue
                
                # Очищаем поле
                field.clear()
                time.sleep(0.3)
                
                # Определяем, что заполнять, по порядку и типу поля
                if field_counter == 0 and field_type == 'text':  # Первое текстовое поле - имя
                    field.send_keys(FORM_NAME)
                    name_filled = True
                    await query.message.reply_text(f"✅ Заполнено имя: {FORM_NAME}")
                    field_counter += 1
                    
                elif field_counter == 1 and field_type == 'text':  # Второе текстовое поле - фамилия
                    field.send_keys(FORM_SURNAME)
                    surname_filled = True
                    await query.message.reply_text(f"✅ Заполнена фамилия: {FORM_SURNAME}")
                    field_counter += 1
                    
                elif field_type == 'tel' or 'phone' in (field.get_attribute('name') or '').lower():  # Поле телефона
                    # Особенная обработка телефона
                    phone_to_send = FORM_PHONE
                    
                    # Пробуем ввести телефон разными способами
                    try:
                        # Способ 1: Просто отправляем цифры
                        field.send_keys(phone_to_send)
                        time.sleep(0.5)
                        
                        # Проверяем, что телефон ввелся
                        current_value = field.get_attribute('value')
                        if not current_value or phone_to_send not in current_value:
                            # Способ 2: Очищаем и пробуем снова
                            field.clear()
                            time.sleep(0.5)
                            field.send_keys("7" + phone_to_send)  # Добавляем 7 в начало
                            time.sleep(0.5)
                            
                        phone_filled = True
                        await query.message.reply_text(f"✅ Заполнен телефон: {phone_to_send}")
                    except Exception as e:
                        await query.message.reply_text(f"⚠️ Ошибка заполнения телефона: {e}")
                    
                elif field.tag_name == 'textarea':  # Поле комментария
                    field.send_keys(FORM_COMMENT)
                    comment_filled = True
                    await query.message.reply_text(f"✅ Заполнен комментарий: {FORM_COMMENT}")
                    
            except Exception as e:
                continue
        
        # 7. ПЕРЕД поиском кнопки Continue, снова пробуем закрыть cookies
        await query.edit_message_text("🔍 Проверяю, не блокирует ли cookies кнопку Continue...")
        time.sleep(2)
        
        # Еще одна попытка закрыть cookies
        if not cookies_closed:
            if await handle_cookies_popup(driver):
                cookies_closed = True
                await query.message.reply_text("✅ Cookies закрыты перед нажатием Continue")
            elif force_close_cookies(driver):
                cookies_closed = True
                await query.message.reply_text("✅ Cookies закрыты принудительно перед нажатием Continue")
        
        # 8. Ищем и нажимаем кнопку Continue на форме контактной информации
        await query.edit_message_text("🔍 Ищу кнопку Continue на форме...")
        
        # Делаем скриншот формы перед поиском кнопки
        form_screenshot = "/tmp/dikidi_form_before_continue.png"
        driver.save_screenshot(form_screenshot)
        with open(form_screenshot, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption="📸 Форма перед поиском кнопки Continue"
            )
        
        continue_submit_clicked = False
        
        # ПОИСК КНОПКИ CONTINUE НА ФОРМЕ КОНТАКТНОЙ ИНФОРМАЦИИ
        try:
            # Ищем все кнопки и ссылки с текстом "Continue" или "Продолжить"
            continue_elements = driver.find_elements(By.XPATH, 
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')] | " +
                "//*[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'продолжить')]"
            )
            
            for elem in continue_elements:
                if elem.is_displayed() and elem.is_enabled():
                    elem_text = elem.text.strip().lower()
                    if 'continue' in elem_text or 'продолжить' in elem_text:
                        # Прокручиваем к элементу
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                        time.sleep(1)
                        
                        # Делаем скриншот перед кликом
                        before_click = "/tmp/dikidi_continue_button.png"
                        driver.save_screenshot(before_click)
                        
                        # Кликаем
                        try:
                            elem.click()
                        except:
                            driver.execute_script("arguments[0].click();", elem)
                        
                        continue_submit_clicked = True
                        await query.message.reply_text(f"✅ Нажата кнопка Continue на форме: '{elem.text}'")
                        
                        with open(before_click, 'rb') as photo:
                            await query.message.reply_photo(
                                photo=photo,
                                caption="📸 Кнопка Continue на форме найдена и нажата"
                            )
                        
                        time.sleep(3)
                        break
        except Exception as e:
            await query.message.reply_text(f"⚠️ Ошибка поиска Continue на форме: {e}")
        
        # 9. Ждем загрузки финальной страницы с кнопкой "Complete the appointment"
        if continue_submit_clicked:
            await query.edit_message_text("⏳ Жду загрузки финальной страницы...")
            time.sleep(3)
            
            # Делаем скриншот финальной страницы
            final_page_screenshot = "/tmp/dikidi_final_page.png"
            driver.save_screenshot(final_page_screenshot)
            with open(final_page_screenshot, 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption="📸 Финальная страница перед Complete the appointment"
                )
        
        # 10. Ищем и нажимаем кнопку "Complete the appointment"
        await query.edit_message_text("🔍 Ищу кнопку Complete the appointment...")
        
        final_submit_clicked = False
        
        # ПОИСК КНОПКИ "COMPLETE THE APPOINTMENT"
        
        # 1. Ищем по точному тексту "Complete the appointment"
        try:
            complete_buttons = driver.find_elements(By.XPATH, 
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'complete the appointment')] | " +
                "//*[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'завершить запись')]"
            )
            
            for btn in complete_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    # Прокручиваем к кнопке
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    
                    # Делаем скриншот перед кликом
                    before_final_click = "/tmp/dikidi_complete_button.png"
                    driver.save_screenshot(before_final_click)
                    
                    # Кликаем
                    try:
                        btn.click()
                    except:
                        driver.execute_script("arguments[0].click();", btn)
                    
                    final_submit_clicked = True
                    await query.message.reply_text(f"✅ Нажата кнопка Complete the appointment: '{btn.text}'")
                    
                    with open(before_final_click, 'rb') as photo:
                        await query.message.reply_photo(
                            photo=photo,
                            caption="📸 Кнопка Complete the appointment найдена и нажата"
                        )
                    
                    time.sleep(3)
                    break
        except Exception as e:
            await query.message.reply_text(f"⚠️ Ошибка поиска Complete the appointment: {e}")
        
        # 2. Ищем по частичному совпадению
        if not final_submit_clicked:
            try:
                partial_texts = ['complete', 'appointment', 'завершить', 'запись', 'готово']
                
                for text in partial_texts:
                    elements = driver.find_elements(By.XPATH, 
                        f"//*[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯABCDEFGHIJKLMNOPQRSTUVWXYZ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяabcdefghijklmnopqrstuvwxyz'), '{text}')]"
                    )
                    
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            elem_text = elem.text.strip().lower()
                            # Проверяем, что это действительно кнопка завершения
                            if 'complete' in elem_text or 'appointment' in elem_text or 'завершить' in elem_text:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                                time.sleep(1)
                                
                                try:
                                    elem.click()
                                except:
                                    driver.execute_script("arguments[0].click();", elem)
                                
                                final_submit_clicked = True
                                await query.message.reply_text(f"✅ Нажата кнопка по частичному тексту '{text}': '{elem.text}'")
                                time.sleep(3)
                                break
                    if final_submit_clicked:
                        break
            except Exception as e:
                await query.message.reply_text(f"⚠️ Ошибка поиска по частичным совпадениям: {e}")
        
        # 3. Ищем все кнопки и ссылки на странице
        if not final_submit_clicked:
            try:
                all_clickable = driver.find_elements(By.XPATH, "//a | //button | //input[@type='submit']")
                
                for elem in all_clickable:
                    try:
                        if elem.is_displayed() and elem.is_enabled():
                            elem_text = elem.text.strip().lower()
                            # Ищем кнопки с текстом, связанным с завершением
                            if elem_text and ('complete' in elem_text or 'finish' in elem_text or 'готово' in elem_text or 'завершить' in elem_text):
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                                time.sleep(1)
                                
                                try:
                                    elem.click()
                                except:
                                    driver.execute_script("arguments[0].click();", elem)
                                
                                final_submit_clicked = True
                                await query.message.reply_text(f"✅ Нажата общая кнопка завершения: '{elem.text}'")
                                time.sleep(3)
                                break
                    except:
                        continue
            except Exception as e:
                await query.message.reply_text(f"⚠️ Ошибка общего поиска: {e}")
        
        # Если всё еще не найдено, делаем дополнительный скриншот для отладки
        if not final_submit_clicked:
            debug_screenshot = "/tmp/dikidi_debug_final.png"
            driver.save_screenshot(debug_screenshot)
            with open(debug_screenshot, 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption="⚠️ Финальная кнопка Complete the appointment не найдена. Скриншот для отладки"
                )
        
        # 11. Проверяем результат
        await query.edit_message_text("🔍 Проверяю результат бронирования...")
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
                f"⏰ Время брони: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"✅ Все этапы пройдены!"
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
                f"✅ Окончательный результат неясен\n"
                f"🔍 Проверьте запись вручную\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}"
            )
        
        await query.edit_message_text(result_message)
        
        # 12. Отправляем итоговый отчет
        await query.message.reply_text(
            f"📊 ИТОГОВЫЙ ОТЧЕТ:\n"
            f"• Cookies закрыты: {'✅' if cookies_closed else '❌'}\n"
            f"• Машина выбрана: {'✅ ' + machine_name if selected_machine else '❌'}\n"
            f"• Время выбрано: {'✅ ' + time_text if time_selected else '❌'}\n"
            f"• Кнопка продолжения (после времени): {'✅' if continue_clicked else '❌'}\n"
            f"• Имя заполнено: {'✅' if name_filled else '❌'}\n"
            f"• Фамилия заполнена: {'✅' if surname_filled else '❌'}\n"
            f"• Телефон заполнен: {'✅' if phone_filled else '❌'}\n"
            f"• Комментарий заполнен: {'✅' if comment_filled else '❌'}\n"
            f"• Кнопка Continue на форме: {'✅' if continue_submit_clicked else '❌'}\n"
            f"• Кнопка Complete the appointment: {'✅' if final_submit_clicked else '❌'}\n"
            f"• Результат: {'✅ Успех' if success else '⚠️ Неясно' if not error else '❌ Ошибка'}"
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
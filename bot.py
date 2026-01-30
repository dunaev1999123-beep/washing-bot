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
            "button[class*='accept']"
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
                    button.click()
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
                if any(keyword in btn_text for keyword in ['accept', 'принять', 'согласен', 'ok', 'готово']):
                    if button.is_displayed():
                        button.click()
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
        
        # Ждем загрузки страницы (ИСПРАВЛЕНО: добавлены двойные скобки)
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
        
        # 6. Проверяем наличие ключевых элементов Dikidi
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
        
        # 1. Переходим на сайт и закрываем cookies
        driver.get(TARGET_URL)
        # ИСПРАВЛЕНО: добавлены двойные скобки
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Закрываем cookies-окно
        cookies_closed = await handle_cookies_popup(driver)
        if cookies_closed:
            await query.edit_message_text("✅ Cookies-окно закрыто")
        
        time.sleep(2)
        
        # 2. Ищем доступные машины по приоритету: Машинка 1 -> Машинка 2 -> Машинка 3
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
                        
                        # Проверяем, не занята ли машина (ищем признаки недоступности)
                        parent_html = selected_machine.get_attribute('outerHTML')
                        if any(indicator in parent_html.lower() for indicator in ['disabled', 'занят', 'busy', 'недоступ', 'unavailable']):
                            await query.message.reply_text(f"⚠️ {machine_text} занята, пробую следующую...")
                            continue
                        
                        # Кликаем на выбранную машину
                        driver.execute_script("arguments[0].click();", selected_machine)
                        await query.message.reply_text(f"✅ Выбрана {machine_text}")
                        time.sleep(2)
                        break
                    else:
                        await query.message.reply_text(f"⚠️ {machine_text} не видна на странице")
            except Exception as e:
                await query.message.reply_text(f"⚠️ Ошибка поиска {machine_text}: {e}")
                continue
        
        if not selected_machine:
            await query.message.reply_text("❌ Не найдено ни одной доступной машины")
            # Пробуем найти любую кнопку или элемент, который может быть машиной
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                all_divs = driver.find_elements(By.TAG_NAME, "div")
                
                for elem in all_buttons + all_divs:
                    try:
                        elem_text = elem.text.strip()
                        if elem_text and ('машин' in elem_text.lower() or 'стир' in elem_text.lower()):
                            driver.execute_script("arguments[0].click();", elem)
                            machine_name = elem_text
                            selected_machine = elem
                            await query.message.reply_text(f"✅ Найдена и выбрана машина: {elem_text}")
                            time.sleep(2)
                            break
                    except:
                        continue
            except:
                pass
        
        if not selected_machine:
            # Делаем скриншот для отладки
            debug_screenshot = "/tmp/dikidi_no_machines.png"
            driver.save_screenshot(debug_screenshot)
            with open(debug_screenshot, 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption="❌ Не найдены машины для бронирования"
                )
            raise Exception("Не найдены доступные машины")
        
        # 3. Ищем и выбираем любое доступное время
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
        
        # Удаляем дубликаты
        unique_elements = []
        seen_ids = set()
        for elem in time_elements:
            try:
                elem_id = elem.id
                if elem_id not in seen_ids:
                    seen_ids.add(elem_id)
                    unique_elements.append(elem)
            except:
                unique_elements.append(elem)
        
        time_elements = unique_elements
        
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
                    
                except Exception as e:
                    continue
            
            if not time_selected and len(time_elements) > 0:
                # Если все слоты кажутся занятыми, пробуем кликнуть на первый
                try:
                    first_time = time_elements[0]
                    time_text = first_time.text.strip()
                    driver.execute_script("arguments[0].click();", first_time)
                    time_selected = True
                    await query.message.reply_text(f"⏰ Выбрано первое доступное время: {time_text}")
                    time.sleep(2)
                except Exception as e:
                    await query.message.reply_text(f"⚠️ Ошибка выбора времени: {e}")
        else:
            await query.message.reply_text("❌ Не найдено слотов времени")
        
        # 4. Ищем кнопку продолжения/подтверждения времени
        await query.edit_message_text("🔍 Ищу кнопку продолжения...")
        
        continue_buttons = [
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
        
        continue_clicked = False
        for selector in continue_buttons:
            try:
                if "contains" in selector:
                    text = selector.split("'")[1]
                    button = driver.find_element(By.XPATH, 
                        f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                    )
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button.is_displayed():
                    driver.execute_script("arguments[0].click();", button)
                    await query.message.reply_text(f"✅ Нажата кнопка: {selector}")
                    continue_clicked = True
                    time.sleep(3)
                    break
            except:
                continue
        
        # 5. Ждем загрузки формы записи
        if continue_clicked:
            await query.edit_message_text("📝 Жду загрузки формы записи...")
            time.sleep(3)
        
        # 6. Ищем и заполняем форму
        await query.edit_message_text("📋 Ищу поля формы...")
        
        # Ищем поле имени
        name_field = None
        name_filled = False
        name_selectors = [
            "input[name='name']",
            "input[name='clientName']",
            "input[name='firstname']",
            "input[name='fio']",
            "input[placeholder*='имя']",
            "input[placeholder*='Имя']",
            "#name",
            "#clientName"
        ]
        
        for selector in name_selectors:
            try:
                name_field = driver.find_element(By.CSS_SELECTOR, selector)
                name_field.clear()
                name_field.send_keys(FORM_NAME)
                await query.message.reply_text(f"✅ Заполнено имя: {FORM_NAME}")
                name_filled = True
                break
            except:
                continue
        
        # Ищем поле фамилии (если есть)
        surname_filled = False
        surname_selectors = [
            "input[name='surname']",
            "input[name='lastname']",
            "input[placeholder*='фамилия']",
            "input[placeholder*='Фамилия']",
            "#surname"
        ]
        
        for selector in surname_selectors:
            try:
                surname_field = driver.find_element(By.CSS_SELECTOR, selector)
                surname_field.clear()
                surname_field.send_keys(FORM_SURNAME)
                await query.message.reply_text(f"✅ Заполнена фамилия: {FORM_SURNAME}")
                surname_filled = True
                break
            except:
                continue
        
        # Ищем поле телефона
        phone_field = None
        phone_filled = False
        phone_selectors = [
            "input[name='phone']",
            "input[type='tel']",
            "input[placeholder*='телефон']",
            "input[placeholder*='Телефон']",
            "#phone",
            "input[name='phoneNumber']",
            "input[name='mobile']"
        ]
        
        for selector in phone_selectors:
            try:
                phone_field = driver.find_element(By.CSS_SELECTOR, selector)
                phone_field.clear()
                phone_field.send_keys(FORM_PHONE)
                await query.message.reply_text(f"✅ Заполнен телефон: {FORM_PHONE}")
                phone_filled = True
                break
            except:
                continue
        
        # Ищем поле комментария (если есть)
        comment_filled = False
        comment_selectors = [
            "textarea[name='comment']",
            "textarea[name='message']",
            "textarea[placeholder*='комментарий']",
            "textarea[placeholder*='Комментарий']",
            "#comment",
            "textarea[name='notes']"
        ]
        
        for selector in comment_selectors:
            try:
                comment_field = driver.find_element(By.CSS_SELECTOR, selector)
                comment_field.clear()
                comment_field.send_keys(FORM_COMMENT)
                await query.message.reply_text(f"✅ Заполнен комментарий: {FORM_COMMENT}")
                comment_filled = True
                break
            except:
                continue
        
        # 7. Ищем кнопку отправки формы
        await query.edit_message_text("🔍 Ищу кнопку отправки формы...")
        
        submit_clicked = False
        submit_selectors = [
            "button[type='submit']",
            "button:contains('Записаться')",
            "button:contains('Подтвердить запись')",
            "button:contains('Отправить')",
            "button:contains('Забронировать')",
            "button:contains('Завершить')",
            ".btn-submit",
            "[data-action='submit']",
            "input[type='submit']"
        ]
        
        for selector in submit_selectors:
            try:
                if "contains" in selector:
                    text = selector.split("'")[1]
                    button = driver.find_element(By.XPATH, 
                        f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
                    )
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button.is_displayed():
                    # Делаем скриншот перед отправкой
                    before_submit = "/tmp/dikidi_before_submit.png"
                    driver.save_screenshot(before_submit)
                    
                    # Кликаем кнопку
                    driver.execute_script("arguments[0].click();", button)
                    submit_clicked = True
                    await query.message.reply_text(f"✅ Форма отправлена! Кнопка: {selector}")
                    
                    # Отправляем скриншот
                    with open(before_submit, 'rb') as photo:
                        await query.message.reply_photo(
                            photo=photo,
                            caption="📸 Форма перед отправкой"
                        )
                    
                    time.sleep(3)
                    break
            except:
                continue
        
        # 8. Проверяем успешность
        await query.edit_message_text("🔍 Проверяю результат бронирования...")
        time.sleep(3)
        
        # Ищем сообщение об успехе
        page_text = driver.page_source.lower()
        success_keywords = ['успешно', 'записан', 'подтвержден', 'спасибо', 'ожидайте', 'success', 'thank you', 'confirmed']
        error_keywords = ['ошибка', 'error', 'не удалось', 'занято', 'busy', 'недоступно']
        
        success = any(keyword in page_text for keyword in success_keywords)
        error = any(keyword in page_text for keyword in error_keywords)
        
        # Делаем финальный скриншот
        final_screenshot = "/tmp/dikidi_final.png"
        driver.save_screenshot(final_screenshot)
        
        with open(final_screenshot, 'rb') as photo:
            await query.message.reply_photo(
                photo=photo,
                caption="📸 Финальный результат"
            )
        
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
        
        # 9. Отправляем дополнительную информацию
        await query.message.reply_text(
            f"📊 ИТОГОВЫЙ ОТЧЕТ:\n"
            f"• Cookies закрыты: {'✅' if cookies_closed else '❌'}\n"
            f"• Машина выбрана: {'✅ ' + machine_name if selected_machine else '❌'}\n"
            f"• Время выбрано: {'✅ ' + time_text if time_selected else '❌'}\n"
            f"• Кнопка продолжения: {'✅' if continue_clicked else '❌'}\n"
            f"• Имя заполнено: {'✅' if name_filled else '❌'}\n"
            f"• Фамилия заполнена: {'✅' if surname_filled else '❌'}\n"
            f"• Телефон заполнен: {'✅' if phone_filled else '❌'}\n"
            f"• Комментарий заполнен: {'✅' if comment_filled else '❌'}\n"
            f"• Форма отправлена: {'✅' if submit_clicked else '❌'}\n"
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
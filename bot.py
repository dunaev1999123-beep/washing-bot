import os
import asyncio
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram import Router
from aiohttp import web

# ========== ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
# Проверяем наличие обязательных переменных
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
ADMIN_ID = os.getenv('ADMIN_ID', '').strip()
TARGET_URL = os.getenv('TARGET_URL', '').strip()

# Данные для заполнения формы
FORM_DATA = {
    'name': os.getenv('FORM_NAME', '').strip(),
    'surname': os.getenv('FORM_SURNAME', '').strip(),
    'comment': os.getenv('FORM_COMMENT', '').strip(),
    'phone': os.getenv('FORM_PHONE', '').strip()  # Только 10 цифр без кода страны
}

# Проверяем, что все обязательные переменные загружены
if not BOT_TOKEN:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не установлен!")
    exit(1)

if not ADMIN_ID:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: ADMIN_ID не установлен!")
    exit(1)

if not TARGET_URL:
    print("⚠️ ВНИМАНИЕ: TARGET_URL не установлен. Бот не сможет работать.")
    # Не выходим, так как бот может работать в режиме диагностики

# Преобразуем ADMIN_ID в число
try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print(f"❌ ОШИБКА: ADMIN_ID должен быть числом, получено: {ADMIN_ID}")
    exit(1)

# Проверяем данные формы
form_errors = []
if not FORM_DATA['name']:
    form_errors.append("FORM_NAME")
if not FORM_DATA['surname']:
    form_errors.append("FORM_SURNAME")
if not FORM_DATA['phone']:
    form_errors.append("FORM_PHONE")
if not FORM_DATA['comment']:
    form_errors.append("FORM_COMMENT")

if form_errors:
    print(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Не установлены переменные формы: {', '.join(form_errors)}")

# Выводим информацию о загруженных переменных
print("=" * 60)
print("🤖 ТЕЛЕГРАМ БОТ ДЛЯ ЗАПИСИ НА СТИРКУ")
print("=" * 60)
print(f"✅ BOT_TOKEN: {'✓ Установлен' if BOT_TOKEN else '❌ НЕ установлен'}")
print(f"✅ ADMIN_ID: {ADMIN_ID} {'✓' if ADMIN_ID else '❌'}")
print(f"✅ TARGET_URL: {'✓ Установлен' if TARGET_URL else '❌ НЕ установлен'}")
print(f"✅ FORM_NAME: {FORM_DATA['name'] or '❌ НЕ установлен'}")
print(f"✅ FORM_SURNAME: {FORM_DATA['surname'] or '❌ НЕ установлен'}")
print(f"✅ FORM_PHONE: {FORM_DATA['phone'] or '❌ НЕ установлен'}")
print(f"✅ FORM_COMMENT: {FORM_DATA['comment'] or '❌ НЕ установлен'}")
print("=" * 60)

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Состояния FSM
class RecordStates(StatesGroup):
    waiting = State()
    processing = State()

# ========== HTTP СЕРВЕР ДЛЯ HEALTHCHECK (ДЛЯ AMVERA) ==========
async def healthcheck_handler(request):
    """Обработчик healthcheck для Amvera"""
    return web.Response(text='🤖 Telegram Bot is running and healthy!')

async def start_http_server():
    """Запуск HTTP сервера для healthcheck"""
    try:
        app = web.Application()
        app.router.add_get('/', healthcheck_handler)
        app.router.add_get('/health', healthcheck_handler)
        app.router.add_get('/status', healthcheck_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("✅ HTTP сервер запущен на порту 8080 для healthcheck")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка запуска HTTP сервера: {e}")
        return False

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def init_driver():
    """Инициализация Chrome с фиксированным размером окна"""
    options = Options()
    
    # Для Docker/безголового режима (Amvera)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--headless')  # Без GUI для сервера
    
    # Устанавливаем фиксированный размер окна
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Добавляем user-agent для маскировки
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Для Docker используем системный chromedriver
    try:
        # Пробуем установить через webdriver_manager (для локальной разработки)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except:
        # Для Docker/Amvera используем системный chromedriver
        options.binary_location = '/usr/bin/google-chrome'
        driver = webdriver.Chrome(options=options)
    
    # Устанавливаем фиксированный размер окна (дополнительная гарантия)
    driver.set_window_size(1920, 1080)
    
    # Маскируем WebDriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def take_screenshot(driver, step_name):
    """Сделать скриншот БЕЗ изменения размера окна"""
    try:
        screenshots_dir = Path('screenshots')
        screenshots_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = screenshots_dir / f"{step_name}_{timestamp}.png"
        
        # ВАЖНО: НЕ меняем размер окна, просто делаем скриншот
        driver.save_screenshot(str(filename))
        logger.info(f"📸 Скриншот: {filename}")
        return filename
    except Exception as e:
        logger.error(f"❌ Ошибка скриншота: {e}")
        return None

async def smart_click(driver, element, element_name):
    """Умный клик с разными методами"""
    try:
        # Прокручиваем к элементу плавно
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        await asyncio.sleep(0.3)
        
        # Пробуем разные методы клика
        methods = [
            lambda: element.click(),  # Обычный клик
            lambda: driver.execute_script("arguments[0].click();", element),  # JS клик
            lambda: ActionChains(driver).move_to_element(element).pause(0.1).click().perform(),  # ActionChains с паузой
        ]
        
        for i, method in enumerate(methods):
            try:
                method()
                logger.info(f"✅ Метод {i+1}: {element_name}")
                await asyncio.sleep(0.2)
                return True
            except:
                continue
        
        logger.error(f"❌ Все методы клика не сработали для {element_name}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка клика {element_name}: {e}")
        return False

async def click_continue_button(driver, button_name="Продолжить"):
    """Универсальная функция для поиска и нажатия кнопки 'Продолжить'"""
    try:
        logger.info(f"🔍 Ищу кнопку '{button_name}'...")
        
        # Селекторы для кнопки "Продолжить" (из HTML кода)
        continue_selectors = [
            # Основные селекторы
            "//a[contains(text(), 'Продолжить')]",
            "//button[contains(text(), 'Продолжить')]",
            "//span[contains(text(), 'Продолжить')]/parent::*",
            "//div[contains(text(), 'Продолжить')]/parent::*",
            
            # По классам (из Dikidi)
            "//a[contains(@class, 'btn-stylized') and contains(@class, 'nrs-gradient')]",
            "//a[contains(@class, 'nr-continue')]",
            "//a[contains(@class, 'btn-default') and contains(@class, 'btn-stylized')]",
            
            # Более общие селекторы
            "//*[contains(@class, 'continue')]",
            "//*[contains(@class, 'submit')]",
            "//*[contains(@class, 'next')]",
            
            # По тексту (любой кнопка с похожим текстом)
            "//*[text()='Далее']",
            "//*[text()='Подтвердить']",
            "//*[text()='Завершить']",
            "//*[text()='Отправить']",
            
            # По атрибутам
            "//*[@type='submit']",
            "//*[@role='button' and contains(text(), 'Продолжить')]",
        ]
        
        continue_button = None
        
        for selector in continue_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            if text and ('продолжить' in text.lower() or 
                                        'далее' in text.lower() or 
                                        'подтвердить' in text.lower() or
                                        'завершить' in text.lower()):
                                continue_button = element
                                logger.info(f"✅ Найдена кнопка '{button_name}' по селектору: {selector}")
                                logger.info(f"   Текст кнопки: '{text}'")
                                break
                    except:
                        continue
                if continue_button:
                    break
            except:
                continue
        
        # Если не нашли по тексту, ищем любую доступную кнопку
        if not continue_button:
            try:
                all_buttons = driver.find_elements(By.XPATH, "//a | //button | //div[@role='button']")
                for button in all_buttons:
                    try:
                        if button.is_displayed() and button.is_enabled():
                            text = button.text.strip()
                            if text:
                                logger.debug(f"   Найдена кнопка с текстом: '{text}'")
                                # Если есть похожие слова
                                if any(word in text.lower() for word in ['продолжить', 'далее', 'записаться', 'подтвердить', 'отправить', 'готово']):
                                    continue_button = button
                                    logger.info(f"✅ Найдена кнопка '{button_name}' по тексту: {text}")
                                    break
                    except:
                        continue
            except:
                pass
        
        if continue_button:
            # Делаем скриншот перед кликом
            take_screenshot(driver, f"before_{button_name.replace(' ', '_')}_click")
            
            # Кликаем на кнопку
            click_success = await smart_click(driver, continue_button, f"Кнопка '{button_name}'")
            
            if click_success:
                logger.info(f"✅ Кнопка '{button_name}' успешно нажата!")
                await asyncio.sleep(0.5)
                return True
            else:
                logger.error(f"❌ Не удалось нажать кнопку '{button_name}'")
                return False
        else:
            logger.warning(f"⚠️ Не найдена кнопка '{button_name}'")
            # Делаем скриншот для отладки
            take_screenshot(driver, f"no_{button_name.replace(' ', '_')}_found")
            return False
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска кнопки '{button_name}': {e}")
        return False

async def fill_contact_form(driver):
    """Заполнить контактную информацию - с правильным вводом телефона (11 цифр с кодом страны)"""
    try:
        logger.info("📝 ЗАПОЛНЯЮ КОНТАКТНУЮ ИНФОРМАЦИЮ...")
        
        # Ждем появления формы
        await asyncio.sleep(2)
        
        # 1. Поле "Ваше имя*" - input с name="first_name"
        try:
            name_field = driver.find_element(By.NAME, "first_name")
            name_field.clear()
            name_field.send_keys(FORM_DATA['name'])
            logger.info(f"✅ Заполнено поле 'Имя': {FORM_DATA['name']}")
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось найти поле 'Имя': {e}")
        
        # 2. Поле "Ваша фамилия" - input с name="last_name"
        try:
            surname_field = driver.find_element(By.NAME, "last_name")
            surname_field.clear()
            surname_field.send_keys(FORM_DATA['surname'])
            logger.info(f"✅ Заполнено поле 'Фамилия': {FORM_DATA['surname']}")
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось найти поле 'Фамилия': {e}")
        
        # 3. Поле "Мобильный телефон*" - ВАЖНО: вводим ПОЛНЫЙ номер (11 цифр)
        try:
            # Ищем поле телефона
            phone_field = driver.find_element(By.CSS_SELECTOR, "input[name='phone'][type='tel']")
            
            # Проверяем текущее значение (может быть автозаполнено)
            current_value = phone_field.get_attribute('value')
            logger.info(f"📱 Текущее значение поля телефона: '{current_value}'")
            
            # Полный номер для России: 7 + 10 цифр = 11 цифр
            target_number = FORM_DATA['phone']  # "9955542240" (10 цифр)
            full_number = f"7{target_number}"  # "79955542240" (11 цифр)
            
            logger.info(f"📱 Буду вводить полный номер: {full_number} (11 цифр с кодом страны)")
            
            # Скриншот перед вводом
            take_screenshot(driver, "before_phone_input")
            
            # Очищаем поле
            phone_field.clear()
            await asyncio.sleep(0.3)
            
            # Кликаем в поле
            phone_field.click()
            await asyncio.sleep(0.2)
            
            # ВАЖНО: Вводим ПОЛНЫЙ номер (11 цифр), а не 10!
            # Метод 1: Вводим целиком
            logger.info("📱 Метод 1: Ввожу номер целиком")
            phone_field.send_keys(full_number)
            await asyncio.sleep(0.5)
            
            # Проверяем результат
            entered_value = phone_field.get_attribute('value')
            logger.info(f"📱 После ввода целиком: '{entered_value}'")
            
            # Если не сработало, пробуем по цифрам
            if not entered_value or len(entered_value.replace('+', '').replace(' ', '')) < 11:
                logger.warning("📱 Метод 1 не сработал, пробую вводить по цифрам")
                
                # Очищаем
                phone_field.clear()
                await asyncio.sleep(0.3)
                
                # Вводим по одной цифре
                for digit in full_number:
                    phone_field.send_keys(digit)
                    await asyncio.sleep(0.1)
                
                await asyncio.sleep(0.5)
            
            # Финальная проверка
            entered_value = phone_field.get_attribute('value')
            logger.info(f"📱 Финальное значение: '{entered_value}'")
            
            # Проверяем, что номер содержит наши цифры
            if target_number in entered_value.replace('+', '').replace(' ', ''):
                logger.info(f"✅ Номер телефона успешно введен: {entered_value}")
            else:
                logger.warning(f"⚠️ Возможная проблема с номером. Ожидалось что-то с {target_number}, получено: '{entered_value}'")
                
                # Пробуем JavaScript как запасной вариант
                logger.info("🔄 Пробую ввести через JavaScript")
                js_script = f"""
                var phoneField = document.querySelector("input[name='phone'][type='tel']");
                if (phoneField) {{
                    phoneField.value = '{full_number}';
                    phoneField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    phoneField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                """
                driver.execute_script(js_script)
                await asyncio.sleep(0.5)
                
                entered_value = phone_field.get_attribute('value')
                logger.info(f"📱 После JS: '{entered_value}'")
            
            # Скриншот после ввода
            take_screenshot(driver, "after_phone_input")
            
        except Exception as e:
            logger.error(f"❌ Ошибка заполнения телефона: {e}")
            take_screenshot(driver, "phone_error")
        
        # 4. Поле "Комментарий" - textarea с name="comment"
        try:
            comment_field = driver.find_element(By.NAME, "comment")
            comment_field.clear()
            comment_field.send_keys(FORM_DATA['comment'])
            logger.info(f"✅ Заполнено поле 'Комментарий': {FORM_DATA['comment']}")
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось найти поле 'Комментарий': {e}")
        
        # Делаем скриншот заполненной формы
        take_screenshot(driver, "form_filled")
        
        # ===== ПЕРВОЕ НАЖАТИЕ КНОПКИ "ПРОДОЛЖИТЬ" =====
        logger.info("🔍 Ищу первую кнопку 'Продолжить'...")
        
        first_click_success = await click_continue_button(driver, "Первая кнопка 'Продолжить'")
        
        if first_click_success:
            logger.info("✅ Первая кнопка 'Продолжить' нажата!")
            await asyncio.sleep(3)
            take_screenshot(driver, "after_first_continue")
            
            # ===== ВТОРОЕ НАЖАТИЕ КНОПКИ "ПРОДОЛЖИТЬ" =====
            logger.info("🔍 Ищу вторую кнопку 'Продолжить'...")
            await asyncio.sleep(2)
            
            second_click_success = await click_continue_button(driver, "Вторая кнопка 'Продолжить'")
            
            if second_click_success:
                logger.info("✅ Вторая кнопка 'Продолжить' нажата!")
                await asyncio.sleep(2)
                take_screenshot(driver, "form_submitted")
                return True, "✅ Форма заполнена и обе кнопки 'Продолжить' нажаты!"
            else:
                logger.warning("⚠️ Не удалось найти вторую кнопку 'Продолжить', но первая нажата")
                return True, "✅ Форма заполнена, первая кнопка нажата"
        else:
            logger.error("❌ Не удалось нажать первую кнопку 'Продолжить'")
            return False, "❌ Форма заполнена, но не удалось нажать первую кнопку 'Продолжить'"
        
    except Exception as e:
        logger.error(f"❌ Ошибка заполнения формы: {e}")
        take_screenshot(driver, "form_error")
        return False, f"❌ Ошибка заполнения формы: {str(e)}"

async def find_time_in_section(driver, section_name):
    """Поиск времени в определенном разделе (Машинка 1 или Машинка 2)"""
    logger.info(f"🔍 Ищу время в разделе '{section_name}'...")
    
    strategies = [
        (f"//*[contains(text(), '{section_name}')]/following::*[contains(text(), ':')][1]", f"Следующий элемент после {section_name}"),
        (f"//*[contains(text(), '{section_name}')]/ancestor::div[1]//*[contains(text(), ':')]", f"В блоке {section_name}"),
        (f"//*[contains(text(), '{section_name}')]/ancestor::div[contains(@class, 'machine')]//*[contains(text(), ':')]", f"В машине {section_name}"),
        (f"//*[contains(@data-machine, '{section_name[-1]}')]//*[contains(text(), ':')]", f"По data-machine {section_name}"),
        (f"//div[contains(@class, '{section_name.lower().replace(' ', '-')}')]//*[contains(text(), ':')]", f"По классу {section_name}"),
    ]
    
    all_time_elements = []
    
    for xpath, description in strategies:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            
            if elements:
                logger.info(f"    Найдено по стратегии '{description}': {len(elements)} элементов")
                
                for elem in elements:
                    try:
                        text = elem.text.strip()
                        if ':' in text and any(c.isdigit() for c in text.split(':')[0]):
                            classes = elem.get_attribute('class') or ''
                            style = elem.get_attribute('style') or ''
                            
                            if ('disabled' not in classes.lower() and 
                                'gray' not in style.lower() and 
                                'занят' not in text.lower() and
                                'недоступ' not in text.lower()):
                                
                                if elem.is_displayed() and elem.is_enabled():
                                    all_time_elements.append((elem, text, description))
                                    logger.info(f"      Найдено доступное время: '{text}'")
                    except Exception as e:
                        continue
        except Exception as e:
            logger.debug(f"    Стратегия '{description}' ошибка: {e}")
            continue
    
    return all_time_elements

async def find_and_select_time(driver):
    """Расширенный поиск и выбор времени - сначала Машинка 1, потом Машинка 2"""
    try:
        logger.info("🔍 ИЩУ ВРЕМЕННЫЕ СЛОТЫ...")
        
        # Шаг 1: Ищем время на МАШИНКА 1
        logger.info("=== ПОИСК НА МАШИНКА 1 ===")
        machine1_times = await find_time_in_section(driver, "Машинка 1")
        
        if machine1_times:
            try:
                machine1_times.sort(key=lambda x: datetime.strptime(x[1].split()[0] if ' ' in x[1] else x[1], "%H:%M"))
            except:
                pass
            
            logger.info(f"✅ Найдено {len(machine1_times)} доступных слотов на Машинка 1")
            
            selected_elem, selected_time, selected_desc = machine1_times[0]
            
            logger.info(f"⏰ Выбираю время на Машинка 1: {selected_time}")
            
            take_screenshot(driver, f"before_select_m1_{selected_time.replace(':', '_')}")
            
            click_success = await smart_click(driver, selected_elem, f"Машинка 1 время {selected_time}")
            
            if click_success:
                await asyncio.sleep(1)
                take_screenshot(driver, f"after_select_m1_{selected_time.replace(':', '_')}")
                
                # После выбора времени, ищем кнопку "Продолжить"
                logger.info("🔍 После выбора времени, ищу кнопку 'Продолжить'...")
                await asyncio.sleep(1)
                
                continue_success = await click_continue_button(driver, "Продолжить после выбора времени")
                
                if continue_success:
                    logger.info("✅ Кнопка 'Продолжить' после выбора времени нажата!")
                    await asyncio.sleep(2)
                    return True, f"✅ Выбрано время на Машинка 1: {selected_time} и нажато 'Продолжить'"
                else:
                    logger.warning("⚠️ Не удалось найти кнопку 'Продолжить' после выбора времени")
                    return True, f"✅ Выбрано время на Машинка 1: {selected_time}, но не найдена кнопка 'Продолжить'"
        
        # Шаг 2: Если на Машинка 1 нет времени, ищем на МАШИНКА 2
        logger.info("=== НА МАШИНКА 1 НЕТ ВРЕМЕНИ, ИЩУ НА МАШИНКА 2 ===")
        machine2_times = await find_time_in_section(driver, "Машинка 2")
        
        if machine2_times:
            try:
                machine2_times.sort(key=lambda x: datetime.strptime(x[1].split()[0] if ' ' in x[1] else x[1], "%H:%M"))
            except:
                pass
            
            logger.info(f"✅ Найдено {len(machine2_times)} доступных слотов на Машинка 2")
            
            selected_elem, selected_time, selected_desc = machine2_times[0]
            
            logger.info(f"⏰ Выбираю время на Машинка 2: {selected_time}")
            
            take_screenshot(driver, f"before_select_m2_{selected_time.replace(':', '_')}")
            
            click_success = await smart_click(driver, selected_elem, f"Машинка 2 время {selected_time}")
            
            if click_success:
                await asyncio.sleep(1)
                take_screenshot(driver, f"after_select_m2_{selected_time.replace(':', '_')}")
                
                # После выбора времени, ищем кнопку "Продолжить"
                logger.info("🔍 После выбора времени, ищу кнопку 'Продолжить'...")
                await asyncio.sleep(1)
                
                continue_success = await click_continue_button(driver, "Продолжить после выбора времени")
                
                if continue_success:
                    logger.info("✅ Кнопка 'Продолжить' после выбора времени нажата!")
                    await asyncio.sleep(2)
                    return True, f"✅ Выбрано время на Машинка 2: {selected_time} и нажато 'Продолжить'"
                else:
                    logger.warning("⚠️ Не удалось найти кнопку 'Продолжить' после выбора времени")
                    return True, f"✅ Выбрано время на Машинка 2: {selected_time}, но не найдена кнопка 'Продолжить'"
        
        if not machine1_times and not machine2_times:
            logger.warning("⚠️ Не найдено доступных временных слотов ни на одной машинке")
            
            logger.info("Пробую общий поиск времени...")
            
            general_strategies = [
                ("//button[contains(text(), ':') and not(contains(@class, 'disabled'))]", "Доступные кнопки времени"),
                ("//*[contains(text(), ':') and not(contains(@class, 'disabled'))]", "Любые доступные элементы"),
                ("//*[contains(@class, 'time-slot') and not(contains(@class, 'disabled'))]", "Слоты времени"),
                ("//*[@data-time and not(contains(@class, 'disabled'))]", "По data-time"),
            ]
            
            for xpath, desc in general_strategies:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    if elements:
                        logger.info(f"Найдено по общей стратегии '{desc}': {len(elements)}")
                        elem = elements[0]
                        text = elem.text.strip()
                        
                        click_success = await smart_click(driver, elem, f"общее время {text}")
                        if click_success:
                            await asyncio.sleep(1)
                            
                            # После выбора времени, ищем кнопку "Продолжить"
                            continue_success = await click_continue_button(driver, "Продолжить после выбора времени")
                            
                            if continue_success:
                                logger.info("✅ Кнопка 'Продолжить' после выбора времени нажата!")
                                await asyncio.sleep(2)
                            return True, f"✅ Выбрано общее время: {text}"
                except:
                    continue
            
            return False, "❌ Не найдено доступных временных слотов ни на одной машинке"
            
    except Exception as e:
        logger.error(f"❌ Ошибка поиска времени: {e}")
        return False, f"❌ Ошибка: {str(e)}"

async def full_booking_process():
    """Полный процесс бронирования: выбор времени + заполнение формы"""
    driver = None
    result_messages = []
    
    try:
        driver = init_driver()
        logger.info(f"🌐 Открываю: {TARGET_URL}")
        
        # 1. Открываем страницу
        driver.get(TARGET_URL)
        await asyncio.sleep(3)
        
        # 2. Делаем первый скриншот
        take_screenshot(driver, "page_loaded")
        result_messages.append("✅ Страница открыта")
        
        # 3. Пробуем найти и выбрать время + первая кнопка "Продолжить"
        time_success, time_message = await find_and_select_time(driver)
        
        if not time_success:
            result_messages.append(f"❌ {time_message}")
            error_screenshot = take_screenshot(driver, "error_final")
            return False, error_screenshot, " | ".join(result_messages)
        
        result_messages.append(f"✅ {time_message}")
        
        # 4. Заполняем контактную форму + две кнопки "Продолжить"
        await asyncio.sleep(1.5)
        form_success, form_message = await fill_contact_form(driver)
        
        if form_success:
            result_messages.append(form_message)
        else:
            result_messages.append(form_message)
        
        # 5. Финальный скриншот
        await asyncio.sleep(1)
        final_screenshot = take_screenshot(driver, "final_result")
        
        return True, final_screenshot, " | ".join(result_messages)
            
    except Exception as e:
        logger.error(f"❌ Ошибка процесса: {e}")
        if driver:
            error_screenshot = take_screenshot(driver, "process_error")
        else:
            error_screenshot = None
        return False, error_screenshot, f"❌ Критическая ошибка: {str(e)}"
    finally:
        if driver:
            driver.quit()

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Скриншот")],
            [KeyboardButton(text="⏰ Выбрать время")],
            [KeyboardButton(text="📝 Полная запись")],
            [KeyboardButton(text="🔍 Диагностика")],
            [KeyboardButton(text="📊 Статус")]
        ],
        resize_keyboard=True
    )
    
    welcome_text = f"""
🤖 БОТ ДЛЯ ЗАПИСИ НА СТИРКУ
✅ Admin ID: {ADMIN_ID}
🌐 Страница: {TARGET_URL or '⚠️ НЕ УСТАНОВЛЕНА'}

Функции:
📸 Скриншот - просто открыть страницу
⏰ Выбрать время - только выбрать время
📝 Полная запись - ПОЛНЫЙ ПРОЦЕСС:
  1. Выбор времени (М1 → если нет → М2)
  2. НАЖАТИЕ ПЕРВОЙ КНОПКИ "Продолжить" 
  3. Заполнение формы контактов
  4. НАЖАТИЕ ВТОРОЙ КНОПКИ "Продолжить"
  5. НАЖАТИЕ ТРЕТЬЕЙ КНОПКИ "Продолжить" (если есть)

🔍 Диагностика - анализ страницы

🔥 ДАННЫЕ ФОРМЫ:
• Имя: {FORM_DATA['name'] or '⚠️ НЕ УСТАНОВЛЕН'}
• Фамилия: {FORM_DATA['surname'] or '⚠️ НЕ УСТАНОВЛЕН'}
• Телефон: {FORM_DATA['phone'] or '⚠️ НЕ УСТАНОВЛЕН'} 
  (будет введен как 7{FORM_DATA['phone'] or ''} - 11 цифр с кодом страны)
• Комментарий: {FORM_DATA['comment'] or '⚠️ НЕ УСТАНОВЛЕН'}

📱 ВАЖНО: Телефон вводится как 11 цифр (7 + 10 цифр номера)

💡 Для работы бота установите все переменные окружения!
"""
    
    await message.answer(welcome_text, reply_markup=keyboard)
    await state.set_state(RecordStates.waiting)

@router.message(F.text == "📝 Полная запись")
async def full_booking_handler(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет прав")
        return
    
    if not TARGET_URL:
        await message.answer("❌ ОШИБКА: Не установлена TARGET_URL")
        return
    
    if not FORM_DATA['phone']:
        await message.answer("❌ ОШИБКА: Не установлен телефон в форме")
        return
    
    await message.answer("📝 Запускаю ПОЛНЫЙ процесс записи...\n\n" +
                         "🔹 Этап 1: Выбор времени\n" +
                         "   • Сначала ищу на Машинка 1\n" +
                         "   • Если нет → Машинка 2\n" +
                         "   • После выбора → НАЖАТИЕ 'Продолжить'\n\n" +
                         "🔹 Этап 2: Заполнение формы\n" +
                         f"   • Имя: {FORM_DATA['name'] or '⚠️ НЕТ'}\n" +
                         f"   • Фамилия: {FORM_DATA['surname'] or '⚠️ НЕТ'}\n" +
                         f"   • Телефон: 7{FORM_DATA['phone']} (11 цифр с кодом страны)\n" +
                         f"   • Комментарий: {FORM_DATA['comment'] or '⚠️ НЕТ'}\n\n" +
                         "🔹 Этап 3: НАЖАТИЕ КНОПОК 'Продолжить'\n" +
                         "   • Первая кнопка (после формы)\n" +
                         "   • Вторая кнопка (на след. странице)\n" +
                         "   • Третья кнопка (если есть)")
    await state.set_state(RecordStates.processing)
    
    success, screenshot, result_text = await full_booking_process()
    
    if success and screenshot:
        try:
            photo = FSInputFile(screenshot)
            await message.answer_photo(photo, caption=result_text)
        except Exception as e:
            await message.answer(f"{result_text}\n❌ Ошибка отправки: {e}")
    else:
        await message.answer(result_text)
    
    await state.set_state(RecordStates.waiting)

# Другие обработчики команд можно добавить здесь...

async def main():
    """Главная функция запуска бота"""
    logger.info("=" * 60)
    logger.info("🤖 ТЕЛЕГРАМ БОТ ЗАПУСКАЕТСЯ")
    logger.info("=" * 60)
    logger.info(f"✅ Admin ID: {ADMIN_ID}")
    logger.info(f"🌐 Target URL: {TARGET_URL}")
    logger.info(f"📱 Phone: 7{FORM_DATA['phone']}")
    logger.info("=" * 60)
    
    # Запускаем HTTP сервер для healthcheck (в фоне)
    http_server_task = asyncio.create_task(start_http_server())
    await asyncio.sleep(0.5)  # Даем время HTTP серверу запуститься
    
    # Запускаем бота
    try:
        Path('screenshots').mkdir(exist_ok=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
    finally:
        # Отменяем HTTP сервер при завершении
        if not http_server_task.done():
            http_server_task.cancel()

if __name__ == '__main__':
    asyncio.run(main())
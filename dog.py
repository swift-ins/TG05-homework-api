import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import requests
from dotenv import load_dotenv
import os
import ssl

# Загрузка токена
load_dotenv()
TOKEN = os.getenv("TOKEN")
THE_DOG_API_KEY = os.getenv('THE_DOG_API_KEY')

# Конфигурация вебхука
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например, https://your-app-name.onrender.com

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")

def get_dog_breeds():
    url = "https://api.thedogapi.com/v1/breeds"
    headers = {"x-api-key": THE_DOG_API_KEY}
    response = requests.get(url, headers=headers)
    return response.json()

def get_dog_image_by_breed(breed_id):
    url = f"https://api.thedogapi.com/v1/images/search?breed_ids={breed_id}"
    headers = {"x-api-key": THE_DOG_API_KEY}
    response = requests.get(url, headers=headers)
    data = response.json()
    return data[0]['url']

def get_random_dog_image():
    url = "https://api.thedogapi.com/v1/images/search"
    headers = {"x-api-key": THE_DOG_API_KEY}
    response = requests.get(url, headers=headers)
    data = response.json()
    return data[0]['url']

def get_breed_info(breed_name):
    breeds = get_dog_breeds()
    for breed in breeds:
        if breed['name'].lower() == breed_name.lower():
            return breed
    return None

def get_top_breeds(limit=5):
    breeds = get_dog_breeds()
    return breeds[:limit]

def get_breeds_by_letter(letter: str):
    breeds = get_dog_breeds()
    return [breed['name'] for breed in breeds if breed['name'].upper().startswith(letter.upper())]

def get_breeds_by_max_weight(max_weight):
    breeds = get_dog_breeds()
    result = []
    for breed in breeds:
        try:
            weight_str = breed['weight']['metric']
            if '-' in weight_str:
                min_weight, max_weight_range = map(float, weight_str.split('-'))
                if min_weight <= max_weight:
                    result.append(breed['name'])
            else:
                weight = float(weight_str)
                if weight <= max_weight:
                    result.append(breed['name'])
        except (KeyError, ValueError):
            continue
    return result

def get_breeds_by_min_weight(min_weight):
    breeds = get_dog_breeds()
    result = []
    for breed in breeds:
        try:
            weight_str = breed['weight']['metric']
            if '-' in weight_str:
                min_w, max_w = map(float, weight_str.split('-'))
                if max_w >= min_weight:
                    result.append({
                        'name': breed['name'],
                        'weight': f"{min_w}-{max_w} кг"
                    })
            else:
                weight = float(weight_str)
                if weight >= min_weight:
                    result.append({
                        'name': breed['name'],
                        'weight': f"{weight} кг"
                    })
        except (KeyError, ValueError):
            continue
    return result

# Обработчики команд (остаются без изменений)
@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer(
        "🐶 Привет! Я бот-энциклопедия собак!\n"
        "Вот что я умею:\n"
        "/start - показать это сообщение\n"
        "/by_letter - найти породу по первой букве\n"
        "/random - случайное фото собаки\n"
        "/list - список всех пород\n\n"
        "/light_dogs - собаки весом до 5 кг\n"
        "/heavy_dogs - собаки весом более 80 кг\n"
        "Можешь просто написать название породы или выбрать поиск по букве!",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Command("random"))
async def random_dog(message: Message):
    dog_image_url = get_random_dog_image()
    await message.answer_photo(
        photo=dog_image_url, 
        caption="Вот случайный песик для тебя! 🐕",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Command("light_dogs"))
async def light_dogs_command(message: Message):
    max_weight = 2
    light_breeds = get_breeds_by_max_weight(max_weight)
    
    if light_breeds:
        keyboard_buttons = []
        for i in range(0, len(light_breeds), 3):
            row = light_breeds[i:i+3]
            keyboard_buttons.append([KeyboardButton(text=breed) for breed in row])
        
        keyboard_buttons.append([KeyboardButton(text="❌ Отмена")])
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=keyboard_buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            f"🐕 Найдено {len(light_breeds)} пород собак весом до {max_weight} кг:",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            f"Не найдено пород собак весом до {max_weight} кг",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(Command("heavy_dogs"))
async def heavy_dogs_command(message: Message):
    min_weight = 80
    heavy_breeds = get_breeds_by_min_weight(min_weight)
    
    if heavy_breeds:
        breeds_list = "\n".join(
            f"🐕‍🦺 {breed['name']} ({breed['weight']})" 
            for breed in heavy_breeds
        )
        
        keyboard_buttons = []
        for i in range(0, len(heavy_breeds), 2):
            row = heavy_breeds[i:i+2]
            keyboard_buttons.append(
                [KeyboardButton(text=breed['name']) for breed in row]
            )
        
        keyboard_buttons.append([KeyboardButton(text="❌ Отмена")])
        
        await message.answer(
            f"🦮 Крупные породы собак (весом более {min_weight} кг):\n\n{breeds_list}",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard_buttons,
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
    else:
        await message.answer(
            f"Не найдено пород собак весом более {min_weight} кг",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(Command("by_letter"))
async def by_letter_command(message: Message):
    await message.answer(
        "Введите первую букву породы собаки (A-Z или А-Я):",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(F.text.regexp(r'^[а-яА-Яa-zA-Z]$'))
async def show_breeds_by_letter(message: Message):
    letter = message.text.upper()
    breeds = get_breeds_by_letter(letter)
    
    if breeds:
        keyboard_buttons = []
        for i in range(0, len(breeds), 3):
            row = breeds[i:i+3]
            keyboard_buttons.append([KeyboardButton(text=breed) for breed in row])
        
        keyboard_buttons.append([KeyboardButton(text="❌ Отмена")])
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=keyboard_buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            f"🔍 Найдено {len(breeds)} пород на букву {letter}:",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            f"Не найдено пород на букву {letter}",
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(F.text == "❌ Отмена")
async def cancel_search(message: Message):
    await message.answer(
        "Поиск отменен. Что хотите сделать?",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Command("list"))
async def list_breeds(message: Message):
    breeds = get_dog_breeds()
    breed_names = [breed['name'] for breed in breeds]
    
    response = "📜 Список всех пород собак:\n\n" + "\n".join(breed_names)
    
    for i in range(0, len(response), 4000):
        await message.answer(
            response[i:i+4000],
            reply_markup=ReplyKeyboardRemove()
        )

@dp.message(F.text)
async def send_dog_info(message: Message):
    if message.text.startswith('/'):
        return
    
    breed_name = message.text
    breed_info = get_breed_info(breed_name)
    
    if breed_info:
        try:
            dog_image_url = get_dog_image_by_breed(breed_info['id'])
            info = (
                f"🐕 <b>{breed_info['name']}</b>\n\n"
                f"🌍 <i>Происхождение:</i> {breed_info.get('origin', 'неизвестно')}\n"
                f"⏳ <i>Продолжительность жизни:</i> {breed_info.get('life_span', 'неизвестно')}\n"
                f"⚖️ <i>Вес:</i> {breed_info.get('weight', {}).get('metric', 'неизвестно')} кг\n\n"
                f"😊 <i>Темперамент:</i> {breed_info.get('temperament', 'неизвестно')}"
            )
            await message.answer_photo(
                photo=dog_image_url,
                caption=info,
                parse_mode="HTML",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            await message.answer(
                "Произошла ошибка при получении данных о собаке 😢",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        await message.answer(
            "Порода не найдена. Попробуйте /by_letter для поиска по букве или /list для списка всех пород.",
            reply_markup=ReplyKeyboardRemove()
        )

async def main():
    # Настройка вебхука
    await bot.set_webhook(
        url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        # certificate=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)  # Раскомментируйте если используете SSL
    )
    
    # Создание aiohttp приложения
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    # Запуск сервера
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Получаем порт из переменной окружения или используем 8000 по умолчанию
    port = int(os.getenv("PORT", 8000))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    
    await site.start()
    
    # Бесконечный цикл для поддержания работы сервера
    while True:
        await asyncio.sleep(3600)  # Спим 1 час

if __name__ == '__main__':
    asyncio.run(main())
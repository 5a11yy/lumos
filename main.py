from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from db import get_bd, get_tomorrow, init_db
from db import get_tomorrow
from keyboard import inline_keyboard
from aiogram.fsm.context import FSMContext
from urllib.parse import quote
from states import Form, Order
import random
import asyncio
import aiohttp
from db import init_db, save_birthday, get_bd, get_tomorrow

load_dotenv()

BOT_TOKEN = '8735927867:AAEvCqM2f2_peWgp1LT59aTfwA9suLTHxME'
WEATHER_API_KEY = '7e68f799c1f3a6afc00855e83d1173ca'

WIDTH = 1024
HEIGHT = 1024

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer(f"Sup, {message.from_user.full_name}!")

@dp.message(F.photo)
async def photo_command(message: Message):
    photo = FSInputFile('sunset.jpg')
    text = '<b>Sunset</b>\n\nThis is a beautiful sunset photo.'
    await message.answer_photo(photo=photo, caption=text, parse_mode=ParseMode.HTML)

@dp.message(Command("weather"))
async def weather_command(message: Message):
    await get_weather(message)

async def get_weather(message: Message):
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Бишкек&appid={WEATHER_API_KEY}&units=metric"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                type = data['weather'][0]['main']
                temp = data['main']['temp']
                description = data['weather'][0]['description']
                feels_like = data['main']['feels_like']

                await message.answer(f"Погода в Бишкеке:\n Температура: {temp}°C \n"
                                     f"Ощущается как: {feels_like}°C \n Тип погоды: {type} \n Описание: {description}",
                                     reply_markup=inline_keyboard)
            else:
                await message.answer("Не удалось получить данные о погоде. Попробуйте позже.")

@dp.callback_query()
async def process_callback(callback: CallbackQuery):
    if callback.data == "sunny":
        await callback.message.answer("Сегодня солнечно!")
    elif callback.data == "rainy":
        await callback.message.answer("Сегодня дождливо!")

async def generate_image(prompt: str):
    url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
           f"?width={WIDTH}&height={HEIGHT}&nologo=true"
           f"&seed={random.randint(1, 10**6)}")
    timeout = aiohttp.ClientTimeout(total=120)

    for attempt in range(3):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.read()
                        if len(data) > 1000:
                            return data                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
                        
@dp.message(Command('draw'))
async def draw_command(message: Message, command: CommandObject):
    prompt = (command.args or "").strip() 

    if not prompt:
        await message.answer("Пожалуйста, укажите описание для генерации изображения. Например: /draw красивый закат")
        return 

    status = await message.answer("Генерация изображения... Пожалуйста, подождите.")
    try:
        data = await generate_image(prompt)
        await message.answer_photo(photo=BufferedInputFile(data, filename="image.png"), caption=f"Вот ваше изображение по запросу: {prompt}")
    except Exception as e:
        await message.answer(f"Произошла ошибка при генерации изображения: {e}")
    finally:
        await status.delete()

@dp.message(Command('order'))
async def start_order(message: Message, state: FSMContext):
    await state.set_state(Order.product)
    await message.answer("Пожалуйста, введите название продукта:")

@dp.message(Order.product)
async def process_product(message: Message, state: FSMContext):
    await state.update_data(product=message.text)
    await state.set_state(Order.quantity)
    await message.answer("Пожалуйста, введите количество:")

@dp.message(Order.quantity)
async def process_quantity(message: Message, state: FSMContext):
    await state.update_data(quantity=message.text)
    await state.set_state(Order.color)
    await message.answer("Пожалуйста, введите цвет продукта:")

@dp.message(Order.color)
async def process_color(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(f"Заказ оформлен!\n \
                         Продукт: {data['product']}\n \
                         Количество: {data['quantity']}\n \
                         Цвет: {message.text}")
    await state.clear()

@dp.message(Command('form'))
async def start_form(message: Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer("Пожалуйста, введите ваше имя:")


@dp.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    if not message.text.isalpha():
        await message.answer("Пожалуйста, введите корректное имя (только буквы).")
        return
    await state.update_data(name=message.text)
    await state.set_state(Form.age)
    await message.answer("Пожалуйста, введите ваш возраст:")

@dp.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректный возраст (только цифры).")
        return
    await state.update_data(age=message.text)
    await state.set_state(Form.city)
    await message.answer("Пожалуйста, введите ваш город:")

@dp.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(f"Анкета заполнена!\n \
                         Имя: {data['name']}\n \
                         Возраст: {data['age']}\n \
                         Город: {message.text}")
    await state.clear()

@dp.message(Command('add'))
async def add_birthday(message: Message, command: CommandObject):
    name, day = command.args.split()
    await save_birthday(message.from_user.id, name, day)
    await message.answer(f"День рождения {name} добавлен на {day}.")

@dp.message(Command('birthdays'))
async def list_birthdays(message: Message):
    birthdays = await get_bd(message.from_user.id)
    await message.answer(f"Ваши дни рождения:\n{birthdays}" if birthdays else "У вас нет сохраненных дней рождения.")

async def remind_birthdays():
    while True:
        try:
            for user_id, name, day in await get_tomorrow():
                await bot.send_message(user_id, f"Завтра день рождения у {name} ({day})!")
        except Exception as e:
            print("Ошибка в напоминании:", e)
        await asyncio.sleep(864000)  

async def main():
    await init_db()
    task =asyncio.create_task(remind_birthdays())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())


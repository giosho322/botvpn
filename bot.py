from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.command import Command
from config import TOKEN, ADMINS
from database import User, session
from wg_utils import generate_wg_config
from datetime import datetime
import asyncio

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

user_keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="Купить VPN 🚀")],
        [KeyboardButton(text="Мой конфиг ⚙️"), KeyboardButton(text="Поддержка 🆘")],
    ],
)

admin_keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="Статистика 📊"), KeyboardButton(text="Юзеры 👥")],
        [KeyboardButton(text="Бан 🔨"), KeyboardButton(text="Рассылка 📢")],
    ],
)

TARIFFS = {
    "1 месяц": {"days": 30, "price": 0},
    "3 месяца": {"days": 90, "price": 0},
    "6 месяцев": {"days": 180, "price": 0},
}

async def start(message: types.Message):
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if not user:
        user = User(
            user_id=message.from_user.id,
            username=message.from_user.username,
            join_date=datetime.now(),
            is_active=True,
        )
        session.add(user)
        session.commit()
    if message.from_user.id in ADMINS:
        await message.answer("Админ-панель", reply_markup=admin_keyboard)
    else:
        await message.answer("Привет, кожанный! Купи VPN и катайся без блоков!", reply_markup=user_keyboard)

async def buy_vpn(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text=f"{name}", callback_data=f"tariff_{name}")]
        for name in TARIFFS
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выбери тариф:", reply_markup=markup)

async def process_fake_payment(callback: types.CallbackQuery):
    tariff = callback.data.split("_",1)[1]
    days = TARIFFS[tariff]["days"]
    user = session.query(User).filter_by(user_id=callback.from_user.id).first()
    if user:
        user.is_active = True
        session.commit()
        config_path, qr_path = generate_wg_config(user.user_id, days)
        await bot.send_message(callback.from_user.id, f"Тариф '{tariff}' активирован! Вот конфиг:")
        await bot.send_document(callback.from_user.id, FSInputFile(config_path))
        await bot.send_photo(callback.from_user.id, FSInputFile(qr_path))

async def get_config(message: types.Message):
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if not user or not user.is_active:
        await message.answer("У тебя нет активной подписки! Выбери тариф через 'Купить VPN 🚀'")
        return
    config_path, qr_path = generate_wg_config(user.user_id, 30)
    await message.answer_document(FSInputFile(config_path))
    await message.answer_photo(FSInputFile(qr_path))

async def stats(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    count = session.query(User).count()
    await message.answer(f"📊 Юзеров: {count}")

# Регистрация
dp.message.register(start, Command(commands=["start"]))
dp.message.register(buy_vpn, lambda m: m.text == "Купить VPN 🚀")
dp.callback_query.register(process_fake_payment, lambda cb: cb.data and cb.data.startswith("tariff_"))
dp.message.register(get_config, lambda m: m.text == "Мой конфиг ⚙️")
dp.message.register(stats, lambda m: m.text == "Статистика 📊")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

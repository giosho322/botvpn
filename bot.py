from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.enums import ParseMode  # <-- Импорт ParseMode
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
        [
            KeyboardButton(text="Мой конфиг ⚙️"),
            KeyboardButton(text="Поддержка 🆘"),
            KeyboardButton(text="Как установить конфиг 🛠️")  # Добавлена кнопка для инструкции
        ],
    ]
)

admin_keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [
            KeyboardButton(text="Статистика 📊"),
            KeyboardButton(text="Юзеры 👥")
        ],
        [
            KeyboardButton(text="Бан 🔨"),
            KeyboardButton(text="Рассылка 📢")
        ],
    ]
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
            is_active=True
        )
        session.add(user)
        session.commit()

    if user.user_id in ADMINS:
        await message.answer("Админ-панель", reply_markup=admin_keyboard)
    else:
        await message.answer("Привет, кожанный! Купи VPN и катайся без блоков!", reply_markup=user_keyboard)

async def buy_vpn(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for name, data in TARIFFS.items():
        markup.add(
            InlineKeyboardButton(
                text=f"{name} (временно бесплатно)",
                callback_data=f"tariff_{name}"
            )
        )
    await message.answer("Выбери тариф:", reply_markup=markup)

async def process_fake_payment(callback: types.CallbackQuery):
    tariff_name = callback.data.split('_', 1)[1]
    days = TARIFFS[tariff_name]["days"]

    user = session.query(User).filter_by(user_id=callback.from_user.id).first()
    if user:
        user.is_active = True
        session.commit()

        config_path, qr_path = generate_wg_config(user.user_id, days)
        await bot.send_message(callback.from_user.id, f"Тариф '{tariff_name}' активирован! Вот твой конфиг:")

        with open(config_path, "rb") as config_file:
            await bot.send_document(callback.from_user.id, config_file)
        with open(qr_path, "rb") as qr_file:
            await bot.send_photo(callback.from_user.id, qr_file)

async def get_config(message: types.Message):
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if not user or not user.is_active:
        await message.answer("У тебя нет активной подписки! Выбери тариф через 'Купить VPN 🚀'")
        return

    config_path, qr_path = generate_wg_config(user.user_id, 30)
    with open(config_path, "rb") as config_file:
        await message.answer_document(config_file)
    with open(qr_path, "rb") as qr_file:
        await message.answer_photo(qr_file)

async def stats(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    users_count = session.query(User).count()
    await message.answer(f"📊 Статистика:\n👥 Юзеров: {users_count}")

async def how_install(message: types.Message):
    text = (
        "Привет! 👋 Вот как настроить WireGuard на компьютере и телефоне:\n\n"
        "💻 **Для компьютера:**\n"
        "1. Скачай и установи WireGuard с официального сайта.\n"
        "2. Импортируй конфиг, который я тебе выдал.\n"
        "3. Включи VPN через приложение.\n\n"
        "📱 **Для телефона:**\n"
        "1. Установи приложение WireGuard из App Store или Google Play.\n"
        "2. Добавь новый туннель, импортировав конфиг через файл или QR-код.\n"
        "3. Включи VPN.\n\n"
        "Если что — пиши, помогу! 😊"
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

# Регистрация хэндлеров с фильтрами
dp.message.register(start, Command(commands=["start"]))
dp.message.register(buy_vpn, lambda message: message.text == "Купить VPN 🚀")
dp.callback_query.register(process_fake_payment, lambda c: c.data and c.data.startswith('tariff_'))
dp.message.register(get_config, lambda message: message.text == "Мой конфиг ⚙️")
dp.message.register(stats, lambda message: message.text == "Статистика 📊")
dp.message.register(how_install, lambda message: message.text == "Как установить конфиг 🛠️")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.command import Command  # noqa
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter

from config import TOKEN, ADMINS
from database import User, session
from wg_utils import generate_wg_config
from datetime import datetime
import asyncio
import subprocess
import os

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- Клавиатуры ---
user_keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="Купить VPN 🚀")],
        [KeyboardButton(text="Мой конфиг ⚙️"), KeyboardButton(text="Поддержка 🆘")],
        [KeyboardButton(text="Как установить конфиг 📖")],
    ],
)

admin_keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="Статистика 📊"), KeyboardButton(text="Юзеры 👥"), KeyboardButton(text="Обновить бот 🔄")],
        [KeyboardButton(text="Бан 🔨"), KeyboardButton(text="Рассылка 📢")],
    ],
)

# --- Тарифы ---
TARIFFS = {
    "1 месяц": {"days": 30},
    "3 месяца": {"days": 90},
    "6 месяцев": {"days": 180},
}

# --- Состояния ---
class MailingState(StatesGroup):
    waiting_for_text = State()

# --- Хендлеры ---
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
        await message.answer("Привет! Купи VPN и катайся без блоков!", reply_markup=user_keyboard)

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
        await message.answer("Нет активной подписки. Купи VPN через 'Купить VPN 🚀'")
        return
    config_path, qr_path = generate_wg_config(user.user_id, 30)
    await message.answer_document(FSInputFile(config_path))
    await message.answer_photo(FSInputFile(qr_path))

async def support(message: types.Message):
    await message.answer("Поддержка: @your_support_username или напиши сюда ваши вопросы!")

async def how_install(message: types.Message):
    text = (
        "📖 *Как установить VPN-конфиг* 📖\n"
        "1. Скачай `.conf` файл на ПК или телефон.\n"
        "2. На ПК: установи WireGuard и импортируй через 'Import tunnel from file' 🌐\n"
        "3. На телефон: установи WireGuard из AppStore/PlayMarket и импортируй конфиг 📱\n"
        "4. Нажми 'Activate' и пользуйся VPN 🚀\n"
        "Если что-то не работает — пиши в поддержку 🆘"
    )
    await message.answer(text, parse_mode="Markdown")

async def stats(message: types.Message):
    count = session.query(User).count()
    await message.answer(f"📊 Всего пользователей: {count}")

async def users_list(message: types.Message):
    users = session.query(User.user_id).all()
    ids = [str(u.user_id) for u in users]
    await message.answer("Список user_id:\n" + "\n".join(ids))

async def ban_user(message: types.Message):
    await message.answer("Функция бана временно недоступна.")

async def mailing(message: types.Message, state: FSMContext):
    await message.answer("Напиши текст рассылки (будет отправлен всем пользователям):")
    await state.set_state(MailingState.waiting_for_text)

async def get_text(msg: types.Message, state: FSMContext):
    users = session.query(User.user_id).all()
    for u in users:
        try:
            await bot.send_message(u.user_id, msg.text)
        except:
            continue
    await msg.answer("✅ Рассылка завершена")
    await state.clear()

async def update_bot(message: types.Message):
    await message.answer("🔄 Начинаю обновление бота...")
    subprocess.call(["git", "-C", "/root/vpnbot", "pull"] )
    await message.answer("✅ Обновление завершено, перезапуск...")
    os.execv("/usr/bin/python3", ["python3", "/root/vpnbot/bot.py"])

# --- Регистрация хендлеров ---
dp.message.register(start, Command(commands=["start"]))
dp.message.register(buy_vpn, lambda m: m.text == "Купить VPN 🚀")
dp.callback_query.register(process_fake_payment, lambda cb: cb.data and cb.data.startswith("tariff_"))
dp.message.register(get_config, lambda m: m.text == "Мой конфиг ⚙️")
dp.message.register(support, lambda m: m.text == "Поддержка 🆘")
dp.message.register(how_install, lambda m: m.text == "Как установить конфиг 📖")

dp.message.register(stats, lambda m: m.text == "Статистика 📊")
dp.message.register(users_list, lambda m: m.text == "Юзеры 👥")
dp.message.register(update_bot, lambda m: m.text == "Обновить бот 🔄")
dp.message.register(ban_user, lambda m: m.text == "Бан 🔨")
dp.message.register(mailing, lambda m: m.text == "Рассылка 📢")
dp.message.register(get_text, StateFilter(MailingState.waiting_for_text))

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

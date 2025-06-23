from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.command import Command, CommandObject

from config import TOKEN, ADMINS
from database import User, session
from wg_utils import generate_wg_config
from datetime import datetime
import asyncio
import os

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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

TARIFFS = {
    "1 месяц": {"days": 30},
    "3 месяца": {"days": 90},
    "6 месяцев": {"days": 180},
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
        await message.answer("Привет! Купи VPN и катайся без блоков!", reply_markup=user_keyboard)

# Общая функция поиска пользователя в БД по id или username
def find_user_by_id_or_username(identifier: str):
    if identifier.startswith('@'):
        username = identifier[1:]
        return session.query(User).filter_by(username=username).first()
    else:
        try:
            user_id = int(identifier)
            return session.query(User).filter_by(user_id=user_id).first()
        except ValueError:
            return None

# Бан пользователя
async def ban_user(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для бана пользователей.")
        return
    args = command.args
    if not args:
        await message.answer("❗ Укажите user_id или @username для бана.\nПример: /ban 123456789")
        return
    user = find_user_by_id_or_username(args.strip())
    if not user:
        await message.answer("❗ Пользователь не найден.")
        return
    user.is_active = False
    session.commit()
    await message.answer(f"✅ Пользователь {user.username or user.user_id} заблокирован.")

# Разбан пользователя
async def unban_user(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для разблокировки пользователей.")
        return
    args = command.args
    if not args:
        await message.answer("❗ Укажите user_id или @username для разблокировки.\nПример: /unban 123456789")
        return
    user = find_user_by_id_or_username(args.strip())
    if not user:
        await message.answer("❗ Пользователь не найден.")
        return
    user.is_active = True
    session.commit()
    await message.answer(f"✅ Пользователь {user.username or user.user_id} разблокирован.")

# Статистика пользователей с подробным списком
async def stats(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для просмотра статистики.")
        return
    users = session.query(User).all()
    total = len(users)
    active = sum(1 for u in users if u.is_active)
    inactive = total - active

    text = f"📊 Статистика пользователей:\nВсего: {total}\nАктивных: {active}\nЗаблокированных: {inactive}\n\nСписок пользователей:\n"
    for u in users:
        status = "✅ Активен" if u.is_active else "❌ Заблокирован"
        name = u.username if u.username else str(u.user_id)
        text += f"- {name} — {status}\n"
    await message.answer(text)

# Регистрация хендлеров
dp.message.register(start, Command(commands=["start"]))
dp.message.register(ban_user, Command(commands=["ban"]))
dp.message.register(unban_user, Command(commands=["unban"]))
dp.message.register(stats, lambda m: m.text == "Статистика 📊")

# Тут добавь остальные хендлеры из твоей версии, например buy_vpn, get_config и т.п.

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.command import Command, CommandObject
from aiogram.enums import ParseMode

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

# --- Функции ---

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
    tariff = callback.data.split("_", 1)[1]
    days = TARIFFS[tariff]["days"]
    user = session.query(User).filter_by(user_id=callback.from_user.id).first()
    if user:
        user.is_active = True
        session.commit()
        config_path, qr_path = generate_wg_config(user.user_id, days)
        await bot.send_message(callback.from_user.id, f"Тариф '{tariff}' активирован! Вот конфиг:")
        await bot.send_document(callback.from_user.id, FSInputFile(config_path))
        await bot.send_photo(callback.from_user.id, FSInputFile(qr_path))
    await callback.answer()  # Чтобы убрать "часики" в UI

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
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

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

async def users_list(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав для просмотра списка пользователей.")
        return
    users = session.query(User.user_id).all()
    ids = [str(u.user_id) for u in users]
    await message.answer("Список user_id:\n" + "\n".join(ids))

# Универсальная функция поиска пользователя
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

async def mailing(message: types.Message):
    await message.answer("Функция рассылки временно недоступна.")

async def update_bot(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У вас нет прав на обновление бота.")
        return
    await message.answer("🔄 Начинаю обновление бота...")
    proc = await asyncio.create_subprocess_exec("git", "-C", "/root/vpnbot", "pull", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    output = (stdout + stderr).decode('utf-8')
    await message.answer(f"📥 Результат git pull:\n<pre>{output}</pre>", parse_mode=ParseMode.HTML)
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
dp.message.register(ban_user, Command(commands=["ban"]))
dp.message.register(unban_user, Command(commands=["unban"]))
dp.message.register(mailing, lambda m: m.text == "Рассылка 📢")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

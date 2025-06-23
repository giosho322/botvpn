from aiogram import Bot, Dispatcher, executor, types #rrrrr
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import TOKEN, ADMINS
from database import User, session
from wg_utils import generate_wg_config
from datetime import datetime

# Инициализация бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

### --- Клавиатуры --- ###
user_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
user_keyboard.add(KeyboardButton("Купить VPN 🚀"))
user_keyboard.add(KeyboardButton("Мой конфиг ⚙️"), KeyboardButton("Поддержка 🆘"))

admin_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
admin_keyboard.add(KeyboardButton("Статистика 📊"), KeyboardButton("Юзеры 👥"))
admin_keyboard.add(KeyboardButton("Бан 🔨"), KeyboardButton("Рассылка 📢"))

### --- Тарифы --- ###
TARIFFS = {
    "1 месяц": {"days": 30, "price": 0},  # Цены больше не имеют значения
    "3 месяца": {"days": 90, "price": 0},
    "6 месяцев": {"days": 180, "price": 0},
}

### --- Обработчики команд --- ###
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if not user:
        user = User(
            user_id=message.from_user.id,
            username=message.from_user.username,
            join_date=datetime.now(),
            is_active=True  # Автоматически активируем
        )
        session.add(user)
        session.commit()

    if user.user_id in ADMINS:
        await message.answer("Админ-панель", reply_markup=admin_keyboard)
    else:
         await message.answer("Админ-панель", reply_markup=admin_keyboard)
    else:
        await message.answer("Привет, кожанный! Купи VPN и катайся без блоков!", reply_markup=user_keyboard)

@dp.message_handler(text="Купить VPN 🚀")
async def buy_vpn(message: types.Message):
    markup = InlineKeyboardMarkup()
    for name, data in TARIFFS.items():
        markup.add(InlineKeyboardButton(
            text=f"{name} (временно бесплатно)",
            callback_data=f"tariff_{name}"
        ))
    await message.answer("Выбери тариф:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('tariff_'))
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

@dp.message_handler(text="Мой конфиг ⚙️")
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

@dp.message_handler(text="Статистика 📊")
async def stats(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    users_count = session.query(User).count()
    await message.answer(f"📊 Статистика:\n👥 Юзеров: {users_count}")

### --- Запуск бота --- ###
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

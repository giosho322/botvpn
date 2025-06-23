from aiogram import Bot, Dispatcher, executor, types  # Основные компоненты aiogram
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton  # Кнопки
from aiogram.contrib.fsm_storage.memory import MemoryStorage  # Для хранения состояний
from config import TOKEN, ADMINS, WG_SERVER_IP, WG_SERVER_PUBKEY, CRYPTOBOT_TOKEN  # Настройки
from database import User, Subscription, session  # База данных
from wg_utils import generate_wg_config  # Генератор конфигов
import requests  # Для API запросов (оплата)
from datetime import datetime, timedelta  # Работа с датами
import os  # Для работы с файлами

# Инициализация бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()  # Хранилище состояний (пока в оперативке)
dp = Dispatcher(bot, storage=storage)  # Диспетчер (обрабатывает сообщения)

### --- Клавиатуры --- ###
user_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
user_keyboard.add(KeyboardButton("Купить VPN 🚀"))
user_keyboard.add(KeyboardButton("Мой конфиг ⚙️"), KeyboardButton("Поддержка 🆘"))

admin_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
admin_keyboard.add(KeyboardButton("Статистика 📊"), KeyboardButton("Юзеры 👥"))
admin_keyboard.add(KeyboardButton("Бан 🔨"), KeyboardButton("Рассылка 📢"))

### --- Тарифы --- ###
TARIFFS = {
    "1 месяц": {"days": 30, "price": 5},  # 5$ за месяц
    "3 месяца": {"days": 90, "price": 12},  # 12$ за 3 месяца
    "6 месяцев": {"days": 180, "price": 20},  # 20$ за полгода
}

### --- Функция создания инвойса (CryptoBot) --- ###
def create_invoice(amount, user_id):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    data = {
        "amount": amount,
        "asset": "USDT",  # Принимаем USDT
        "description": f"Оплата VPN для user_{user_id}",
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()["result"]["pay_url"]  # Ссылка на оплату

### --- Обработчики команд --- ###
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if not user:
        user = User(
            user_id=message.from_user.id,
            username=message.from_user.username,
            join_date=datetime.now()
        )
        session.add(user)
        session.commit()

    if user.user_id in ADMINS:
        await message.answer("Админ-панель", reply_markup=admin_keyboard)
    else:
        await message.answer("Привет, кожанный! Купи VPN и катайся без блоков!", reply_markup=user_keyboard)

@dp.message_handler(text="Купить VPN 🚀")
async def buy_vpn(message: types.Message):
    markup = InlineKeyboardMarkup()
    for name, data in TARIFFS.items():
        markup.add(InlineKeyboardButton(
            text=f"{name} - {data['price']} USDT",
            callback_data=f"tariff_{name}"
        ))
    await message.answer("Выбери тариф:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('tariff_'))
async def process_payment(callback: types.CallbackQuery):
    tariff_name = callback.data.split('_')[1]
    tariff = TARIFFS[tariff_name]
    invoice_url = create_invoice(tariff["price"], callback.from_user.id)
    await bot.send_message(
        callback.from_user.id,
        f"Оплати {tariff['price']} USDT:\n{invoice_url}\nПосле оплаты конфиг придёт автоматически."
    )

@dp.message_handler(text="Мой конфиг ⚙️")
async def get_config(message: types.Message):
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if not user or not user.is_active:
        await message.answer("У тебя нет активной подписки! Купи VPN через /buy")
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
    active_subs = session.query(Subscription).filter(Subscription.end_date > datetime.now()).count()
    await message.answer(f"📊 Статистика:\n👥 Юзеров: {users_count}\n🚀 Активных подписок: {active_subs}")

### --- Запуск бота --- ###
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
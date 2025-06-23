from aiogram.types import InputFile

async def buy_vpn(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text=f"{name} (временно бесплатно)", callback_data=f"tariff_{name}")]
        for name in TARIFFS.keys()
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
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

        config_file = InputFile(config_path)
        qr_file = InputFile(qr_path)
        await bot.send_document(callback.from_user.id, config_file)
        await bot.send_photo(callback.from_user.id, qr_file)

async def get_config(message: types.Message):
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if not user or not user.is_active:
        await message.answer("У тебя нет активной подписки! Выбери тариф через 'Купить VPN 🚀'")
        return

    config_path, qr_path = generate_wg_config(user.user_id, 30)
    config_file = InputFile(config_path)
    qr_file = InputFile(qr_path)
    await message.answer_document(config_file)
    await message.answer_photo(qr_file)

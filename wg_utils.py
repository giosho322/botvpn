import os  # Для работы с файлами
import qrcode  # Для QR-кодов (чтобы юзеры не ебали мозг)
from datetime import datetime, timedelta  # Для работы с датами
from config import WG_SERVER_PUBKEY
from config import WG_SERVER_IP

# Папка, где будут лежать конфиги (создаётся автоматом)
CONFIGS_DIR = "configs"
os.makedirs(CONFIGS_DIR, exist_ok=True)  # exist_ok=True – если папка есть, ошибки не будет

def generate_wg_config(user_id: int, days: int):
    """Генерирует конфиг и QR-код для пользователя"""
    # Генерим приватный ключ (через команду wg genkey)
    private_key = os.popen("wg genkey").read().strip()  # strip() убирает лишние пробелы

    # Получаем публичный ключ из приватного (через wg pubkey)
    public_key = os.popen(f"echo '{private_key}' | wg pubkey").read().strip()

    # Даём пользователю IP вида 10.0.0.X (чтобы не было конфликтов)
    ip = f"10.0.0.{user_id % 254 + 2}"  # %254 – чтобы не вылезти за пределы сети

    # Сам конфиг (тут всё по стандарту WG)
    config = f"""
[Interface]
PrivateKey = {private_key}
Address = {ip}/24
DNS = 8.8.8.8  # Гугловский DNS, можно сменить

[Peer]
PublicKey = {WG_SERVER_PUBKEY}
Endpoint = {WG_SERVER_IP}:51820
AllowedIPs = 0.0.0.0/0  # Весь трафик через VPN
"""

    # Сохраняем конфиг в файл
    config_path = f"{CONFIGS_DIR}/client_{user_id}.conf"
    with open(config_path, "w") as f:
        f.write(config.strip())  # strip() убирает лишние переносы

    # Генерим QR-код (чтобы юзеры могли быстро подключиться)
    qr = qrcode.make(config)
    qr_path = f"{CONFIGS_DIR}/client_{user_id}.png"
    qr.save(qr_path)

    return config_path, qr_path  # Возвращаем пути к файлам

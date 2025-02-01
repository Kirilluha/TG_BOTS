import asyncio
import socket
import os
import platform
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from dotenv import load_dotenv
from aiogram.exceptions import TelegramBadRequest
import time

# Загрузка переменных из .env
load_dotenv()

# Конфигурация из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
PC_MAC_ADDRESS = os.getenv("PC_MAC_ADDRESS")
PC_IP_ADDRESS = os.getenv("PC_IP_ADDRESS")
BROADCAST_ADDRESS = os.getenv("BROADCAST_ADDRESS")
PING_COUNT = int(os.getenv("PING_COUNT", "1"))
TCP_SERVER_IP = os.getenv("TCP_SERVER_IP")
TCP_SERVER_PORT = int(os.getenv("TCP_SERVER_PORT", "65432"))
ALLOWED_USERS = set(map(int, os.getenv("ALLOWED_USERS", "").split(',')))

if not all([BOT_TOKEN, PC_MAC_ADDRESS, PC_IP_ADDRESS, TCP_SERVER_IP, TCP_SERVER_PORT]):
    raise ValueError("Необходимо установить BOT_TOKEN, PC_MAC_ADDRESS, PC_IP_ADDRESS, TCP_SERVER_IP и TCP_SERVER_PORT в переменные окружения.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Кнопки
wake_button = InlineKeyboardButton(text="Включить ПК", callback_data="wake_pc")
shutdown_button = InlineKeyboardButton(text="Выключить ПК", callback_data="shutdown_pc")
sleep_button = InlineKeyboardButton(text="Перевести в сон", callback_data="sleep_pc")

keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [wake_button],
    [shutdown_button, sleep_button],
])

# Асинхронные задачи для команд
current_shutdown_task = None
current_sleep_task = None

# Переменные для автообновления
auto_update_task = None
auto_update_message_id = None
auto_update_chat_id = None

# TCP-клиент
class TCPClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.reader = None
        self.writer = None
        self.connected = False
        self.lock = asyncio.Lock()

    def log_info(self, message):
        """Функция для вывода информационных сообщений с временной меткой."""
        print(f"[INFO] {time.strftime('%Y-%m-%d %H:%M:%S')} - {message}")

    def log_error(self, message):
        """Функция для вывода сообщений об ошибках с временной меткой."""
        print(f"[ERROR] {time.strftime('%Y-%m-%d %H:%M:%S')} - {message}")

    async def connect(self):
        while not self.connected:
            try:
                self.log_info(f"Пытаемся подключиться к {self.server_ip}:{self.server_port}")
                self.reader, self.writer = await asyncio.open_connection(self.server_ip, self.server_port)
                self.connected = True
                self.log_info("Успешно подключились к серверу.")
            except (ConnectionRefusedError, OSError) as e:
                self.log_error(f"Не удалось подключиться к серверу: {e}. Повторная попытка через 2 секунды.")
                self.connected = False  # Добавляем этот момент, чтобы статус обновлялся!

                await asyncio.sleep(2)

    async def send_command(self, command):
        async with self.lock:
            if not self.connected:
                await self.connect()
            try:
                self.log_info(f"Отправка команды: {command}")
                self.writer.write(command.encode())
                await self.writer.drain()
                response = await asyncio.wait_for(self.reader.read(1024), timeout=5)
                decoded_response = response.decode()
                self.log_info(f"Получен ответ: {decoded_response}")
                return decoded_response
            except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionResetError) as e:
                self.log_error(f"Ошибка при отправке команды: {e}. Попытка переподключиться.")
                self.connected = False
                await self.connect()
                return "Не удалось отправить команду."

tcp_client = TCPClient(TCP_SERVER_IP, TCP_SERVER_PORT)

async def tcp_client_runner():
    """Поддерживаем соединение с TCP-сервером в фоне."""
    await tcp_client.connect()
    while True:
        await asyncio.sleep(3600)  # Держим клиент активным, пытаемся reconnect

async def send_tcp_command(command: str) -> str:
    return await tcp_client.send_command(command)

def wake_on_lan(mac: str, ip: str = PC_IP_ADDRESS):
    """Отправляет WOL-пакет по MAC-адресу."""
    try:
        mac_bytes = bytes.fromhex(mac.replace(':', '').replace('-', ''))
        magic_packet = b'\xff' * 6 + mac_bytes * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(magic_packet, (ip, 9))
        # Логирование успешной отправки
        print(f"[INFO] {time.strftime('%Y-%m-%d %H:%M:%S')} - WOL-пакет успешно отправлен на MAC: {mac}")
    except Exception as e:
        # Логирование ошибки с деталями
        print(f"[ERROR] {time.strftime('%Y-%m-%d %H:%M:%S')} - Ошибка при отправке WOL-пакета: {str(e)}")

async def is_host_up(ip: str) -> bool:
    """Проверяем, доступен ли хост через ping."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    timeout = '1000' if platform.system().lower() == 'windows' else '1'
    command = ['ping', param, str(PING_COUNT), timeout_param, str(timeout), ip]

    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        return_code = await proc.wait()
        return return_code == 0
    except Exception:
        return False

async def update_status_message():
    """
    Постоянно (в бесконечном цикле) обновляет статус
    в сообщении, которое мы сохранили при /start.
    """
    previous_text = ""

    while True:
        pc_status = "ПК включен" if await is_host_up(PC_IP_ADDRESS) else "ПК выключен"
        tcp_status = "Сервер: подключен" if tcp_client.connected else "Сервер: нет соединения"

        text_to_show = f"Статус ПК: {pc_status}\n{tcp_status}"

        if text_to_show != previous_text:
            # print("Обновляем")
            try:
                await bot.edit_message_text(
                    chat_id=auto_update_chat_id,
                    message_id=auto_update_message_id,
                    text=text_to_show,
                    reply_markup=keyboard
                )
                previous_text = text_to_show
            except TelegramBadRequest as e:
                # "message is not modified" — не критично
                if "message is not modified" in str(e):
                    pass
                else:
                    pass  # Можно логировать или обрабатывать другие ошибки
            except Exception:
                pass
        # else: 
            # print("Обновление не нужно")
        await asyncio.sleep(3) 

@dp.message(Command("start"))
async def start_command(message: Message):
   
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("У вас нет доступа к этому боту.")
        return

    sent_msg = await message.answer("Подождите, идёт инициализация статуса...", reply_markup=keyboard)

    # Запоминаем chat_id и message_id для дальнейшей правки
    global auto_update_message_id, auto_update_chat_id, auto_update_task
    auto_update_chat_id = sent_msg.chat.id
    auto_update_message_id = sent_msg.message_id

    # Если ещё не запускали задачу автообновления — запускаем
    if not auto_update_task:
        auto_update_task = asyncio.create_task(update_status_message())

@dp.callback_query(F.data == "wake_pc")
async def on_wake_pc(callback_query: CallbackQuery):
    # Логирование действия
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] User {callback_query.from_user.id} initiated WAKE command")
    wake_on_lan(PC_MAC_ADDRESS, PC_IP_ADDRESS)
    await callback_query.answer("Сигнал WOL отправлен.")

@dp.callback_query(F.data == "shutdown_pc")
async def on_shutdown_pc(callback_query: CallbackQuery):
    # Логирование действия
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] User {callback_query.from_user.id} initiated SHUTDOWN command")
    global current_shutdown_task
    if current_shutdown_task and not current_shutdown_task.done():
        current_shutdown_task.cancel()

    async def shutdown_task():
        try:
            await send_tcp_command('shutdown')
            await callback_query.answer("Команда на выключение отправлена.")
        except asyncio.CancelledError:
            raise
        except Exception:
            await callback_query.answer("Произошла ошибка при отправке команды.")

    current_shutdown_task = asyncio.create_task(shutdown_task())

@dp.callback_query(F.data == "sleep_pc")
async def on_sleep_pc(callback_query: CallbackQuery):
    # Логирование действия
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] User {callback_query.from_user.id} initiated SLEEP command")
    global current_sleep_task
    if current_sleep_task and not current_sleep_task.done():
        current_sleep_task.cancel()

    async def sleep_task():
        try:
            await send_tcp_command('sleep')
            await callback_query.answer("Команда на перевод в сон отправлена.")
        except asyncio.CancelledError:
            raise
        except Exception:
            await callback_query.answer("Произошла ошибка при отправке команды.")
    current_sleep_task = asyncio.create_task(sleep_task())
    
async def main():
    # Запуск TCP-клиента в фоне
    asyncio.create_task(tcp_client_runner())
    # Запуск бота
    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        pass  # Остановка бота вручную

if __name__ == "__main__":
    asyncio.run(main())

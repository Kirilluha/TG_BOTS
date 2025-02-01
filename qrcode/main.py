import asyncio
import io
import qrcode
import os
import traceback
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import BufferedInputFile
from aiogram.filters import Command
from dotenv import load_dotenv
from qrcode.image.svg import SvgPathImage

# Загружаем переменные окружения из .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def log(level, message):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}")

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    try:
        await message.answer("Привет! Отправь мне ссылку, и я создам QR-код.")
        log("INFO", f"Отправлено приветствие пользователю {message.from_user.id}")
    except Exception as e:
        log("ERROR", f"Ошибка в send_welcome: {str(e)}\n{traceback.format_exc()}")

@dp.message()
async def generate_qr(message: types.Message):
    try:
        log("INFO", f"Получено сообщение от {message.from_user.id}: {message.text}")

        if not message.text:
            await message.answer("Пожалуйста, отправьте текст (например, ссылку), чтобы я мог создать QR-код.")
            return

        text = message.text
        
        # Создаем QR-код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        # Создаем png изображение
        img = qr.make_image(fill='black', back_color='white')
        # Создаем SVG изображение
        img_svg = qr.make_image(image_factory=SvgPathImage)
        # Сохраняем изображение в буфер
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Сохраняем SVG в байтовый буфер
        svg_buffer = io.BytesIO()
        img_svg.save(svg_buffer)  
        svg_data = svg_buffer.getvalue()

        # Отправляем изображение
        photo = BufferedInputFile(img_bytes.read(), filename="qrcode.png")
        await message.answer_photo(photo)
        log("INFO", f"QR-код png успешно отправлен пользователю {message.from_user.id}")
        
        # Отправляем SVG как документ
        file = BufferedInputFile(svg_data, filename="qrcode.svg")
        await message.answer_document(file)
        log("INFO", f"QR-код svg успешно отправлен пользователю {message.from_user.id}")        
    except Exception as e:
        error_msg = f"Ошибка в generate_qr: {str(e)}\n{traceback.format_exc()}"
        log("ERROR", error_msg)
        await message.answer("Произошла ошибка при генерации QR-кода. Попробуйте еще раз.")

async def main():
    try:
        log("INFO", "Бот запущен")
        await dp.start_polling(bot)
    except Exception as e:
        log("ERROR", f"Ошибка в main: {str(e)}\n{traceback.format_exc()}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("WARNING", "Бот остановлен пользователем")
    except Exception as e:
        log("ERROR", f"Критическая ошибка: {str(e)}\n{traceback.format_exc()}")

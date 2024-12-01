import logging
import re, os
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware


load_dotenv()

API_TOKEN = os.getenv('API_KEY')
print(API_TOKEN)

# Данные для SMTP
SMTP_SERVER = 'smtp.yandex.ru'
SMTP_PORT = 465
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Регулярное выражение для проверки email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

user_data = {}


# Отправка email
def send_email(to_email, subject, body):
    try:

        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
            logging.info(f'Email отправлен на {to_email}')
    except Exception as e:
        logging.error(f'Ошибка отправки email: {e}')


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button = KeyboardButton("Введите ваш email")
    keyboard.add(button)

    await message.reply(
        "Здравствуйте! Пожалуйста, нажмите кнопку ниже, чтобы ввести ваш email для отправления сообщений.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    # Переход к сбору email
    user_data[message.chat.id] = {'stage': 'waiting_for_email'}


# Хэндлер для получения email
@dp.message_handler(lambda message: user_data.get(message.chat.id, {}).get('stage') == 'waiting_for_email')
async def get_email(message: types.Message):
    email = message.text.strip()
    if re.match(EMAIL_REGEX, email):
        # Сохраняем email
        user_data[message.chat.id]['email'] = email
        user_data[message.chat.id]['stage'] = 'waiting_for_message'
        await message.reply("Теперь напишите текст сообщения, который вы хотите отправить.")
    else:
        await message.reply("Пожалуйста, введите корректный email !")


@dp.message_handler(lambda message: user_data.get(message.chat.id, {}).get('stage') == 'waiting_for_message')
async def get_message(message: types.Message):
    text_message = message.text.strip()
    email = user_data[message.chat.id].get('email')
    if email and text_message:
        # Отправляем email
        send_email(email, "Сообщение от пользователя", text_message)
        await message.reply(f"Сообщение успешно отправлено на {email}.")

        # Добавляем кнопку для отправки нового сообщения
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        button = KeyboardButton("Отправить сообщение другому пользователю")
        keyboard.add(button)

        await message.reply(
            "Вы можете отправить сообщение другому пользователю. Нажмите кнопку ниже.",
            reply_markup=keyboard
        )

        # Завершаем взаимодействие
        del user_data[message.chat.id]
    else:
        await message.reply("Ошибка: отсутствует email или текст сообщения. Попробуйте снова.")


# Хэндлер для повторного ввода сообщения
@dp.message_handler(lambda message: message.text == "Отправить сообщение другому пользователю")
async def restart(message: types.Message):
    # Снова начинаем процесс сбора email
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button = KeyboardButton("Введите ваш email")
    keyboard.add(button)

    await message.reply(
        "Пожалуйста, нажмите кнопку ниже, чтобы ввести новый email для отправления сообщений.",
        reply_markup=keyboard
    )
    user_data[message.chat.id] = {'stage': 'waiting_for_email'}


if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)

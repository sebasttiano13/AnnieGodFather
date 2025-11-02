
from aiogram import Router, F, html, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from telethon import TelegramClient

from anniegodfather.clients import DadClient

cmd_router = Router()

class RegisterUserStates(StatesGroup):
    waiting_for_username = State()


@cmd_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")

@cmd_router.message(Command(commands=["register"]))
async def command_register_handler(message: Message, state: FSMContext):
    await message.answer("Введите ваш username:")
    await state.set_state(RegisterUserStates.waiting_for_username)

@cmd_router.message(RegisterUserStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext, dad: DadClient, telethon: TelegramClient, bot: Bot):
    await state.update_data(username=message.text)
    user_data = await state.get_data()
    username = user_data.get("username")
    telegram_id = message.from_user.id
    if username:
        try:
            await dad.register_user(telegram_id=telegram_id, username=username)
        except Exception:
            raise
    await message.answer(f"User with name {username} and telegram id {telegram_id} successfully registered")
    await state.clear()

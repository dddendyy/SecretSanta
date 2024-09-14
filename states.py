from aiogram.dispatcher.filters.state import StatesGroup, State

class Profile(StatesGroup):
    sex = State()
    name = State()
    surname = State()
    age = State()
    desc = State()

class Room(StatesGroup):
    name = State()
    member_count = State()
    desc = State()
    confirm = State()
    exit_confirm = State()
    kick_confirm = State()
    # validity = State()

class Connect(StatesGroup):
    code = State()

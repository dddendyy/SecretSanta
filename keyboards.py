from aiogram.types import (ReplyKeyboardRemove,
                           ReplyKeyboardMarkup,
                           KeyboardButton,
                           InlineKeyboardMarkup,
                           InlineKeyboardButton)


stop_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
stop_button = KeyboardButton(text='Cтоп ❌')
stop_keyboard.add(stop_button)


command_kb = ReplyKeyboardMarkup(resize_keyboard=True)
create_room = KeyboardButton(text='Создать комнату 🚪')
create_profile = KeyboardButton(text='Заполнить информаю о себе 📋')
show_profile = KeyboardButton(text='Мой профиль 👤')
my_rooms = KeyboardButton(text='Мои комнаты 👥')
join_room = KeyboardButton(text='Вступить в комнату ✅')
(command_kb.add(create_profile, show_profile)
 .add(create_room, my_rooms)
 .add(join_room))


male_female_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
male = '♂'
female = '♀'
male_female_keyboard.add(male, female).add(stop_button)

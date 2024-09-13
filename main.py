import database
from config import TOKEN
from states import *
from keyboards import *
from aiogram import Bot, executor, Dispatcher, types
from aiogram.utils.exceptions import BadRequest
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from magic_filter import F


greetings_message = '''Привет!\n
Перед тобой бот для игры в <i>Тайного Санту</i>🎅 
Все кнопки у тебя на экране, писать ничего <b>не надо!</b> ⚠\n
Чтобы создать свой профиль, нажми на кнопку <b>"Заполнить информаю о себе 📋"</b>\n
Чтобы посмотреть уже созданные профиль, нажми <b>"Мой профиль 👤"</b>'''


storage = MemoryStorage()
bot = Bot(TOKEN)
dp = Dispatcher(bot=bot,
                storage=storage)


async def on_startup(_):
    '''
    функция, запускающаяся при старте
    '''
    await database.start()


@dp.message_handler(commands='start')
async def start_cmd(message: types.Message):
    await message.answer(text=greetings_message,
                         parse_mode=types.ParseMode.HTML,
                         reply_markup=command_kb)


@dp.message_handler(text='Cтоп ❌', state='*')
async def stop_cmd(message: types.Message, state: FSMContext):
    '''
    Обработчик команды "стоп", то есть команда для выхода из любого состояния
    '''
    current_state = await state.get_state()
    if current_state is None: # если текущее состояние буквально отсутствует
        return # ничего не возвращаем
    else: # иначе кидаем сообщени и финишируем состояние
        await message.answer('Действие прервано пользователем ⚠',
                             reply_markup=command_kb)
        await state.finish()


@dp.message_handler(text='Заполнить информаю о себе 📋')
async def create_profile(message: types.Message):
    '''
    С этой функции начинаем заполнение анкеты
    '''
    await message.answer(text='Отлично! Давай заполним профиль!\n'
                              'Если хочешь закончить, нажми на кнопку "стоп ❌"\n'
                              'Какого ты пола?',
                         reply_markup=male_female_keyboard)
    await database.create_profile(message.from_user.id) # создаём профиль, но не заполняем (см. database)
    await Profile.sex.set()


@dp.message_handler(F.text.in_({'♂', '♀'}),
                    state=Profile.sex)
async def  sex_cmd(message: types.Message, state: FSMContext):
    '''
    Здесь получаем пол от пользователя
    '''
    async with state.proxy() as data: # в хранилище данных состояние записываем данные профиля
        if message.text == '♂':
            data['sex'] = 'М' # если мужской пол - М
        else:
            data['sex'] = 'Ж' # если женский - Ж
    await message.answer(text='Теперь введи имя!',
                         reply_markup=stop_keyboard)
    await Profile.next()


@dp.message_handler(F.text.isalpha(),
                    state=Profile.name)
async def name_cmd(message: types.Message, state: FSMContext):
    '''
    Здесь получаем имя и проверяем его функцией isalpha()
    '''
    async with state.proxy() as data:
        data['name'] = message.text

    await message.answer(text='Спасибо, теперь фамилию!',
                         reply_markup=stop_keyboard)
    await Profile.next()


@dp.message_handler(F.text.isalpha() == False,
                    state=Profile.name)
async def name_error(message: types.Message):
    '''
    метод isalpha делает всю работу за нас,
    проверяет состоит ли строка только из букв
    отлавливает пробелы и спец символы
    прошу прощения у всех девушек, что хотят указать фамилию через дефис :(
    '''
    await message.answer('Введи нормальное имя одним словом без пробелов и специальных символов ⚠')


@dp.message_handler(F.text.isalpha(),
                    state=Profile.surname)
async def surname_cmd(message: types.Message, state: FSMContext):
    '''
    Здесь получаем фамилию и проверяем его функцией isalpha()
    '''
    async with state.proxy() as data:
        data['surname'] = message.text

    await message.answer(text='Спасибо, теперь введи свой возраст!',
                         reply_markup=stop_keyboard)
    await Profile.next()


@dp.message_handler(F.text.isalpha() == False,
                    state=Profile.surname)
async def surname_error(message: types.Message):
    '''
    аналогично хендлеру выше
    '''
    await message.answer('Введи фамилию одним словом без пробелов и специальных символов ⚠')


@dp.message_handler(F.text.isdigit() & (F.text.len() <= 2),
                    state=Profile.age)
async def age_cmd(message: types.Message, state: FSMContext):
    '''
    Здесь получаем возраст и проверяем его функцией isdigit()
    '''
    async with state.proxy() as data:
        data['age'] = message.text

    await message.answer(text='Спасибо, теперь пару слов о себе '
                              '(хобби, любимый фильм, группа, книга, да вообще что угодно)!')
    await Profile.next()


@dp.message_handler((F.text.isdigit() == False) | (F.text.len() > 2),
                    state=Profile.age)
async def error_age(message: types.Message):
    '''
    Если вдруг в возрасте встречены лишний символы,
     либо он не проходит по длине,
    то попапдаем сюдым
    '''
    await message.answer(text='Возраст не может содержать больше <b>двух цифр</b> ⚠\n'
                              'У нас, как у лего, 99+',
                         parse_mode=types.ParseMode.HTML,
                         reply_markup=stop_keyboard)


@dp.message_handler(F.text,
                    state=Profile.desc)
async def desc_cmd(message: types.Message, state: FSMContext):
    '''
    Получаем описание пользователя и соответственно обновляем инфу в БД
    '''
    async with state.proxy() as data:
        data['desc'] = message.text
        data['username'] = message.from_user.username

    await database.update_profile(message.from_user.id, state)
    await message.answer('Профиль создан, чтобы посмотреть, нажми <b>"Мой профиль 👤"</b>',
                         parse_mode=types.ParseMode.HTML,
                         reply_markup=command_kb)
    await state.finish()


@dp.message_handler(text='Мой профиль 👤')
async def show_profile(message: types.Message):
    '''
    Получаем инфу о профиле, чтобы её вывести с помощью database.show_profile()
                                                        ^^^^^^^ cм. database.py
    И сразу суём в обработчик исключений, чтобы обработать вызов "пустого" профиля
    '''
    profile = await database.show_profile(message.from_user.id)

    if profile is None:
        await message.answer(text='Упс! Твой профиль не заполнен ☹\n'
                             'Мы можем это исправить! ☝🤓\n'
                             'Просто нажми <b>Заполнить информаю о себе 📋</b>',
                             parse_mode=types.ParseMode.HTML)
        return

    for value in profile.values():
        if value in ('', 0):
            await message.answer(text='Упс! Твой профиль заполнен не до конца ☹\n'
                                      'Мы можем это исправить! ☝🤓\n'
                                      'Просто нажми <b>Заполнить информаю о себе 📋</b>',
                                 parse_mode=types.ParseMode.HTML)
            return

    await message.answer(text=f"{profile['name']} {profile['surname']}, \n"
                              f"пол: {profile['sex']} \n"
                              f"Возраст: {profile['age']} \n"
                              f"{profile['desc']}")


@dp.message_handler(text='Создать комнату 🚪')
async def create_room(message: types.Message):
    '''
    Хэндлер, вызывающий процесс создания комнаты
    '''
    await message.answer('Введи название для своей комнаты')
    await Room.name.set()


@dp.message_handler(F.text, state=Room.name)
async def name_room(message: types.Message, state: FSMContext):
    '''
    тут уже присваиваем комнате название
    '''
    async with state.proxy() as data:
        data['room_name'] = message.text
    await message.answer('Теперь введи количество игроков (не менее 6-ти игроков)')
    await Room.next()


@dp.message_handler(lambda message: message.text.isdigit() == True
                                     and int(message.text) >= 6
                                     and int(message.text) % 2 == 0
                                     and len(message.text) <= 2,
                    state=Room.member_count)
async def member_count(message: types.Message, state: FSMContext):
    '''
    a тут присваиваем количество игроков
    '''
    async with state.proxy() as data:
        data['member_count'] = message.text

    await message.answer('Замечательно! А теперь нам нужно описание этой комнаты!\n'
                         'Это увидят те, кто сюда подключится 🙋‍♂️')
    await Room.next()


@dp.message_handler(lambda message: message.text.isdigit() != True
                                     or int(message.text) < 6
                                     or len(message.text) > 2,
                    state=Room.member_count)
async def error_member_count(message: types.Message):
    '''
    обработчик дибила(зачеркнуто) некорректного ввода от пользователя
    '''
    await message.answer('Количество игроков должно быть не менее 6-ти!')
    await bot.send_sticker(chat_id=message.from_user.id,
                     sticker='CAACAgQAAxkBAAJHEmXx7XCoC3w4OzkhnY400Nh8R8spAAIJCAACJBZZUj94r2NSYLEVNAQ')


@dp.message_handler(state=Room.desc)
async def room_desc(message: types.Message, state: FSMContext):
    '''
    Делаем описание для комнаты
    '''
    async with state.proxy() as data:
        data['room_desc'] = message.text

    async with state.proxy() as data:
        data['room_id'] = await database.create_room(state, message.from_user.id, message.from_user.username)

    await message.answer('Круто! Группа создана 🎉\n'
                         f'Код для подключения: {data["room_id"]}.'
                         f' Теперь, чтобы подключиться, надо нажать <b>Вступить в комнату ✅</b> и ввести код.\n'
                         f'И всё! Праздник начинается 🥳\n'
                         f'Для просмотра комнат, в которых ты участвуешь, нажми <b>Мои комнаты 👥</b>',
                         parse_mode=types.ParseMode.HTML)
    await state.finish()


@dp.message_handler(text='Вступить в комнату ✅')
async def join_room(message: types.Message):
    await message.answer('Введи код подключения к комнате!')
    user_input = message.text
    await Connect.code.set()


@dp.message_handler(state=Connect.code)
async def connect_cmd(message: types.Message, state=FSMContext):

    room = await database.join_room(message.text, message.from_user.username)

    if room is None:
        await message.answer('Такой комнаты не существует. Введи код повторно ⚠')

    elif room is False:
        await message.answer('Достигнут лимит пользователей в комнате!')
        await state.finish()

    elif room is True:
        await message.answer('Ты уже поключен к этой комнате')
        await state.finish()

    else:
        await message.answer(f'Ты подключен к комнате {room["room_name"]}')
        await state.finish()


@dp.message_handler(text='Мои комнаты 👥')
async def my_rooms(message: types.Message):

    my_rooms = await database.show_rooms_list(message.from_user.username, message.from_user.id)
    await message.answer('Ты состоишь в следующих комнатах 👇')

    for room in my_rooms:
        if str(message.from_user.id) == room["admin"] and room["state"] != "запущена":
            room_text = f'''Название: {room["room_name"]} 👑
{len(room["members"].split(" "))}/{room["member_count"]} участвуют
Описание: {room["desc"]}
Игра {room["state"]}
Код для подключения: {room["room_id"]}'''
            
            admin_keyboard = InlineKeyboardMarkup()
            delete_button = InlineKeyboardButton(text='Удалить комнату',
                                                 callback_data=f'delete {room["room_id"]}')
            shuffle_button = InlineKeyboardButton(text='Начать игру',
                                                 callback_data=f'shuffle {room["room_id"]}')
            admin_keyboard.add(delete_button, shuffle_button)

            await bot.send_message(chat_id=message.from_user.id,
                                   text=room_text,
                                   reply_markup=admin_keyboard)
            
        elif str(message.from_user.id) == room["admin"] and room["state"] == "запущена":
            room_text = f'''Название: {room["room_name"]} 👑
{len(room["members"].split(" "))}/{room["member_count"]} участвуют
Описание: {room["desc"]}
Игра {room["state"]}
Код для подключения: {room["room_id"]}'''
            await bot.send_message(chat_id=message.from_user.id,
                                   text=room_text)
            
        elif str(message.from_user.id) != room["admin"]:
            room_text = room_text = f'''Название: {room["room_name"]} 
{len(room["members"].split(" "))}/{room["member_count"]} участвуют
Описание: {room["desc"]}
Игра {room["state"]}
Код для подключения: {room["room_id"]}'''
            await bot.send_message(chat_id=message.from_user.id,
                                   text=room_text)


@dp.callback_query_handler(F.data.contains('delete'))
async def delete_room(callback: types.CallbackQuery):
    confirm_keyboard = InlineKeyboardMarkup()
    agree_button = InlineKeyboardButton(text='Да',
                                        callback_data=f'confirm_{callback.data[-5:]}')
    disagree_button = InlineKeyboardButton(text='Нет',
                                        callback_data=f'refuse_{callback.data[-5:]}')
    confirm_keyboard.add(agree_button, disagree_button)
    await bot.answer_callback_query(callback_query_id=callback.id,
                                    text='Удаление комнаты')
    await callback.message.edit_text(f'{callback.message.text}\n'
                                     f'----------------------------------------------\n'
                                     f'<b>Вы уверены, что хотите удалить данную комнату?</b>',
                                     reply_markup=confirm_keyboard,
                                     parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(F.data.contains('confirm'))
async def confirm_delete(callback: types.CallbackQuery):
    await database.delete_room(callback.data[-5:])
    await bot.answer_callback_query(callback_query_id=callback.id,
                                    text='Комната удалена')
    await callback.message.delete()


@dp.callback_query_handler(F.data.contains('refuse'))
async def refuse_delete(callback: types.CallbackQuery):
    # await callback.message.edit_text(callback.message.text[:-93])
    await bot.answer_callback_query(callback_query_id=callback.id,
                                    text='Удаление отменено')
    admin_keyboard = InlineKeyboardMarkup()
    delete_button = InlineKeyboardButton(text='Удалить комнату',
                                         callback_data=f'delete {callback.data[-5:]}')
    shuffle_button = InlineKeyboardButton(text='Начать игру',
                                          callback_data=f'shuffle {callback.data[-5:]}')
    admin_keyboard.add(delete_button, shuffle_button)
    await callback.message.edit_text(text=callback.message.text[:-93],
                                     reply_markup=admin_keyboard)


@dp.callback_query_handler(F.data.contains('shuffle'))
async def shuffle_room_confirm(callback: types.CallbackQuery):
    '''
    Если админ нажимает на запуск игры, бот спросит подтверждение
    '''
    confirm_keyboard = InlineKeyboardMarkup()
    start_game_button = InlineKeyboardButton(text='Да',
                                        callback_data=f'start_{callback.data[-5:]}')
    stop_game_button = InlineKeyboardButton(text='Нет',
                                           callback_data=f'stop_{callback.data[-5:]}')
    confirm_keyboard.add(start_game_button, stop_game_button)
    await bot.answer_callback_query(callback_query_id=callback.id,
                                    text='АНЯ, ЗАПУСКАЙ')
    await callback.message.edit_text(f'{callback.message.text}\n'
                                     f'----------------------------------------------\n'
                                     f'<b>Вы уверены, что хотите начать ИГРУ?</b>',
                                     reply_markup=confirm_keyboard,
                                     parse_mode=types.ParseMode.HTML)
    await Room.confirm.set()


@dp.callback_query_handler(F.data.contains('start'), state=Room.confirm)
async def shuffle_room(callback: types.CallbackQuery, state: FSMContext):
    '''
    Если админ согласен на запуск комнаты
    '''
    room_id = callback.data[-5:]
    await database.update_state_started(room_id)
    await bot.answer_callback_query(callback_query_id=callback.id,
                                    text='Игроки перемешаны')
    admin_keyboard = InlineKeyboardMarkup()
    delete_button = InlineKeyboardButton(text='Удалить комнату',
                                         callback_data=f'delete {room_id}')
    admin_keyboard.add(delete_button)
    # await callback.message.edit_text(text=callback.message.text[:-83],
    #                                  reply_markup=admin_keyboard)
    
    shuffled_players_dict = await database.shuffle_players(room_id) # получаем перемешанных распределенных игроков
    new_room = await database.get_room(room_id)

    new_room_text = f'''Название: {new_room["room_name"]} 👑
{len(new_room["members"].split(" "))}/{new_room["member_count"]} участвуют
Описание: {new_room["desc"]}
Игра {new_room["state"]}
Код для подключения: {new_room["room_id"]}'''

    await callback.message.edit_text(text=new_room_text,
                                     reply_markup=admin_keyboard)

    for username in shuffled_players_dict:
        # проходимся по ним
        player = await database.get_profile(username) # получаем игрока, которому отправляем сообщение
        opponent = await database.get_profile(shuffled_players_dict[player['username']]) # и про которого отправляем
        # ну и само сообщение
        await bot.send_message(chat_id=player['member_id'],
                               text='Привет! 👋\n'
                                    'Это бот для игры в Тайного Санту 🎅\n'
                                    'Администратор комнаты, в которой ты состоишь, начал игру.'
                                    ' Теперь тебе нужно подарить подарок человек, чью анкетку ты видишь ниже 🎁\n'
                                    f'{opponent["name"]} {opponent["surname"]}\n'
                                    f'Возраст: {opponent["age"]}\n'
                                    f'{opponent["desc"]}')

    await state.finish()


@dp.callback_query_handler(F.data.contains('stop'), state=Room.confirm)
async def stop_shuffle_room(callback: types.CallbackQuery, state: FSMContext):
    '''
    Если админ НЕ согласен на запуск комнаты
    '''
    await callback.message.answer

    new_room = await database.get_room(callback.data[-5:])
    new_room_text = f'''Название: {new_room["room_name"]} 👑
{len(new_room["members"].split(" "))}/{new_room["member_count"]} участвуют
Описание: {new_room["desc"]}
Игра {new_room["state"]}
Код для подключения: {new_room["room_id"]}'''

    admin_keyboard = InlineKeyboardMarkup()
    delete_button = InlineKeyboardButton(text='Удалить комнату',
                                         callback_data=f'delete {callback.data[-5:]}')
    shuffle_button = InlineKeyboardButton(text='Начать игру',
                                          callback_data=f'shuffle {callback.data[-5:]}')
    admin_keyboard.add(delete_button, shuffle_button)

    await callback.message.edit_text(text=new_room_text,
                                     reply_markup=admin_keyboard)
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup)

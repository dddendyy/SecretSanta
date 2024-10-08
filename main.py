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
    profile = await database.get_profile_by_id(message.from_user.id)

    if profile is None:
        await message.answer(text='Упс! Твой профиль не заполнен ☹\n'
                             'Мы можем это исправить! ☝🤓\n'
                             'Просто нажми <b>"Заполнить информаю о себе 📋"</b>',
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
    player = await database.get_profile_by_id(message.from_user.id)
    if player is None or player["username"] == '':
        await message.answer('Сначала заполни свой профиль через кнопку <b>"Заполнить информаю о себе 📋"</b>',
                             parse_mode=types.ParseMode.HTML)
        return
    await message.answer('Введи название для своей комнаты', reply_markup=stop_keyboard)
    await Room.name.set()


@dp.message_handler(F.text, state=Room.name)
async def name_room(message: types.Message, state: FSMContext):
    '''
    тут уже присваиваем комнате название
    '''
    async with state.proxy() as data:
        data['room_name'] = message.text
    await message.answer('Теперь введи количество игроков (не менее 6-ти игроков)', reply_markup=stop_keyboard)
    await Room.next()


@dp.message_handler(lambda message: message.text.isdigit() == True
                                     and int(message.text) >= 6
                                     and len(message.text) <= 2,
                    state=Room.member_count)
async def member_count(message: types.Message, state: FSMContext):
    '''
    a тут присваиваем количество игроков
    '''
    async with state.proxy() as data:
        data['member_count'] = message.text

    await message.answer('Замечательно! А теперь нам нужно описание этой комнаты!\n'
                         'Это увидят те, кто сюда подключится 🙋‍♂️', reply_markup=stop_keyboard)
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
    player = await database.get_profile_by_id(message.from_user.id)
    if player is None or player["username"] == '':

        await message.answer('Сначала заполни свой профиль через кнопку <b>"Заполнить информаю о себе 📋"</b>',
                             parse_mode=types.ParseMode.HTML)
        return

    await message.answer('Введи код подключения к комнате!', reply_markup=stop_keyboard)
    user_input = message.text
    await Connect.code.set()


@dp.message_handler(state=Connect.code)
async def connect_cmd(message: types.Message, state=FSMContext):

    room = await database.join_room(message.text, message.from_user.username, message)

    if room is None:
        await message.answer('Такой комнаты не существует. Введи код повторно ⚠', reply_markup=stop_keyboard)

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

    player = await database.get_profile_by_id(message.from_user.id)
    if player is None or player["username"] == '':
        await message.answer('Сначала заполни свой профиль через кнопку <b>"Заполнить информаю о себе 📋"</b>',
                             parse_mode=types.ParseMode.HTML)
        return

    my_rooms = await database.show_rooms_list(message.from_user.username, message.from_user.id)
    await message.answer('Ты состоишь в следующих комнатах 👇')

    for room in my_rooms:
        if str(message.from_user.id) == room["admin"] and room["state"] != "запущена": # если админ 

            room_text = (f'Название: {room["room_name"]} 👑\n'
                         f'{len(room["members"].split(" "))}/{room["member_count"]} участвуют\n'
                         f'Описание: {room["desc"]}\n'
                         f'Игра {room["state"]}\n'
                         f'Код для подключения: {room["room_id"]}\n')
            
            admin_keyboard = InlineKeyboardMarkup()
            delete_button = InlineKeyboardButton(text='Удалить комнату', callback_data=f'delete {room["room_id"]}')
            shuffle_button = InlineKeyboardButton(text='Начать игру', callback_data=f'shuffle {room["room_id"]}')
            members_button = InlineKeyboardButton(text='Посмотреть список участников', callback_data=f'check members {room["room_id"]}')
            admin_keyboard.add(delete_button, shuffle_button).add(members_button)

            await bot.send_message(chat_id=message.from_user.id,
                                   text=room_text,
                                   reply_markup=admin_keyboard)
            
        elif str(message.from_user.id) == room["admin"] and room["state"] == "запущена": # если админ, но комната запущена 

            members_keyboard = InlineKeyboardMarkup()
            members_button = InlineKeyboardButton(text='Посмотреть список участников', callback_data=f'check members {room["room_id"]}')
            members_keyboard.add(members_button)

            room_text = (f'Название: {room["room_name"]} 👑\n'
                         f'{len(room["members"].split(" "))}/{room["member_count"]} участвуют\n'
                         f'Описание: {room["desc"]}\n'
                         f'Игра {room["state"]}\n'
                         f'Код для подключения: {room["room_id"]}\n')

            await bot.send_message(chat_id=message.from_user.id,
                                   text=room_text,
                                   reply_markup=members_keyboard)
            
        elif str(message.from_user.id) != room["admin"]: # если не админ

            room_text = (f'Название: {room["room_name"]}\n'
                         f'{len(room["members"].split(" "))}/{room["member_count"]} участвуют\n'
                         f'Описание: {room["desc"]}\n'
                         f'Игра {room["state"]}\n'
                         f'Код для подключения: {room["room_id"]}\n')

            exit_keyboard = InlineKeyboardMarkup()
            exit_button = InlineKeyboardButton(text='Покинуть комнату', callback_data=f'exit {room["room_id"]}')
            members_button = InlineKeyboardButton(text='Посмотреть список участников',
                                                  callback_data=f'check members {room["room_id"]}')
            exit_keyboard.add(exit_button).add(members_button)
            await bot.send_message(chat_id=message.from_user.id,
                                   text=room_text,
                                   reply_markup=exit_keyboard)


@dp.callback_query_handler(F.data.contains('check members'))
async def check_members_list(callback: types.CallbackQuery):
    '''Обрабатываем вывод списка игроков в комнате'''
    room_id = callback.data[-5:]
    room = await database.get_room(room_id)
    members_list = room['members'].split(' ')
    await bot.answer_callback_query(callback_query_id=callback.id, text="Ну давай посмотрим, кто с нами играет ;)")
    await bot.send_message(chat_id=callback.from_user.id, text=f'В комнате <b>"{room["room_name"]}"</b> состоят 👇',
                           parse_mode=types.ParseMode.HTML)
    for member in members_list:
        if room['admin'] == str(callback.from_user.id):
            player = await database.get_profile_by_username(member)
            if room['admin'] == player['member_id']:
                player['surname'] += ' 👑'
            kick_keyboard = InlineKeyboardMarkup()
            kick_button = InlineKeyboardButton(text='Исключить', callback_data=f'kick {player["member_id"]} {room_id}')
            kick_keyboard.add(kick_button)

            if player['member_id'] == str(callback.from_user.id):
                await bot.send_message(chat_id=callback.from_user.id,
                                       text=f'{player["name"]} {player["surname"]}\n'
                                            f'@{player["username"]}')
            else:
                await bot.send_message(chat_id=callback.from_user.id,
                                       text=f'{player["name"]} {player["surname"]}\n'
                                            f'@{player["username"]}',
                                       reply_markup=kick_keyboard)
            continue

        player = await database.get_profile_by_username(member)
        await bot.send_message(chat_id=callback.from_user.id, text=f'{player["name"]} {player["surname"]}\n'
                                                             f'@{player["username"]}')


@dp.callback_query_handler(F.data.contains('kick'))
async def confirm_kick(callback: types.CallbackQuery, state: FSMContext):
    '''Спрашиваем у админа, точно ли мы будем выгонять игрока'''
    async with state.proxy() as data:
        data['member_id'] = str(callback.data).split(' ')[1]
        data['room_id'] = str(callback.data).split(' ')[2]
        data['member_text'] = callback.message.text

    async with state.proxy() as data:
        await callback.message.edit_text(text=callback.message.text )
        confirm_keyboard = InlineKeyboardMarkup()
        agree_button = InlineKeyboardButton(text='Да', callback_data=f' confirm_kick_{data["member_id"]}')
        disagree_button = InlineKeyboardButton(text='Нет', callback_data=f' refuse_kick_{data["member_id"]}')
        confirm_keyboard.add(agree_button, disagree_button)

    await callback.message.edit_text(f'{callback.message.text}\n'
                                     f'----------------------------------------------\n'
                                     f'<b>Вы уверены, что хотите выгнать данного игрока?</b>',
                                     reply_markup=confirm_keyboard,
                                     parse_mode=types.ParseMode.HTML)
    await Room.kick_confirm.set()


@dp.callback_query_handler(F.data.contains(' confirm_kick_'), state=Room.kick_confirm)
async def confirm_kick(callback: types.CallbackQuery, state: FSMContext):
    '''Тут мы обрабатываем согласие на изгнание игрока'''
    async with state.proxy() as data:
        room = await database.get_room(data['room_id'])
        members_list = room['members'].split(' ')
        deleted_member = await database.get_profile_by_id(data['member_id'])
        members_list.remove(deleted_member['username'])
        updated_members_list = ' '.join(members_list)
        await database.delete_member(data['room_id'], updated_members_list)
        await bot.send_message(chat_id=data['member_id'],
                               text=f'Ой-ёй... Кажется, администратор комнаты "<b>{room["room_name"]}</b>"'
                                    f' исключил тебя из неё 😢\n',
                               parse_mode=types.ParseMode.HTML)
        await bot.send_sticker(chat_id=data['member_id'],
                               sticker='CAACAgIAAxkBAAJ1Imblj9Ti_o85qsFPSlWYzSEfmtWaAAJ-EAACLzgAAUtI7H4VYC04vTYE')
    await callback.message.delete()
    await bot.answer_callback_query(callback_query_id=callback.id, text='До свидания, жулик!')
    await state.finish()


@dp.callback_query_handler(F.data.contains(' refuse_kick_'), state=Room.kick_confirm)
async def refuse_kick(callback: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        kick_keyboard = InlineKeyboardMarkup()
        kick_button = InlineKeyboardButton(text='Исключить', callback_data=f'kick {data["member_id"]} {data["room_id"]}')
        kick_keyboard.add(kick_button)
        await callback.message.edit_text(data['member_text'], reply_markup=kick_keyboard)
    await bot.answer_callback_query(callback_query_id=callback.id, text='Черт с тобой, золотая рыбка!')
    await state.finish()


@dp.callback_query_handler(F.data.contains('exit'))
async def exit_room(callback: types.CallbackQuery, state: FSMContext):
    '''Обрабатываем попытку выхода из комнаты'''
    room_id = callback.data[-5:]
    confirm_keyboard = InlineKeyboardMarkup()
    agree_button = InlineKeyboardButton(text='Да', callback_data=f' agree_{room_id}')
    disagree_button = InlineKeyboardButton(text='Нет', callback_data=f'disagree_{room_id}')
    confirm_keyboard.add(agree_button, disagree_button)
    async with state.proxy() as data:
        data["room_text"] = callback.message.text
    await callback.message.edit_text(f'{callback.message.text}\n'
                                     f'----------------------------------------------\n'
                                     f'<b>Вы уверены, что хотите покинуть комнату?</b>',
                                     reply_markup=confirm_keyboard,
                                     parse_mode=types.ParseMode.HTML)
    await Room.exit_confirm.set()


@dp.callback_query_handler(F.data.contains(' agree'), state=Room.exit_confirm)
async def confirm_exit_room(callback: types.CallbackQuery, state: FSMContext):
    '''Соглашаемся с выходом из комнаты'''
    room_id = callback.data[-5:]
    room = await database.get_room(room_id)
    members_list = room["members"].split(' ')
    deleted_member = await database.get_profile_by_id(callback.from_user.id)
    members_list.remove(deleted_member["username"])
    updated_members_list = ' '.join(members_list)
    await database.delete_member(room_id, updated_members_list)
    await callback.message.delete()
    await bot.answer_callback_query(callback_query_id=callback.id, text='Вы успешно покинули комнату!')
    await state.finish()


@dp.callback_query_handler(F.data.contains('disagree'), state=Room.exit_confirm)
async def disagree_exit_room(callback: types.CallbackQuery, state: FSMContext):
    '''Отказываемся от выхода из комнаты'''
    room = await database.get_room(callback.data[-5:])
    await bot.answer_callback_query(callback_query_id=callback.id, text='Рааазворот!')
    exit_keyboard = InlineKeyboardMarkup()
    exit_button = InlineKeyboardButton(text='Покинуть комнату', callback_data=f'exit {room["room_id"]}')
    exit_keyboard.add(exit_button)
    async with state.proxy() as data:
        await callback.message.edit_text(text=data["room_text"], reply_markup=exit_keyboard)
    await state.finish()


@dp.callback_query_handler(F.data.contains('delete'))
async def delete_room(callback: types.CallbackQuery):
    confirm_keyboard = InlineKeyboardMarkup()
    agree_button = InlineKeyboardButton(text='Да', callback_data=f'confirm_{callback.data[-5:]}')
    disagree_button = InlineKeyboardButton(text='Нет', callback_data=f'refuse_{callback.data[-5:]}')
    confirm_keyboard.add(agree_button, disagree_button)
    await bot.answer_callback_query(callback_query_id=callback.id, text='Удаление комнаты')
    await callback.message.edit_text(f'{callback.message.text}\n'
                                     f'----------------------------------------------\n'
                                     f'<b>Вы уверены, что хотите удалить данную комнату?</b>',
                                     reply_markup=confirm_keyboard,
                                     parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(F.data.contains('confirm'))
async def confirm_delete(callback: types.CallbackQuery):
    room = await database.get_room(callback.data[-5:])
    members = room["members"].split(' ')
    for member in members:
        profile = await database.get_profile_by_username(member)
        if profile["member_id"] == room["admin"]:
            continue
        await bot.send_message(chat_id=profile["member_id"],
                         text=f'Упс! Кажется админ комнаты под названием <b>{room["room_name"]}</b> удалил её ❌. Игра не будет запущена и в следующий раз ты её не увидишь!',
                         parse_mode=types.ParseMode.HTML)
    await database.delete_room(callback.data[-5:])
    await bot.answer_callback_query(callback_query_id=callback.id, text='Комната удалена')
    await callback.message.delete()


@dp.callback_query_handler(F.data.contains('refuse'))
async def refuse_delete(callback: types.CallbackQuery):
    # await callback.message.edit_text(callback.message.text[:-93])
    await bot.answer_callback_query(callback_query_id=callback.id, text='Удаление отменено')
    admin_keyboard = InlineKeyboardMarkup()
    delete_button = InlineKeyboardButton(text='Удалить комнату', callback_data=f'delete {callback.data[-5:]}')
    shuffle_button = InlineKeyboardButton(text='Начать игру', callback_data=f'shuffle {callback.data[-5:]}')
    admin_keyboard.add(delete_button, shuffle_button)
    await callback.message.edit_text(text=callback.message.text[:-93], reply_markup=admin_keyboard)


@dp.callback_query_handler(F.data.contains('shuffle'))
async def shuffle_room_confirm(callback: types.CallbackQuery):
    '''
    Если админ нажимает на запуск игры, бот спросит подтверждение
    '''
    confirm_keyboard = InlineKeyboardMarkup()
    start_game_button = InlineKeyboardButton(text='Да', callback_data=f'start_{callback.data[-5:]}')
    stop_game_button = InlineKeyboardButton(text='Нет', callback_data=f'stop_{callback.data[-5:]}')
    confirm_keyboard.add(start_game_button, stop_game_button)
    await bot.answer_callback_query(callback_query_id=callback.id,text='АНЯ, ЗАПУСКАЙ')
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
    await bot.answer_callback_query(callback_query_id=callback.id, text='Игроки перемешаны')
    admin_keyboard = InlineKeyboardMarkup()
    delete_button = InlineKeyboardButton(text='Удалить комнату', callback_data=f'delete {room_id}')
    admin_keyboard.add(delete_button)
    
    shuffled_players_dict = await database.shuffle_players(room_id) # получаем перемешанных распределенных игроков
    new_room = await database.get_room(room_id)

    new_room_text = f'''Название: {new_room["room_name"]} 👑
{len(new_room["members"].split(" "))}/{new_room["member_count"]} участвуют
Описание: {new_room["desc"]}
Игра {new_room["state"]}
Код для подключения: {new_room["room_id"]}'''

    await callback.message.edit_text(text=new_room_text, reply_markup=admin_keyboard)

    for username in shuffled_players_dict:
        # проходимся по ним
        player = await database.get_profile_by_username(username) # получаем игрока, которому отправляем сообщение
        opponent = await database.get_profile_by_username(shuffled_players_dict[player['username']]) # и про которого отправляем
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

    new_room = await database.get_room(callback.data[-5:])
    new_room_text = f'''Название: {new_room["room_name"]} 👑
{len(new_room["members"].split(" "))}/{new_room["member_count"]} участвуют
Описание: {new_room["desc"]}
Игра {new_room["state"]}
Код для подключения: {new_room["room_id"]}'''

    admin_keyboard = InlineKeyboardMarkup()
    delete_button = InlineKeyboardButton(text='Удалить комнату', callback_data=f'delete {callback.data[-5:]}')
    shuffle_button = InlineKeyboardButton(text='Начать игру', callback_data=f'shuffle {callback.data[-5:]}')
    admin_keyboard.add(delete_button, shuffle_button)

    await callback.message.edit_text(text=new_room_text, reply_markup=admin_keyboard)
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

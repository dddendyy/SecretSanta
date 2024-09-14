import sqlite3 as sqlite
import random
from config import DATABASE
from copy import deepcopy

async def start():

    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Rooms(
    room_id TEXT PRIMARY KEY,
    name TEXT,
    member_count INTEGER,
    admin TEXT,
    state TEXT,
    desc TEXT, 
    members TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Members(
    member_id TEXT PRIMARY KEY,
    username TEXT,
    name TEXT,
    sex TEXT,
    age INTEGER, 
    desc TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Addictions(
    member_1 TEXT, 
    member_2 TEXT,
    room TEXT
    )
    ''')

    db.commit()
    db.close()


async def create_profile(user_id):
    '''
    Перед тем, как забить данные о профиле, его надо создать,
    чтобы не апдейтить несуществующие значения
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    sql = cursor.execute('SELECT * FROM members WHERE member_id = :user_id', {'user_id': user_id}).fetchone()

    if not sql:
        cursor.execute('INSERT INTO members VALUES (?, ?, ?, ?, ?, ?, ?)', (user_id, '', '', '', '', 0, ''))
        db.commit()

    db.close()


async def update_profile(user_id, state):
    '''
    Забивает данные профиля после создания в БД
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    async with state.proxy() as data:
        cursor.execute('UPDATE members SET name = ?, surname = ?, sex = ?, age = ?, desc = ?, username = ? WHERE member_id = ?',
                       (data['name'], data['surname'], data['sex'], data['age'], data['desc'], data['username'], user_id))
        db.commit()

    db.close()


async def get_profile_by_id(user_id):
    '''
    С помощью dict(zip()) возвращаем словарь из ключей (ими будут поля БД)
    и значений - ими будут результаты запроса SELECT
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    result = ['member_id', 'username', 'name', 'surname', 'sex', 'age', 'desc'] # список с ключами

    sql = cursor.execute('SELECT * FROM members WHERE member_id = :user_id', {'user_id': user_id}).fetchone()

    if not sql: # если запрос ничего не вернул, то функция вернёт None
        return None

    db.commit()
    db.close()

    profile = dict(zip(result, sql)) # теперь с помощью zip объеденяем словарь из ключей с результатом запроса
    # ииии приводим к словарю функцией dict

    return profile


async def get_profile_by_username(username):
    '''
    С помощью dict(zip()) возвращаем словарь из ключей (ими будут поля БД)
    и значений - ими будут результаты запроса SELECT
    Нужно для отправки сообщения при обработке шафла (перемешка игроков, т.е. кто-кому дарит)
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    result = ['member_id', 'username', 'name', 'surname', 'sex', 'age', 'desc'] # список с ключами

    sql = cursor.execute('SELECT * FROM Members WHERE username = :username', {'username': username}).fetchone()

    if not sql: # если запрос ничего не вернул, то функция вернёт None
        return None

    db.commit()
    db.close()

    profile = dict(zip(result, sql)) # теперь с помощью zip объеденяем словарь из ключей с результатом запроса
    # ииии приводим к словарю функцией dict

    return profile


async def create_room(state, user_id, username):
    '''
    Создадим комнату с её уникальным номером
    Уникальным номером выступит набор из 5 цифр, сгенерированных с помощью цикла и random.choice()
    По этому уникальному номеру и будет происходит подключение
    флоу: 1. запускаем бесконечный цикл -> 2. генерируем ID -> 3. проверяем существование комнаты с таким ID ->
    -> 4. если есть такая, то переходим пропускаем итерацию и возвращаемся к шагу 2, если такой нет, то создаем
    и выходим из цикла
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    while True: # запускаем цикл (1)

        nums = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] # формируем словарь из циферок (я знаю, что это строки)(2)
        room_id = '' # будущий ID комнаты (пока что пустой, но скоро будет не пустой)(2)

        for i in range(5):
            room_id += random.choice(nums) # пять раз берём рандомное значение из списка циферок и вуаля! получаем ID(2)

        sql = cursor.execute('SELECT * FROM Rooms WHERE room_id = :room_id',
                             {'room_id': room_id}).fetchone() # запрос для проверки наличия комнаты(3)

        if not sql: # если такой комнаты нет, то создаём(4)
            async with state.proxy() as data:
                cursor.execute('INSERT INTO Rooms VALUES (?, ?, ?, ?, ?, ?, ?)',
                               (room_id, data['room_name'], data['member_count'], user_id, 'создана', data['room_desc'], username))
            db.commit() # СОХРАНЯЕМ!!!! СУКА ЧАС НЕ МОГ ПОНЯТЬ ПОЧЕМУ НЕ СОХРАНЯЕТСЯ!!!!!!!!!
            return room_id
        else:
            continue
    db.close()
# ЕБУЧИЙ db.commit()!!! УХ НАМУЧИЛСЯ


async def join_room(room_id, username, message):
    '''
    Здесь мы будем получать инфу о комнате и добавлять игрока к комнате с помощью UPDATE
    1. Проверяем наличие комнаты с помощью SELECT -> 2. Ищем пользователя по ID ->
    -> 3. Через UPDATE добавляем его ID в последнюю ячейку комнаты В ней будут храниться ID подключенных игроков.
    '''
    result = ['room_id', 'room_name', 'member_count', 'admin', 'state', 'desc', 'members']

    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    sql = cursor.execute('SELECT * FROM Rooms where room_id = :room_id', {'room_id': room_id}).fetchone()

    if not sql:
        db.close()
        return None

    room = dict(zip(result, sql))

    if str(username) in room['members']:
        db.close()
        return True

    elif len(room['members'].split(' ')) >= room['member_count']:
        db.close()
        return False

    else:
        new_member = room['members'] + f' {str(username)}'
        cursor.execute('UPDATE Rooms SET members = :new_member WHERE room_id = :room_id',
                       {'new_member': new_member, 'room_id': room_id})
        db.commit()

    db.close()

    return room


async def show_rooms_list(username, user_id):
    rooms_list = []
    result = ['room_id', 'room_name', 'member_count', 'admin', 'state', 'desc', 'members']
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    sql = cursor.execute('SELECT * FROM Rooms WHERE instr (members, :username)',
                         {'username': username}).fetchall()

    db.close()

    for room in sql:
        rooms_list.append(dict(zip(result, room)))

    return rooms_list


async def get_room(room_id):
    '''
    Здесь мы получаем комнату по id,
    в параметрах принимают room_id из callback.data()
    '''

    result = ['room_id', 'room_name', 'member_count', 'admin', 'state', 'desc', 'members']

    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    sql = cursor.execute('SELECT * FROM Rooms WHERE room_id = :room_id', {'room_id': room_id}).fetchone()
    
    return dict(zip(result, sql))


async def delete_member(room_id, members):
    '''
    В main мы получаем комнату через get_room, оттуда берём список участников,
    удаляем нужного участника из списка и закидываем список участников в БД
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    sql = cursor.execute('UPDATE Rooms SET Members = :members WHERE room_id = :room_id',
                         {'members': members, 'room_id': room_id}).fetchone()

    db.commit()
    db.close()


async def delete_room(room_id):
    '''
    Удаление комнаты по id
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    sql = cursor.execute('SELECT * FROM Rooms WHERE room_id = :room_id', {'room_id': room_id}).fetchone()

    if sql:
        cursor.execute('DELETE FROM Rooms WHERE room_id = :room_id', {'room_id': room_id})

    db.commit()
    db.close()


async def shuffle_players(room_id):
    '''
    Тут будем перемешивать игроков
    Получаем список игроков по комнате > сплитуем > перемешиваем
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    sql = cursor.execute('SELECT members FROM Rooms where room_id = :room_id', {'room_id': room_id}).fetchone()[0]

    players_list = sql.split(' ') # делаем сплит, чтобы получить список из игроков
    players_list_copy = deepcopy(players_list)
    shuffled_players_dict = dict.fromkeys(players_list)
    
    used_values = []

    for num in shuffled_players_dict.keys():
        # Чтобы исключить текущее значение ключа из выбора
        available_values = [value for value in players_list_copy if value != num]
        random_player = random.choice(available_values)
        shuffled_players_dict[num] = random_player
        players_list_copy.remove(random_player)  # Удаляем использованное значение

    db.close()
    return shuffled_players_dict


async def update_state_started(room_id):
    '''
    У каждой нашей комнаты будет статус: "создана". "запущена", "завершена"
    Тут мы будем делать запуска
    '''
    db = sqlite.connect(DATABASE)
    cursor = db.cursor()

    sql = cursor.execute('UPDATE Rooms SET state = "запущена" WHERE room_id = :room_id', {'room_id': room_id})

    db.commit()
    db.close()

    return sql

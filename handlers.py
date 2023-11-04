import json
import base64
import shutil
from pathlib import Path
import re
import sqlite3

# # mobile version
DATA_BASE_NAME = "//data/data/ru.travelfood.simple_ui/databases/birds"
TEMP_PHOTO_PATH = "//data/data/ru.travelfood.simple_ui/birds/TempPhoto/"

# web version
# DATA_BASE_NAME = "birds"
# TEMP_PHOTO_PATH = ""

global_bird_id = ""


def init_on_start(hashMap, _files=None, _data=None):
    # shutil.copy2("//data/data/ru.travelfood.simple_ui/databases/birds", "//sdcard") # Выгрузить БД из эмулятора
    # shutil.copy2("//sdcard", "//data/data/ru.travelfood.simple_ui/databases/birds") # Загрузить БД в эмулятор
    Path(TEMP_PHOTO_PATH).mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATA_BASE_NAME)
    cursor = connection.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='birds';")
    if len(cursor.fetchall()) < 1:
        cursor.execute(
            "create table birds("
            "id integer primary key autoincrement,"
            "name char(128) not null unique,"
            "description char(512),"
            "color char(32),"
            "photo blob);"
        )
        cursor.execute(
            "create table seen_birds("
            "id integer primary key autoincrement,"
            "bird_id integer,"
            "date_time char(16),"
            "foreign key (bird_id)  references birds (id) ON DELETE CASCADE);"
        )
        connection.commit()
        hashMap.put('toast', "Таблицы проинициализированы")
    connection.close()
    return hashMap


def cards_on_open(hashMap, _files=None, _data=None):
    j = Utils.get_main_card_settings()
    j["customcards"]["cardsdata"] = []
    birds = Utils.get_birds_list()

    for idd, name, descr, color, photo in birds:
        photo_path = ""
        if photo and TEMP_PHOTO_PATH:
            with open(f"{TEMP_PHOTO_PATH}photo_{idd}", 'wb') as image:
                image.write(photo)
            photo_path = f"~{TEMP_PHOTO_PATH}photo_{idd}"
        c = {
            "key": str(idd),
            "pic": str(photo_path) if TEMP_PHOTO_PATH else Utils.get_encoded_img_str(photo),
            "descr": descr,
            "idd": f"ID: {idd}",
            "string1": name,
        }
        j["customcards"]["cardsdata"].append(c)

    hashMap.put("cards", json.dumps(j))
    return hashMap


def cards_input(hashMap, _files=None, _data=None):
    # handlers code
    if hashMap.get("listener") == 'CardsClick':
        hashMap.put('ShowScreen', "ИзменитьПтицу")
    if hashMap.get("listener") == 'LayoutAction':
        if hashMap.get("layout_listener") == "Удалить":
            Utils.delete_bird_by_id(json.loads(hashMap.get("card_data"))["key"])
            hashMap.put('toast', "Удалено")
    if hashMap.get("listener") == 'ON_BACK_PRESSED':
        hashMap.put("FinishProcess", "")

    return hashMap


def on_press_delete(hashMap, _files=None, _data=None):
    idd = hashMap.get("del_id")
    if not idd or int(idd) < int(1):
        hashMap.put("toast", "ID должен быть больше 1")
        return hashMap
    if Utils.delete_bird_by_id(int(idd)):
        hashMap.put("toast", "Удалено")
    else:
        hashMap.put("toast", f"Птицы с ID {idd} не найдено")
    return hashMap


def on_press_add(hashMap, _files=None, _data=None):
    if hashMap.get("listener") == "add_btn":
        name, color, descr = hashMap.get("name"), hashMap.get("color"), hashMap.get("descr")
        photo = hashMap.get("photo_cam") if hashMap.get("photo_cam") else hashMap.get("photo_gal")
        photo = photo if photo else None
        if name and not re.search(r"[0-9]", name):
            if Utils.add_bird(name, color, descr, photo):
                hashMap.put("toast", "Добавлено")
            else:
                hashMap.put("toast", f"Птица с именем {name} уже существует")
        else:
            hashMap.put("toast", "Имя не должно быть пустым или содержать цифры")
    return hashMap


def on_start_edit(hashMap, _files=None, _data=None):
    bird_id = hashMap.get("selected_card_key")
    connection = sqlite3.connect(DATA_BASE_NAME)
    cursor = connection.cursor()
    cursor.execute(f"SELECT name, description, color FROM birds WHERE id={int(bird_id)}")
    name, descr, color = cursor.fetchall()[0]
    connection.close()
    hashMap.put("name", name)
    hashMap.put("color", color)
    hashMap.put("descr", descr)
    return hashMap


def on_press_edit(hashMap, _files=None, _data=None):
    global global_bird_id
    bird_id = hashMap.get("selected_card_key")

    if hashMap.get("listener") == "edit_btn":
        name, color, descr = hashMap.get("name"), hashMap.get("color"), hashMap.get("descr")
        if name and not re.search(r"[0-9]", name):
            if Utils.update_bird(bird_id, name, color, descr):
                hashMap.put("toast", "Изменено")
                hashMap.put('ShowScreen', "main")
                return hashMap
            else:
                hashMap.put("toast", f"Птица с именем {name} уже существует")
        else:
            hashMap.put("toast", "Имя не должно быть пустым или содержать цифры")

    if hashMap.get("listener") == "seen":
        global_bird_id = bird_id
        hashMap.put("toast", "Можете внести птицу в список увиденных")

    if hashMap.get("listener") == 'ON_BACK_PRESSED':
        hashMap.put("ShowScreen", "main")
    return hashMap


def on_start_seen_table(hashMap, _files=None, _data=None):
    table = Utils.get_seen_table_settings()
    connection = sqlite3.connect(DATA_BASE_NAME)
    cursor = connection.cursor()
    cursor.execute("SELECT b.name, s.date_time, s.count_seen " +
                   "FROM birds b " +
                   "JOIN (SELECT bird_id, max(date_time) date_time, count(bird_id) count_seen FROM seen_birds GROUP "
                   "BY bird_id) s " +
                   "ON b.id = s.bird_id")
    results = cursor.fetchall()

    rows = []
    for record in results:
        rows.append({"cell": record[0], "nom": record[1], "qty": record[2]})
    table['rows'] = rows

    hashMap.put("table", json.dumps(table))

    return hashMap


def on_press_seen_table(hashMap, _files=None, _data=None):
    global global_bird_id
    if hashMap.get("listener") == "saw":
        if global_bird_id:
            connection = sqlite3.connect(DATA_BASE_NAME)
            cursor = connection.cursor()
            cursor.execute(
                f"INSERT INTO seen_birds (bird_id, date_time) VALUES ({int(global_bird_id)}, datetime('now'))")
            connection.commit()
            connection.close()
            hashMap.put("toast", "Птица увидена")
            global_bird_id = ""
            on_start_seen_table(hashMap, _files=None, _data=None)
        else:
            hashMap.put("toast", "Вы не увидели никакую птицу")

    return hashMap


class Utils:

    @staticmethod
    def get_encoded_img_str(binary_img: bytes):
        if binary_img:
            img = base64.b64encode(binary_img)
            return str(f"data:image/png;base64,{img.__str__()[2:-1]}")
        return ''

    @staticmethod
    def get_birds_list():
        connection = sqlite3.connect(DATA_BASE_NAME)
        cursor = connection.cursor()
        cursor.execute("SELECT id, name, description, color, photo FROM birds")
        return cursor.fetchall()

    @staticmethod
    def delete_bird_by_id(idd):
        connection = sqlite3.connect(DATA_BASE_NAME)
        cursor = connection.cursor()
        cursor.execute(f"SELECT id FROM birds where id={int(idd)}")
        if not cursor.fetchall():
            return None
        else:
            cursor.execute(f"DELETE FROM birds where id={int(idd)}")
            connection.commit()
            connection.close()
            return True

    @staticmethod
    def add_bird(name, color, descr, photo):
        connection = sqlite3.connect(DATA_BASE_NAME)
        cursor = connection.cursor()
        photo = base64.b64decode(photo) if photo else None
        try:
            cursor.execute(
                "INSERT INTO birds (name, description, color, photo) values (?, ?, ?, ?)",
                (name, descr, color, photo))
        except sqlite3.IntegrityError:
            return False
        connection.commit()
        connection.close()
        return True

    @staticmethod
    def update_bird(idd, name, color, descr):
        connection = sqlite3.connect(DATA_BASE_NAME)
        cursor = connection.cursor()
        try:
            cursor.execute(
                "UPDATE birds SET name = ?,"
                "description = ?,"
                "color= ?"
                "WHERE id = ?",
                (name, descr, color, int(idd)))
        except sqlite3.IntegrityError:
            return False
        connection.commit()
        connection.close()
        return True

    @staticmethod
    def get_seen_table_settings():
        t = {
            "type": "table",
            "textsize": "17",

            "columns": [
                {
                    "name": "cell",
                    "header": "Название птицы",
                    "weight": "2"
                },
                {
                    "name": "nom",
                    "header": "Дата и время видения",
                    "weight": "2"
                },
                {
                    "name": "qty",
                    "header": "Сколько раз видел",
                    "weight": "1"
                }
            ]
        }
        return t

    @staticmethod
    def get_main_card_settings():
        j = {"customcards": {
            "options": {
                "search_enabled": True,
                "save_position": True
            },
            "layout": {
                "type": "LinearLayout",
                "orientation": "vertical",
                "height": "match_parent",
                "width": "match_parent",
                "weight": "0",
                "Elements": [
                    {
                        "type": "LinearLayout",
                        "orientation": "horizontal",
                        "height": "wrap_content",
                        "width": "match_parent",
                        "weight": "0",
                        "Elements": [
                            {
                                "type": "Picture",
                                "show_by_condition": "",
                                "Value": "@pic",
                                "NoRefresh": False,
                                "document_type": "",
                                "mask": "",
                                "Variable": "",
                                "TextSize": "16",
                                "TextColor": "#DB7093",
                                "TextBold": True,
                                "TextItalic": False,
                                "BackgroundColor": "",
                                "width": 125,
                                "height": 125,
                                "weight": 0
                            },
                            # {
                            #     "type": "CheckBox",
                            #     "Value": "@cb1",
                            #     "NoRefresh": False,
                            #     "document_type": "",
                            #     "mask": "",
                            #     "Variable": "cb1",
                            #     "BackgroundColor": "#DB7093",
                            #     "width": "match_parent",
                            #     "height": "wrap_content",
                            #     "weight": 2
                            # },
                            {
                                "type": "LinearLayout",
                                "orientation": "vertical",
                                "height": "wrap_content",
                                "width": "match_parent",
                                "weight": "1",
                                "Elements": [
                                    {
                                        "type": "TextView",
                                        "show_by_condition": "",
                                        "Value": "@string1",
                                        "NoRefresh": False,
                                        "document_type": "",
                                        "TextSize": "16",
                                        "mask": "",
                                        "Variable": "",
                                        "gravity_horizontal": "right"
                                    },
                                    # {
                                    #     "type": "TextView",
                                    #     "show_by_condition": "",
                                    #     "Value": "@string2",
                                    #     "NoRefresh": False,
                                    #     "document_type": "",
                                    #     "mask": "",
                                    #     "Variable": ""
                                    # },
                                    # {
                                    #     "type": "TextView",
                                    #     "show_by_condition": "",
                                    #     "Value": "@string3",
                                    #     "NoRefresh": False,
                                    #     "document_type": "",
                                    #     "mask": "",
                                    #     "Variable": ""
                                    # },
                                    # {
                                    #     "type": "Button",
                                    #     "show_by_condition": "",
                                    #     "Value": "#f290",
                                    #     "TextColor": "#DB7093",
                                    #     "Variable": "btn_tst1",
                                    #     "NoRefresh": False,
                                    #     "document_type": "",
                                    #     "mask": ""
                                    #
                                    # },
                                    # {
                                    #     "type": "Button",
                                    #     "show_by_condition": "",
                                    #     "Value": "#f469",
                                    #     "TextColor": "#DB7093",
                                    #     "Variable": "btn_tst2",
                                    #     "NoRefresh": False,
                                    #     "document_type": "",
                                    #     "mask": ""
                                    #
                                    # }
                                ]
                            },
                            {
                                "type": "TextView",
                                "show_by_condition": "",
                                "Value": "@idd",
                                "NoRefresh": False,
                                "document_type": "",
                                "mask": "",
                                "Variable": "",
                                "TextSize": "12",
                                "TextColor": "#DB7093",
                                "TextBold": True,
                                "TextItalic": False,
                                "BackgroundColor": "",
                                "width": "match_parent",
                                "height": "wrap_content",
                                "weight": 2
                            },
                            {
                                "type": "PopupMenuButton",
                                "show_by_condition": "",
                                "Value": "Удалить",
                                "NoRefresh": False,
                                "document_type": "",
                                "mask": "",
                                "Variable": "menu_delete"

                            }
                        ]
                    },
                    {
                        "type": "TextView",
                        "show_by_condition": "",
                        "Value": "@descr",
                        "NoRefresh": False,
                        "document_type": "",
                        "mask": "",
                        "Variable": "",
                        "TextSize": "16",
                        "TextColor": "#6F9393",
                        "TextBold": False,
                        "TextItalic": True,
                        "BackgroundColor": "",
                        "width": "wrap_content",
                        "height": "wrap_content",
                        "weight": 0,
                        "gravity_horizontal": "center"
                    }
                ]
            }

        }
        }
        return j

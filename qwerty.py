import telebot
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials
from geopy.distance import geodesic

TOKEN = "7161319223:AAEbEA2Ev6AaFX8HTXMSRPjhKEYuLIzNYHo"
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 1470380973

SCHOOL_LOCATION = (39.692530741662026, 66.7251181857347)
MAX_DISTANCE_METERS = 300

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

TEACHERS_SHEET = "O'qituvchilar Ro'yxati"
teachers_sheet = client.open(TEACHERS_SHEET).sheet1

ATTENDANCE_SHEET = "Davomat"
attendance_sheet = client.open(ATTENDANCE_SHEET).sheet1

user_data = {}  # {chat_id: {"id": user_id, "familiya": familiya, "ism": ism}}

def get_teacher_info(user_id):
    try:
        data = teachers_sheet.get_all_records()
        for row in data:
            if str(row['ID']) == user_id:
                return row['Familiya'], row['Ism']
    except Exception as e:
        print("Google Sheets o‘qishda xatolik:", e)
    return None, None

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    if user_id in user_data:
        familiya, ism = user_data[user_id]['familiya'], user_data[user_id]['ism']
    else:
        familiya, ism = get_teacher_info(user_id)
    
    if familiya and ism:
        user_data[user_id] = {"id": user_id, "familiya": familiya, "ism": ism}
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = telebot.types.KeyboardButton("Keldim", request_location=True)
        btn2 = telebot.types.KeyboardButton("Ketdim")
        markup.add(btn1, btn2)
        bot.send_message(message.chat.id, f"Assalomu alaykum, {familiya} {ism}!", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Iltimos, ID raqamingizni kiriting:")
        bot.register_next_step_handler(message, register_teacher)

def register_teacher(message):
    user_id = str(message.chat.id)
    input_id = message.text.strip()
    
    familiya, ism = get_teacher_info(input_id)
    if familiya and ism:
        user_data[user_id] = {"id": input_id, "familiya": familiya, "ism": ism}
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = telebot.types.KeyboardButton("Keldim", request_location=True)
        btn2 = telebot.types.KeyboardButton("Ketdim")
        markup.add(btn1, btn2)
        bot.send_message(message.chat.id, f"ID tasdiqlandi. {familiya} {ism} endi tizimdan foydalanishingiz mumkin.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Bunday ID topilmadi. Iltimos, qayta tekshirib kiriting:")
        bot.register_next_step_handler(message, register_teacher)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    user_info = user_data.get(str(message.chat.id))
    if not user_info:
        bot.send_message(message.chat.id, "Iltimos, avval /start ni bosib ID kiriting.")
        return

    user_location = (message.location.latitude, message.location.longitude)
    distance = geodesic(SCHOOL_LOCATION, user_location).meters
    if distance > MAX_DISTANCE_METERS:
        bot.send_message(message.chat.id, "Siz ish joyida emassiz!")
        return

    now = datetime.datetime.now()
    date_today = now.strftime("%Y-%m-%d")
    time_now = now.strftime("%H:%M:%S")
    latitude = message.location.latitude
    longitude = message.location.longitude
    
    try:
        attendance_sheet.append_row([user_info["id"], user_info["familiya"], user_info["ism"], "Keldi", date_today, time_now, latitude, longitude])
        bot.send_message(message.chat.id, "Keldi vaqtingiz qayd qilindi!")
        bot.send_message(ADMIN_ID, f"📌 {user_info['familiya']} {user_info['ism']} Keldi \n📅 {date_today} ⏰ {time_now}\n📍 Lokatsiya: {latitude}, {longitude}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e}")

@bot.message_handler(func=lambda message: message.text == "Ketdim")
def handle_ketdim(message):
    user_info = user_data.get(str(message.chat.id))
    if not user_info:
        bot.send_message(message.chat.id, "Iltimos, avval /start ni bosib ID kiriting.")
        return

    now = datetime.datetime.now()
    date_today = now.strftime("%Y-%m-%d")
    time_now = now.strftime("%H:%M:%S")
    
    try:
        attendance_sheet.append_row([user_info["id"], user_info["familiya"], user_info["ism"], "Ketdi", date_today, time_now, "", ""])
        bot.send_message(message.chat.id, "Ketdi vaqtingiz qayd qilindi!")
        bot.send_message(ADMIN_ID, f"📌 {user_info['familiya']} {user_info['ism']} Ketdi \n📅 {date_today} ⏰ {time_now}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Xatolik yuz berdi: {e}")

bot.polling()

import telebot
from telebot import types
import json
import os
import time
from datetime import datetime, timedelta
import calendar
import random
import string
import re

# ==================== KONFIGURATSIYA ====================
TOKEN = "8393020811:AAF8TrxilToozbFpvcGLWOvITA_mGpzzNB4"  # @BotFather dan olgan tokeningiz
ADMIN_ID = 8099300728  # Admin ID

bot = telebot.TeleBot(TOKEN)

# ==================== MALUMOTLAR BAZASI ====================
REQUESTS_FILE = "requests.json"
USERS_FILE = "users.json"

user_data = {}
user_state = {}
chat_mode = {}  # Admin bilan chat rejimi
temp_data = {}  # Vaqtinchalik ma'lumotlar

# ==================== YORDAMCHI FUNKSIYALAR ====================

def unique_id():
    date = datetime.now().strftime("%y%m%d")
    rand = ''.join(random.choices(string.digits, k=3))
    return f"REQ-{date}-{rand}"

def users_load():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def users_save(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def requests_load():
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def requests_save(data):
    with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== BONUS FUNKSIYALARI ====================

def add_bonus(user_id, amount, reason):
    """Foydalanuvchiga bonus ball qo'shish"""
    users = users_load()
    user_id = str(user_id)
    
    if user_id in users:
        if 'bonus_ball' not in users[user_id]:
            users[user_id]['bonus_ball'] = 0
        if 'bonus_history' not in users[user_id]:
            users[user_id]['bonus_history'] = []
        
        users[user_id]['bonus_ball'] += amount
        users[user_id]['bonus_history'].append({
            'amount': amount,
            'reason': reason,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'balance': users[user_id]['bonus_ball']
        })
        
        users_save(users)
        return True
    return False

# ==================== KALENDAR FUNKSIYASI ====================

def create_calendar(year=None, month=None):
    """Chiroyli kalendar jadval yaratish"""
    now = datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    
    markup = types.InlineKeyboardMarkup(row_width=7)
    
    # Oy va yil sarlavhasi
    month_names = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", 
                   "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]
    markup.add(types.InlineKeyboardButton(
        f"📅 {month_names[month-1]} {year}", 
        callback_data="ignore"
    ))
    
    # Hafta kunlari
    week_days = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    row = []
    for day in week_days:
        row.append(types.InlineKeyboardButton(day, callback_data="ignore"))
    markup.row(*row)
    
    # Oy kunlari
    cal = calendar.monthcalendar(year, month)
    
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                # Bugungi sanani belgilash
                if day == now.day and month == now.month and year == now.year:
                    btn_text = f"📌 {day}"
                else:
                    btn_text = str(day)
                
                row.append(types.InlineKeyboardButton(
                    btn_text, 
                    callback_data=f"cal_{year}_{month}_{day}"
                ))
        markup.row(*row)
    
    # Navigatsiya tugmalari
    row = []
    
    # Oldingi oy
    if month > 1:
        row.append(types.InlineKeyboardButton("◀️", callback_data=f"cal_prev_{year}_{month-1}"))
    else:
        row.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
    
    # Bekor qilish tugmasi
    row.append(types.InlineKeyboardButton("❌ Bekor qilish", callback_data="cal_cancel"))
    
    # Keyingi oy
    if month < 12:
        row.append(types.InlineKeyboardButton("▶️", callback_data=f"cal_next_{year}_{month+1}"))
    else:
        row.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
    
    markup.row(*row)
    
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith('cal_'))
def calendar_callback(call):
    """Kalendar tugmalarini boshqarish"""
    chat_id = call.message.chat.id
    data = call.data.split('_')
    
    if data[1] == 'prev':
        year = int(data[2])
        month = int(data[3])
        markup = create_calendar(year, month)
        bot.edit_message_text(
            "📅 Sanani tanlang:",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif data[1] == 'next':
        year = int(data[2])
        month = int(data[3])
        markup = create_calendar(year, month)
        bot.edit_message_text(
            "📅 Sanani tanlang:",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif data[1] == 'cancel':
        bot.edit_message_text(
            "❌ Sana tanlash bekor qilindi.",
            chat_id,
            call.message.message_id
        )
        users = users_load()
        if str(chat_id) in users:
            main_menu(chat_id, users[str(chat_id)]['name'])
    
    else:
        # Sana tanlandi (kun bosilganda)
        year = int(data[1])
        month = int(data[2])
        day = int(data[3])
        
        date_str = f"{day:02d}.{month:02d}.{year}"
        
        # Qaysi xizmat ekanligini aniqlash
        if chat_id in user_data and 'calendar_for' in user_data[chat_id]:
            service = user_data[chat_id]['calendar_for']
            
            if service == 'avia_date':
                user_data[chat_id]['date'] = date_str
                bot.edit_message_text(
                    f"✅ Sana tanlandi: {date_str}",
                    chat_id,
                    call.message.message_id
                )
                avia_after_date(chat_id)
            
            elif service == 'avia_return':
                user_data[chat_id]['return_date'] = date_str
                bot.edit_message_text(
                    f"✅ Qaytish sanasi: {date_str}",
                    chat_id,
                    call.message.message_id
                )
                avia_after_return(chat_id)
            
            elif service == 'tour_date':
                user_data[chat_id]['date'] = date_str
                bot.edit_message_text(
                    f"✅ Sana tanlandi: {date_str}",
                    chat_id,
                    call.message.message_id
                )
                tour_after_date(chat_id)

# ==================== ASOSIY MENYU ====================

def main_menu(chat_id, name):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("✈️ Aviachiptalar"),
        types.KeyboardButton("🌍 Turlar"),
        types.KeyboardButton("🛂 Viza yordami"),
        types.KeyboardButton("🕋 Umra safarlari"),
        types.KeyboardButton("📞 Bog'lanish"),
        types.KeyboardButton("👤 Admin bilan chat"),
        types.KeyboardButton("⭐ Mening bonuslarim"),
        types.KeyboardButton("👥 Do'st taklif qilish")
    )
    text = f"🏝 EasyBooking Jizzax\n\n👤 {name}, xush kelibsiz!\n\nQuyidagi bo'limlardan birini tanlang:"
    bot.send_message(chat_id, text, reply_markup=markup)

# ==================== START ====================

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    text = message.text
    users = users_load()
    
    # Referal link orqali kelganmi?
    refered_by = None
    if len(text.split()) > 1:
        ref_code = text.split()[1]
        if ref_code.startswith('ref'):
            try:
                refered_by = int(ref_code.replace('ref', ''))
            except:
                refered_by = None
    
    if str(chat_id) in users:
        main_menu(chat_id, users[str(chat_id)]['name'])
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("❌ Bekor qilish"))
    bot.send_message(chat_id, "✨ EasyBooking Jizzax botiga xush kelibsiz! ✨\n\n📝 Iltimos, ismingizni kiriting:", reply_markup=markup)
    
    if chat_id not in user_data:
        user_data[chat_id] = {}
    if refered_by:
        user_data[chat_id]['refered_by'] = refered_by
    
    user_state[chat_id] = "waiting_name"

# ==================== ISM ====================

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_name")
def get_name(message):
    chat_id = message.chat.id
    if message.text == "❌ Bekor qilish":
        user_state.pop(chat_id, None)
        bot.send_message(chat_id, "❌ Bot to'xtatildi. Qaytadan /start bosing.")
        return
    
    name = message.text.strip()
    if len(name) < 2:
        bot.send_message(chat_id, "❌ Ism juda qisqa. Qayta kiriting:")
        return
    
    user_data[chat_id]['name'] = name
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Telefon raqamni ulashish", request_contact=True))
    markup.add(types.KeyboardButton("❌ Bekor qilish"))
    bot.send_message(chat_id, f"👤 {name}, endi telefon raqamingizni ulashing:", reply_markup=markup)
    user_state[chat_id] = "waiting_phone"

# ==================== TELEFON ====================

@bot.message_handler(content_types=['contact'])
def get_phone(message):
    chat_id = message.chat.id
    if user_state.get(chat_id) != "waiting_phone":
        return
    
    phone = message.contact.phone_number
    name = user_data[chat_id]['name']
    refered_by = user_data[chat_id].get('refered_by')
    
    users = users_load()
    
    users[str(chat_id)] = {
        'name': name,
        'phone': phone,
        'username': message.from_user.username,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'bonus_ball': 5,
        'bonus_history': [{
            'amount': 5,
            'reason': 'Xush kelibsiz',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'balance': 5
        }],
        'referal_link': f"ref{chat_id}",
        'refered_by': refered_by,
        'referals_count': 0,
        'referals_list': [],
        'requests_count': 0,
        'orders_count': 0,
        'monthly_stats': {}
    }
    
    # Referal bonus
    if refered_by and str(refered_by) in users:
        users[str(refered_by)]['bonus_ball'] = users[str(refered_by)].get('bonus_ball', 0) + 10
        users[str(refered_by)]['referals_count'] = users[str(refered_by)].get('referals_count', 0) + 1
        users[str(refered_by)]['referals_list'].append(chat_id)
        users[str(refered_by)]['bonus_history'].append({
            'amount': 10,
            'reason': f"Do'st taklif qildi ({name})",
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'balance': users[str(refered_by)]['bonus_ball']
        })
        
        try:
            bot.send_message(
                refered_by,
                f"🎉 Tabriklaymiz! Do'stingiz {name} sizning linkingiz orqali ro'yxatdan o'tdi!\n\n+10 bonus ball qo'shildi."
            )
        except:
            pass
    
    users_save(users)
    
    bot.send_message(ADMIN_ID, f"🆕 Yangi foydalanuvchi!\n\n👤 {name}\n📞 {phone}\n🆔 {chat_id}")
    
    user_state.pop(chat_id, None)
    user_data.pop(chat_id, None)
    main_menu(chat_id, name)

# ==================== BONUSLAR ====================

@bot.message_handler(func=lambda m: m.text == "⭐ Mening bonuslarim")
def my_bonus(message):
    chat_id = message.chat.id
    users = users_load()
    
    if str(chat_id) not in users:
        bot.send_message(chat_id, "❌ Avval /start orqali ro'yxatdan o'ting!")
        return
    
    user = users[str(chat_id)]
    bonus = user.get('bonus_ball', 0)
    history = user.get('bonus_history', [])[-10:]
    
    text = f"⭐ Mening bonuslarim\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"💰 Jami ball: {bonus} 🪙\n\n"
    text += f"📋 Oxirgi amallar:\n"
    
    for h in history[::-1]:
        emoji = "➕" if h['amount'] > 0 else "➖"
        text += f"{emoji} {h['amount']} ball - {h['reason']}\n   🕐 {h['date']}\n"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🏠 Asosiy menyu"))
    
    bot.send_message(chat_id, text, reply_markup=markup)

# ==================== DO'ST TAKLIF QILISH ====================

@bot.message_handler(func=lambda m: m.text == "👥 Do'st taklif qilish")
def my_referal(message):
    chat_id = message.chat.id
    users = users_load()
    
    if str(chat_id) not in users:
        bot.send_message(chat_id, "❌ Avval /start orqali ro'yxatdan o'ting!")
        return
    
    user = users[str(chat_id)]
    ref_link = f"https://t.me/easybooking_jizzaxbot?start={user.get('referal_link', f'ref{chat_id}')}"
    
    text = f"👥 DO'ST TAKLIF QILISH\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"🔗 SIZNING SHAXSIY LINKINGIZ:\n\n"
    text += f"{ref_link}\n\n"
    text += f"Bu linkni do'stlaringizga yuboring!\nHar bir taklif uchun +10 ball 🎁\n\n"
    text += f"📊 STATISTIKA:\n"
    text += f"   Taklif qilganlar: {user.get('referals_count', 0)} ta\n"
    text += f"   To'plangan ball: {user.get('bonus_ball', 0)} 🪙\n\n"
    
    if user.get('referals_list'):
        text += f"👥 TAKLIF QILGAN DO'STLAR:\n"
        for ref_id in user['referals_list'][-10:]:
            ref_user = users.get(str(ref_id), {})
            ref_name = ref_user.get('name', 'Noma\'lum')
            text += f"   ✓ {ref_name}\n"
        text += "\n"
    
    # Botga o'tish tugmasi
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton(
        "🤖 Botga o'tish", 
        url=f"https://t.me/easybooking_jizzaxbot"
    )
    markup.add(btn)
    
    bot.send_message(chat_id, text, reply_markup=markup)

# ==================== BO'LIMLAR ====================

@bot.message_handler(func=lambda m: m.text in ["✈️ Aviachiptalar", "🌍 Turlar", "🛂 Viza yordami", "🕋 Umra safarlari", "📞 Bog'lanish", "👤 Admin bilan chat"])
def handle_sections(message):
    chat_id = message.chat.id
    users = users_load()
    
    if str(chat_id) not in users:
        bot.send_message(chat_id, "❌ Avval /start orqali ro'yxatdan o'ting!")
        return
    
    name = users[str(chat_id)]['name']
    
    if message.text == "✈️ Aviachiptalar":
        start_avia(chat_id, name)
    elif message.text == "🌍 Turlar":
        start_tour(chat_id, name)
    elif message.text == "🛂 Viza yordami":
        start_visa(chat_id, name)
    elif message.text == "🕋 Umra safarlari":
        start_umra(chat_id, name)
    elif message.text == "📞 Bog'lanish":
        contact_info(chat_id, name)
    elif message.text == "👤 Admin bilan chat":
        start_chat(message)

# ==================== BOG'LANISH ====================

def contact_info(chat_id, name):
    text = (
        "📞 Biz bilan bog'lanish\n\n"
        "👤 Admin: @jabbarov_otajon\n"
        "📱 Telefon: +998991987272\n"
        "📸 Instagram: @easybooking_jizzax\n\n"
        "💬 Savol va takliflar uchun murojaat qiling!"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🏠 Asosiy menyu"))
    bot.send_message(chat_id, text, reply_markup=markup)

# ==================== ASOSIY MENYUGA QAYTISH ====================

@bot.message_handler(func=lambda m: m.text == "🏠 Asosiy menyu")
def back_to_main(message):
    chat_id = message.chat.id
    users = users_load()
    if str(chat_id) in users:
        if chat_id in chat_mode:
            chat_mode.pop(chat_id)
        main_menu(chat_id, users[str(chat_id)]['name'])
        if chat_id in user_state:
            user_state.pop(chat_id, None)
        if chat_id in temp_data:
            temp_data.pop(chat_id)

@bot.message_handler(func=lambda m: m.text == "🔙 Orqaga")
def back_handler(message):
    chat_id = message.chat.id
    users = users_load()
    if str(chat_id) in users:
        main_menu(chat_id, users[str(chat_id)]['name'])
        if chat_id in user_state:
            user_state.pop(chat_id, None)

# ==================== ADMIN BILAN CHAT ====================

def start_chat(message):
    chat_id = message.chat.id
    users = users_load()
    
    chat_mode[chat_id] = True
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ Chatni tugatish"))
    markup.add(types.KeyboardButton("🏠 Asosiy menyu"))
    
    bot.send_message(
        chat_id,
        "📞 Admin bilan bog'lanishingiz mumkin\n\n"
        "Endi yozgan xabarlaringiz to'g'ridan-to'g'ri admin @jabbarov_otajon ga boradi.\n"
        "Admin javob berganda sizga yetkaziladi.\n\n"
        "❌ Chatni tugatish uchun pastdagi tugmani bosing.",
        reply_markup=markup
    )
    
    bot.send_message(
        ADMIN_ID,
        f"📞 Foydalanuvchi admin bilan bog'landi!\n\n"
        f"👤 {users[str(chat_id)]['name']}\n"
        f"📞 {users[str(chat_id)]['phone']}\n"
        f"🆔 {chat_id}"
    )

@bot.message_handler(func=lambda m: chat_mode.get(m.chat.id) == True and m.text not in ["❌ Chatni tugatish", "🏠 Asosiy menyu"])
def handle_chat(message):
    chat_id = message.chat.id
    users = users_load()
    
    if message.chat.id != ADMIN_ID:
        bot.send_message(
            ADMIN_ID,
            f"📱 Foydalanuvchi: {users[str(chat_id)]['name']}\n"
            f"🆔 {chat_id}\n\n"
            f"{message.text}"
        )
        bot.send_message(chat_id, "✅ Xabar adminga yuborildi. Javob kuting.")

@bot.message_handler(func=lambda m: m.text == "❌ Chatni tugatish")
def end_chat(message):
    chat_id = message.chat.id
    users = users_load()
    
    if chat_id in chat_mode:
        chat_mode.pop(chat_id)
    
    bot.send_message(chat_id, "✅ Chat tugatildi.")
    bot.send_message(ADMIN_ID, f"❌ Foydalanuvchi {users[str(chat_id)]['name']} chatni tugatdi.")
    main_menu(chat_id, users[str(chat_id)]['name'])

# ==================== ADMIN JAVOB ====================

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.reply_to_message is not None)
def admin_reply(message):
    try:
        replied_msg = message.reply_to_message
        replied_text = replied_msg.text or replied_msg.caption or ""
        
        req_match = re.search(r'(REQ-\d{6}-\d{3})', replied_text)
        user_match = re.search(r'🆔 (\d+)', replied_text)
        
        if req_match:
            req_id = req_match.group(1)
            reqs = requests_load()
            
            if req_id in reqs:
                user_id = reqs[req_id]['user_id']
                
                if message.photo:
                    photo = message.photo[-1].file_id
                    caption = message.caption if message.caption else "Admin javobi"
                    
                    bot.send_photo(
                        user_id,
                        photo,
                        caption=f"📬 Admin javobi:\n\n{caption}"
                    )
                    
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    btn1 = types.InlineKeyboardButton("✅ Buyurtma berish", callback_data=f"order_{req_id}")
                    btn2 = types.InlineKeyboardButton("🔄 Boshqa variant", callback_data=f"restart_{req_id}")
                    markup.add(btn1, btn2)
                    
                    bot.send_message(
                        user_id,
                        "Quyidagilardan birini tanlang:",
                        reply_markup=markup
                    )
                    
                    bot.send_message(ADMIN_ID, f"✅ Rasm yuborildi!\n📋 {req_id}")
                
                elif message.text:
                    bot.send_message(
                        user_id,
                        f"📬 Admin javobi:\n\n{message.text}"
                    )
                    
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    btn1 = types.InlineKeyboardButton("✅ Buyurtma berish", callback_data=f"order_{req_id}")
                    btn2 = types.InlineKeyboardButton("🔄 Boshqa variant", callback_data=f"restart_{req_id}")
                    markup.add(btn1, btn2)
                    
                    bot.send_message(
                        user_id,
                        "Quyidagilardan birini tanlang:",
                        reply_markup=markup
                    )
                    
                    bot.send_message(ADMIN_ID, f"✅ Matn yuborildi!\n📋 {req_id}")
                
                reqs[req_id]['status'] = 'javob_berildi'
                requests_save(reqs)
                return
        
        elif user_match:
            user_id = int(user_match.group(1))
            
            if message.photo:
                photo = message.photo[-1].file_id
                caption = message.caption if message.caption else "Admin javobi"
                bot.send_photo(
                    user_id,
                    photo,
                    caption=f"📬 Admin javobi:\n\n{caption}"
                )
                bot.send_message(ADMIN_ID, f"✅ Chatda rasm yuborildi!")
            
            elif message.text:
                bot.send_message(
                    user_id,
                    f"📬 Admin javobi:\n\n{message.text}"
                )
                bot.send_message(ADMIN_ID, f"✅ Chatda matn yuborildi!")
            return
        
        else:
            bot.send_message(
                ADMIN_ID,
                "❌ So'rov ID yoki User ID topilmadi!\n"
                "Iltimos, so'rov yoki foydalanuvchi xabariga reply qiling."
            )
            
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Xatolik: {str(e)}")

# ==================== BUYURTMA TUGMALARI ====================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        user_id = call.message.chat.id
        data = call.data
        
        if data.startswith("order_"):
            req_id = data.replace("order_", "")
            reqs = requests_load()
            
            if req_id in reqs:
                add_bonus(user_id, 25, "Buyurtma berdi")
                
                user_name = reqs[req_id].get('user_name', 'Noma\'lum')
                user_phone = reqs[req_id].get('user_phone', 'Noma\'lum')
                
                bot.send_message(
                    ADMIN_ID,
                    f"✅ BUYURTMA QILINDI!\n\n"
                    f"📋 So'rov: {req_id}\n"
                    f"👤 Foydalanuvchi: {user_name}\n"
                    f"📞 Telefon: {user_phone}\n"
                    f"🆔 ID: {user_id}\n\n"
                    f"🚀 Tez orada bog'lanishingiz kerak!"
                )
                
                bot.edit_message_text(
                    "✅ Buyurtmangiz qabul qilindi!\nTez orada adminlarimiz siz bilan bog'lanadi.\n\n+25 bonus ball qo'shildi! 🎁",
                    user_id,
                    call.message.message_id
                )
                
                reqs[req_id]['status'] = 'buyurtma_qilindi'
                requests_save(reqs)
                
        elif data.startswith("restart_"):
            bot.edit_message_text(
                "🔄 Yangi so'rov yaratmoqchisiz? Quyidagi bo'limlardan birini tanlang.",
                user_id,
                call.message.message_id
            )
            
            users = users_load()
            if str(user_id) in users:
                main_menu(user_id, users[str(user_id)]['name'])
            
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Callback xatolik: {str(e)}")

# ==================== ADMIN BUYRUQLARI ====================

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.chat.id != ADMIN_ID:
        return
    
    users = users_load()
    requests_data = requests_load()
    
    total_users = len(users)
    total_requests = len(requests_data)
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_users = 0
    for user in users.values():
        if user.get('date', '').startswith(today):
            today_users += 1
    
    requests_by_type = {}
    for req in requests_data.values():
        service = req.get('service', 'unknown')
        requests_by_type[service] = requests_by_type.get(service, 0) + 1
    
    total_bonus = 0
    users_with_bonus = 0
    for user in users.values():
        bonus = user.get('bonus_ball', 0)
        total_bonus += bonus
        if bonus > 0:
            users_with_bonus += 1
    
    total_refs = 0
    top_refs = []
    for user_id, user in users.items():
        refs = user.get('referals_count', 0)
        total_refs += refs
        if refs > 0:
            top_refs.append({
                'name': user.get('name', 'Noma\'lum'),
                'count': refs
            })
    
    top_refs = sorted(top_refs, key=lambda x: x['count'], reverse=True)[:5]
    
    text = f"📊 BOT STATISTIKASI\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"👥 FOYDALANUVCHILAR:\n"
    text += f"   Jami: {total_users}\n"
    text += f"   Bugun: +{today_users}\n\n"
    
    text += f"📋 SO'ROVLAR:\n"
    text += f"   Jami: {total_requests}\n"
    for service, count in requests_by_type.items():
        service_name = {
            'avia': '✈️ Avia',
            'tour': '🌍 Tur',
            'visa': '🛂 Viza',
            'umra': '🕋 Umra'
        }.get(service, service)
        text += f"   {service_name}: {count}\n"
    text += "\n"
    
    text += f"⭐ BONUS TIZIMI:\n"
    text += f"   Jami ball: {total_bonus} 🪙\n"
    text += f"   Ball egalari: {users_with_bonus}\n\n"
    
    text += f"👥 REFERAL TIZIM:\n"
    text += f"   Jami takliflar: {total_refs}\n"
    if top_refs:
        text += f"   Top 5:\n"
        for ref in top_refs:
            text += f"      {ref['name']}: {ref['count']} ta\n"
    
    bot.send_message(ADMIN_ID, text)

@bot.message_handler(commands=['cleanup'])
def admin_cleanup(message):
    if message.chat.id != ADMIN_ID:
        return
    
    requests_data = requests_load()
    
    old_requests = []
    now = datetime.now()
    for req_id, req in requests_data.items():
        if 'created_at' in req:
            try:
                req_date = datetime.strptime(req['created_at'].split()[0], "%Y-%m-%d")
                if (now - req_date).days > 30:
                    old_requests.append(req_id)
            except:
                pass
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ Ha", callback_data="cleanup_confirm")
    btn2 = types.InlineKeyboardButton("❌ Yo'q", callback_data="cleanup_cancel")
    markup.add(btn1, btn2)
    
    bot.send_message(
        ADMIN_ID,
        f"🔍 TEKSHIRISH...\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🗑 Eski so'rovlar (30+ kun): {len(old_requests)} ta\n\n"
        f"🔄 TOZALASH TASDIQLANSINMI?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("cleanup_"))
def cleanup_callback(call):
    if call.message.chat.id != ADMIN_ID:
        return
    
    if call.data == "cleanup_confirm":
        requests_data = requests_load()
        
        old_count = 0
        now = datetime.now()
        new_requests = {}
        
        for req_id, req in requests_data.items():
            if 'created_at' in req:
                try:
                    req_date = datetime.strptime(req['created_at'].split()[0], "%Y-%m-%d")
                    if (now - req_date).days <= 30:
                        new_requests[req_id] = req
                    else:
                        old_count += 1
                except:
                    new_requests[req_id] = req
            else:
                new_requests[req_id] = req
        
        requests_save(new_requests)
        
        bot.edit_message_text(
            f"✅ TOZALANDI!\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🗑 O'chirilgan so'rovlar: {old_count}\n"
            f"📦 Qolgan so'rovlar: {len(new_requests)}",
            ADMIN_ID,
            call.message.message_id
        )
    else:
        bot.edit_message_text(
            "❌ Tozalash bekor qilindi.",
            ADMIN_ID,
            call.message.message_id
        )

@bot.message_handler(commands=['broadcast'])
def broadcast_start(message):
    if message.chat.id != ADMIN_ID:
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("❌ Bekor qilish"))
    
    bot.send_message(
        ADMIN_ID,
        "📢 **Broadcast rejimi**\n\n"
        "Endi yubormoqchi bo'lgan xabaringizni yozing yoki rasm yuboring.\n\n"
        "❌ Bekor qilish uchun tugmani bosing."
    )
    user_state[ADMIN_ID] = "broadcast_waiting"

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and user_state.get(ADMIN_ID) == "broadcast_waiting")
def broadcast_receive(message):
    chat_id = message.chat.id
    
    if message.text == "❌ Bekor qilish":
        user_state.pop(chat_id, None)
        users = users_load()
        main_menu(chat_id, users[str(chat_id)]['name'])
        return
    
    user_data[chat_id] = {'broadcast_msg': message}
    users = users_load()
    users_count = len(users)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ Ha", callback_data="broadcast_confirm")
    btn2 = types.InlineKeyboardButton("❌ Yo'q", callback_data="broadcast_cancel")
    markup.add(btn1, btn2)
    
    if message.photo:
        caption = message.caption if message.caption else "Rasm"
        bot.send_message(
            ADMIN_ID,
            f"🖼 **Rasm tayyor**\nIzoh: {caption}\n\n"
            f"👥 {users_count} ta foydalanuvchiga yuborilsinmi?",
            reply_markup=markup
        )
    else:
        bot.send_message(
            ADMIN_ID,
            f"📝 **Matn tayyor**\n{message.text}\n\n"
            f"👥 {users_count} ta foydalanuvchiga yuborilsinmi?",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data in ["broadcast_confirm", "broadcast_cancel"])
def broadcast_callback(call):
    if call.message.chat.id != ADMIN_ID:
        return
    
    if call.data == "broadcast_cancel":
        user_state.pop(ADMIN_ID, None)
        user_data.pop(ADMIN_ID, None)
        bot.edit_message_text(
            "❌ Broadcast bekor qilindi.",
            ADMIN_ID,
            call.message.message_id
        )
        users = users_load()
        main_menu(ADMIN_ID, users[str(ADMIN_ID)]['name'])
        return
    
    msg = user_data.get(ADMIN_ID, {}).get('broadcast_msg')
    if not msg:
        bot.edit_message_text("❌ Xabar topilmadi!", ADMIN_ID, call.message.message_id)
        return
    
    # "Yuborilmoqda" xabarini o'zgartirish
    bot.edit_message_text(
        "⏳ Xabar yuborilmoqda...\nBu biroz vaqt olishi mumkin.\n\n"
        "✅ Tugagach xabar beraman.",
        ADMIN_ID,
        call.message.message_id
    )
    
    users = users_load()
    success = 0
    failed = 0
    
    # Foydalanuvchilar ro'yxatini olish
    user_ids = list(users.keys())
    total = len(user_ids)
    
    # Har bir foydalanuvchiga yuborish
    for i, user_id in enumerate(user_ids):
        try:
            if msg.photo:
                photo = msg.photo[-1].file_id
                caption = msg.caption if msg.caption else "📢 Xabar"
                bot.send_photo(
                    int(user_id),
                    photo,
                    caption=f"📢 **Xabar**\n\n{caption}"
                )
            else:
                bot.send_message(
                    int(user_id),
                    f"📢 **Xabar**\n\n{msg.text}"
                )
            
            success += 1
            
            # Har 10 ta foydalanuvchidan keyin holatni yangilash
            if i % 10 == 0 and i > 0:
                try:
                    bot.edit_message_text(
                        f"⏳ Yuborilmoqda... {i}/{total}\n"
                        f"✓ Yuborilgan: {success}\n"
                        f"✗ Yuborilmagan: {failed}",
                        ADMIN_ID,
                        call.message.message_id
                    )
                except:
                    pass
            
            # Telegram limiti (1 soniyada 30 ta xabar)
            time.sleep(0.05)
            
        except Exception as e:
            failed += 1
            print(f"Xatolik {user_id}: {e}")
    
    # Yakuniy xabar
    try:
        bot.edit_message_text(
            f"✅ **Broadcast yakunlandi!**\n\n"
            f"📊 **Natija:**\n"
            f"✓ Yuborilgan: {success}\n"
            f"✗ Yuborilmagan: {failed}\n"
            f"👥 Jami: {total}",
            ADMIN_ID,
            call.message.message_id
        )
    except:
        bot.send_message(
            ADMIN_ID,
            f"✅ **Broadcast yakunlandi!**\n\n"
            f"📊 **Natija:**\n"
            f"✓ Yuborilgan: {success}\n"
            f"✗ Yuborilmagan: {failed}\n"
            f"👥 Jami: {total}"
        )
    
    user_state.pop(ADMIN_ID, None)
    user_data.pop(ADMIN_ID, None)

# ==================== AVIA ====================

def start_avia(chat_id, name):
    user_data[chat_id] = {'xizmat': 'avia', 'ism': name}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🛫 Borish"), types.KeyboardButton("🛫🛬 Borish va qaytish"))
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "✈️ Aviachipta\n\nQanday chipta kerak?", reply_markup=markup)
    user_state[chat_id] = "avia_type"

def avia_after_date(chat_id):
    if "Borish va qaytish" in user_data[chat_id]['type']:
        user_data[chat_id]['calendar_for'] = 'avia_return'
        bot.send_message(
            chat_id,
            "📅 Qaytish sanasini tanlang:",
            reply_markup=create_calendar()
        )
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "👥 Necha kishi?", reply_markup=markup)
        user_state[chat_id] = "avia_passengers"

def avia_after_return(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "👥 Necha kishi?", reply_markup=markup)
    user_state[chat_id] = "avia_passengers"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "avia_type")
def avia_type(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        users = users_load()
        main_menu(chat_id, users[str(chat_id)]['name'])
        user_state.pop(chat_id, None)
        return
    
    user_data[chat_id]['type'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "📍 Qayerdan?\nMisol: Toshkent", reply_markup=markup)
    user_state[chat_id] = "avia_from"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "avia_from")
def avia_from(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        start_avia(chat_id, user_data[chat_id]['ism'])
        return
    user_data[chat_id]['from'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "📍 Qayerga?\nMisol: Istanbul", reply_markup=markup)
    user_state[chat_id] = "avia_to"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "avia_to")
def avia_to(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "📍 Qayerdan?", reply_markup=markup)
        user_state[chat_id] = "avia_from"
        return
    user_data[chat_id]['to'] = message.text
    
    user_data[chat_id]['calendar_for'] = 'avia_date'
    bot.send_message(
        chat_id,
        "📅 Borish sanasini tanlang:",
        reply_markup=create_calendar()
    )
    user_state.pop(chat_id, None)

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "avia_passengers")
def avia_passengers(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        if "return_date" in user_data[chat_id]:
            user_data[chat_id]['calendar_for'] = 'avia_return'
            bot.send_message(
                chat_id,
                "📅 Qaytish sanasini tanlang:",
                reply_markup=create_calendar()
            )
            user_state.pop(chat_id, None)
        else:
            user_data[chat_id]['calendar_for'] = 'avia_date'
            bot.send_message(
                chat_id,
                "📅 Borish sanasini tanlang:",
                reply_markup=create_calendar()
            )
            user_state.pop(chat_id, None)
        return
    user_data[chat_id]['passengers'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🧳 Bagajli"), types.KeyboardButton("🛄 Bagajsiz"))
    markup.add(types.KeyboardButton("⚖️ Ikkalasini ham"))
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "🧳 Bagaj\n\nQanday bagaj kerak?", reply_markup=markup)
    user_state[chat_id] = "avia_baggage"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "avia_baggage")
def avia_baggage(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "👥 Necha kishi?", reply_markup=markup)
        user_state[chat_id] = "avia_passengers"
        return
    
    user_data[chat_id]['baggage'] = message.text
    submit_avia(chat_id)

def submit_avia(chat_id):
    req_id = unique_id()
    user_data[chat_id]['req_id'] = req_id
    user_data[chat_id]['time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    users = users_load()
    phone = users[str(chat_id)]['phone']
    
    add_bonus(chat_id, 5, "Aviachipta so'rovi")
    
    users[str(chat_id)]['requests_count'] = users[str(chat_id)].get('requests_count', 0) + 1
    
    month = datetime.now().strftime("%Y-%m")
    if 'monthly_stats' not in users[str(chat_id)]:
        users[str(chat_id)]['monthly_stats'] = {}
    if month not in users[str(chat_id)]['monthly_stats']:
        users[str(chat_id)]['monthly_stats'][month] = {'requests': 0, 'orders': 0}
    users[str(chat_id)]['monthly_stats'][month]['requests'] += 1
    
    users_save(users)
    
    bot.send_message(
        chat_id,
        f"✅ So'rovingiz qabul qilindi!\n\n"
        f"📋 So'rov raqami: {req_id}\n\n"
        f"⏳ Adminlarimiz eng arzon reysni qidirmoqda...\n\n"
        f"+5 bonus ball qo'shildi! 🎁"
    )
    
    text = f"✈️ YANGI AVIA SO'ROVI\n\n"
    text += f"📋 {req_id}\n"
    text += f"👤 {user_data[chat_id]['ism']}\n"
    text += f"📞 {phone}\n\n"
    text += f"📍 {user_data[chat_id]['from']} → {user_data[chat_id]['to']}\n"
    text += f"📅 {user_data[chat_id]['date']}\n"
    if 'return_date' in user_data[chat_id]:
        text += f"📅 Qaytish: {user_data[chat_id]['return_date']}\n"
    text += f"👥 {user_data[chat_id]['passengers']}\n"
    text += f"🧳 {user_data[chat_id]['baggage']}\n\n"
    text += f"✅ Javob berish uchun reply qiling!"
    
    bot.send_message(ADMIN_ID, text)
    
    reqs = requests_load()
    reqs[req_id] = {
        'user_id': chat_id,
        'user_name': user_data[chat_id]['ism'],
        'user_phone': phone,
        'service': 'avia',
        'data': user_data[chat_id].copy(),
        'status': 'yangi',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    requests_save(reqs)
    
    user_state.pop(chat_id, None)
    if chat_id in temp_data:
        temp_data.pop(chat_id)
    users = users_load()
    main_menu(chat_id, users[str(chat_id)]['name'])

# ==================== TURLAR ====================

def start_tour(chat_id, name):
    user_data[chat_id] = {'xizmat': 'tour', 'ism': name}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "🌍 Sayohat turlari\n\n📍 Qayerdan?", reply_markup=markup)
    user_state[chat_id] = "tour_from"

def tour_after_date(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "🌙 Necha kecha?", reply_markup=markup)
    user_state[chat_id] = "tour_nights"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "tour_from")
def tour_from(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        users = users_load()
        main_menu(chat_id, users[str(chat_id)]['name'])
        user_state.pop(chat_id, None)
        return
    user_data[chat_id]['from'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "📍 Qayerga?", reply_markup=markup)
    user_state[chat_id] = "tour_to"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "tour_to")
def tour_to(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "📍 Qayerdan?", reply_markup=markup)
        user_state[chat_id] = "tour_from"
        return
    user_data[chat_id]['to'] = message.text
    
    user_data[chat_id]['calendar_for'] = 'tour_date'
    bot.send_message(
        chat_id,
        "📅 Qachon borishni xohlaysiz?",
        reply_markup=create_calendar()
    )
    user_state.pop(chat_id, None)

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "tour_nights")
def tour_nights(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        user_data[chat_id]['calendar_for'] = 'tour_date'
        bot.send_message(
            chat_id,
            "📅 Qachon borishni xohlaysiz?",
            reply_markup=create_calendar()
        )
        user_state.pop(chat_id, None)
        return
    user_data[chat_id]['nights'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "👥 Necha kishi?", reply_markup=markup)
    user_state[chat_id] = "tour_people"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "tour_people")
def tour_people(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "🌙 Necha kecha?", reply_markup=markup)
        user_state[chat_id] = "tour_nights"
        return
    user_data[chat_id]['people'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "👨‍👩‍👧‍👦 Kimlar uchun?\nO'zingiz yozing:", reply_markup=markup)
    user_state[chat_id] = "tour_for"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "tour_for")
def tour_for(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "👥 Necha kishi?", reply_markup=markup)
        user_state[chat_id] = "tour_people"
        return
    user_data[chat_id]['for'] = message.text
    submit_tour(chat_id)

def submit_tour(chat_id):
    req_id = unique_id()
    user_data[chat_id]['req_id'] = req_id
    user_data[chat_id]['time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    users = users_load()
    phone = users[str(chat_id)]['phone']
    
    add_bonus(chat_id, 5, "Tur so'rovi")
    
    users[str(chat_id)]['requests_count'] = users[str(chat_id)].get('requests_count', 0) + 1
    
    month = datetime.now().strftime("%Y-%m")
    if 'monthly_stats' not in users[str(chat_id)]:
        users[str(chat_id)]['monthly_stats'] = {}
    if month not in users[str(chat_id)]['monthly_stats']:
        users[str(chat_id)]['monthly_stats'][month] = {'requests': 0, 'orders': 0}
    users[str(chat_id)]['monthly_stats'][month]['requests'] += 1
    
    users_save(users)
    
    bot.send_message(
        chat_id,
        f"✅ So'rovingiz qabul qilindi!\n\n"
        f"📋 So'rov raqami: {req_id}\n\n"
        f"⏳ Adminlarimiz eng yaxshi turni qidirmoqda...\n\n"
        f"+5 bonus ball qo'shildi! 🎁"
    )
    
    text = f"🌍 YANGI TUR SO'ROVI\n\n"
    text += f"📋 {req_id}\n"
    text += f"👤 {user_data[chat_id]['ism']}\n"
    text += f"📞 {phone}\n\n"
    text += f"📍 {user_data[chat_id]['from']} → {user_data[chat_id]['to']}\n"
    text += f"📅 {user_data[chat_id]['date']}\n"
    text += f"🌙 {user_data[chat_id]['nights']}\n"
    text += f"👥 {user_data[chat_id]['people']}\n"
    text += f"👨‍👩‍👧‍👦 {user_data[chat_id]['for']}\n\n"
    text += f"✅ Javob berish uchun reply qiling!"
    
    bot.send_message(ADMIN_ID, text)
    
    reqs = requests_load()
    reqs[req_id] = {
        'user_id': chat_id,
        'user_name': user_data[chat_id]['ism'],
        'user_phone': phone,
        'service': 'tour',
        'data': user_data[chat_id].copy(),
        'status': 'yangi',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    requests_save(reqs)
    
    user_state.pop(chat_id, None)
    if chat_id in temp_data:
        temp_data.pop(chat_id)
    users = users_load()
    main_menu(chat_id, users[str(chat_id)]['name'])

# ==================== VIZA ====================

def start_visa(chat_id, name):
    user_data[chat_id] = {'xizmat': 'visa', 'ism': name}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "🛂 Viza yordami\n\n🌍 Qaysi davlat?", reply_markup=markup)
    user_state[chat_id] = "visa_country"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "visa_country")
def visa_country(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        users = users_load()
        main_menu(chat_id, users[str(chat_id)]['name'])
        user_state.pop(chat_id, None)
        return
    user_data[chat_id]['country'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "👥 Necha kishi?", reply_markup=markup)
    user_state[chat_id] = "visa_people"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "visa_people")
def visa_people(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "🌍 Qaysi davlat?", reply_markup=markup)
        user_state[chat_id] = "visa_country"
        return
    user_data[chat_id]['people'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("15 kun"),
        types.KeyboardButton("30 kun"),
        types.KeyboardButton("90 kun"),
        types.KeyboardButton("1 yil"),
        types.KeyboardButton("Ko'proq")
    )
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "⏳ Viza muddati?", reply_markup=markup)
    user_state[chat_id] = "visa_term"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "visa_term")
def visa_term(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "👥 Necha kishi?", reply_markup=markup)
        user_state[chat_id] = "visa_people"
        return
    
    user_data[chat_id]['term'] = message.text
    submit_visa(chat_id)

def submit_visa(chat_id):
    req_id = unique_id()
    user_data[chat_id]['req_id'] = req_id
    user_data[chat_id]['time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    users = users_load()
    phone = users[str(chat_id)]['phone']
    
    add_bonus(chat_id, 5, "Viza so'rovi")
    
    users[str(chat_id)]['requests_count'] = users[str(chat_id)].get('requests_count', 0) + 1
    
    month = datetime.now().strftime("%Y-%m")
    if 'monthly_stats' not in users[str(chat_id)]:
        users[str(chat_id)]['monthly_stats'] = {}
    if month not in users[str(chat_id)]['monthly_stats']:
        users[str(chat_id)]['monthly_stats'][month] = {'requests': 0, 'orders': 0}
    users[str(chat_id)]['monthly_stats'][month]['requests'] += 1
    
    users_save(users)
    
    bot.send_message(
        chat_id,
        f"✅ So'rovingiz qabul qilindi!\n\n"
        f"📋 So'rov raqami: {req_id}\n\n"
        f"⏳ Adminlarimiz tez orada bog'lanadi!\n\n"
        f"+5 bonus ball qo'shildi! 🎁"
    )
    
    text = f"🛂 YANGI VIZA SO'ROVI\n\n"
    text += f"📋 {req_id}\n"
    text += f"👤 {user_data[chat_id]['ism']}\n"
    text += f"📞 {phone}\n\n"
    text += f"🌍 {user_data[chat_id]['country']}\n"
    text += f"👥 {user_data[chat_id]['people']}\n"
    text += f"⏳ {user_data[chat_id]['term']}\n\n"
    text += f"✅ Javob berish uchun reply qiling!"
    
    bot.send_message(ADMIN_ID, text)
    
    reqs = requests_load()
    reqs[req_id] = {
        'user_id': chat_id,
        'user_name': user_data[chat_id]['ism'],
        'user_phone': phone,
        'service': 'visa',
        'data': user_data[chat_id].copy(),
        'status': 'yangi',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    requests_save(reqs)
    
    user_state.pop(chat_id, None)
    users = users_load()
    main_menu(chat_id, users[str(chat_id)]['name'])

# ==================== UMRA ====================

def start_umra(chat_id, name):
    user_data[chat_id] = {'xizmat': 'umra', 'ism': name}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "🕋 Umra safarlari\n\n🏙 Qaysi viloyat?", reply_markup=markup)
    user_state[chat_id] = "umra_region"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "umra_region")
def umra_region(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        users = users_load()
        main_menu(chat_id, users[str(chat_id)]['name'])
        user_state.pop(chat_id, None)
        return
    user_data[chat_id]['region'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Orqaga"))
    bot.send_message(chat_id, "👥 Necha kishi?", reply_markup=markup)
    user_state[chat_id] = "umra_people"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "umra_people")
def umra_people(message):
    chat_id = message.chat.id
    if message.text == "🔙 Orqaga":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Orqaga"))
        bot.send_message(chat_id, "🏙 Qaysi viloyat?", reply_markup=markup)
        user_state[chat_id] = "umra_region"
        return
    user_data[chat_id]['people'] = message.text
    submit_umra(chat_id)

def submit_umra(chat_id):
    req_id = unique_id()
    user_data[chat_id]['req_id'] = req_id
    user_data[chat_id]['time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    users = users_load()
    phone = users[str(chat_id)]['phone']
    
    add_bonus(chat_id, 5, "Umra so'rovi")
    
    users[str(chat_id)]['requests_count'] = users[str(chat_id)].get('requests_count', 0) + 1
    
    month = datetime.now().strftime("%Y-%m")
    if 'monthly_stats' not in users[str(chat_id)]:
        users[str(chat_id)]['monthly_stats'] = {}
    if month not in users[str(chat_id)]['monthly_stats']:
        users[str(chat_id)]['monthly_stats'][month] = {'requests': 0, 'orders': 0}
    users[str(chat_id)]['monthly_stats'][month]['requests'] += 1
    
    users_save(users)
    
    bot.send_message(
        chat_id,
        f"✅ So'rovingiz qabul qilindi!\n\n"
        f"📋 So'rov raqami: {req_id}\n\n"
        f"⏳ Adminlarimiz tez orada bog'lanadi!\n\n"
        f"+5 bonus ball qo'shildi! 🎁"
    )
    
    text = f"🕋 YANGI UMRA SO'ROVI\n\n"
    text += f"📋 {req_id}\n"
    text += f"👤 {user_data[chat_id]['ism']}\n"
    text += f"📞 {phone}\n\n"
    text += f"🏙 {user_data[chat_id]['region']}\n"
    text += f"👥 {user_data[chat_id]['people']}\n\n"
    text += f"✅ Javob berish uchun reply qiling!"
    
    bot.send_message(ADMIN_ID, text)
    
    reqs = requests_load()
    reqs[req_id] = {
        'user_id': chat_id,
        'user_name': user_data[chat_id]['ism'],
        'user_phone': phone,
        'service': 'umra',
        'data': user_data[chat_id].copy(),
        'status': 'yangi',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    requests_save(reqs)
    
    user_state.pop(chat_id, None)
    users = users_load()
    main_menu(chat_id, users[str(chat_id)]['name'])

# ==================== ISHGA TUSHIRISH ====================

if __name__ == "__main__":
    print("🤖 EasyBooking Jizzax Bot ishga tushmoqda...")
    print(f"✅ Admin ID: {ADMIN_ID}")
    
    while True:
        try:
            print("🤖 Bot ishlamoqda...")
            bot.polling(non_stop=True, interval=0, timeout=30)
        except Exception as e:
            print(f"❌ Xatolik: {e}")
            print("⏳ 10 soniyadan keyin qayta ishga tushadi...")
            time.sleep(10)
            continue
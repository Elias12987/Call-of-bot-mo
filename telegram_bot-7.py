import sqlite3
import json
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import schedule
import time

# تنظیمات
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # توکن ربات رو اینجا بزار
CHANNEL_1 = "phdjld"  # بدون @
CHANNEL_2 = "poruirlae"  # بدون @

# لیست ادمین‌ها (آیدی عددی)
ADMIN_IDS = [
    123456789,  # ادمین اول
    987654321,  # ادمین دوم
    111111111,  # ادمین سوم (دلخواه)
]

bot = TeleBot(BOT_TOKEN)

# ==== DATABASE SETUP ====
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # جدول کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, points INTEGER, 
                  referral_code TEXT, joined_date TEXT, verified INTEGER)''')
    
    # جدول محصولات (دکمه‌ها)
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                  cost INTEGER, description TEXT, button_text TEXT, action TEXT)''')
    
    # جدول دعوت‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (referrer_id INTEGER, referred_id INTEGER, date TEXT, 
                  FOREIGN KEY(referrer_id) REFERENCES users(user_id),
                  FOREIGN KEY(referred_id) REFERENCES users(user_id))''')
    
    # جدول تنظیمات ادمین
    c.execute('''CREATE TABLE IF NOT EXISTS admin_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, 
                  type TEXT, created_at TEXT)''')
    
    # جدول امتیاز روزانه
    c.execute('''CREATE TABLE IF NOT EXISTS daily_rewards
                 (user_id INTEGER PRIMARY KEY, last_claim_date TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ==== DATABASE FUNCTIONS ====
def user_exists(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def create_user(user_id, username, referral_code=None):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    if referral_code is None:
        referral_code = f"ref_{user_id}"
    c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, username, 0, referral_code, datetime.now().isoformat(), 0))
    conn.commit()
    conn.close()

def get_user_points(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def add_points(user_id, points):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    current = get_user_points(user_id)
    c.execute("UPDATE users SET points = ? WHERE user_id = ?", (current + points, user_id))
    conn.commit()
    conn.close()

def subtract_points(user_id, points):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    current = get_user_points(user_id)
    if current >= points:
        c.execute("UPDATE users SET points = ? WHERE user_id = ?", (current - points, user_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def verify_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_verified(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT verified FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO referrals VALUES (?, ?, ?)",
              (referrer_id, referred_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_products():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return products

def add_product(name, cost, description, button_text, action):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO products (name, cost, description, button_text, action) VALUES (?, ?, ?, ?, ?)",
              (name, cost, description, button_text, action))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def get_user_stats():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT SUM(points) FROM users")
    total_points = c.fetchone()[0] or 0
    conn.close()
    return total_users, total_points

def can_claim_daily_reward(user_id):
    """بررسی اینکه آیا کاربر امتیاز روزانه رو دریافت کرده"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT last_claim_date FROM daily_rewards WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return True
    
    last_claim = result[0]
    return last_claim != today

def claim_daily_reward(user_id):
    """ثبت امتیاز روزانه"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT last_claim_date FROM daily_rewards WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        c.execute("UPDATE daily_rewards SET last_claim_date = ? WHERE user_id = ?", 
                 (today, user_id))
    else:
        c.execute("INSERT INTO daily_rewards VALUES (?, ?)", (user_id, today))
    
    add_points(user_id, 1)  # 1 امتیاز روزانه
    conn.commit()
    conn.close()

def transfer_points_admin(from_user_id, to_user_id, amount):
    """انتقال امتیاز توسط ادمین"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # بررسی کاربر مبدا
    c.execute("SELECT points FROM users WHERE user_id = ?", (from_user_id,))
    from_user = c.fetchone()
    
    # بررسی کاربر مقصد
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (to_user_id,))
    to_user = c.fetchone()
    
    conn.close()
    
    if not to_user:
        return False, "❌ کاربر مقصد یافت نشد"
    
    if not from_user:
        return False, "❌ کاربر مبدا یافت نشد"
    
    # انتقال امتیاز
    if subtract_points(from_user_id, amount):
        add_points(to_user_id, amount)
        return True, f"✅ {amount} امتیاز به کاربر منتقل شد"
    else:
        return False, "❌ امتیاز ناکافی است"

# ==== HELPER FUNCTIONS ====
def check_channel_membership(user_id):
    try:
        # بررسی عضویت در کانال اول
        member1 = bot.get_chat_member(f"@{CHANNEL_1}", user_id)
        status1 = member1.status in ['member', 'administrator', 'creator']
        
        # بررسی عضویت در کانال دوم
        member2 = bot.get_chat_member(f"@{CHANNEL_2}", user_id)
        status2 = member2.status in ['member', 'administrator', 'creator']
        
        return status1, status2
    except:
        return False, False

def create_main_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ تأیید عضویت", callback_data="verify"))
    markup.add(InlineKeyboardButton("🎁 امتیاز روزانه🎁", callback_data="daily_reward"))
    markup.add(InlineKeyboardButton("🎁 بخش محصولات", callback_data="products"))
    markup.add(InlineKeyboardButton("👥 دعوت دوستان", callback_data="invite"))
    markup.add(InlineKeyboardButton("📊 آمار من", callback_data="stats"))
    markup.add(InlineKeyboardButton("⚙️ ادمین", callback_data="admin_panel"))
    return markup

def create_channel_verification_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"🔗 {CHANNEL_1}", url=f"https://t.me/{CHANNEL_1}"))
    markup.add(InlineKeyboardButton(f"🔗 {CHANNEL_2}", url=f"https://t.me/{CHANNEL_2}"))
    markup.add(InlineKeyboardButton("✅ تأیید کردم", callback_data="check_verify"))
    return markup

# ==== COMMANDS ====
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    # اگر کاربر جدید است
    if not user_exists(user_id):
        # بررسی اینکه آیا از طریق لینک referral آمده است
        args = message.text.split()
        referrer_id = None
        if len(args) > 1:
            try:
                referrer_id = int(args[1])
                if user_exists(referrer_id):
                    add_referral(referrer_id, user_id)
                    add_points(referrer_id, 1)  # 1 امتیاز برای دعوت
            except:
                pass
        
        create_user(user_id, username)
    
    msg = "🎉 خوش‌آمدید!\n\nبرای استفاده از بات، ابتدا باید در کانال‌های زیر عضو شوید:"
    bot.send_message(user_id, msg, reply_markup=create_channel_verification_menu())

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_handler(call):
    user_id = call.from_user.id
    status1, status2 = check_channel_membership(user_id)
    
    if status1 and status2:
        verify_user(user_id)
        bot.answer_callback_query(call.id, "✅ تایید شد!", show_alert=False)
        bot.send_message(user_id, "🎉 شما تأیید شدید! اکنون می‌توانید از همه بخش‌ها استفاده کنید.",
                        reply_markup=create_main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ ابتدا در هر دو کانال عضو شوید", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "check_verify")
def check_verify(call):
    user_id = call.from_user.id
    status1, status2 = check_channel_membership(user_id)
    
    if status1 and status2:
        verify_user(user_id)
        bot.answer_callback_query(call.id, "✅ تایید شد!", show_alert=False)
        bot.send_message(user_id, "🎉 شما تأیید شدید! اکنون می‌توانید از همه بخش‌ها استفاده کنید.",
                        reply_markup=create_main_menu())
    else:
        missing = []
        if not status1:
            missing.append(CHANNEL_1)
        if not status2:
            missing.append(CHANNEL_2)
        msg = f"❌ شما هنوز در کانال‌های زیر عضو نشده‌اید:\n" + "\n".join(f"@{ch}" for ch in missing)
        bot.answer_callback_query(call.id, msg, show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "products")
def products_handler(call):
    user_id = call.from_user.id
    
    if not is_verified(user_id):
        bot.answer_callback_query(call.id, "❌ ابتدا تأیید شوید", show_alert=True)
        return
    
    products = get_products()
    if not products:
        bot.send_message(user_id, "❌ محصولی در دسترس نیست")
        return
    
    user_points = get_user_points(user_id)
    msg = f"💰 امتیازات شما: {user_points}\n\n📦 محصولات:\n\n"
    
    markup = InlineKeyboardMarkup()
    for product in products:
        prod_id, name, cost, desc, button_text, action = product
        msg += f"• {name} - {cost} امتیاز\n"
        markup.add(InlineKeyboardButton(f"{button_text} ({cost}⭐)", 
                                       callback_data=f"buy_{prod_id}"))
    
    markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    bot.send_message(user_id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_handler(call):
    user_id = call.from_user.id
    product_id = int(call.data.split("_")[1])
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT name, cost FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()
    
    if not product:
        bot.answer_callback_query(call.id, "❌ محصول یافت نشد", show_alert=True)
        return
    
    name, cost = product
    if subtract_points(user_id, cost):
        bot.answer_callback_query(call.id, f"✅ {name} را خریدید!", show_alert=False)
        bot.send_message(user_id, f"🎉 تبریک! شما {name} را خریدید.\n\n(توضیحات بیشتر را از ادمین بپرسید)")
    else:
        bot.answer_callback_query(call.id, "❌ امتیاز ناکافی است", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "invite")
def invite_handler(call):
    user_id = call.from_user.id
    
    if not is_verified(user_id):
        bot.answer_callback_query(call.id, "❌ ابتدا تأیید شوید", show_alert=True)
        return
    
    referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    msg = f"👥 لینک دعوت شما:\n\n<code>{referral_link}</code>\n\nهر نفری که از این لینک دعوت کنید: +1 امتیاز"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 آمار دعوت‌های من", callback_data="referral_stats"))
    markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    
    bot.send_message(user_id, msg, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "referral_stats")
def referral_stats(call):
    user_id = call.from_user.id
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    
    msg = f"📊 تعداد افرادی که دعوت کردید: {count}\n💰 امتیاز جمع‌آوری شده: {count}"
    bot.send_message(user_id, msg)

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats_handler(call):
    user_id = call.from_user.id
    points = get_user_points(user_id)
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    referrals = c.fetchone()[0]
    conn.close()
    
    msg = f"📊 آمار شما:\n\n💰 امتیازات: {points}\n👥 دعوت‌های شما: {referrals}"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    
    bot.send_message(user_id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    user_id = call.from_user.id
    bot.send_message(user_id, "برگشتید به منوی اصلی:", reply_markup=create_main_menu())
    bot.delete_message(user_id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "daily_reward")
def daily_reward_handler(call):
    user_id = call.from_user.id
    
    if not is_verified(user_id):
        bot.answer_callback_query(call.id, "❌ ابتدا تأیید شوید", show_alert=True)
        return
    
    if can_claim_daily_reward(user_id):
        claim_daily_reward(user_id)
        msg = "🎉 تبریک میگم! مقدار 1 امتیاز برنده شدی! 🎉\n\n✅ هر روز ساعت 3 میتونی این بخش و فعال کنی\n\n• یادت نره ساعت 3 این بخش و فعال کنی و امتیاز بگیری"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
        
        bot.send_message(user_id, msg, reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "❌ شما امروز قبلاً امتیاز دریافت کرده‌اید\n\n⏰ فردا ساعت 3 دوباره می‌تونی بگیری", show_alert=True)

# ==== ADMIN PANEL ====
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel(call):
    user_id = call.from_user.id
    
    if user_id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ شما ادمین نیستید", show_alert=True)
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ اضافه کردن محصول", callback_data="admin_add_product"))
    markup.add(InlineKeyboardButton("📝 ویرایش محصولات", callback_data="admin_list_products"))
    markup.add(InlineKeyboardButton("💸 انتقال امتیاز", callback_data="admin_transfer_points"))
    markup.add(InlineKeyboardButton("📢 پیام گروهی", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats"))
    markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"))
    
    msg = "⚙️ پنل ادمین"
    bot.send_message(user_id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_product")
def admin_add_product(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    msg = "📝 برای اضافه کردن محصول جدید:\n\nنام محصول را وارد کنید:"
    bot.send_message(user_id, msg)
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_name)

def admin_product_name(message):
    user_id = message.from_user.id
    product_name = message.text
    
    msg = "💰 هزینه (امتیاز) را وارد کنید:"
    bot.send_message(user_id, msg)
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_cost, product_name)

def admin_product_cost(message, product_name):
    user_id = message.from_user.id
    try:
        cost = int(message.text)
    except:
        bot.send_message(user_id, "❌ عدد صحیح وارد کنید")
        return
    
    msg = "📖 توضیحات محصول را وارد کنید:"
    bot.send_message(user_id, msg)
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_desc, product_name, cost)

def admin_product_desc(message, product_name, cost):
    user_id = message.from_user.id
    description = message.text
    
    msg = "🔘 متن دکمه را وارد کنید:"
    bot.send_message(user_id, msg)
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_button, product_name, cost, description)

def admin_product_button(message, product_name, cost, description):
    user_id = message.from_user.id
    button_text = message.text
    
    msg = "⚡ عملیات دکمه را وارد کنید (یا 'none' برای فعلاً):"
    bot.send_message(user_id, msg)
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_action, product_name, cost, description, button_text)

def admin_product_action(message, product_name, cost, description, button_text):
    user_id = message.from_user.id
    action = message.text
    
    add_product(product_name, cost, description, button_text, action)
    bot.send_message(user_id, f"✅ محصول '{product_name}' اضافه شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_products")
def admin_list_products(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    products = get_products()
    if not products:
        bot.send_message(user_id, "❌ محصولی وجود ندارد")
        return
    
    msg = "📦 لیست محصولات:\n\n"
    markup = InlineKeyboardMarkup()
    
    for product in products:
        prod_id, name, cost, desc, button_text, action = product
        msg += f"ID: {prod_id} - {name} ({cost}⭐)\n"
        markup.add(InlineKeyboardButton(f"🗑️ حذف {name}", callback_data=f"admin_delete_{prod_id}"))
    
    bot.send_message(user_id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_delete_"))
def admin_delete_product(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    product_id = int(call.data.split("_")[2])
    delete_product(product_id)
    bot.answer_callback_query(call.id, "✅ محصول حذف شد", show_alert=False)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    msg = "📢 پیام خود را برای ارسال به همه کاربران وارد کنید:"
    bot.send_message(user_id, msg)
    bot.register_next_step_handler_by_chat_id(user_id, admin_send_broadcast)

def admin_send_broadcast(message):
    user_id = message.from_user.id
    broadcast_msg = message.text
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    count = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 پیام از ادمین:\n\n{broadcast_msg}")
            count += 1
        except:
            pass
    
    bot.send_message(user_id, f"✅ پیام به {count} کاربر ارسال شد")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    total_users, total_points = get_user_stats()
    msg = f"📊 آمار کل:\n\n👥 کل کاربران: {total_users}\n💰 کل امتیازات: {total_points}"
    
    bot.send_message(user_id, msg)

@bot.callback_query_handler(func=lambda call: call.data == "admin_transfer_points")
def admin_transfer_points(call):
    user_id = call.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    msg = "💸 برای انتقال امتیاز:\n\nآیدی عددی کاربر گیرنده را وارد کنید:"
    bot.send_message(user_id, msg)
    bot.register_next_step_handler_by_chat_id(user_id, transfer_points_step1)

def transfer_points_step1(message):
    """گرفتن آیدی کاربر گیرنده"""
    user_id = message.from_user.id
    
    try:
        recipient_id = int(message.text)
    except:
        bot.send_message(user_id, "❌ آیدی صحیح وارد کنید (عددی)")
        return
    
    # چک کن کاربر وجود داره
    if not user_exists(recipient_id):
        bot.send_message(user_id, "❌ این کاربر در سیستم نیست")
        return
    
    msg = "💰 مقدار امتیاز را وارد کنید:"
    bot.send_message(user_id, msg)
    bot.register_next_step_handler_by_chat_id(user_id, transfer_points_step2, recipient_id)

def transfer_points_step2(message, recipient_id):
    """گرفتن مقدار امتیاز"""
    user_id = message.from_user.id
    
    try:
        amount = int(message.text)
        if amount <= 0:
            bot.send_message(user_id, "❌ مقدار باید بیشتر از صفر باشد")
            return
    except:
        bot.send_message(user_id, "❌ عدد صحیح وارد کنید")
        return
    
    # انتقال امتیاز
    success, msg = transfer_points_admin(user_id, recipient_id, amount)
    
    if success:
        bot.send_message(user_id, msg)
        # پیام به کاربر گیرنده
        try:
            bot.send_message(recipient_id, f"🎉 {amount} امتیاز از طرف ادمین دریافت کردید!")
        except:
            pass
    else:
        bot.send_message(user_id, msg)

# ==== RUN BOT ====
if __name__ == "__main__":
    print("🤖 ربات در حال اجرا است...")
    bot.infinity_polling()

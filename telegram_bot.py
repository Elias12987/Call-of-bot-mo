import sqlite3
from datetime import datetime
from telebot import TeleBot, types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# تنظیمات
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
CHANNEL_1 = "phdjld"   # بدون @
CHANNEL_2 = "poruirlae"  # بدون @
ADMIN_ID = 123456789   # آیدی عددی ادمین

bot = TeleBot(BOT_TOKEN)

# ==== DATABASE SETUP ====
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, points INTEGER DEFAULT 0,
                  referral_code TEXT, joined_date TEXT, verified INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
                  cost INTEGER, description TEXT, button_text TEXT, action TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (referrer_id INTEGER, referred_id INTEGER, date TEXT,
                  FOREIGN KEY(referrer_id) REFERENCES users(user_id),
                  FOREIGN KEY(referred_id) REFERENCES users(user_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT,
                  type TEXT, created_at TEXT)''')
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

def create_user(user_id, username):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    referral_code = f"ref_{user_id}"
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)",
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
    c.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
    conn.commit()
    conn.close()

def subtract_points(user_id, points):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result and result[0] >= points:
        c.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (points, user_id))
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

def referral_exists(referrer_id, referred_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM referrals WHERE referred_id = ?", (referred_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

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

# ==== HELPER FUNCTIONS ====
def check_channel_membership(user_id):
    try:
        member1 = bot.get_chat_member(f"@{CHANNEL_1}", user_id)
        status1 = member1.status in ['member', 'administrator', 'creator']
        member2 = bot.get_chat_member(f"@{CHANNEL_2}", user_id)
        status2 = member2.status in ['member', 'administrator', 'creator']
        return status1, status2
    except:
        return False, False

# ==== KEYBOARDS ====
def create_main_keyboard(user_id=None):
    """کیبورد پایین صفحه"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🎁 محصولات"),
        KeyboardButton("👥 دعوت دوستان")
    )
    markup.add(
        KeyboardButton("📊 آمار من"),
        KeyboardButton("✅ تأیید عضویت")
    )
    if user_id and user_id == ADMIN_ID:
        markup.add(KeyboardButton("⚙️ پنل ادمین"))
    return markup

def create_channel_inline():
    """دکمه‌های inline برای لینک کانال‌ها"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"📢 {CHANNEL_1}", url=f"https://t.me/{CHANNEL_1}"))
    markup.add(InlineKeyboardButton(f"📢 {CHANNEL_2}", url=f"https://t.me/{CHANNEL_2}"))
    markup.add(InlineKeyboardButton("✅ تأیید کردم", callback_data="check_verify"))
    return markup

def create_admin_inline():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ اضافه کردن محصول", callback_data="admin_add_product"))
    markup.add(InlineKeyboardButton("📝 ویرایش محصولات", callback_data="admin_list_products"))
    markup.add(InlineKeyboardButton("📢 پیام گروهی", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats"))
    return markup

# ==== START ====
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    # ثبت کاربر جدید
    if not user_exists(user_id):
        create_user(user_id, username)
        # بررسی referral
        args = message.text.split()
        if len(args) > 1:
            try:
                referrer_id = int(args[1])
                if referrer_id != user_id and user_exists(referrer_id) and not referral_exists(referrer_id, user_id):
                    add_referral(referrer_id, user_id)
                    add_points(referrer_id, 1)
                    try:
                        bot.send_message(referrer_id, "🎉 یک نفر با لینک دعوت شما ثبت‌نام کرد! +1 امتیاز")
                    except:
                        pass
            except:
                pass

    # اگه قبلاً تایید شده منوی اصلی بده
    if is_verified(user_id):
        bot.send_message(user_id,
            f"👋 خوش برگشتی!\n\n💰 امتیاز فعلی: {get_user_points(user_id)}",
            reply_markup=create_main_keyboard(user_id))
        return

    # اگه تایید نشده، بفرست کانال‌ها
    bot.send_message(user_id,
        "🎉 خوش‌آمدید!\n\nبرای استفاده از بات، ابتدا باید در کانال‌های زیر عضو شوید:",
        reply_markup=create_channel_inline())

# ==== CALLBACK: تایید عضویت ====
@bot.callback_query_handler(func=lambda call: call.data == "check_verify")
def check_verify(call):
    user_id = call.from_user.id
    status1, status2 = check_channel_membership(user_id)

    if status1 and status2:
        verify_user(user_id)
        bot.answer_callback_query(call.id, "✅ تایید شد!", show_alert=False)
        bot.send_message(user_id,
            "🎉 شما تأیید شدید! اکنون می‌توانید از همه بخش‌ها استفاده کنید.",
            reply_markup=create_main_keyboard(user_id))
    else:
        missing = []
        if not status1: missing.append(CHANNEL_1)
        if not status2: missing.append(CHANNEL_2)
        bot.answer_callback_query(call.id,
            "❌ هنوز در این کانال‌ها عضو نشدید:\n" + "\n".join(f"@{ch}" for ch in missing),
            show_alert=True)

# ==== KEYBOARD HANDLER ====
@bot.message_handler(func=lambda m: True)
def message_handler(message):
    user_id = message.from_user.id
    text = message.text

    if text == "✅ تأیید عضویت":
        if is_verified(user_id):
            bot.send_message(user_id, "✅ شما قبلاً تایید شده‌اید!", reply_markup=create_main_keyboard(user_id))
        else:
            bot.send_message(user_id, "برای تایید ابتدا در کانال‌ها عضو شوید:", reply_markup=create_channel_inline())

    elif text == "🎁 محصولات":
        if not is_verified(user_id):
            bot.send_message(user_id, "❌ ابتدا عضویت خود را تأیید کنید.", reply_markup=create_channel_inline())
            return
        products = get_products()
        if not products:
            bot.send_message(user_id, "❌ محصولی در دسترس نیست.", reply_markup=create_main_keyboard(user_id))
            return
        user_points = get_user_points(user_id)
        msg = f"💰 امتیازات شما: {user_points}\n\n📦 محصولات:\n\n"
        markup = InlineKeyboardMarkup()
        for product in products:
            prod_id, name, cost, desc, button_text, action = product
            msg += f"• {name} - {cost} امتیاز\n  {desc}\n\n"
            markup.add(InlineKeyboardButton(f"{button_text} ({cost}⭐)", callback_data=f"buy_{prod_id}"))
        bot.send_message(user_id, msg, reply_markup=markup)

    elif text == "👥 دعوت دوستان":
        if not is_verified(user_id):
            bot.send_message(user_id, "❌ ابتدا عضویت خود را تأیید کنید.")
            return
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        count = c.fetchone()[0]
        conn.close()
        msg = (f"👥 لینک دعوت شما:\n\n"
               f"<code>{referral_link}</code>\n\n"
               f"📊 تعداد دعوت‌های موفق: {count}\n"
               f"💰 امتیاز کسب شده از دعوت: {count}")
        bot.send_message(user_id, msg, parse_mode="HTML", reply_markup=create_main_keyboard(user_id))

    elif text == "📊 آمار من":
        points = get_user_points(user_id)
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        referrals = c.fetchone()[0]
        conn.close()
        msg = f"📊 آمار شما:\n\n💰 امتیازات: {points}\n👥 دعوت‌های موفق: {referrals}"
        bot.send_message(user_id, msg, reply_markup=create_main_keyboard(user_id))

    elif text == "⚙️ پنل ادمین":
        if user_id != ADMIN_ID:
            bot.send_message(user_id, "❌ شما ادمین نیستید.")
            return
        bot.send_message(user_id, "⚙️ پنل ادمین:", reply_markup=create_admin_inline())

# ==== CALLBACK: خرید محصول ====
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_handler(call):
    user_id = call.from_user.id
    product_id = int(call.data.split("_")[1])
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT name, cost, description FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()
    if not product:
        bot.answer_callback_query(call.id, "❌ محصول یافت نشد", show_alert=True)
        return
    name, cost, desc = product
    if subtract_points(user_id, cost):
        bot.answer_callback_query(call.id, f"✅ {name} خریداری شد!", show_alert=False)
        bot.send_message(user_id, f"🎉 خرید موفق!\n\n📦 {name}\n📖 {desc}")
    else:
        bot.answer_callback_query(call.id, f"❌ امتیاز کافی نیست! نیاز: {cost} امتیاز", show_alert=True)

# ==== ADMIN CALLBACKS ====
@bot.callback_query_handler(func=lambda call: call.data == "admin_add_product")
def admin_add_product(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        return
    bot.send_message(user_id, "📝 نام محصول را وارد کنید:")
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_name)

def admin_product_name(message):
    user_id = message.from_user.id
    product_name = message.text
    bot.send_message(user_id, "💰 هزینه (امتیاز) را وارد کنید:")
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_cost, product_name)

def admin_product_cost(message, product_name):
    user_id = message.from_user.id
    try:
        cost = int(message.text)
    except:
        bot.send_message(user_id, "❌ عدد صحیح وارد کنید")
        return
    bot.send_message(user_id, "📖 توضیحات محصول را وارد کنید:")
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_desc, product_name, cost)

def admin_product_desc(message, product_name, cost):
    user_id = message.from_user.id
    description = message.text
    bot.send_message(user_id, "🔘 متن دکمه را وارد کنید:")
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_button, product_name, cost, description)

def admin_product_button(message, product_name, cost, description):
    user_id = message.from_user.id
    button_text = message.text
    bot.send_message(user_id, "⚡ عملیات دکمه را وارد کنید (یا 'none'):")
    bot.register_next_step_handler_by_chat_id(user_id, admin_product_action, product_name, cost, description, button_text)

def admin_product_action(message, product_name, cost, description, button_text):
    user_id = message.from_user.id
    action = message.text
    add_product(product_name, cost, description, button_text, action)
    bot.send_message(user_id, f"✅ محصول '{product_name}' با موفقیت اضافه شد!\n\nکاربران می‌توانند آن را در بخش 🎁 محصولات ببینند.",
                     reply_markup=create_admin_inline())

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_products")
def admin_list_products(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        return
    products = get_products()
    if not products:
        bot.send_message(user_id, "❌ محصولی وجود ندارد")
        return
    msg = "📦 لیست محصولات:\n\n"
    markup = InlineKeyboardMarkup()
    for product in products:
        prod_id, name, cost, desc, button_text, action = product
        msg += f"🔹 [{prod_id}] {name} - {cost}⭐\n"
        markup.add(InlineKeyboardButton(f"🗑️ حذف: {name}", callback_data=f"admin_delete_{prod_id}"))
    bot.send_message(user_id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_delete_"))
def admin_delete_product(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        return
    product_id = int(call.data.split("_")[2])
    delete_product(product_id)
    bot.answer_callback_query(call.id, "✅ محصول حذف شد", show_alert=True)
    # لیست آپدیت شده
    products = get_products()
    if products:
        msg = "📦 لیست محصولات:\n\n"
        markup = InlineKeyboardMarkup()
        for product in products:
            prod_id, name, cost, desc, button_text, action = product
            msg += f"🔹 [{prod_id}] {name} - {cost}⭐\n"
            markup.add(InlineKeyboardButton(f"🗑️ حذف: {name}", callback_data=f"admin_delete_{prod_id}"))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        bot.edit_message_text("❌ هیچ محصولی باقی نمانده.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        return
    bot.send_message(user_id, "📢 پیام خود را برای ارسال به همه کاربران وارد کنید:")
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
    if user_id != ADMIN_ID:
        return
    total_users, total_points = get_user_stats()
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals")
    total_referrals = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM products")
    total_products = c.fetchone()[0]
    conn.close()
    msg = (f"📊 آمار کل:\n\n"
           f"👥 کل کاربران: {total_users}\n"
           f"💰 کل امتیازات: {total_points}\n"
           f"🔗 کل دعوت‌ها: {total_referrals}\n"
           f"📦 تعداد محصولات: {total_products}")
    bot.send_message(user_id, msg)

# ==== RUN ====
if __name__ == "__main__":
    print("🤖 ربات در حال اجرا است...")
    bot.infinity_polling()

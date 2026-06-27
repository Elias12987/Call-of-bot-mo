import sqlite3
from datetime import datetime
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# تنظیمات
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
CHANNEL_1 = "phdjld"
CHANNEL_2 = "poruirlae"
ADMIN_ID = 123456789

bot = TeleBot(BOT_TOKEN)

# ==== DATABASE ====
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
                 (referrer_id INTEGER, referred_id INTEGER, date TEXT)''')
    conn.commit()
    conn.close()

init_db()

def user_exists(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone(); conn.close(); return r is not None

def create_user(user_id, username):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)",
              (user_id, username, 0, f"ref_{user_id}", datetime.now().isoformat(), 0))
    conn.commit(); conn.close()

def get_points(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone(); conn.close(); return r[0] if r else 0

def add_points(user_id, pts):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("UPDATE users SET points=points+? WHERE user_id=?", (pts, user_id))
    conn.commit(); conn.close()

def subtract_points(user_id, pts):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    if r and r[0] >= pts:
        c.execute("UPDATE users SET points=points-? WHERE user_id=?", (pts, user_id))
        conn.commit(); conn.close(); return True
    conn.close(); return False

def verify_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("UPDATE users SET verified=1 WHERE user_id=?", (user_id,))
    conn.commit(); conn.close()

def is_verified(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT verified FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone(); conn.close(); return r[0] == 1 if r else False

def referral_exists(referred_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM referrals WHERE referred_id=?", (referred_id,))
    r = c.fetchone(); conn.close(); return r is not None

def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO referrals VALUES (?,?,?)", (referrer_id, referred_id, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_products():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    r = c.fetchall(); conn.close(); return r

def add_product(name, cost, description, button_text, action):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO products (name,cost,description,button_text,action) VALUES (?,?,?,?,?)",
              (name, cost, description, button_text, action))
    conn.commit(); conn.close()

def delete_product(pid):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit(); conn.close()

def get_referral_count(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
    r = c.fetchone(); conn.close(); return r[0]

def get_all_users():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    r = c.fetchall(); conn.close(); return r

def get_stats():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(points) FROM users")
    r = c.fetchone()
    c.execute("SELECT COUNT(*) FROM referrals")
    ref = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM products")
    prod = c.fetchone()[0]
    conn.close()
    return r[0], r[1] or 0, ref, prod

# ==== KEYBOARDS ====
def main_kb(user_id=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🎁 محصولات"),
        KeyboardButton("👥 دعوت دوستان"),
        KeyboardButton("📊 آمار من"),
        KeyboardButton("✅ تأیید عضویت")
    )
    if user_id == ADMIN_ID:
        kb.add(KeyboardButton("⚙️ پنل ادمین"))
    return kb

def channel_inline():
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton(f"📢 کانال اول", url=f"https://t.me/{CHANNEL_1}"))
    mk.add(InlineKeyboardButton(f"📢 کانال دوم", url=f"https://t.me/{CHANNEL_2}"))
    mk.add(InlineKeyboardButton("✅ عضو شدم، تأیید کن", callback_data="check_verify"))
    return mk

def products_kb(products):
    """کیبورد محصولات روی صفحه"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for p in products:
        kb.add(KeyboardButton(f"{p[4]} ({p[2]}⭐)"))
    kb.add(KeyboardButton("🔙 بازگشت"))
    return kb

def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("➕ افزودن محصول"),
        KeyboardButton("📝 لیست محصولات"),
        KeyboardButton("📢 پیام همگانی"),
        KeyboardButton("📊 آمار کل"),
        KeyboardButton("🔙 بازگشت")
    )
    return kb

# ==== START ====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    if not user_exists(user_id):
        create_user(user_id, username)
        args = message.text.split()
        if len(args) > 1:
            try:
                ref_id = int(args[1])
                if ref_id != user_id and user_exists(ref_id) and not referral_exists(user_id):
                    add_referral(ref_id, user_id)
                    add_points(ref_id, 1)
                    try:
                        bot.send_message(ref_id, "🎉 یک نفر با لینک دعوت شما ثبت‌نام کرد! +1 امتیاز")
                    except:
                        pass
            except:
                pass

    if is_verified(user_id):
        bot.send_message(user_id, f"💰 امتیاز شما: {get_points(user_id)}", reply_markup=main_kb(user_id))
    else:
        bot.send_message(user_id, "برای استفاده از بات، ابتدا در کانال‌های زیر عضو شوید:",
                         reply_markup=channel_inline())

# ==== CALLBACK: تأیید عضویت ====
@bot.callback_query_handler(func=lambda c: c.data == "check_verify")
def check_verify(call):
    user_id = call.from_user.id
    try:
        m1 = bot.get_chat_member(f"@{CHANNEL_1}", user_id)
        m2 = bot.get_chat_member(f"@{CHANNEL_2}", user_id)
        ok1 = m1.status in ['member','administrator','creator']
        ok2 = m2.status in ['member','administrator','creator']
    except:
        ok1 = ok2 = False

    if ok1 and ok2:
        verify_user(user_id)
        bot.answer_callback_query(call.id, "✅ تأیید شد!")
        bot.send_message(user_id, "✅ عضویت تأیید شد!", reply_markup=main_kb(user_id))
    else:
        missing = []
        if not ok1: missing.append(CHANNEL_1)
        if not ok2: missing.append(CHANNEL_2)
        bot.answer_callback_query(call.id,
            "❌ هنوز عضو نشدید:\n" + "\n".join(f"@{ch}" for ch in missing), show_alert=True)

# ==== MESSAGE HANDLER ====
# این متغیر برای ذخیره حالت کاربر
user_states = {}

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text

    # اگه در حالت خاصی هست (ادمین داره محصول اضافه میکنه)
    if user_id in user_states:
        handle_state(message)
        return

    # دکمه بازگشت
    if text == "🔙 بازگشت":
        bot.send_message(user_id, "منوی اصلی:", reply_markup=main_kb(user_id))
        return

    # تأیید عضویت
    if text == "✅ تأیید عضویت":
        if is_verified(user_id):
            bot.send_message(user_id, "✅ قبلاً تأیید شده‌اید!", reply_markup=main_kb(user_id))
        else:
            bot.send_message(user_id, "ابتدا در کانال‌ها عضو شوید:", reply_markup=channel_inline())
        return

    if not is_verified(user_id) and text not in ["✅ تأیید عضویت"]:
        bot.send_message(user_id, "❌ ابتدا عضویت خود را تأیید کنید.", reply_markup=channel_inline())
        return

    # محصولات
    if text == "🎁 محصولات":
        products = get_products()
        if not products:
            bot.send_message(user_id, "❌ محصولی موجود نیست.", reply_markup=main_kb(user_id))
            return
        pts = get_points(user_id)
        msg = f"💰 امتیاز شما: {pts}\n\nیک محصول انتخاب کنید:"
        bot.send_message(user_id, msg, reply_markup=products_kb(products))
        user_states[user_id] = {"step": "selecting_product", "products": products}
        return

    # دعوت دوستان
    if text == "👥 دعوت دوستان":
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        count = get_referral_count(user_id)
        bot.send_message(user_id,
            f"👥 لینک دعوت شما:\n\n<code>{link}</code>\n\n"
            f"دعوت‌های موفق: {count}\n"
            f"امتیاز از دعوت: {count}",
            parse_mode="HTML", reply_markup=main_kb(user_id))
        return

    # آمار من
    if text == "📊 آمار من":
        count = get_referral_count(user_id)
        pts = get_points(user_id)
        bot.send_message(user_id,
            f"📊 آمار شما:\n\n💰 امتیاز: {pts}\n👥 دعوت‌های موفق: {count}",
            reply_markup=main_kb(user_id))
        return

    # پنل ادمین
    if text == "⚙️ پنل ادمین":
        if user_id != ADMIN_ID:
            bot.send_message(user_id, "❌ شما ادمین نیستید.")
            return
        bot.send_message(user_id, "⚙️ پنل ادمین:", reply_markup=admin_kb())
        return

    # دکمه‌های ادمین
    if user_id == ADMIN_ID:
        if text == "➕ افزودن محصول":
            bot.send_message(user_id, "📝 نام محصول را وارد کنید:")
            user_states[user_id] = {"step": "add_name"}
            return
        if text == "📝 لیست محصولات":
            products = get_products()
            if not products:
                bot.send_message(user_id, "❌ محصولی وجود ندارد.", reply_markup=admin_kb())
                return
            msg = "📦 لیست محصولات:\n\n"
            mk = InlineKeyboardMarkup()
            for p in products:
                msg += f"🔹 [{p[0]}] {p[1]} - {p[2]}⭐\n"
                mk.add(InlineKeyboardButton(f"🗑️ حذف: {p[1]}", callback_data=f"del_{p[0]}"))
            bot.send_message(user_id, msg, reply_markup=mk)
            return
        if text == "📢 پیام همگانی":
            bot.send_message(user_id, "📢 متن پیام را وارد کنید:")
            user_states[user_id] = {"step": "broadcast"}
            return
        if text == "📊 آمار کل":
            total_u, total_p, total_r, total_pr = get_stats()
            bot.send_message(user_id,
                f"📊 آمار کل:\n\n👥 کاربران: {total_u}\n💰 امتیازات: {total_p}\n"
                f"🔗 دعوت‌ها: {total_r}\n📦 محصولات: {total_pr}",
                reply_markup=admin_kb())
            return

def handle_state(message):
    user_id = message.from_user.id
    text = message.text
    state = user_states.get(user_id, {})
    step = state.get("step")

    # انتخاب محصول توسط کاربر
    if step == "selecting_product":
        products = state.get("products", [])
        selected = None
        for p in products:
            if text == f"{p[4]} ({p[2]}⭐)":
                selected = p
                break
        if text == "🔙 بازگشت":
            del user_states[user_id]
            bot.send_message(user_id, "منوی اصلی:", reply_markup=main_kb(user_id))
            return
        if not selected:
            bot.send_message(user_id, "❌ محصول نامعتبر است.")
            return
        prod_id, name, cost, desc, btn, action = selected
        if subtract_points(user_id, cost):
            del user_states[user_id]
            bot.send_message(user_id, f"✅ خرید موفق!\n\n📦 {name}\n📖 {desc}",
                             reply_markup=main_kb(user_id))
        else:
            bot.send_message(user_id, f"❌ امتیاز کافی نیست! نیاز: {cost}⭐ | شما: {get_points(user_id)}⭐",
                             reply_markup=main_kb(user_id))
            del user_states[user_id]
        return

    # ادمین - افزودن محصول
    if step == "add_name":
        user_states[user_id] = {"step": "add_cost", "name": text}
        bot.send_message(user_id, "💰 هزینه (امتیاز) را وارد کنید:")
        return
    if step == "add_cost":
        try:
            cost = int(text)
            user_states[user_id]["cost"] = cost
            user_states[user_id]["step"] = "add_desc"
            bot.send_message(user_id, "📖 توضیحات محصول را وارد کنید:")
        except:
            bot.send_message(user_id, "❌ عدد صحیح وارد کنید:")
        return
    if step == "add_desc":
        user_states[user_id]["desc"] = text
        user_states[user_id]["step"] = "add_btn"
        bot.send_message(user_id, "🔘 متن دکمه را وارد کنید (این روی کیبورد نشون داده میشه):")
        return
    if step == "add_btn":
        user_states[user_id]["btn"] = text
        user_states[user_id]["step"] = "add_action"
        bot.send_message(user_id, "⚡ عملیات را وارد کنید (یا 'none'):")
        return
    if step == "add_action":
        s = user_states[user_id]
        add_product(s["name"], s["cost"], s["desc"], s["btn"], text)
        del user_states[user_id]
        bot.send_message(user_id, f"✅ محصول '{s['name']}' اضافه شد!", reply_markup=admin_kb())
        return

    # ادمین - پیام همگانی
    if step == "broadcast":
        users = get_all_users()
        count = 0
        for u in users:
            try:
                bot.send_message(u[0], f"📢 پیام از ادمین:\n\n{text}")
                count += 1
            except:
                pass
        del user_states[user_id]
        bot.send_message(user_id, f"✅ پیام به {count} نفر ارسال شد.", reply_markup=admin_kb())

# ==== CALLBACK: حذف محصول ====
@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def delete_cb(call):
    if call.from_user.id != ADMIN_ID:
        return
    pid = int(call.data.split("_")[1])
    delete_product(pid)
    bot.answer_callback_query(call.id, "✅ حذف شد", show_alert=True)
    products = get_products()
    if products:
        msg = "📦 لیست محصولات:\n\n"
        mk = InlineKeyboardMarkup()
        for p in products:
            msg += f"🔹 [{p[0]}] {p[1]} - {p[2]}⭐\n"
            mk.add(InlineKeyboardButton(f"🗑️ حذف: {p[1]}", callback_data=f"del_{p[0]}"))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=mk)
    else:
        bot.edit_message_text("❌ هیچ محصولی باقی نمانده.", call.message.chat.id, call.message.message_id)

# ==== RUN ====
if __name__ == "__main__":
    print("🤖 ربات در حال اجرا است...")
    bot.infinity_polling()

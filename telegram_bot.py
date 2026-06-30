import sqlite3
from datetime import datetime, date
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8763045779:AAExV3KrNzRhZjFedUW-oQhnXswwAVoVQtQ"
CHANNEL_1 = "phdjld"
CHANNEL_2 = "poruirlae"
ADMIN_ID = 8256022764

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
    c.execute('''CREATE TABLE IF NOT EXISTS daily_claims
                 (user_id INTEGER, claim_date TEXT,
                  PRIMARY KEY(user_id, claim_date))''')
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

def get_referral_count(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
    r = c.fetchone(); conn.close(); return r[0]

def get_products():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    r = c.fetchall(); conn.close(); return r

def get_product_by_btn(btn_text):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE button_text=?", (btn_text,))
    r = c.fetchone(); conn.close(); return r

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

def can_claim_daily(user_id):
    today = date.today().isoformat()
    if datetime.now().hour < 3:
        return False, "❌ امتیاز روزانه از ساعت ۳ فعاله!"
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM daily_claims WHERE user_id=? AND claim_date=?", (user_id, today))
    r = c.fetchone(); conn.close()
    if r:
        return False, "❌ امروز قبلاً امتیاز روزانه گرفتی!\n\n• یادت نره فردا ساعت ۳ دوباره بیای 😊"
    return True, ""

def claim_daily(user_id):
    today = date.today().isoformat()
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO daily_claims VALUES (?,?)", (user_id, today))
    conn.commit(); conn.close()
    add_points(user_id, 1)

def get_all_user_ids():
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
    products = get_products()
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btns = [KeyboardButton(p[4]) for p in products]
    if btns:
        kb.add(*btns)
    kb.add(KeyboardButton("👥 دعوت دوستان"), KeyboardButton("🎁امتیاز روزانه🎁"))
    kb.add(KeyboardButton("👤 حساب کاربری"))
    if user_id == ADMIN_ID:
        kb.add(KeyboardButton("⚙️ پنل ادمین"))
    return kb

def channel_inline():
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("📢 کانال اول", url=f"https://t.me/{CHANNEL_1}"))
    mk.add(InlineKeyboardButton("📢 کانال دوم", url=f"https://t.me/{CHANNEL_2}"))
    mk.add(InlineKeyboardButton("✅ عضو شدم", callback_data="check_verify"))
    return mk

def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("➕ افزودن محصول"),
        KeyboardButton("📝 لیست محصولات"),
        KeyboardButton("📢 پیام همگانی"),
        KeyboardButton("📊 آمار کل"),
        KeyboardButton("💸 انتقال امتیاز"),
        KeyboardButton("🔙 بازگشت")
    )
    return kb

user_states = {}

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

    if not is_verified(user_id):
        bot.send_message(user_id,
            "برای استفاده از بات، ابتدا در کانال‌های زیر عضو شوید:",
            reply_markup=channel_inline())
        return

    bot.send_message(user_id, f"💰 امتیاز: {get_points(user_id)}", reply_markup=main_kb(user_id))

# ==== CALLBACK: تأیید عضویت ====
@bot.callback_query_handler(func=lambda c: c.data == "check_verify")
def check_verify(call):
    user_id = call.from_user.id
    try:
        m1 = bot.get_chat_member(f"@{CHANNEL_1}", user_id)
        m2 = bot.get_chat_member(f"@{CHANNEL_2}", user_id)
        ok1 = m1.status in ['member', 'administrator', 'creator']
        ok2 = m2.status in ['member', 'administrator', 'creator']
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
            "❌ هنوز عضو نشدید:\n" + "\n".join(f"@{ch}" for ch in missing),
            show_alert=True)

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
            msg += f"🔹 {p[1]} | {p[2]}⭐ | دکمه: {p[4]}\n"
            mk.add(InlineKeyboardButton(f"🗑️ حذف: {p[1]}", callback_data=f"del_{p[0]}"))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=mk)
    else:
        bot.edit_message_text("❌ هیچ محصولی باقی نمانده.", call.message.chat.id, call.message.message_id)

# ==== MESSAGE HANDLER ====
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text

    if user_id in user_states:
        handle_state(message)
        return

    if text == "🔙 بازگشت":
        bot.send_message(user_id, f"💰 امتیاز: {get_points(user_id)}", reply_markup=main_kb(user_id))
        return

    if not is_verified(user_id):
        bot.send_message(user_id, "❌ ابتدا عضویت را تأیید کنید:", reply_markup=channel_inline())
        return

    if text == "🎁امتیاز روزانه🎁":
        can, err_msg = can_claim_daily(user_id)
        if can:
            claim_daily(user_id)
            bot.send_message(user_id,
                "تبریک میگم! مقدار 1 امتیاز برنده شدی! 🎉\n\n"
                "✅ هر روز ساعت 3 میتونی این بخش و فعال کنی\n\n"
                "• یادت نره ساعت 3 این بخش و فعال کنی و امتیاز بگیری",
                reply_markup=main_kb(user_id))
        else:
            bot.send_message(user_id, err_msg, reply_markup=main_kb(user_id))
        return

    if text == "👤 حساب کاربری":
        user = message.from_user
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        count = get_referral_count(user_id)
        pts = get_points(user_id)
        msg = (
            f"👤 *حساب کاربری*\n\n"
            f"📛 نام: {user.full_name}\n"
            f"🔖 یوزرنیم: @{user.username or 'ندارد'}\n"
            f"🆔 آیدی عددی: `{user_id}`\n"
            f"💰 امتیاز: {pts}\n"
            f"👥 دعوت‌های موفق: {count}\n\n"
            f"🔗 لینک رفرال:\n`{ref_link}`"
        )
        bot.send_message(user_id, msg, parse_mode="Markdown", reply_markup=main_kb(user_id))
        return

    if text == "👤 حساب کاربری":
        username = message.from_user.username
        full_name = message.from_user.full_name
        pts = get_points(user_id)
        ref_count = get_referral_count(user_id)
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.send_message(user_id,
            f"👤 حساب کاربری\n\n"
            f"📛 نام: {full_name}\n"
            f"🔖 یوزرنیم: @{username if username else 'ندارد'}\n"
            f"🆔 آیدی عددی: {user_id}\n"
            f"💰 امتیاز: {pts}\n"
            f"👥 دعوت‌های موفق: {ref_count}\n\n"
            f"🔗 لینک رفرال:\n{link}",
            reply_markup=main_kb(user_id))
        return

    if text == "👥 دعوت دوستان":
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        count = get_referral_count(user_id)
        bot.send_message(user_id,
            f"👥 لینک دعوت شما:\n\n<code>{link}</code>\n\n"
            f"دعوت‌های موفق: {count} | امتیاز کسب‌شده: {count}",
            parse_mode="HTML", reply_markup=main_kb(user_id))
        return

    if text == "⚙️ پنل ادمین" and user_id == ADMIN_ID:
        bot.send_message(user_id, "⚙️ پنل ادمین:", reply_markup=admin_kb())
        return

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
                msg += f"🔹 {p[1]} | {p[2]}⭐ | دکمه: {p[4]}\n"
                mk.add(InlineKeyboardButton(f"🗑️ حذف: {p[1]}", callback_data=f"del_{p[0]}"))
            bot.send_message(user_id, msg, reply_markup=mk)
            return
        if text == "📢 پیام همگانی":
            bot.send_message(user_id, "📢 متن پیام را وارد کنید:")
            user_states[user_id] = {"step": "broadcast"}
            return
        if text == "📊 آمار کل":
            u, p, r, pr = get_stats()
            bot.send_message(user_id,
                f"📊 آمار:\n👥 کاربران: {u}\n💰 امتیازات: {p}\n🔗 دعوت‌ها: {r}\n📦 محصولات: {pr}",
                reply_markup=admin_kb())
            return
        if text == "💸 انتقال امتیاز":
            bot.send_message(user_id, "💸 مقدار امتیاز را وارد کنید:")
            user_states[user_id] = {"step": "transfer_amount"}
            return

    product = get_product_by_btn(text)
    if product:
        pid, name, cost, desc, btn, action = product
        if subtract_points(user_id, cost):
            bot.send_message(user_id, f"✅ خرید موفق!\n\n📦 {name}\n📖 {desc}",
                             reply_markup=main_kb(user_id))
        else:
            bot.send_message(user_id,
                f"❌ امتیاز کافی نیست!\nنیاز: {cost}⭐ | شما: {get_points(user_id)}⭐",
                reply_markup=main_kb(user_id))
        return

def handle_state(message):
    user_id = message.from_user.id
    text = message.text
    state = user_states.get(user_id, {})
    step = state.get("step")

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
        bot.send_message(user_id, "🔘 متن دکمه را وارد کنید:")
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
        bot.send_message(user_id,
            f"✅ محصول '{s['name']}' اضافه شد!",
            reply_markup=admin_kb())
        return

    if step == "broadcast":
        users = get_all_user_ids()
        count = 0
        for u in users:
            try:
                bot.send_message(u[0], f"📢 پیام از ادمین:\n\n{text}")
                count += 1
            except:
                pass
        del user_states[user_id]
        bot.send_message(user_id, f"✅ پیام به {count} نفر ارسال شد.", reply_markup=admin_kb())
        return

    if step == "transfer_amount":
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError
            user_states[user_id]["transfer_amount"] = amount
            user_states[user_id]["step"] = "transfer_id"
            bot.send_message(user_id, "👤 آیدی عددی گیرنده را وارد کنید:")
        except:
            bot.send_message(user_id, "❌ عدد صحیح مثبت وارد کنید:")
        return

    if step == "transfer_id":
        try:
            target_id = int(text)
            if not user_exists(target_id):
                bot.send_message(user_id, "❌ کاربری با این آیدی پیدا نشد.", reply_markup=admin_kb())
                del user_states[user_id]
                return
            amount = user_states[user_id]["transfer_amount"]
            add_points(target_id, amount)
            del user_states[user_id]
            try:
                bot.send_message(target_id, f"🎁 ادمین {amount} امتیاز به حساب شما اضافه کرد!")
            except:
                pass
            bot.send_message(user_id,
                f"✅ {amount} امتیاز به کاربر {target_id} منتقل شد.\n💰 موجودی جدید: {get_points(target_id)}",
                reply_markup=admin_kb())
        except:
            bot.send_message(user_id, "❌ آیدی نامعتبر است.")
        return

# ==== RUN ====
if __name__ == "__main__":
    print("🤖 ربات در حال اجرا است...")
    bot.infinity_polling()

import logging
import sqlite3
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)

# ---------------------------------------------------------
# RENDER FREE TIER KEEP-ALIVE SERVER
# ---------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Kan Gebeya Bot is running!")

    def log_message(self, format, *args):
        return  # Silence HTTP logs

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ---------------------------------------------------------
# BOT CONFIGURATION
# ---------------------------------------------------------
BOT_TOKEN = "8990836657:AAEgyMHpLUCxYma3xbPqDGsCdYiA2D6lorM"
ADMIN_IDS = [6720581112]  # የአድሚን የቴሌግራም ID ቁጥር
SUPPORT_USERNAME = "Kan_Gebeya"  # የቴሌግራም Support / የሻጭ አካውንት (ያለ @)
PHONE_NUMBER = "0906078429"
TELEBIRR_ACCOUNT = "0906078429"
CBE_ACCOUNT = "1000000000000"

# PREDEFINED CATEGORIES
DEFAULT_CATEGORIES = [
    "👗 የሴቶች አልባሳት",
    "👔 የወንዶች አልባሳት",
    "💻 ላፕቶፕ / PC",
    "📱 ስልክ",
    "🔌 ኤሌክትሮኒክስ",
    "📦 ሌሎች"
]

# Conversation States for Admin Add & Edit Product
ADD_NAME, ADD_CATEGORY, ADD_PRICE, ADD_DESC, ADD_PHOTO = range(5)
EDIT_PRICE_STATE, EDIT_DESC_STATE = range(5, 7)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------------------------------------------------
# DICTIONARY FOR MULTI-LANGUAGE SUPPORT (አማርኛ & ENGLISH)
# ---------------------------------------------------------
STRINGS = {
    'am': {
        'welcome': (
            "እንኳን ወደ **ካን ገበያ (Kan Gebeya)** በደህና መጡ! 🛒\n\n"
            "እዚህ የተለያዩ አልባሳት፣ ኤሌክትሮኒክስ፣ ስልኮች እና ጥራት ያላቸውን ምርቶች በቀላሉ ማዘዝ ይችላሉ።\n\n"
            "ለመጀመር ከታች ያሉትን ቁልፎች ይጠቀሙ👇"
        ),
        'btn_products': "🛍 ምርቶች",
        'btn_cart': "🛒 ካርት",
        'btn_orders': "📦 ትዕዛዞቼ",
        'btn_help': "📞 እርዳታ እና አድራሻ",
        'btn_lang': "🌐 ቋንቋ / Language",
        'btn_admin': "⚙️ አድሚን ፓነል",
        'select_cat': "እባክዎን የሚፈልጉትን ካታጎሪ ይምረጡ:",
        'no_products': "በዚህ ካታጎሪ ውስጥ እስካሁን የተመዘገበ ምርት የለም።",
        'empty_cart': "የገበያ ካርትዎ ባዶ ነው። 🛒",
        'cart_title': "🛒 **የገበያ ካርትዎ ዝርዝር:**\n\n",
        'checkout_btn': "💳 ክፍያ ፈፅም (Checkout)",
        'clear_cart_btn': "🗑 ካርቱን አጽዳ",
        'cart_cleared': "የገበያ ካርትዎ ጸድቷል።",
        'add_to_cart_btn': "🛒 ወደ ካርት ጨምር",
        'added_to_cart': "✅ ምርቱ ወደ ካርትዎ ተጨምሯል!",
        'go_to_cart': "🛒 ወደ ካርት ሂድ",
        'more_products': "🛍️ ተጨማሪ ምርቶች እይ",
        'contact_seller': "💬 ከሻጭ ጋር ተነጋገር (Support)",
        'back': "⬅️ ተመለስ",
        'help_msg': (
            "📞 **ካን ገበያ - የእርዳታ ማዕከል**\n\n"
            "📍 **አድራሻ:** አዲስ አበባ፣ ኢትዮጵያ\n"
            f"📱 **ስልክ:** {PHONE_NUMBER}\n"
            f"💬 **ቴሌግራም:** @{SUPPORT_USERNAME}\n\n"
            "**የክፍያ አማራጮች:**\n"
            f"• Telebirr: {TELEBIRR_ACCOUNT}\n"
            f"• CBE: {CBE_ACCOUNT} (Kan Gebeya)"
        ),
        'checkout_instructions': (
            "💳 **የክፍያ መመሪያ:**\n\n"
            "እባክዎን ክፍያውን በሚከተሉት አካውንቶች ያጠናቁ:\n"
            f"• **Telebirr:** {TELEBIRR_ACCOUNT}\n"
            f"• **CBE:** {CBE_ACCOUNT}\n\n"
            "ከክፍያ በኋላ **የደረሰኙን ስክሪንሾት (Photo)** እዚህ ይላኩ::"
        ),
        'receipt_received': "✅ የክፍያ ደረሰኝዎ ተልኳል! በቅርቡ አረጋግጠን እናደርሳለን። እናመሰግናለን!",
        'no_orders': "እስካሁን ምንም ያዘዙት ምርት የለም።",
        'my_orders_title': "📦 **የእርስዎ ትዕዛዞች:**\n\n",
        'select_lang_msg': "🌐 እባክዎን ቋንቋ ይምረጡ / Please select your language:",
        'lang_changed': "✅ ቋንቋው ወደ አማርኛ ተቀይሯል።",
        'admin_add_prod': "➕ አዲስ ምርት ጨምር",
        'admin_manage_prod': "🛠 ምርቶችን አስተካክል / ሰርዝ",
        'admin_view_orders': "📦 ትዕዛዞችን እይ",
        'admin_stats': "📊 የተጠቃሚዎች ብዛት",
        'admin_back_main': "⬅️ ወደ ዋናው ገጽ ተመለስ",
        'admin_welcome': "የአድሚን አስተዳደር ገጽ እንኳን በደህና መጡ! የምትፈልጉትን መምረጥ ትችላላችሁ:",
    },
    'en': {
        'welcome': (
            "Welcome to **Kan Gebeya**! 🛒\n\n"
            "You can easily order clothing, electronics, phones, and top-quality products here.\n\n"
            "Use the buttons below to get started👇"
        ),
        'btn_products': "🛍 Products",
        'btn_cart': "🛒 Cart",
        'btn_orders': "📦 My Orders",
        'btn_help': "📞 Help & Contact",
        'btn_lang': "🌐 Language / ቋንቋ",
        'btn_admin': "⚙️ Admin Panel",
        'select_cat': "Please select a category:",
        'no_products': "There are currently no products in this category.",
        'empty_cart': "Your shopping cart is empty. 🛒",
        'cart_title': "🛒 **Your Cart Details:**\n\n",
        'checkout_btn': "💳 Checkout",
        'clear_cart_btn': "🗑 Clear Cart",
        'cart_cleared': "Your cart has been cleared.",
        'add_to_cart_btn': "🛒 Add to Cart",
        'added_to_cart': "✅ Product added to your cart!",
        'go_to_cart': "🛒 Go to Cart",
        'more_products': "🛍️ Browse More Products",
        'contact_seller': "💬 Chat with Seller (Support)",
        'back': "⬅️ Back",
        'help_msg': (
            "📞 **Kan Gebeya - Support Center**\n\n"
            "📍 **Location:** Addis Ababa, Ethiopia\n"
            f"📱 **Phone:** +251 906078429\n"
            f"💬 **Telegram:** @{SUPPORT_USERNAME}\n\n"
            "**Payment Options:**\n"
            f"• Telebirr: {TELEBIRR_ACCOUNT}\n"
            f"• CBE: {CBE_ACCOUNT} (Kan Gebeya)"
        ),
        'checkout_instructions': (
            "💳 **Payment Instructions:**\n\n"
            "Please complete your payment using:\n"
            f"• **Telebirr:** {TELEBIRR_ACCOUNT}\n"
            f"• **CBE:** {CBE_ACCOUNT}\n\n"
            "After paying, please send the **Receipt Screenshot (Photo)** here."
        ),
        'receipt_received': "✅ Payment receipt received! We will verify and process your order soon. Thank you!",
        'no_orders': "You haven't placed any orders yet.",
        'my_orders_title': "📦 **Your Orders:**\n\n",
        'select_lang_msg': "🌐 Please select your language / እባክዎን ቋንቋ ይምረጡ:",
        'lang_changed': "✅ Language changed to English.",
        'admin_add_prod': "➕ Add New Product",
        'admin_manage_prod': "🛠 Edit / Delete Products",
        'admin_view_orders': "📦 View Orders",
        'admin_stats': "📊 User Statistics",
        'admin_back_main': "⬅️ Back to Main Menu",
        'admin_welcome': "Welcome to the Admin Panel! Choose an option below:",
    }
}

# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'am'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            photo_id TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            total_price REAL NOT NULL,
            receipt_photo_id TEXT,
            status TEXT DEFAULT 'PENDING'
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_user_lang(user_id):
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 'am'

def set_user_lang(user_id, lang):
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, language) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET language=excluded.language",
        (user_id, lang)
    )
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# KEYBOARDS
# ---------------------------------------------------------
def main_menu_keyboard(user_id):
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]
    keyboard = [
        [KeyboardButton(txt['btn_products']), KeyboardButton(txt['btn_cart'])],
        [KeyboardButton(txt['btn_orders']), KeyboardButton(txt['btn_help'])],
        [KeyboardButton(txt['btn_lang'])]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(txt['btn_admin'])])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_menu_keyboard(user_id):
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]
    keyboard = [
        [KeyboardButton(txt['admin_add_prod']), KeyboardButton(txt['admin_manage_prod'])],
        [KeyboardButton(txt['admin_view_orders']), KeyboardButton(txt['admin_stats'])],
        [KeyboardButton(txt['admin_back_main'])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def categories_admin_keyboard():
    keyboard = [
        [KeyboardButton("👗 የሴቶች አልባሳት"), KeyboardButton("👔 የወንዶች አልባሳት")],
        [KeyboardButton("💻 ላፕቶፕ / PC"), KeyboardButton("📱 ስልክ")],
        [KeyboardButton("🔌 ኤሌክትሮኒክስ"), KeyboardButton("📦 ሌሎች")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def language_inline_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="setlang_am"),
            InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------------------------------------------------------
# START & LANGUAGE HANDLERS
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(user.id)
    set_user_lang(user.id, lang)
    txt = STRINGS[lang]

    await update.message.reply_text(
        txt['welcome'],
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(user.id)
    )

async def show_language_selector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]
    await update.message.reply_text(
        txt['select_lang_msg'],
        reply_markup=language_inline_keyboard()
    )

async def handle_language_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if query.data == "setlang_am":
        set_user_lang(user_id, "am")
        msg = STRINGS['am']['lang_changed']
    else:
        set_user_lang(user_id, "en")
        msg = STRINGS['en']['lang_changed']

    await query.message.reply_text(
        msg,
        reply_markup=main_menu_keyboard(user_id)
    )

# ---------------------------------------------------------
# CATEGORY & PRODUCT DISPLAY
# ---------------------------------------------------------
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]

    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM products")
    db_cats = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Combine default categories and database categories
    all_cats = list(dict.fromkeys(DEFAULT_CATEGORIES + db_cats))

    keyboard = []
    # Create 2 buttons per row
    row = []
    for cat in all_cats:
        row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(txt['select_cat'], reply_markup=reply_markup)

async def handle_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]
    data = query.data

    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()

    if data.startswith("cat_"):
        cat_name = data.split("cat_")[1]
        cursor.execute("SELECT id, name, price FROM products WHERE category = ?", (cat_name,))
        products = cursor.fetchall()
        
        if not products:
            await query.answer()
            keyboard = [[InlineKeyboardButton(txt['back'], callback_data="show_cats")]]
            await query.message.edit_text(
                f"{cat_name}\n\n⚠️ **{txt['no_products']}**", 
                parse_mode="Markdown", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            conn.close()
            return

        keyboard = []
        for p in products:
            keyboard.append([InlineKeyboardButton(f"🛍 {p[1]} - {p[2]:,.0f} ETB", callback_data=f"prod_{p[0]}")])
        keyboard.append([InlineKeyboardButton(txt['back'], callback_data="show_cats")])
        
        await query.answer()
        await query.message.edit_text(f"📁 **{cat_name}**:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "show_cats":
        cursor.execute("SELECT DISTINCT category FROM products")
        db_cats = [row[0] for row in cursor.fetchall()]
        all_cats = list(dict.fromkeys(DEFAULT_CATEGORIES + db_cats))

        keyboard = []
        row = []
        for cat in all_cats:
            row.append(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        await query.answer()
        await query.message.edit_text(txt['select_cat'], reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("prod_"):
        prod_id = int(data.split("prod_")[1])
        cursor.execute("SELECT name, category, price, description, photo_id FROM products WHERE id = ?", (prod_id,))
        p = cursor.fetchone()

        if p:
            msg = (
                f"🛍 **{p[0]}**\n\n"
                f"🏷 **ካታጎሪ:** {p[1]}\n"
                f"💰 **ዋጋ:** {p[2]:,.2f} ETB\n\n"
                f"📝 **መግለጫ:**\n{p[3]}"
            )
            keyboard = [
                [InlineKeyboardButton(txt['add_to_cart_btn'], callback_data=f"addcart_{prod_id}")],
                [InlineKeyboardButton(txt['contact_seller'], url=f"https://t.me/{SUPPORT_USERNAME}")],
                [InlineKeyboardButton(txt['back'], callback_data=f"cat_{p[1]}")]
            ]
            await query.answer()
            if p[4]:
                await query.message.delete()
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=p[4],
                    caption=msg,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("addcart_"):
        prod_id = int(data.split("addcart_")[1])
        
        cursor.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, prod_id))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE user_id = ? AND product_id = ?", (user_id, prod_id))
        else:
            cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)", (user_id, prod_id))
        conn.commit()

        await query.answer(txt['added_to_cart'], show_alert=True)

        keyboard = [
            [InlineKeyboardButton(txt['go_to_cart'], callback_data="btn_go_cart")],
            [InlineKeyboardButton(txt['contact_seller'], url=f"https://t.me/{SUPPORT_USERNAME}")],
            [InlineKeyboardButton(txt['more_products'], callback_data="show_cats")]
        ]
        
        await query.message.reply_text(
            f"✅ **{txt['added_to_cart']}**\n\nቀጥሎ ምን ማድረግ ይፈልጋሉ?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "btn_go_cart":
        await query.answer()
        await show_cart_from_callback(query, context)

    conn.close()

# ---------------------------------------------------------
# CART FUNCTIONS
# ---------------------------------------------------------
async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await render_cart_message(user_id, update.message.reply_text)

async def show_cart_from_callback(query, context):
    user_id = query.from_user.id
    await render_cart_message(user_id, query.message.reply_text)

async def render_cart_message(user_id, reply_func):
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]

    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name, p.price, c.quantity, (p.price * c.quantity)
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (user_id,))
    items = cursor.fetchall()
    conn.close()

    if not items:
        await reply_func(txt['empty_cart'])
        return

    total = 0
    msg = txt['cart_title']
    for i, item in enumerate(items, 1):
        msg += f"{i}. **{item[0]}** x{item[2]} = {item[3]:,.2f} ETB\n"
        total += item[3]

    msg += f"\n💵 **ጠቅላላ ዋጋ:** {total:,.2f} ETB"

    keyboard = [
        [InlineKeyboardButton(txt['checkout_btn'], callback_data="checkout")],
        [InlineKeyboardButton(txt['clear_cart_btn'], callback_data="clear_cart")],
        [InlineKeyboardButton(txt['contact_seller'], url=f"https://t.me/{SUPPORT_USERNAME}")]
    ]
    await reply_func(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]

    await query.answer()

    if query.data == "clear_cart":
        conn = sqlite3.connect("kan_gebeya.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await query.message.edit_text(txt['cart_cleared'])

    elif query.data == "checkout":
        await query.message.reply_text(txt['checkout_instructions'], parse_mode="Markdown")

# ---------------------------------------------------------
# RECEIPT UPLOAD HANDLER
# ---------------------------------------------------------
async def handle_receipt_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(user.id)
    txt = STRINGS[lang]

    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT SUM(p.price * c.quantity)
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (user.id,))
    total = cursor.fetchone()[0] or 0.0

    if total == 0:
        conn.close()
        return

    photo_id = update.message.photo[-1].file_id
    username = user.username or user.first_name

    cursor.execute(
        "INSERT INTO orders (user_id, username, total_price, receipt_photo_id) VALUES (?, ?, ?, ?)",
        (user.id, username, total, photo_id)
    )
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user.id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(txt['receipt_received'])

    admin_msg = (
        f"🚨 **አዲስ የክፍያ ትዕዛዝ ደርሷል!**\n\n"
        f"👤 **ተጠቃሚ:** @{username} (ID: `{user.id}`)\n"
        f"💰 **የተከፈለ መጠን:** {total:,.2f} ETB"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=admin_msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")

# ---------------------------------------------------------
# ORDERS DISPLAY
# ---------------------------------------------------------
async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]

    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()

    if user_id in ADMIN_IDS and update.message and update.message.text in [STRINGS['am']['admin_view_orders'], STRINGS['en']['admin_view_orders']]:
        cursor.execute("SELECT id, username, total_price, status FROM orders ORDER BY id DESC LIMIT 10")
        orders = cursor.fetchall()
        conn.close()
        if not orders:
            await update.message.reply_text("ምንም ትዕዛዞች የሉም።")
            return
        msg = "📦 **የቅርብ ጊዜ ትዕዛዞች (Admin View):**\n\n"
        for o in orders:
            msg += f"• Order #{o[0]} | @{o[1]} | {o[2]:,.2f} ETB | **{o[3]}**\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    cursor.execute("SELECT id, total_price, status FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,))
    orders = cursor.fetchall()
    conn.close()

    if not orders:
        await update.message.reply_text(txt['no_orders'])
        return

    msg = txt['my_orders_title']
    for o in orders:
        msg += f"• ትዕዛዝ #{o[0]} - {o[1]:,.2f} ETB ({o[2]})\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ---------------------------------------------------------
# ADMIN ADD PRODUCT CONVERSATION
# ---------------------------------------------------------
async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await update.message.reply_text("የምርቱን ስም ያስገቡ (ለምሳሌ: የወንድ ጂንስ ሱሪ / Samsung S23):")
    return ADD_NAME

async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['prod_name'] = update.message.text.strip()
    await update.message.reply_text(
        "የምርቱን ካታጎሪ ከታች ካሉት ቁልፎች ይምረጡ (ወይም በጽሁፍ ይጻፉ):",
        reply_markup=categories_admin_keyboard()
    )
    return ADD_CATEGORY

async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['prod_cat'] = update.message.text.strip()
    await update.message.reply_text(
        "የምርቱን ዋጋ በብር ያስገቡ (ቁጥር ብቻ፤ ለምሳሌ: 2500):",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_PRICE

async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(',', '').replace('Birr', '').strip()
    try:
        price = float(text)
        context.user_data['prod_price'] = price
        await update.message.reply_text("ስለ ምርቱ መግለጫ (Description) ያስገቡ:")
        return ADD_DESC
    except ValueError:
        await update.message.reply_text("⚠️ እባክዎን ትክክለኛ ቁጥር ብቻ ያስገቡ (ለምሳሌ: 2500):")
        return ADD_PRICE

async def add_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['prod_desc'] = update.message.text.strip()
    await update.message.reply_text("አሁን የምርቱን ፎቶ ይላኩ:")
    return ADD_PHOTO

async def add_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id
    
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, category, price, description, photo_id) VALUES (?, ?, ?, ?, ?)",
        (context.user_data['prod_name'], context.user_data['prod_cat'], context.user_data['prod_price'], context.user_data['prod_desc'], photo_id)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ ምርቱ በትክክል ተመዝግቧል!", reply_markup=admin_menu_keyboard(update.effective_user.id))
    return ConversationHandler.END

# ---------------------------------------------------------
# ADMIN EDIT & DELETE PRODUCT FUNCTIONS
# ---------------------------------------------------------
async def admin_manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price FROM products ORDER BY id DESC")
    products = cursor.fetchall()
    conn.close()

    if not products:
        await update.message.reply_text("ምንም የተመዘገቡ ምርቶች የሉም።")
        return

    keyboard = []
    for p in products:
        keyboard.append([InlineKeyboardButton(f"🛠 {p[1]} ({p[2]:,.0f} ETB)", callback_data=f"mng_{p[0]}")])

    await update.message.reply_text(
        "🛠 **ለማስተካከል ወይም ለመሰረዝ የሚፈልጉትን ምርት ይምረጡ:**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_manage_product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        return

    data = query.data
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()

    if data.startswith("mng_"):
        prod_id = int(data.split("mng_")[1])
        cursor.execute("SELECT name, price, description FROM products WHERE id = ?", (prod_id,))
        p = cursor.fetchone()
        conn.close()

        if p:
            msg = f"🛠 **ምርት ማስተካከያ ገጽ**\n\n📌 **ስም:** {p[0]}\n💰 **ዋጋ:** {p[1]:,.2f} ETB\n📝 **መግለጫ:**\n{p[2]}"
            keyboard = [
                [InlineKeyboardButton("💰 ዋጋ ቀይር", callback_data=f"editprice_{prod_id}")],
                [InlineKeyboardButton("📝 መግለጫ (Post) ቀይር", callback_data=f"editdesc_{prod_id}")],
                [InlineKeyboardButton("🗑 ምርቱን ሰርዝ", callback_data=f"delprod_{prod_id}")],
                [InlineKeyboardButton("⬅️ ተመለስ", callback_data="mng_back")]
            ]
            await query.answer()
            await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("delprod_"):
        prod_id = int(data.split("delprod_")[1])
        cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
        cursor.execute("DELETE FROM cart WHERE product_id = ?", (prod_id,))
        conn.commit()
        conn.close()

        await query.answer("ምርቱ ተሰርዟል!", show_alert=True)
        await query.message.edit_text("✅ **ምርቱ በትክክል ከሲስተሙ ተሰርዟል!**", parse_mode="Markdown")

    elif data == "mng_back":
        conn.close()
        await query.answer()
        await admin_manage_products(update, context)

# Start edit price conversation
async def start_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("editprice_")[1])
    context.user_data['edit_prod_id'] = prod_id

    await query.message.reply_text("እባክዎን አዲሱን ዋጋ በቁጥር ብቻ ያስገቡ (ለምሳሌ: 2500):")
    return EDIT_PRICE_STATE

async def save_edited_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(',', '').replace('Birr', '').strip()
    try:
        new_price = float(text)
        prod_id = context.user_data.get('edit_prod_id')

        conn = sqlite3.connect("kan_gebeya.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, prod_id))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ **የምርቱ ዋጋ ወደ {new_price:,.2f} ETB በትክክል ተቀይሯል!**",
            parse_mode="Markdown",
            reply_markup=admin_menu_keyboard(update.effective_user.id)
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("⚠️ እባክዎን ትክክለኛ ቁጥር ብቻ ያስገቡ (ለምሳሌ: 2500):")
        return EDIT_PRICE_STATE

# Start edit description conversation
async def start_edit_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("editdesc_")[1])
    context.user_data['edit_prod_id'] = prod_id

    await query.message.reply_text("እባክዎን አዲሱን የምርት መግለጫ (Post Text) ያስገቡ:")
    return EDIT_DESC_STATE

async def save_edited_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_desc = update.message.text.strip()
    prod_id = context.user_data.get('edit_prod_id')

    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET description = ? WHERE id = ?", (new_desc, prod_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "✅ **የምርቱ መግለጫ (Post Text) በትክክል ተሻሽሏል!**",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard(update.effective_user.id)
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ተሰርዟል።", reply_markup=main_menu_keyboard(update.effective_user.id))
    return ConversationHandler.END

# ---------------------------------------------------------
# MAIN MENU HANDLER
# ---------------------------------------------------------
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    txt = STRINGS[lang]

    if text in [STRINGS['am']['btn_products'], STRINGS['en']['btn_products']]:
        await show_categories(update, context)
    elif text in [STRINGS['am']['btn_cart'], STRINGS['en']['btn_cart']]:
        await show_cart(update, context)
    elif text in [STRINGS['am']['btn_orders'], STRINGS['en']['btn_orders']]:
        await show_orders(update, context)
    elif text in [STRINGS['am']['btn_help'], STRINGS['en']['btn_help']]:
        await update.message.reply_text(txt['help_msg'], parse_mode="Markdown")
    elif text in [STRINGS['am']['btn_lang'], STRINGS['en']['btn_lang']]:
        await show_language_selector(update, context)
    elif text in [STRINGS['am']['btn_admin'], STRINGS['en']['btn_admin']] and user_id in ADMIN_IDS:
        await update.message.reply_text(
            txt['admin_welcome'],
            reply_markup=admin_menu_keyboard(user_id)
        )
    elif text in [STRINGS['am']['admin_manage_prod'], STRINGS['en']['admin_manage_prod']] and user_id in ADMIN_IDS:
        await admin_manage_products(update, context)
    elif text in [STRINGS['am']['admin_stats'], STRINGS['en']['admin_stats']] and user_id in ADMIN_IDS:
        await show_admin_stats(update, context)
    elif text in [STRINGS['am']['admin_back_main'], STRINGS['en']['admin_back_main']]:
        await update.message.reply_text(
            "ወደ ዋናው ገጽ ተመልሰዋል። / Back to main menu.",
            reply_markup=main_menu_keyboard(user_id)
        )
    elif text in [STRINGS['am']['admin_view_orders'], STRINGS['en']['admin_view_orders']] and user_id in ADMIN_IDS:
        await show_orders(update, context)

async def show_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_price), 0) FROM orders")
    orders_data = cursor.fetchone()
    total_orders = orders_data[0] or 0
    total_sales = orders_data[1] or 0.0

    conn.close()

    msg = (
        f"📊 **የካን ገበያ ቦት ስታቲስቲክስ (Bot Statistics):**\n\n"
        f"👥 **ጠቅላላ ተጠቃሚዎች:** {total_users}\n"
        f"🛍 **የተመዘገቡ ምርቶች:** {total_products}\n"
        f"📦 **ጠቅላላ ትዕዛዞች:** {total_orders}\n"
        f"💰 **ጠቅላላ የሽያጭ መጠን:** {total_sales:,.2f} ETB"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ---------------------------------------------------------
# MAIN BOT RUNNER
# ---------------------------------------------------------
def main():
    threading.Thread(target=run_health_check_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    # Add product conversation handler
    add_prod_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(➕ አዲስ ምርት ጨምር|➕ Add New Product)$'), start_add_product)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_name)],
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_category)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_price)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_desc)],
            ADD_PHOTO: [MessageHandler(filters.PHOTO, add_product_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Edit price conversation handler
    edit_price_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_edit_price, pattern='^editprice_')],
        states={
            EDIT_PRICE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_price)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Edit desc conversation handler
    edit_desc_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_edit_desc, pattern='^editdesc_')],
        states={
            EDIT_DESC_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_desc)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(add_prod_handler)
    app.add_handler(edit_price_handler)
    app.add_handler(edit_desc_handler)
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_upload))
    
    app.add_handler(CallbackQueryHandler(handle_language_change, pattern='^(setlang_am|setlang_en)$'))
    app.add_handler(CallbackQueryHandler(handle_category_callback, pattern='^(cat_|prod_|addcart_|show_cats|btn_go_cart)'))
    app.add_handler(CallbackQueryHandler(handle_cart_callback, pattern='^(clear_cart|checkout)'))
    app.add_handler(CallbackQueryHandler(handle_manage_product_callback, pattern='^(mng_|delprod_)'))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))

    print("🤖 Kan Gebeya Bot እየሰራ ነው...")
    app.run_polling()

if __name__ == '__main__':
    main()

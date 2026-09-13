import logging
import sqlite3
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters, CallbackQueryHandler
)

# -----------------------------------------------------------------------------
# BOT CONFIGURATION
# -----------------------------------------------------------------------------
BOT_TOKEN = "8990836657:AAEgyMHpLUCxYma3xbPqDGsCdYiA2D6lorM"
ADMIN_IDS = [6720581112]  # የአድሚን የቴሌግራም ID
SUPPORT_USERNAME = "Kan_Gebeya"
PHONE_NUMBER = "0906078429"
TELEBIRR_ACCOUNT = "0906078429"
CBE_ACCOUNT = "100000000000"

# ቻናል እና ቦት አያያዝ
BOT_USERNAME = "kan_gebeya_bot"        # ያለ @
CHANNEL_ID = "@kan_gebeya_channel"      # የቻናልህ username (ከ @ ጋር)

# Conversation States for Admin Add Product
ADD_NAME, ADD_CATEGORY, ADD_PRICE, ADD_DESC, ADD_PHOTO = range(5)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# DATABASE SETUP
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            photo_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# KEYBOARDS
# -----------------------------------------------------------------------------
def get_main_keyboard(user_id):
    buttons = [
        [KeyboardButton("🛍 ምርቶች"), KeyboardButton("🛒 የእኔ ካርት")],
        [KeyboardButton("📞 እኛን ለማነጋገር"), KeyboardButton("❓ እርዳታ")]
    ]
    if user_id in ADMIN_IDS:
        buttons.append([KeyboardButton("⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_categories_keyboard():
    buttons = [
        [KeyboardButton("👗 የሴቶች አልባሳት"), KeyboardButton("👔 የወንዶች አልባሳት")],
        [KeyboardButton("💻 ላፕቶፕ / PC"), KeyboardButton("📱 ስልክ")],
        [KeyboardButton("🔌 ኤሌክትሮኒክስ"), KeyboardButton("📦 ሌሎች")],
        [KeyboardButton("⬅️ ወደ ዋናው ገጽ")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_admin_keyboard():
    buttons = [
        [KeyboardButton("➕ Add New Product"), KeyboardButton("🛠 Edit / Delete Products")],
        [KeyboardButton("📦 View Orders"), KeyboardButton("📊 User Statistics")],
        [KeyboardButton("⬅️ Back to Main Menu")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# -----------------------------------------------------------------------------
# START & MAIN MENU HANDLERS
# -----------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user.id, user.username, user.first_name)
    )
    conn.commit()
    conn.close()

    # Deep linking check (ከቻናል የመጣ ደንበኛ)
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith("item_"):
            try:
                product_id = int(arg.split("_")[1])
                await show_product_details(update, context, product_id)
                return
            except Exception as e:
                logger.error(f"Deep link error: {e}")

    welcome_text = (
        f"እንኳን ወደ **Kan Gebeya** በደህና መጡ! 🛒\n\n"
        f"እዚህ አልባሳት፣ ኤሌክትሮኒክስ፣ ላፕቶፖች እና ስልኮችን በጥራት ማዘዝ ይችላሉ።\n\n"
        f"ለመጀመር ከታች ያሉትን ቁልፎች ይጠቀሙ 👇"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(user.id), parse_mode="Markdown")

async def show_product_details(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, category, price, description, photo_id FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()
    conn.close()

    if prod:
        name, category, price, description, photo_id = prod
        caption = (
            f"🛍 **{name}**\n\n"
            f"📁 **ካታጎሪ:** {category}\n"
            f"💰 **ዋጋ:** {price:,.2f} ETB\n\n"
            f"📝 **መግለጫ:**\n{description}\n\n"
            f"📞 ለማዘዝ አሁኑኑ ይጫኑ!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 አሁኑኑ እዘዝ (Order Now)", callback_data=f"order_{product_id}")],
            [InlineKeyboardButton("📞 አድሚንን አነጋግር", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ])
        if photo_id:
            await update.message.reply_photo(photo=photo_id, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(text=caption, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text("ይቅርታ፣ ምርቱ አልተገኘም ወይም ተሰርዟል።")

# -----------------------------------------------------------------------------
# CATEGORY & PRODUCT VIEWING FOR USERS
# -----------------------------------------------------------------------------
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🛍 ምርቶች":
        await update.message.reply_text("እባክዎን ማየት የሚፈልጉትን የምርት ካታጎሪ ይምረጡ፦", reply_markup=get_categories_keyboard())

    elif text in ["👗 የሴቶች አልባሳት", "👔 የወንዶች አልባሳት", "💻 ላፕቶፕ / PC", "📱 ስልክ", "🔌 ኤሌክትሮኒክስ", "📦 ሌሎች"]:
        conn = sqlite3.connect("kan_gebeya.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, description, photo_id FROM products WHERE category = ?", (text,))
        products = cursor.fetchall()
        conn.close()

        if not products:
            await update.message.reply_text(f"በ '{text}' ካታጎሪ ውስጥ የተመዘገበ ምርት የለም።", reply_markup=get_categories_keyboard())
            return

        for prod in products:
            p_id, p_name, p_price, p_desc, p_photo = prod
            caption = f"🛍 **{p_name}**\n💰 **ዋጋ:** {p_price:,.2f} ETB\n\n📝 {p_desc}"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 አሁኑኑ እዘዝ", callback_data=f"order_{p_id}")]
            ])
            if p_photo:
                await update.message.reply_photo(photo=p_photo, caption=caption, reply_markup=keyboard, parse_mode="Markdown")
            else:
                await update.message.reply_text(caption, reply_markup=keyboard, parse_mode="Markdown")

    elif text in ["⬅️ ወደ ዋናው ገጽ", "⬅️ Back to Main Menu"]:
        await update.message.reply_text("ወደ ዋናው ገጽ ተመልሰዋል።", reply_markup=get_main_keyboard(user_id))

    elif text == "📞 እኛን ለማነጋገር":
        contact_text = f"📞 **እኛን ለማነጋገር:**\n\n📱 ስልክ: {PHONE_NUMBER}\n💬 Telegram: @{SUPPORT_USERNAME}\n💳 Telebirr: {TELEBIRR_ACCOUNT}"
        await update.message.reply_text(contact_text, parse_mode="Markdown")

    elif text == "❓ እርዳታ":
        await update.message.reply_text("እቃ ለመግዛት '🛍 ምርቶች' የሚለውን በመጫን ካታጎሪ መርጠው ማዘዝ ይችላሉ።")

    elif text == "⚙️ Admin Panel" and user_id in ADMIN_IDS:
        await update.message.reply_text("Welcome to Admin Panel!", reply_markup=get_admin_keyboard())

# -----------------------------------------------------------------------------
# ADMIN ADD PRODUCT CONVERSATION HANDLER
# -----------------------------------------------------------------------------
async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END

    await update.message.reply_text("1️⃣ **እባክዎን የምርቱን ስም ያስገቡ:**\n(ለምሳሌ፦ Predator Helios 16)", parse_mode="Markdown")
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['p_name'] = update.message.text
    await update.message.reply_text(
        "2️⃣ **እባክዎን የምርቱን ካታጎሪ ከታች ካሉት ቁልፎች ይምረጡ:**",
        reply_markup=get_categories_keyboard(),
        parse_mode="Markdown"
    )
    return ADD_CATEGORY

async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    if category not in ["👗 የሴቶች አልባሳት", "👔 የወንዶች አልባሳት", "💻 ላፕቶፕ / PC", "📱 ስልክ", "🔌 ኤሌክትሮኒክስ", "📦 ሌሎች"]:
        await update.message.reply_text("እባክዎን ከታች ከተቀመጡት ቁልፎች አንዱን ይምረጡ!")
        return ADD_CATEGORY

    context.user_data['p_category'] = category
    await update.message.reply_text("3️⃣ **እባክዎን የምርቱን ዋጋ በብር (ቁጥር ብቻ) ያስገቡ:**\n(ለምሳሌ፦ 285000)", parse_mode="Markdown")
    return ADD_PRICE

async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
        context.user_data['p_price'] = price
        await update.message.reply_text("4️⃣ **እባክዎን የምርቱን መግለጫ (Description) ያስገቡ:**", parse_mode="Markdown")
        return ADD_DESC
    except ValueError:
        await update.message.reply_text("እባክዎን ትክክለኛ ቁጥር ብቻ ያስገቡ (ለምሳሌ: 1500):")
        return ADD_PRICE

async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['p_desc'] = update.message.text
    await update.message.reply_text("5️⃣ **እባክዎን የምርቱን ፎቶ ይላኩ:**", parse_mode="Markdown")
    return ADD_PHOTO

async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id if update.message.photo else None
    
    name = context.user_data['p_name']
    category = context.user_data['p_category']
    price = context.user_data['p_price']
    desc = context.user_data['p_desc']

    # 1. Save to Database
    conn = sqlite3.connect("kan_gebeya.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, category, price, description, photo_id) VALUES (?, ?, ?, ?, ?)",
        (name, category, price, desc, photo_id)
    )
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ **ምርቱ በጥሩ ሁኔታ በቦቱ ላይ ተመዝግቧል!**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

    # 2. Auto-post to Channel
    try:
        deep_link = f"https://t.me/{BOT_USERNAME}?start=item_{product_id}"
        channel_caption = (
            f"🔥 **አዲስ ምርት ገብቷል!** 🔥\n\n"
            f"📌 **{name}**\n"
            f"📁 **ካታጎሪ:** {category}\n"
            f"💰 **ዋጋ:** {price:,.2f} ETB\n\n"
            f"📝 **መግለጫ:**\n{desc}\n\n"
            f"👇 **በቦታችን ለማዘዝ እዚህ ይጫኑ:**"
        )
        channel_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 በቦት ለማዘዝ / ለመግዛት", url=deep_link)]
        ])

        if photo_id:
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=channel_caption, reply_markup=channel_keyboard, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=channel_caption, reply_markup=channel_keyboard, parse_mode="Markdown")

        await update.message.reply_text("📢 **ምርቱ ወደ ቴሌግራም ቻናልህም በራሱ ጊዜ ፖስት ተደርጓል!**")
    except Exception as e:
        logger.error(f"Channel post error: {e}")
        await update.message.reply_text("⚠️ ምርቱ ቦቱ ላይ ተመዝግቧል፤ ነገር ግን ወደ ቻናል ፖስት ሲደረግ ስህተት አጋጥሟል (ቦቱ የቻናሉ አድሚን መሆኑን አረጋግጥ)።")

    return ConversationHandler.END

async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("የምርት መመዝገብ ሂደቱ ተሰርዟል።", reply_markup=get_admin_keyboard())
    return ConversationHandler.END

# -----------------------------------------------------------------------------
# CALLBACK QUERY (ORDER BUTTONS)
# -----------------------------------------------------------------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("order_"):
        product_id = query.data.split("_")[1]
        user = query.from_user

        conn = sqlite3.connect("kan_gebeya.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE id = ?", (product_id,))
        prod = cursor.fetchone()

        if prod:
            cursor.execute("INSERT INTO orders (user_id, product_id) VALUES (?, ?)", (user.id, product_id))
            conn.commit()
            
            await query.message.reply_text(
                f"✅ **ትዕዛዝዎ ተመዝግቧል!**\n\n"
                f"🛍 **ምርት:** {prod[0]}\n"
                f"💰 **ክፍያ:** {prod[1]:,.2f} ETB\n\n"
                f"💳 **ክፍያ የሚፈጽሙበት ሂሳብ:**\n"
                f"• Telebirr: `{TELEBIRR_ACCOUNT}`\n"
                f"• CBE: `{CBE_ACCOUNT}`\n\n"
                f"የከፈሉበትን ደረሰኝ ለ አድሚን (@{SUPPORT_USERNAME}) ይላኩ። አመሰግናለሁ!",
                parse_mode="Markdown"
            )
        conn.close()

# -----------------------------------------------------------------------------
# MAIN APP EXECUTION
# -----------------------------------------------------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Add Product Conversation
    add_prod_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Add New Product$"), start_add_product)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc)],
            ADD_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT, add_photo)],
        },
        fallbacks=[MessageHandler(filters.Regex("^⬅️ Back to Main Menu$"), cancel_add)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_prod_handler)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))

    print("🤖 Kan Gebeya Bot እየሰራ ነው...")
    app.run_polling()

if __name__ == "__main__":
    main()

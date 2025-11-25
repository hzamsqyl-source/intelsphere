import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT = "@intelsphere_logs"  # غيّره لقناتك أو اتركه كذا

# ==== قاعدة البيانات ====
def init_db():
    conn = sqlite3.connect("reports.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        platform TEXT,
        link TEXT,
        screenshot_path TEXT,
        description TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# ==== مراحل المحادثة ====
PLATFORM, LINK, DESCRIPTION, SCREENSHOT = range(4)

# ==== /start ====
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🛡️ أهلاً بك في IntelSphere Bot!\n"
        "نستقبل بلاغاتك ضد الحسابات المزيفة والمبتزين.\n\n"
        "➡️ استخدم /report لرفع بلاغ جديد."
    )

# ==== /report ====
def report(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("فيسبوك", callback_data='facebook')],
        [InlineKeyboardButton("تويتر", callback_data='twitter')],
        [InlineKeyboardButton("إنستغرام", callback_data='instagram')],
        [InlineKeyboardButton("تيك توك", callback_data='tiktok')]
    ]
    update.message.reply_text("اختر المنصة:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PLATFORM

# ==== استقبال المنصة ====
def platform(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data['platform'] = query.data
    query.edit_message_text(text="📎 أرسل رابط الحساب المبلغ عنه:")
    return LINK

# ==== استقبال الرابط ====
def link(update: Update, context: CallbackContext):
    context.user_data['link'] = update.message.text
    update.message.reply_text("📝 اكتب وصفاً مختصراً للمشكلة (ابتزاز، انتحال، تشهير...):")
    return DESCRIPTION

# ==== استقبال الوصف ====
def description(update: Update, context: CallbackContext):
    context.user_data['description'] = update.message.text
    update.message.reply_text("📸 أرسل لقطة شاشة (صورة):")
    return SCREENSHOT

# ==== استقبال الصورة وحفظ البلاغ ====
def screenshot(update: Update, context: CallbackContext):
    photo = update.message.photo[-1].file_id
    user = update.message.from_user
    conn = sqlite3.connect("reports.db")
    c = conn.cursor()
    c.execute("INSERT INTO reports (user_id, username, platform, link, screenshot_path, description) VALUES (?,?,?,?,?,?)",
              (user.id, user.username, context.user_data['platform'], context.user_data['link'], photo, context.user_data['description']))
    conn.commit()
    conn.close()

    # أزرار البلاغ الخارجي
    platform = context.user_data['platform']
    link = context.user_data['link']
    urls = {
        "facebook":  f"https://www.facebook.com/help/contact/272217376552627?report_link={link}",
        "twitter":   f"https://help.twitter.com/forms/impersonation?report_link={link}",
        "instagram": f"https://help.instagram.com/contact/723586364339719?report_link={link}",
        "tiktok":    f"https://www.tiktok.com/report?report_link={link}"
    }
    keyboard = [[InlineKeyboardButton("📢 إرسال البلاغ إلى " + platform, url=urls[platform])]]
    update.message.reply_text("✅ تم حفظ بلاغك.", reply_markup=InlineKeyboardMarkup(keyboard))

    # إرسال نسخة إلى قناة المشرفين
    context.bot.send_message(
        chat_id=ADMIN_CHAT,
        text=f"بلاغ جديد!\nالمنصة: {platform}\nالرابط: {link}\nالوصف: {context.user_data['description']}"
    )
    return ConversationHandler.END

# ==== إلغاء ====
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❌ تم الإلغاء.")
    return ConversationHandler.END

# ==== main ====
def main():
    init_db()
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler('report', report)],
        states={
            PLATFORM: [CallbackQueryHandler(platform)],
            LINK: [MessageHandler(Filters.text & ~Filters.command, link)],
            DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, description)],
            SCREENSHOT: [MessageHandler(Filters.photo, screenshot)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

import os
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler
from database import Database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8979539331:AAH-rsV0IJ41OzcqNxGY6C3H9rJva7VdfQs")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5906806720"))

PHONE, SERVICE, DATE, TIME, CONFIRM = range(5)
db = Database()

async def start(update, context):
    user = update.effective_user
    db.add_user(user.id, user.first_name, user.username)
    keyboard = [["📅 Navbat olish", "📋 Mening navbatlarim"], ["💈 Xizmatlar va narxlar", "📞 Bog'lanish"]]
    await update.message.reply_text(f"Assalomu alaykum, {user.first_name}! 👋\n\n💈 Sartaroshxonaga xush kelibsiz!\n\nQuyidagi xizmatlardan birini tanlang:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode="Markdown")

async def book_appointment(update, context):
    keyboard = [[KeyboardButton("📱 Raqamni yuborish", request_contact=True)]]
    await update.message.reply_text("Telefon raqamingizni yuboring 👇", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True))
    return PHONE

async def get_phone(update, context):
    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    context.user_data['phone'] = phone
    db.update_phone(update.effective_user.id, phone)
    keyboard = [[InlineKeyboardButton("✂️ Soch olish - 30,000 so'm", callback_data="service_soch")], [InlineKeyboardButton("🪒 Soqol olish - 20,000 so'm", callback_data="service_soqol")], [InlineKeyboardButton("✂️🪒 Ikkalasi - 45,000 so'm", callback_data="service_ikkalasi")]]
    await update.message.reply_text("Xizmat turini tanlang 👇", reply_markup=InlineKeyboardMarkup(keyboard))
    return SERVICE

async def get_service(update, context):
    query = update.callback_query
    await query.answer()
    service_map = {"service_soch": "✂️ Soch olish - 30,000 so'm", "service_soqol": "🪒 Soqol olish - 20,000 so'm", "service_ikkalasi": "✂️🪒 Ikkalasi - 45,000 so'm"}
    context.user_data['service'] = service_map[query.data]
    today = datetime.now()
    keyboard = []
    row = []
    for i in range(7):
        day = today + timedelta(days=i)
        row.append(InlineKeyboardButton(day.strftime("%d.%m (%a)"), callback_data=f"date_{day.strftime('%Y-%m-%d')}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    await query.edit_message_text(f"✅ Xizmat: *{service_map[query.data]}*\n\n📅 Kun tanlang:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return DATE

async def get_date(update, context):
    query = update.callback_query
    await query.answer()
    date_val = query.data.replace("date_", "")
    context.user_data['date'] = date_val
    booked = db.get_booked_times(date_val)
    all_times = ["09:00","09:30","10:00","10:30","11:00","11:30","12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30","16:00","16:30","17:00","17:30"]
    keyboard = []
    row = []
    for t in all_times:
        btn = InlineKeyboardButton(f"❌ {t}" if t in booked else f"🟢 {t}", callback_data="booked" if t in booked else f"time_{t}")
        row.append(btn)
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    await query.edit_message_text(f"📅 *{datetime.strptime(date_val, '%Y-%m-%d').strftime('%d.%m.%Y')}*\n\n🕐 Vaqt tanlang:\n🟢 Bo'sh | ❌ Band", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return TIME

async def get_time(update, context):
    query = update.callback_query
    if query.data == "booked":
        await query.answer("Bu vaqt band! Boshqa vaqt tanlang.", show_alert=True)
        return TIME
    await query.answer()
    context.user_data['time'] = query.data.replace("time_", "")
    date_val = context.user_data['date']
    service = context.user_data['service']
    phone = context.user_data['phone']
    time_val = context.user_data['time']
    date_display = datetime.strptime(date_val, '%Y-%m-%d').strftime('%d.%m.%Y')
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_yes"), InlineKeyboardButton("❌ Bekor qilish", callback_data="confirm_no")]])
    await query.edit_message_text(f"📋 *Navbat ma'lumotlari:*\n\n📅 Sana: {date_display}\n🕐 Vaqt: {time_val}\n💈 Xizmat: {service}\n📱 Telefon: {phone}\n\nTasdiqlaysizmi?", reply_markup=keyboard, parse_mode="Markdown")
    return CONFIRM

async def confirm_booking(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_no":
        await query.edit_message_text("❌ Navbat bekor qilindi.")
        return ConversationHandler.END
    user = update.effective_user
    date_val = context.user_data['date']
    time_val = context.user_data['time']
    service = context.user_data['service']
    phone = context.user_data['phone']
    booking_id = db.add_booking(user.id, phone, date_val, time_val, service)
    date_display = datetime.strptime(date_val, '%Y-%m-%d').strftime('%d.%m.%Y')
    await query.edit_message_text(f"✅ *Navbatingiz qabul qilindi!*\n\n📅 {date_display}\n🕐 {time_val}\n💈 {service}\n\n⚠️ Admin tasdiqlashi kutilmoqda...", parse_mode="Markdown")
    admin_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_confirm_{booking_id}"), InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{booking_id}")]])
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 *Yangi navbat!*\n\n👤 {user.first_name}\n📱 {phone}\n📅 {date_display}\n🕐 {time_val}\n💈 {service}\n🆔 #{booking_id}", reply_markup=admin_keyboard, parse_mode="Markdown")
    return ConversationHandler.END

async def admin_action(update, context):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_ID:
        return
    if query.data.startswith("admin_confirm_"):
        booking_id = int(query.data.replace("admin_confirm_", ""))
        booking = db.get_booking(booking_id)
        db.update_booking_status(booking_id, "confirmed")
        await query.edit_message_text(query.message.text + "\n\n✅ TASDIQLANDI", parse_mode="Markdown")
        date_display = datetime.strptime(booking['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        await context.bot.send_message(chat_id=booking['user_id'], text=f"🎉 *Navbatingiz tasdiqlandi!*\n\n📅 {date_display} soat {booking['time']}\n💈 {booking['service']}\n\nKo'rishguncha! 😊", parse_mode="Markdown")
    elif query.data.startswith("admin_reject_"):
        booking_id = int(query.data.replace("admin_reject_", ""))
        booking = db.get_booking(booking_id)
        db.update_booking_status(booking_id, "rejected")
        await query.edit_message_text(query.message.text + "\n\n❌ RAD ETILDI", parse_mode="Markdown")
        await context.bot.send_message(chat_id=booking['user_id'], text="😔 Afsuski, tanlagan vaqtingiz band.\nBoshqa vaqt tanlang: /start")

async def my_bookings(update, context):
    bookings = db.get_user_bookings(update.effective_user.id)
    if not bookings:
        await update.message.reply_text("📋 Sizda hozircha navbat yo'q.\n\n/start - Navbat olish")
        return
    text = "📋 *Sizning navbatlaringiz:*\n\n"
    for b in bookings:
        date_display = datetime.strptime(b['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        status_map = {"pending": "⏳", "confirmed": "✅", "rejected": "❌"}
        text += f"{status_map.get(b['status'], '❓')} {date_display} - {b['time']}\n💈 {b['service']}\n──────\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def prices(update, context):
    await update.message.reply_text("💈 *Xizmatlar va narxlar:*\n\n✂️ Soch olish — 30,000 so'm\n🪒 Soqol olish — 20,000 so'm\n✂️🪒 Soch + Soqol — 45,000 so'm\n\n⏱ Ish vaqti: 09:00 - 18:00", parse_mode="Markdown")

async def contact(update, context):
    await update.message.reply_text("📞 *Bog'lanish:*\n\n📱 Telefon: +998 XX XXX XX XX\n📍 Manzil: [Manzilingiz]\n🕐 09:00 - 18:00", parse_mode="Markdown")

async def admin_today(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    bookings = db.get_day_bookings(today)
    if not bookings:
        await update.message.reply_text("📅 Bugun navbat yo'q.")
        return
    text = f"📅 *Bugungi navbatlar:*\n\n"
    for b in bookings:
        status_map = {"pending": "⏳", "confirmed": "✅", "rejected": "❌"}
        text += f"{status_map.get(b['status'], '❓')} {b['time']} — {b['service']} | 📱 {b['phone']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def send_reminders(context):
    users = db.get_users_for_reminder()
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text="💈 *Salom!*\n\nSochingizni olishga vaqt bo'ldi! 🕐\n\nNavbat olish uchun /start bosing 👇", parse_mode="Markdown")
            db.update_reminder_sent(user['user_id'])
        except Exception as e:
            logger.error(f"Xato: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📅 Navbat olish$"), book_appointment)],
        states={
            PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, get_phone)],
            SERVICE: [CallbackQueryHandler(get_service, pattern="^service_")],
            DATE: [CallbackQueryHandler(get_date, pattern="^date_")],
            TIME: [CallbackQueryHandler(get_time, pattern="^time_|^booked$")],
            CONFIRM: [CallbackQueryHandler(confirm_booking, pattern="^confirm_")],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex("^📋 Mening navbatlarim$"), my_bookings))
    app.add_handler(MessageHandler(filters.Regex("^💈 Xizmatlar va narxlar$"), prices))
    app.add_handler(MessageHandler(filters.Regex("^📞 Bog'lanish$"), contact))
    app.add_handler(CommandHandler("bugun", admin_today))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^admin_"))
    app.job_queue.run_repeating(send_reminders, interval=1296000, first=10)
    logger.info("Bot ishga tushdi! ✅")
    app.run_polling()

if __name__ == "__main__":
    main()

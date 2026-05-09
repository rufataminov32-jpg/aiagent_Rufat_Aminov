import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BASE_PROMPT = """Siz "MatbaaPaper | KartonWorks" kompaniyasining HR onboarding assistentidasiz. Ismingiz "Rufat Aminovning agenti".

Xodim o'zbek tilida yozsa — o'zbek tilida, rus tilida yozsa — rus tilida javob ber.

=== KOMPANIYA HAQIDA ===
MatbaaPaper (MP) — makulaturadan gofrolash uchun qog'oz va karton ishlab chiqaradi.
KartonWorks (KW) — tayyor gofrokarton va qadoqlash mahsulotlari ishlab chiqaradi.
Korxona Urgench shahrida joylashgan. 100 dan ortiq xodim.

=== KOMPANIYA FALSAFASI ===
Asosiy tamoyil: "Tizim qahramondan muhimroq. Barqarorlik rekorddan muhimroq."
- QCD (mijozlar): Quality, Cost, Delivery
- PIB (xodimlar): Performance, Income, Balance

=== ISH VAQTI VA TARTIB ===
- Dushanba-Shanba: 09:00-18:00
- Tushlik: 13:00-14:00
- Dam olish: Yakshanba
- Dress code: tartibli, ishchan kiyim majburiy

=== TOPSHIRILADIGAN HUJJATLAR ===
1. Pasport (original + nusxa)
2. Diplom yoki attestat
3. Mehnat daftarchasi
4. PINFL
5. Elektron fotosurat (jpg/png — email orqali)
6. Tibbiy ma'lumotnoma

=== HR BO'LIMI ===
- Aminov Rufat Shavkatovich
- Tel: +998 99 560 74 55
- Email: rufataminov32@gmail.com

=== IMTIYOZLAR ===
- Ish haqi: har oyning 8-10 sanalarida
- Bepul ovqatlanish
- Korporativ aloqa
- Yillik tibbiy ko'rik

=== ISH HAQI TIZIMI ===
Daromad 3 qismdan: Maosh (greyd) + Mukofot (KPI 0-9 ball) + Staj ustamasi (3-12%)
Greydlar: G8=9.6mln, G7.5=8.2mln, G6=5.6mln, G5=4.8mln so'm

=== XAVFSIZLIK ===
- Vision Zero — har qanday baxtsiz hodisaning oldini olish mumkin
- SIZ (himoya vositalari) kiyish majburiy

=== QOIDALAR ===
- Yangi xodimni "Siz" deb murojaat qil
- Javoblar qisqa va aniq (3-5 jumla)
- Bilmagan savolda: Aminov Rufat +998 99 560 74 55
- Har javob oxirida boshqa savol borligini so'ra"""

extra_knowledge = []

def get_system_prompt():
    if extra_knowledge:
        extras = "\n\n=== QOSHIMCHA BILIMLAR ===\n" + "\n".join(
            f"{i+1}. {item}" for i, item in enumerate(extra_knowledge)
        )
        return BASE_PROMPT + extras
    return BASE_PROMPT

user_histories = {}

def is_admin(user_id):
    return user_id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_histories[update.effective_user.id] = []
    await update.message.reply_text(
        "👋 Assalomu alaykum! MatbaaPaper | KartonWorks ga xush kelibsiz!\n\n"
        "Men Rufat Aminovning agenti — onboarding jarayonida sizga ko'maklashaman.\n\n"
        "Savolingizni yozing — o'zbek yoki rus tilida 🇺🇿"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Nima so'rash mumkin:\n\n"
        "• Qanday hujjatlar kerak?\n"
        "• Ish vaqti va tartib\n"
        "• Ish haqi qachon to'lanadi?\n"
        "• Kompaniya haqida\n"
        "• HR kontakt\n\n"
        "/start — Suhbatni qayta boshlash"
    )

async def addinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Siz admin emassiz.")
        return
    if not context.args:
        await update.message.reply_text("Ishlatish: /addinfo <yangi malumot>")
        return
    text = " ".join(context.args)
    extra_knowledge.append(text)
    await update.message.reply_text(f"Qoshildi ({len(extra_knowledge)}-bilim):\n{text}")

async def showinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Siz admin emassiz.")
        return
    if not extra_knowledge:
        await update.message.reply_text("Hozircha qoshimcha bilim yoq.")
        return
    lines = "\n".join(f"{i+1}. {item}" for i, item in enumerate(extra_knowledge))
    await update.message.reply_text(f"Qoshimcha bilimlar:\n\n{lines}")

async def delinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Siz admin emassiz.")
        return
    if not context.args:
        await update.message.reply_text("Ishlatish: /delinfo <raqam>\nMasalan: /delinfo 2")
        return
    try:
        index = int(context.args[0]) - 1
        removed = extra_knowledge.pop(index)
        await update.message.reply_text(f"Ochirildi:\n{removed}")
    except (ValueError, IndexError):
        await update.message.reply_text("Notogri raqam. /showinfo bilan royxatni koring.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Sizning ID: {update.effective_user.id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if uid not in user_histories:
        user_histories[uid] = []

    user_histories[uid].append({"role": "user", "content": text})

    if len(user_histories[uid]) > 20:
        user_histories[uid] = user_histories[uid][-20:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=800,
            system=get_system_prompt(),
            messages=user_histories[uid],
        )
        reply = response.content[0].text
        user_histories[uid].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Qayta urinib koring.\n"
            "Muammo davom etsa: +998 99 560 74 55"
        )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("addinfo", addinfo))
    app.add_handler(CommandHandler("showinfo", showinfo))
    app.add_handler(CommandHandler("delinfo", delinfo))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

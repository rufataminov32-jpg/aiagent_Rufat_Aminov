import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Siz "MatbaaPaper | KartonWorks" kompaniyasining HR onboarding assistentidasiz. Ismingiz "Rufat Aminovning agenti".

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

user_histories = {}


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
            model="claude-3-5-sonnet-20241022",
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=user_histories[uid],
        )
        reply = response.content[0].text
        user_histories[uid].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(
            "⚠️ Xatolik yuz berdi. Qayta urinib ko'ring.\n"
            "Muammo davom etsa: +998 99 560 74 55"
        )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

import os
import io
import base64
import logging
import fitz
from docx import Document
import openpyxl
from pptx import Presentation
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel("gemini-2.0-flash")

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
- Markdown sarlavhalar (###, ##, #) ishlatma — oddiy matn yoz
- Bilmagan savolda: Aminov Rufat +998 99 560 74 55
- Har javob oxirida boshqa savol borligini so'ra"""

extra_knowledge = []
user_histories = {}

def get_system_prompt():
    if extra_knowledge:
        extras = "\n\n=== QOSHIMCHA BILIMLAR ===\n" + "\n".join(
            f"{i+1}. {item}" for i, item in enumerate(extra_knowledge)
        )
        return BASE_PROMPT + extras
    return BASE_PROMPT

def is_admin(user_id):
    return user_id == ADMIN_ID

def extract_pdf(data):
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def extract_docx(data):
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extract_xlsx(data):
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    lines = []
    for sheet in wb.worksheets:
        lines.append(f"[{sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            row_text = " | ".join(str(c) for c in row if c is not None)
            if row_text:
                lines.append(row_text)
    return "\n".join(lines)

def extract_pptx(data):
    prs = Presentation(io.BytesIO(data))
    lines = []
    for i, slide in enumerate(prs.slides, 1):
        lines.append(f"[Slayd {i}]")
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                lines.append(shape.text)
    return "\n".join(lines)

def gemini_chat(uid, user_text):
    history = user_histories.get(uid, [])
    prompt = get_system_prompt() + "\n\n"
    for msg in history[-10:]:
        role = "Foydalanuvchi" if msg["role"] == "user" else "Siz"
        prompt += f"{role}: {msg['content']}\n"
    prompt += f"Foydalanuvchi: {user_text}\nSiz:"
    response = gemini.generate_content(prompt)
    return response.text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_histories[update.effective_user.id] = []
    await update.message.reply_text(
        "Assalomu alaykum! MatbaaPaper | KartonWorks ga xush kelibsiz!\n\n"
        "Men Rufat Aminovning agenti — onboarding jarayonida sizga ko'maklashaman.\n\n"
        "Savolingizni yozing yoki fayl yuboring (PDF, Word, Excel, PowerPoint, rasm)"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Nima so'rash mumkin:\n\n"
        "Qanday hujjatlar kerak?\n"
        "Ish vaqti va tartib\n"
        "Ish haqi qachon to'lanadi?\n"
        "Kompaniya haqida\n"
        "HR kontakt\n\n"
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
        await update.message.reply_text("Ishlatish: /delinfo <raqam>")
        return
    try:
        index = int(context.args[0]) - 1
        removed = extra_knowledge.pop(index)
        await update.message.reply_text(f"Ochirildi:\n{removed}")
    except (ValueError, IndexError):
        await update.message.reply_text("Notogri raqam.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Sizning ID: {update.effective_user.id}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    fname = doc.file_name.lower()

    if doc.mime_type in ["image/jpeg", "image/png", "image/jpg"]:
        await handle_image(update, context)
        return

    if not any(fname.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]):
        await update.message.reply_text("Qabul qilinadigan formatlar: PDF, Word, Excel, PowerPoint, JPEG, PNG")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("Fayl o'qilmoqda...")

    try:
        file = await doc.get_file()
        data = bytes(await file.download_as_bytearray())

        if fname.endswith(".pdf"):
            text = extract_pdf(data)
        elif fname.endswith((".doc", ".docx")):
            text = extract_docx(data)
        elif fname.endswith((".xls", ".xlsx")):
            text = extract_xlsx(data)
        elif fname.endswith((".ppt", ".pptx")):
            text = extract_pptx(data)
        else:
            text = ""

        if not text.strip():
            await update.message.reply_text("Faylda matn topilmadi.")
            return

        uid = update.effective_user.id
        if uid not in user_histories:
            user_histories[uid] = []

        caption = update.message.caption or "Ushbu faylni tahlil qil va asosiy ma'lumotlarni tushuntir."
        prompt = get_system_prompt() + f"\n\n[Fayl: {doc.file_name}]\n{text[:8000]}\n\nSavol: {caption}"
        response = gemini.generate_content(prompt)
        reply = response.text
        user_histories[uid].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Fayl xatosi: {e}")
        await update.message.reply_text("Faylni o'qishda xatolik. Qayta urinib ko'ring.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1] if update.message.photo else None
    doc = update.message.document

    if doc and doc.mime_type in ["image/jpeg", "image/png", "image/jpg"]:
        file = await doc.get_file()
        mime = doc.mime_type
    elif photo:
        file = await photo.get_file()
        mime = "image/jpeg"
    else:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("Rasm tahlil qilinmoqda...")

    try:
        data = bytes(await file.download_as_bytearray())
        caption = update.message.caption or "Ushbu rasmni tahlil qil."
        image_part = {"mime_type": mime, "data": data}
        response = gemini.generate_content([get_system_prompt() + "\n\n" + caption, image_part])
        reply = response.text
        uid = update.effective_user.id
        if uid not in user_histories:
            user_histories[uid] = []
        user_histories[uid].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Rasm xatosi: {e}")
        await update.message.reply_text("Rasmni o'qishda xatolik. Qayta urinib ko'ring.")

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
        reply = gemini_chat(uid, text)
        user_histories[uid].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
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
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

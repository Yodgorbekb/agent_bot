import os
import logging
import random
import asyncio
import urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from groq import Groq
# main.py ning eng tepasiga ushbu importni qo'shing:
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Bot ishlamoqda!"


def run_flask():
    app.run(host='0.0.0.0', port=8080)
# ---------------------------------------------------------
# SOZLAMALAR (O'z ma'lumotlaringizni kiriting)
# ---------------------------------------------------------
BOT_TOKEN = "7780892612:AAH7Ttx-Lg9wUqcgj684gStlcaF7jBNazYc"
GROQ_API_KEY = "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"
CHANNEL_ID = "@yodgorbek_dev"  # Masalan: @my_tech_channel yoki -100123456789
ADMIN_ID = 7325994091  # Telegram ID ingiz (Faqat sizga javob berishi uchun)

# Post tashlash intervali (sekundlarda): 2 soat = 7200 sekund
POST_INTERVAL_SECONDS = 40  #7200

# Kanalingiz yoki botingiz imzosi (Post oxirida chiqadi)
AUTHOR_SIGNATURE = "✍️ <b>Muallif:</b> <a href='https://t.me/yodgorbek_dev'>BOLTAYEV</a>"

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Groq va Bot obyektlari
groq_client = Groq(api_key=GROQ_API_KEY)

# Bot holati (Ishlayaptimi yoki pauzadamimi)
is_active = False
post_task = None


# ---------------------------------------------------------
# POST VA RASM GENERATSIYA QILISH FUNKSIYASI
# ---------------------------------------------------------
async def generate_and_send_post(app_bot):
    try:
        logger.info("Yangi post generatsiya qilinmoqda...")

        # 1. Har gal har xil mavzuni tasodifiy (random) tanlaymiz
        topics = [
            "Linux internals va Bash terminal hiylalari",
            "SQL va PostgreSQL so'rovlarini optimizatsiya qilish (Indexing, EXPLAIN ANALYZE)",
            "Pentesting, Kiberxavfsizlik va Web zaifliklar (OWASP Top 10)",
            "Backend arxitekturasi va REST API / gRPC dizayni",
            "Python, Django va FastAPI chuqur va amaliy insaytlari",
            "Git, Docker va CI/CD devops texnikalari",
            "Sun'iy intellekt, LLM va Machine Learning amaliyotlari",
            "Asinxron dasturlash va Ko'p oqimlilik (Concurrency/Multithreading)",
        ]
        selected_topic = random.choice(topics)

        # 2. Groq'dan Telegram HTML formatida post va INGILIZCHA prompt olish
        system_prompt = (
            "Siz IT va dasturlash bo'yicha professional muhandissiz.\n"
            "Kanalingiz uchun o'zbek tilida juda foydali, aniq va ortiqcha 'suv'siz (behuda kirish gaplarisiz) post tayyorlang.\n\n"
            "TALABLAR:\n"
            "1. Quruq kirish gaplarini tashlab yuboring ('Bugungi kunda...', 'Hammamizga ma'lumki...' YOZILMASIN).\n"
            "2. Darhol asosiy texnik insayt, amaliy kod/buyruq va maslahat bilan boshlang.\n"
            "3. Matn o'rtacha uzunlikda bo'lsin (1 daqiqalik o'qish uchun).\n"
            "4. Telegram HTML teglari ishlatilsin:\n"
            "   - Sarlavha: <b>Sarlavha Matni</b>\n"
            "   - Muhim tushunchalar: <b>bold</b> yoki <i>italic</i>\n"
            "   - Sintaksis, terminal buyruqlari yoki kod parchasi uchun: <code>buyruq/kod</code> yoki <pre>kod bloki</pre>\n"
            "   - Emotikonlardan unumli foydalaning.\n"
            "5. POST MATNIGA MOS TARZDA rasm yaratish uchun ingliz tilida juda aniq va batafsil prompt yozing.\n"
            "6. Javobingizni faqat ushbu formatda bering:\n"
            "POST_START\n"
            "[HTML formatdagi post matni]\n"
            "POST_END\n"
            "PROMPT_START\n"
            "[Rasm uchun inglizcha prompt, masalan: 8k resolution photorealistic 3d render related to the topic]\n"
            "PROMPT_END"
        )

        user_prompt = f"Aynan ushbu mavzuda juda qiziqarli va foydali insayt yozib ber: '{selected_topic}'"

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,  # Har xil va ijodiyroq javoblar berishi uchun 0.8 ga oshirildi
        )

        response_text = completion.choices[0].message.content

        # Post va Promptni ajratib olish
        if "POST_START" in response_text and "PROMPT_START" in response_text:
            post_content = (
                response_text.split("POST_START")[1].split("POST_END")[0].strip()
            )
            image_prompt = (
                response_text.split("PROMPT_START")[1]
                .split("PROMPT_END")[0]
                .strip()
            )
        else:
            post_content = (
                f"<b>🤖 {selected_topic}</b>\n\nTexnologik yangiliklar va amaliy insaytlar!"
            )
            image_prompt = f"cybersecurity technology programming concept 8k render {selected_topic}"

        # Post oxiriga muallif imzosini qo'shish
        final_caption = f"{post_content}\n\n{AUTHOR_SIGNATURE}"

        # 3. Pollinations.ai orqali xar safar MUTLAQO YANGI rasm generatsiya qilish
        # seed parametringiz rasmni keshlashini oldini oladi va har gal yangi shakl beradi
        random_seed = random.randint(1, 999999)
        encoded_prompt = urllib.parse.quote(image_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&seed={random_seed}&nologo=true"

        # Telegram Caption limiti HTML teglar bilan 1024 ta belgi.
        if len(final_caption) > 1024:
            final_caption = final_caption[:950] + "...\n\n" + AUTHOR_SIGNATURE

        # 4. Rasm va matnni bitta post qilib kanalga yuborish
        await app_bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=image_url,
            caption=final_caption,
            parse_mode=ParseMode.HTML,
        )
        logger.info(
            f"Post ({selected_topic}) muvaffaqiyatli kanalga joylandi!"
        )

    except Exception as e:
        logger.error(f"Post yaratishda xatolik yuz berdi: {e}")


# ---------------------------------------------------------
# AVTOMATIK SIKL (PERIODIC LOOP)
# ---------------------------------------------------------
async def periodic_post_loop(app_bot):
    global is_active
    while is_active:
        await generate_and_send_post(app_bot)
        await asyncio.sleep(POST_INTERVAL_SECONDS)


# ---------------------------------------------------------
# BOT TUGMALARI VA BUYRUQLARI
# ---------------------------------------------------------
def get_control_keyboard():
    status_emoji = "🟢 Ishlamoqda" if is_active else "🔴 To'xtatilgan (Pauza)"
    action_button = (
        InlineKeyboardButton("⏹ To'xtatish (Pauza)", callback_data="stop_bot")
        if is_active
        else InlineKeyboardButton("▶️ Ishga tushirish", callback_data="start_bot")
    )
    test_button = InlineKeyboardButton("⚡️ Hozir post tashlash (Test)", callback_data="test_post")

    keyboard = [
        [action_button],
        [test_button]
    ]
    return InlineKeyboardMarkup(keyboard), status_emoji


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Faqat ADMIN ID ga javob beradi
    if update.effective_user.id != ADMIN_ID:
        return

    reply_markup, status_emoji = get_control_keyboard()
    await update.message.reply_text(
        f"<b>🤖 Kanal Avto-Post Boti Boshqaruvi</b>\n\n"
        f"<b>Joriy holat:</b> {status_emoji}\n"
        f"<b>Interval:</b> Har {POST_INTERVAL_SECONDS // 3600} soatda\n\n"
        f"Tugmalar orqali botni boshqaring:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    global is_active, post_task

    if query.data == "start_bot":
        if not is_active:
            is_active = True
            post_task = asyncio.create_task(periodic_post_loop(context.bot))
            await query.edit_message_text(
                "✅ <b>Bot ishga tushirildi!</b> Endi har 2 soatda avtomatik post tashlanadi.",
                reply_markup=get_control_keyboard()[0],
                parse_mode=ParseMode.HTML
            )

    elif query.data == "stop_bot":
        if is_active:
            is_active = False
            if post_task:
                post_task.cancel()
                post_task = None
            await query.edit_message_text(
                "⏸ <b>Bot to'xtatildi (Pauza).</b> Yangi postlar yuborilmaydi.",
                reply_markup=get_control_keyboard()[0],
                parse_mode=ParseMode.HTML
            )

    elif query.data == "test_post":
        await query.message.reply_text("⏳ Test post generatsiya qilinmoqda, kuting...")
        await generate_and_send_post(context.bot)
        await query.message.reply_text("✅ Test post kanalga yuborildi!")


# ---------------------------------------------------------
# MAIN ASYNC ASOSIY QISM
# ---------------------------------------------------------
if __name__ == "__main__":
    # Flask veb-serverni orqa fonda yurgizish (Render Web Service o'chirib qo'ymasligi uchun)
    t = Thread(target=run_flask)
    t.start()

    # Botni ishga tushirish
    main()

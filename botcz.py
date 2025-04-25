import asyncio
from flask import Flask, request
import stripe
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta
import json
import os
from threading import Thread

# Nastavení
TOKEN = "7531757455:AAHz4VHlgmU3RaJzEMLP4JpQ4pFaVbdX8W0"
BASE_PAYMENT_LINK = "https://buy.stripe.com/test_7sIbLF7vc7Dk3ao000"
STRIPE_SECRET_KEY = "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"
STRIPE_ENDPOINT_SECRET = "whsec_lkEVY53mQgIYTBUbh2TKKPiDyZV9Jaik"
GROUP_ID = -4732979925
PREMIUM_DB = "premium_data.json"

# Inicializace Flask + Telegram bota
app = Flask(__name__)
bot = Bot(token=TOKEN)
stripe.api_key = STRIPE_SECRET_KEY

# 📬 /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context, update.effective_chat.id)

# 📦 Funkce pro hlavní menu
async def send_main_menu(update, context, chat_id):
    text = """👋 *Vítej v AD-Trading!*

📥 Pro *bezplatný přístup k signálům* napiš:  
/register

💎 Pro vstup do *PREMIUM zóny* s obchodními signály, mentoringem a dalšími výhodami napiš:  
/premium

❓ Pokud si nebudeš s něčím vědět rady, napiš:  
/pomoc nebo nás kontaktuj přes /kontakt

Těšíme se na společnou spolupráci a přejeme ti mnoho úspěchů v obchodování! 📈💼"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Register", callback_data="register")],
        [InlineKeyboardButton("💎 Premium", callback_data="premium")],
        [InlineKeyboardButton("🆘 Pomoc", callback_data="pomoc")],
        [InlineKeyboardButton("📲 Kontakt", callback_data="kontakt")]
    ])

    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=keyboard)

# 🔁 Callback tlačítka
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "kontakt":
        text = """📞 *KONTAKTUJ NÁS*

📩 E-mail: info@ad-trading.cz  
🌐 Web: www.ad-trading.cz  
📲 Instagram: @ad-trading.cz"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Zpět", callback_data="zpet")]
        ])
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif query.data == "premium":
        user_id = query.from_user.id
        personalized_link = f"{BASE_PAYMENT_LINK}?client_reference_id={user_id}"

        text = """💎 *AD-Trading Premium*

Získej přístup do Premium členské sekce:
- Obchodní signály
- Mentoring
- Extra obsah

👇 Klikni na tlačítko níže pro platbu:"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Zaplatit Premium", url=personalized_link)],
            [InlineKeyboardButton("🔙 Zpět", callback_data="zpet")]
        ])

        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif query.data == "zpet":
        await send_main_menu(update, context, query.message.chat_id)

# 🌐 Webhook příjem
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature", None)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_ENDPOINT_SECRET)
    except Exception as e:
        return f"Webhook error: {e}", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        telegram_user_id = session.get("client_reference_id")

        if telegram_user_id:
            try:
                # Přidání do skupiny
                bot.add_chat_members(chat_id=GROUP_ID, user_ids=[int(telegram_user_id)])

                # Uložení expirace
                expiry = datetime.now() + timedelta(days=30)
                if os.path.exists(PREMIUM_DB):
                    with open(PREMIUM_DB, "r") as f:
                        data = json.load(f)
                else:
                    data = {}
                data[str(telegram_user_id)] = expiry.isoformat()
                with open(PREMIUM_DB, "w") as f:
                    json.dump(data, f)

                print(f"✅ Uživateli {telegram_user_id} bylo aktivováno členství Premium.")
            except Exception as e:
                print(f"❌ Chyba při přidávání do skupiny: {e}")
        else:
            print("⚠️ Chybí client_reference_id")

    return "", 200

# ▶️ Spuštění bota a Flask serveru v paralelních vláknech

def run_bot():
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button_callback))
    print("🤖 Bot běží... a webhook server taky 🔥")
    app_bot.run_polling()

if __name__ == "__main__":
    # Spustí Flask ve vlákně
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=4242))
    flask_thread.start()

    # Spustí bota
    run_bot()

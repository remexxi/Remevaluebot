import os
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

SUREBET_TOKEN = os.getenv('SUREBET_API_TOKEN')
BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = "https://api.apostasseguras.com"
MIN_VALUE = 0.0
CHECK_INTERVAL = 60

ya_enviadas = set()
chats_activos = set()

def fetch_valuebets():
    if not SUREBET_TOKEN:
        return []
    try:
        r = requests.get(
            f"{BASE_URL}/request",
            params={
                "product": "valuebets",
                "source": "pinnaclesports|retabet_apuestas|unibet_au|winamax_es",
                "sport": "Football|Tennis|Basketball"
            },
            headers={"Authorization": f"Bearer {SUREBET_TOKEN}"},
            timeout=30
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("records", [])
        return []
    except:
        return []

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats_activos.add(update.effective_chat.id)
    await update.message.reply_text(f"✅ Activado. Te avisaré de valuebets ≥ {MIN_VALUE}%.")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats_activos.discard(update.effective_chat.id)
    await update.message.reply_text("⛔ Alertas desactivadas.")

async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = fetch_valuebets()
    await update.message.reply_text(f"Registros encontrados: {len(data)}\n\nPrimero:\n{str(data[0])[:2000] if data else 'Vacío'}")

async def check_valuebets(app):
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        if not chats_activos:
            continue
        for item in fetch_valuebets():
            try:
                value = float(item.get("overvalue", 0))
            except:
                continue
            if value < MIN_VALUE:
                continue
            prongs = item.get("prongs", [])
            teams = prongs[0].get("teams", []) if prongs else []
            event = " vs ".join(teams) if teams else "Sin nombre"
            key = f"{event}_{value}"
            if key in ya_enviadas:
                continue
            ya_enviadas.add(key)
            casa = prongs[0].get("bk", "N/A") if prongs else "N/A"
            cuota = prongs[0].get("value", "?") if prongs else "?"
            t = prongs[0].get("type", {}) if prongs else {}
            mercado = f"{t.get('variety', '')} {t.get('type', '')} {t.get('condition', '')}".strip()
            for chat_id in chats_activos:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"📈 *VALUEBET*\n\n📊 {event}\n🏦 {casa} @{cuota}\n📋 Mercado: {mercado}\n💰 Value: *{value}%*",
                        parse_mode="Markdown"
                    )
                except:
                    pass

async def post_init(app):
    asyncio.create_task(check_valuebets(app))

if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("test", cmd_test))
    print("🤖 Bot de valuebets iniciado correctamente")
    app.run_polling()

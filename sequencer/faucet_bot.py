import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Continuum Network Telegram Faucet Bot Token
BOT_TOKEN = "8947007755:AAFolOQ7E24tRzWHHi0Mtkxeu1q9FNUmOzE"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Render Web Service sağlık kontrolü (Health Check) için arka plan HTTP sunucusu
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Continuum Faucet Bot is Active!")

    def log_message(self, format, *args):
        return

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚡ *Continuum Network ($CTM) Testnet Faucet*\n\n"
        "Welcome to the official Continuum L2 Faucet Bot!\n"
        "To request 100 Testnet $CTM tokens, send your EVM wallet address:\n\n"
        "`/faucet YOUR_EVM_ADDRESS`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def faucet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide a valid wallet address.\nExample: `/faucet 0x123...`", parse_mode="Markdown")
        return
    
    wallet_address = context.args[0]
    
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        await update.message.reply_text("❌ Invalid EVM wallet address format. Make sure it starts with `0x` and is 42 characters long.")
        return
    
    response_text = (
        f"✅ *100 $CTM Sent Successfully!*\n\n"
        f"👤 *Recipient:* `{wallet_address}`\n"
        f"🔥 *Gas Fee:* 0 $ETH (Sponsored by Token-Paymaster)\n"
        f"🌐 *Explorer:* https://continuum-explorer.streamlit.app"
    )
    await update.message.reply_text(response_text, parse_mode="Markdown")

if __name__ == '__main__':
    # Render'ın botu kapatmaması için HTTP portunu arka planda başlatıyoruz
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("faucet", faucet))
    print("Continuum Faucet Bot active on Render Web Service...")
    app.run_polling()

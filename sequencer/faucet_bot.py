import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. RENDER PORT HEALTH CHECK (Render'ın Botu Kapatmasını Önler) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Continuum Faucet Bot is Alive!")

def start_health_check_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Health Check server listening on port {port}")
    server.serve_forever()

# Background Thread Olarak Portu Başlat
threading.Thread(target=start_health_check_server, daemon=True).start()

# --- 2. BOT KONFİGÜRASYONU ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PAYMASTER_PRIVATE_KEY = os.getenv("PAYMASTER_PRIVATE_KEY")
BASE_SEPOLIA_RPC = "https://sepolia.base.org"

CONTRACT_ADDRESS = "0x078712Ac537F24B76a1AAB05624c02A9E0a28C13"

w3 = Web3(Web3.HTTPProvider(BASE_SEPOLIA_RPC))

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]

contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ERC20_ABI)
faucet_history = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚡ *Continuum Network ($CTM) Testnet Faucet Bot*\n\n"
        "Welcome to Continuum L2 Testnet! You can request testnet $CTM tokens to participate in "
        "gasless transactions and explore the ecosystem.\n\n"
        "📌 *Command:* `/faucet <YOUR_WALLET_ADDRESS>`\n"
        "⏱ *Limit:* 100 CTM per address every 24 hours."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def faucet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide a wallet address.\nExample: `/faucet 0x123...`", parse_mode="Markdown")
        return

    user_address = context.args[0]
    if not w3.is_address(user_address):
        await update.message.reply_text("❌ Invalid Ethereum address! Check and try again.")
        return

    user_address = Web3.to_checksum_address(user_address)
    now = datetime.now()

    if user_address in faucet_history:
        last_claim = faucet_history[user_address]
        if now - last_claim < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_claim)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await update.message.reply_text(f"⏳ Cooldown active! Try again in {hours}h {minutes}m.")
            return

    if not PAYMASTER_PRIVATE_KEY:
        await update.message.reply_text("⚠️ Faucet wallet key not set on server. Testnet distribution paused.")
        return

    try:
        faucet_account = w3.eth.account.from_key(PAYMASTER_PRIVATE_KEY)
        amount = 100 * (10 ** 18)

        tx = contract.functions.transfer(user_address, amount).build_transaction({
            'from': faucet_account.address,
            'nonce': w3.eth.get_transaction_count(faucet_account.address),
            'gas': 100000,
            'maxFeePerGas': w3.to_wei('2', 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei('1', 'gwei'),
            'chainId': 84532
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PAYMASTER_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        faucet_history[user_address] = now

        await update.message.reply_text(
            f"✅ *100 $CTM Successfully Sent!*\n\n"
            f"👤 *Recipient:* `{user_address}`\n"
            f"🔗 *Tx Hash:* [View on Basescan](https://sepolia.basescan.org/tx/{tx_hash.hex()})",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Transaction failed: {str(e)}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ HATA: TELEGRAM_BOT_TOKEN Render paneline eklenmemiş!")
        return
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("faucet", faucet))
    print("🤖 Faucet Bot başarıyla çalıştırıldı ve dinliyor...")
    app.run_polling()

if __name__ == "__main__":
    main()

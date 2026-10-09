import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. RENDER PORT HEALTH CHECK ---
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

threading.Thread(target=start_health_check_server, daemon=True).start()

# --- 2. BOT KONFİGÜRASYONU ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PAYMASTER_PRIVATE_KEY = os.getenv("PAYMASTER_PRIVATE_KEY")
BASE_SEPOLIA_RPC = "https://sepolia.base.org"

# Kanal Katılım Ayarları
REQUIRED_CHANNEL = "@ContinuumAnnouncements"
CHANNEL_LINK = "https://t.me/ContinuumAnnouncements"

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

# Cooldown geçmişi: Hem Telegram User ID hem de Adres bazlı takip
user_cooldowns = {}
address_cooldowns = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "⚡ <b>Continuum Network ($CTM) Testnet Faucet Bot</b>\n\n"
        "Welcome to Continuum L2 Testnet! You can request testnet $CTM tokens to participate in "
        "gasless transactions and explore the ecosystem.\n\n"
        f"📢 <b>Join Channel:</b> <a href='{CHANNEL_LINK}'>{CHANNEL_LINK}</a>\n"
        "📌 <b>Command:</b> <code>/faucet &lt;YOUR_WALLET_ADDRESS&gt;</code>\n"
        "⏱ <b>Limit:</b> 100 CTM per user/address every 24 hours."
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML", disable_web_page_preview=True)

def execute_transfer_sync(user_address: str, amount: int):
    """Web3 transferini gerçekleştirir ve blokzincir onayını bekler."""
    faucet_account = w3.eth.account.from_key(PAYMASTER_PRIVATE_KEY)

    # 1. Faucet Cüzdanındaki CTM Bakiyesini Kontrol Et
    faucet_balance = contract.functions.balanceOf(faucet_account.address).call()
    if faucet_balance < amount:
        raise Exception("Faucet cüzdanında yeterli $CTM kalmadı! Lütfen yöneticinizle iletişime geçin.")

    nonce = w3.eth.get_transaction_count(faucet_account.address, 'pending')

    tx = contract.functions.transfer(user_address, amount).build_transaction({
        'from': faucet_account.address,
        'nonce': nonce,
        'gas': 100000,
        'maxFeePerGas': w3.to_wei('2', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('1', 'gwei'),
        'chainId': 84532
    })

    signed_tx = w3.eth.account.sign_transaction(tx, PAYMASTER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    # 2. Blokzincir Onayını Bekle (Timeout: 30 sn)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    if receipt.status != 1:
        raise Exception("İşlem ağda gönderildi fakat başarısız oldu (Reverted). Faucet cüzdanının Sepolia ETH gaz bakiyesini kontrol edin.")

    tx_hash_hex = tx_hash.hex()
    return tx_hash_hex if tx_hash_hex.startswith("0x") else f"0x{tx_hash_hex}"

async def faucet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id

    # 1. Telegram Kanal Katılım Kontrolü
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=tg_user_id)
        if member.status in ['left', 'kicked', 'banned']:
            await update.message.reply_text(
                f"🚀 <b>To use this bot, you must join our channel first:</b>\n<a href='{CHANNEL_LINK}'>{CHANNEL_LINK}</a>",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return
    except Exception as e:
        print(f"Kanal kontrol hatası (Bot kanalda admin mi?): {e}")

    if not context.args:
        await update.message.reply_text("❌ Please provide a wallet address.\nExample: <code>/faucet 0x123...</code>", parse_mode="HTML")
        return

    raw_address = context.args[0].strip()
    
    # Asenkron Adres Doğrulama
    is_valid = await asyncio.to_thread(w3.is_address, raw_address)
    if not is_valid:
        await update.message.reply_text("❌ Invalid Ethereum address! Check and try again.")
        return

    user_address = Web3.to_checksum_address(raw_address)
    now = datetime.now()

    # 2. Telegram Kullanıcısı Cooldown Kontrolü
    if tg_user_id in user_cooldowns:
        last_claim = user_cooldowns[tg_user_id]
        if now - last_claim < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_claim)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await update.message.reply_text(f"⏳ Cooldown active for your account! Try again in {hours}h {minutes}m.")
            return

    # 3. Cüzdan Adresi Cooldown Kontrolü
    if user_address in address_cooldowns:
        last_claim = address_cooldowns[user_address]
        if now - last_claim < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_claim)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await update.message.reply_text(f"⏳ Cooldown active for this wallet address! Try again in {hours}h {minutes}m.")
            return

    if not PAYMASTER_PRIVATE_KEY:
        await update.message.reply_text("⚠️ Faucet wallet key not set on server. Testnet distribution paused.")
        return

    msg = await update.message.reply_text("⏳ Processing transaction on Base Sepolia...")

    try:
        amount = 100 * (10 ** 18)
        # Web3 transferini bloklama yapmadan asenkron çalıştırır ve onay bekler
        tx_hash_str = await asyncio.to_thread(execute_transfer_sync, user_address, amount)

        user_cooldowns[tg_user_id] = now
        address_cooldowns[user_address] = now

        await msg.edit_text(
            f"✅ <b>100 $CTM Successfully Sent!</b>\n\n"
            f"👤 <b>Recipient:</b> <code>{user_address}</code>\n"
            f"🔗 <b>Tx Hash:</b> <a href='https://sepolia.basescan.org/tx/{tx_hash_str}'>View on Basescan</a>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Faucet error: {e}")
        await msg.edit_text(f"❌ Transaction failed: {str(e)}")

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

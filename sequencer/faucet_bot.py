import os
import json
import random
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from web3 import Web3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- 1. CONFIGURATION & ENVIRONMENT ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PAYMASTER_PRIVATE_KEY = os.getenv("PAYMASTER_PRIVATE_KEY")
BASE_SEPOLIA_RPC = "https://sepolia.base.org"

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

user_cooldowns = {}
address_cooldowns = {}

# --- REFERRAL, GAME & LEADERBOARD DATA ENGINE ---
DATA_FILE = "referrals.json"

def load_ref_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}, "referred_by": {}}

def save_ref_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Kayıt hatası: {e}")

# --- 2. RENDER HEALTH CHECK, PAYMASTER & GAME API SERVER ---
class PaymasterRelayerHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        if parsed_url.path == "/api/leaderboard":
            data = load_ref_data()
            users = data.get("users", {})
            leaderboard = []
            for uid, info in users.items():
                leaderboard.append({
                    "user_id": uid,
                    "username": info.get("username", "Anonim"),
                    "points": info.get("points", 0),
                    "referrals": info.get("referrals_count", 0)
                })
            leaderboard.sort(key=lambda x: x["points"], reverse=True)
            self._set_headers(200)
            self.wfile.write(json.dumps({"success": True, "leaderboard": leaderboard[:100]}).encode())

        elif parsed_url.path == "/api/user-info":
            user_id = query_params.get("user_id", [None])[0]
            db = load_ref_data()
            users = db.get("users", {})
            referred_by = db.get("referred_by", {})

            if user_id and user_id in users:
                u_info = users[user_id]
                my_friends = []
                for uid, ref_id in referred_by.items():
                    if ref_id == user_id and uid in users:
                        my_friends.append({
                            "username": users[uid].get("username", "Anonim"),
                            "points": users[uid].get("points", 0),
                            "wallet": users[uid].get("wallet_address", "Henüz Cüzdan Aktif Değil")
                        })
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "success": True,
                    "points": u_info.get("points", 0),
                    "referrals_count": u_info.get("referrals_count", 0),
                    "friends": my_friends
                }).encode())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"success": False, "error": "Kullanıcı bulunamadı."}).encode())

        elif parsed_url.path == "/api/resolve":
            username = query_params.get("username", [None])[0]
            if username:
                clean_name = username.replace("@", "").strip().lower()
                db = load_ref_data()
                users = db.get("users", {})
                found_address = None
                for uid, info in users.items():
                    if info.get("username", "").lower() == clean_name:
                        found_address = info.get("wallet_address")
                        break
                if found_address:
                    self._set_headers(200)
                    self.wfile.write(json.dumps({"success": True, "address": found_address}).encode())
                    return
            self._set_headers(404)
            self.wfile.write(json.dumps({"success": False, "error": "Kullanıcı adı bulunamadı veya cüzdanı kayıtlı değil."}).encode())
        else:
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "ok", "message": "Continuum Game & Paymaster API Active!"}).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'

        if self.path == "/api/register-wallet":
            try:
                data = json.loads(post_data.decode('utf-8'))
                tg_id = str(data.get("user_id"))
                wallet_addr = data.get("wallet_address")
                username = data.get("username", "Anonim")

                db = load_ref_data()
                users = db.setdefault("users", {})
                if tg_id not in users:
                    users[tg_id] = {"username": username, "points": 10, "referrals_count": 0}

                if wallet_addr and Web3.is_address(wallet_addr):
                    users[tg_id]["wallet_address"] = Web3.to_checksum_address(wallet_addr)
                    if username and username != "Anonim":
                        users[tg_id]["username"] = username
                    save_ref_data(db)
                    self._set_headers(200)
                    self.wfile.write(json.dumps({"success": True, "message": "Cüzdan başarıyla eşlendi."}).encode())
                else:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"success": False, "error": "Geçersiz cüzdan adresi."}).encode())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/farm":
            try:
                data = json.loads(post_data.decode('utf-8'))
                tg_id = str(data.get("user_id"))
                db = load_ref_data()
                users = db.get("users", {})

                if tg_id in users:
                    now = datetime.now()
                    last_farm_str = users[tg_id].get("last_farm", "")
                    
                    can_farm = True
                    if last_farm_str:
                        last_farm = datetime.fromisoformat(last_farm_str)
                        if now - last_farm < timedelta(hours=8):
                            can_farm = False

                    if can_farm:
                        gained = 100
                        users[tg_id]["points"] = users[tg_id].get("points", 0) + gained
                        users[tg_id]["last_farm"] = now.isoformat()
                        save_ref_data(db)
                        self._set_headers(200)
                        self.wfile.write(json.dumps({"success": True, "message": "+100 Puan Toplandı!", "new_points": users[tg_id]["points"]}).encode())
                    else:
                        self._set_headers(400)
                        self.wfile.write(json.dumps({"success": False, "error": "Henüz farming süren dolmadı (8 saat)!"}).encode())
                else:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"success": False, "error": "Kullanıcı bulunamadı."}).encode())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/send-chest":
            try:
                data = json.loads(post_data.decode('utf-8'))
                sender_id = str(data.get("sender_id"))
                user_address = data.get("user_address")

                if user_address:
                    bal = contract.functions.balanceOf(Web3.to_checksum_address(user_address)).call() / (10**18)
                    if bal < 100:
                        self._set_headers(400)
                        self.wfile.write(json.dumps({"success": False, "error": "Şans sandığı gönderebilmek için en az 100 $CTM bakiyeniz olmalıdır!"}).encode())
                        return

                db = load_ref_data()
                users = db.get("users", {})

                if sender_id in users:
                    reward = random.randint(25, 300)
                    users[sender_id]["points"] = users[sender_id].get("points", 0) + reward
                    save_ref_data(db)

                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "success": True, 
                        "message": f"🎁 Şans Sandığı Başarıyla Açıldı! +{reward} Puan Kazandınız!",
                        "new_points": users[sender_id]["points"]
                    }).encode())
                else:
                    self._set_headers(404)
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

        elif self.path == "/api/sponsor-gas":
            try:
                data = json.loads(post_data.decode('utf-8'))
                user_address = Web3.to_checksum_address(data.get("userAddress"))

                sender_balance = contract.functions.balanceOf(user_address).call()
                sender_ctm = sender_balance / (10**18)

                if sender_ctm < 100:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"success": False, "error": "Paymaster gaz desteği için cüzdanınızda en az 100 $CTM bulunmalıdır!"}).encode())
                    return

                if not PAYMASTER_PRIVATE_KEY:
                    self._set_headers(500)
                    self.wfile.write(json.dumps({"success": False, "error": "Sunucuda Paymaster Private Key tanımlı değil."}).encode())
                    return

                user_eth_balance = w3.eth.get_balance(user_address)
                
                if user_eth_balance < w3.to_wei(0.0003, 'ether'):
                    paymaster_account = w3.eth.account.from_key(PAYMASTER_PRIVATE_KEY)
                    nonce = w3.eth.get_transaction_count(paymaster_account.address, 'pending')
                    
                    tx = {
                        'nonce': nonce,
                        'to': user_address,
                        'value': w3.to_wei(0.0005, 'ether'),
                        'gas': 21000,
                        'maxFeePerGas': w3.to_wei('2', 'gwei'),
                        'maxPriorityFeePerGas': w3.to_wei('1', 'gwei'),
                        'chainId': 84532
                    }

                    signed_tx = w3.eth.account.sign_transaction(tx, PAYMASTER_PRIVATE_KEY)
                    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=15)

                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "message": "Gaz sponsorluğu sağlandı."}).encode())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())
        else:
            self._set_headers(404)

def start_health_check_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PaymasterRelayerHandler)
    print(f"🌐 Game & Paymaster Relayer Server {port} portunda aktif!")
    server.serve_forever()

threading.Thread(target=start_health_check_server, daemon=True).start()

# --- 3. TELEGRAM BOT LOGIC ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_user_id = str(user.id)
    username = user.username or user.first_name or "Anonim"

    db = load_ref_data()
    users = db.setdefault("users", {})
    referred_by = db.setdefault("referred_by", {})

    if tg_user_id not in users:
        users[tg_user_id] = {
            "username": username,
            "points": 10,
            "referrals_count": 0
        }

    if context.args and tg_user_id not in referred_by:
        referrer_id = context.args[0].replace("ref_", "").strip()
        if referrer_id != tg_user_id and referrer_id in users:
            referred_by[tg_user_id] = referrer_id
            users[referrer_id]["referrals_count"] += 1
            users[referrer_id]["points"] += 50
            users[tg_user_id]["points"] += 20
            
            try:
                await context.bot.send_message(
                    chat_id=int(referrer_id),
                    text=f"🎉 <b>Yeni Referans!</b>\n<code>@{username}</code> senin linkinle katıldı! +50 Puan kazandın.",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    save_ref_data(db)

    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{tg_user_id}"

    welcome_text = (
        "⚡ <b>Continuum Network ($CTM) Testnet & Game Hub</b>\n\n"
        "Welcome to Continuum L2 Ecosystem! Tap to farm $CTM Points, complete X tasks, send Mystery Chests, and climb the Leaderboard!\n\n"
        f"🎁 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
        f"📊 <b>Your Points:</b> {users[tg_user_id]['points']} PTS | <b>Referrals:</b> {users[tg_user_id]['referrals_count']}\n\n"
        f"📢 <b>Join Channel:</b> <a href='{CHANNEL_LINK}'>{CHANNEL_LINK}</a>\n"
        "📌 <b>Command:</b> <code>/faucet &lt;YOUR_WALLET_ADDRESS&gt;</code>\n"
        "🏆 <b>Leaderboard:</b> <code>/leaderboard</code>"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML", disable_web_page_preview=True)

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_user_id = str(user.id)
    db = load_ref_data()
    u_data = db.get("users", {}).get(tg_user_id, {"points": 0, "referrals_count": 0})

    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{tg_user_id}"

    msg = (
        f"🔗 <b>Your Personal Referral Link:</b>\n<code>{ref_link}</code>\n\n"
        f"🏆 <b>Total Points:</b> {u_data['points']} PTS\n"
        f"👥 <b>Total Invited:</b> {u_data['referrals_count']} Users\n\n"
        "💡 <i>Earn +50 Points for every friend who joins via your link!</i>"
    )
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_ref_data()
    users = db.get("users", {})
    sorted_users = sorted(users.items(), key=lambda x: x[1].get("points", 0), reverse=True)[:10]

    msg = "🏆 <b>Continuum Network — Top 10 Leaderboard</b>\n\n"
    for idx, (uid, info) in enumerate(sorted_users, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        msg += f"{medal} <b>@{info.get('username', 'Anonim')}</b> — {info.get('points', 0)} PTS ({info.get('referrals_count', 0)} Refs)\n"

    await update.message.reply_text(msg, parse_mode="HTML")

def execute_transfer_sync(user_address: str, amount: int):
    faucet_account = w3.eth.account.from_key(PAYMASTER_PRIVATE_KEY)
    faucet_balance = contract.functions.balanceOf(faucet_account.address).call()
    if faucet_balance < amount:
        raise Exception("Faucet cüzdanında yeterli $CTM kalmadı!")

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

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    if receipt.status != 1:
        raise Exception("İşlem ağda gönderildi fakat başarısız oldu (Reverted).")

    tx_hash_hex = tx_hash.hex()
    return tx_hash_hex if tx_hash_hex.startswith("0x") else f"0x{tx_hash_hex}"

async def faucet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Anonim"

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
        print(f"Kanal kontrol hatası: {e}")

    if not context.args:
        await update.message.reply_text("❌ Please provide a wallet address.\nExample: <code>/faucet 0x123...</code>", parse_mode="HTML")
        return

    raw_address = context.args[0].strip()
    
    is_valid = await asyncio.to_thread(w3.is_address, raw_address)
    if not is_valid:
        await update.message.reply_text("❌ Invalid Ethereum address! Check and try again.")
        return

    user_address = Web3.to_checksum_address(raw_address)
    now = datetime.now()

    if tg_user_id in user_cooldowns:
        last_claim = user_cooldowns[tg_user_id]
        if now - last_claim < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_claim)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await update.message.reply_text(f"⏳ Cooldown active for your account! Try again in {hours}h {minutes}m.")
            return

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
        tx_hash_str = await asyncio.to_thread(execute_transfer_sync, user_address, amount)

        user_cooldowns[tg_user_id] = now
        address_cooldowns[user_address] = now

        db = load_ref_data()
        str_uid = str(tg_user_id)
        users = db.setdefault("users", {})
        if str_uid not in users:
            users[str_uid] = {"username": username, "points": 15, "referrals_count": 0}
        
        users[str_uid]["points"] += 15
        users[str_uid]["wallet_address"] = user_address
        save_ref_data(db)

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
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    print("🤖 Faucet Bot, Game Hub & Paymaster Relayer aktif...")
    app.run_polling()

if __name__ == "__main__":
    main()

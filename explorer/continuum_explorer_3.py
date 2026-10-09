import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../sequencer')))
import streamlit as st
import pandas as pd
import time
import requests
from web3 import Web3

# Deployed Base Sepolia Kontrat Adresi
DEPLOYED_CONTRACT_ADDRESS = "0x078712Ac537F24B76a1AAB05624c02A9E0a28C13"
RPC_URL = "https://sepolia.base.org"
BURN_ADDRESS = "0x0000000000000000000000000000000000000000"

try:
    from continuum_network_3 import ContinuumL2Blockchain, CryptoEngine, CONTRACT_ADDRESS, FOUNDER_WALLET_ADDRESS
except ImportError as e:
    st.error(f"⚠️ 'continuum_network_3.py' yüklenirken hata oluştu: {e}")
    st.stop()

# --- STREAMLIT SAYFA AYARI VE TEMA KODLARI ---
st.set_page_config(
    page_title="Continuum Network ($CTM) L2 Explorer",
    page_icon="⚡",
    layout="wide"
)

# Dark Glassmorphism CSS Uygulaması
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
        color: #f8fafc;
    }
    .stApp {
        background-color: #07090e;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        background-color: rgba(255, 255, 255, 0.03);
    }
    </style>
""", unsafe_allow_html=True)

if "l2_chain" not in st.session_state:
    st.session_state.l2_chain = ContinuumL2Blockchain()

l2: ContinuumL2Blockchain = st.session_state.l2_chain

# --- BASE SEPOLIA ZİNCİR ÜSTÜ (ON-CHAIN) CANLI VERİ ÇEKİMİ ---
ERC20_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
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

@st.cache_data(ttl=10) # 10 saniyede bir otomatik veriyi yeniler
def fetch_base_sepolia_data():
    latest_block = None
    total_burned = 0.0
    tx_list = []

    # 1. Web3 ile güncel blok numarası ve yakılan CTM miktarını çek
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if w3.is_connected():
            latest_block = w3.eth.block_number
            contract = w3.eth.contract(address=Web3.to_checksum_address(DEPLOYED_CONTRACT_ADDRESS), abi=ERC20_ABI)
            raw_burned = contract.functions.balanceOf(BURN_ADDRESS).call()
            total_burned = raw_burned / (10**18)
    except Exception:
        pass

    # 2. Basescan API ile Tüm Geçmiş Transfer Hareketlerini Çek (RPC Blok Sınırına Takılmaz)
    try:
        api_url = f"https://api-sepolia.basescan.org/api?module=account&action=tokentx&contractaddress={DEPLOYED_CONTRACT_ADDRESS}&page=1&offset=100&sort=desc"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(api_url, headers=headers, timeout=6)
        data = res.json()

        if data.get("status") == "1" and "result" in data:
            for tx in data["result"]:
                val = float(tx["value"]) / (10**18)
                from_addr = tx["from"]
                to_addr = tx["to"]

                if latest_block is None and "blockNumber" in tx:
                    latest_block = int(tx["blockNumber"])

                tx_list.append({
                    "Tx Hash": tx["hash"],
                    "Blok": int(tx["blockNumber"]),
                    "Gönderen": Web3.to_checksum_address(from_addr),
                    "Alıcı": Web3.to_checksum_address(to_addr),
                    "Miktar ($CTM)": f"{val:,.2f} CTM"
                })
    except Exception:
        pass

    # 3. Fallback: API yanıt vermezse küçük aralıkla RPC'den dene
    if not tx_list and latest_block:
        try:
            w3 = Web3(Web3.HTTPProvider(RPC_URL))
            contract = w3.eth.contract(address=Web3.to_checksum_address(DEPLOYED_CONTRACT_ADDRESS), abi=ERC20_ABI)
            from_block = max(0, latest_block - 2000)
            events = contract.events.Transfer.get_logs(fromBlock=from_block, toBlock='latest')
            for event in reversed(events):
                val = event['args']['value'] / (10**18)
                tx_list.append({
                    "Tx Hash": event['transactionHash'].hex(),
                    "Blok": event['blockNumber'],
                    "Gönderen": event['args']['from'],
                    "Alıcı": event['args']['to'],
                    "Miktar ($CTM)": f"{val:,.2f} CTM"
                })
        except Exception:
            pass

    df = pd.DataFrame(tx_list)
    return latest_block, total_burned, len(tx_list), df

live_block, live_burned, live_tx_count, df_live_tx = fetch_base_sepolia_data()

# --- YAN PANEL (Ağ Durumu & Ekosistem Linkleri) ---
st.sidebar.title("⚡ Continuum L2 Network")
if live_block:
    st.sidebar.caption(f"Ağ Durumu: 🟢 CANLI (Base Sepolia #{live_block})")
else:
    st.sidebar.caption("Ağ Durumu: 🟡 SEQUENCER MODU")

st.sidebar.markdown("---")
st.sidebar.subheader("🌐 Ekosistem & Linkler")

st.sidebar.markdown("🌐 **[Web DApp İstemcisi](https://0xcontinuum.github.io/continuum-network-l2/)**")
st.sidebar.markdown("🤖 **[Testnet Faucet Botu (@ContinuumCTM_bot)](https://t.me/ContinuumCTM_bot)**")
st.sidebar.markdown("📢 **[Telegram Duyuru Kanalı](https://t.me/ContinuumAnnouncements)**")
st.sidebar.markdown("𝕏 **[X / Twitter (@ContinuumL2)](https://x.com/ContinuumL2)**")
st.sidebar.markdown("💻 **[GitHub Deposu](https://github.com/0xContinuum/continuum-network-l2)**")

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Ağ & Kontrat Bilgileri")

st.sidebar.text_input("Base Sepolia CTM Kontratı", value=DEPLOYED_CONTRACT_ADDRESS, disabled=True)
st.sidebar.text_input("Kurucu (Founder) Cüzdan", value=FOUNDER_WALLET_ADDRESS, disabled=True)
st.sidebar.text_input("Sequencer Düğümü", value="0xContinuum_Sequencer_Main", disabled=True)

st.sidebar.markdown("---")
st.sidebar.info(
    "ℹ️ **Explorer Modu:** Bu panel Continuum L2 ağ durumunu, canlı Base Sepolia işlemlerini ve Paymaster durumunu izler."
)

if st.sidebar.button("🔄 Ağ Durumunu Yenile", type="primary", use_container_width=True):
    l2.load_state()
    st.cache_data.clear()
    st.sidebar.success("Veriler güncellendi!")
    st.rerun()

# --- MAIN PANEL ---
st.title("⚡ Continuum Network ($CTM) - L2 EVM Explorer")

# HIZLI ERİŞİM BUTONLARI
col_a, col_b, col_c, col_d, col_e = st.columns(5)
col_a.link_button("🌐 Web DApp", "https://0xcontinuum.github.io/continuum-network-l2/", use_container_width=True)
col_b.link_button("🤖 Faucet Bot", "https://t.me/ContinuumCTM_bot", use_container_width=True)
col_c.link_button("📢 Telegram", "https://t.me/ContinuumAnnouncements", use_container_width=True)
col_d.link_button("𝕏 Twitter", "https://x.com/ContinuumL2", use_container_width=True)
col_e.link_button("💻 GitHub", "https://github.com/0xContinuum/continuum-network-l2", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# METRİKLER (CANLI VE SEQUENCER DENGELİ)
m1, m2, m3, m4, m5 = st.columns(5)

total_blocks = live_block if live_block else len(l2.chain)
total_supply = l2.TOTAL_SUPPLY
founder_bal = l2.balances.get(FOUNDER_WALLET_ADDRESS, 0.0)
paymaster_eth = l2.paymaster.eth_gas_tank
contract_short = f"{DEPLOYED_CONTRACT_ADDRESS[:6]}...{DEPLOYED_CONTRACT_ADDRESS[-4:]}"

m1.metric("Ağ / Blok", f"#{total_blocks}" if live_block else f"L2 #{total_blocks}")
m2.metric("Toplam $CTM Arzı", f"{total_supply:,.0f}")
m3.metric("🔥 Yakılan ($CTM)", f"{live_burned:,.2f} CTM")
m4.metric("Paymaster Gas Deposu", f"{paymaster_eth:.4f} ETH")
m5.metric("Base Sepolia Kontratı", contract_short)

st.markdown("<br>", unsafe_allow_html=True)

# SEKMELER
tab1, tab2, tab3, tab4 = st.tabs([
    "💸 Canlı Zincir Transferleri (Base Sepolia)", 
    "🧊 L2 Sequencer Blokları", 
    "💰 Cüzdan Bakiyeleri (State)", 
    "⛽ Paymaster & Gas Sponsorluğu"
])

with tab1:
    st.subheader("🔗 Base Sepolia Üzerindeki Canlı CTM Transferleri")
    if not df_live_tx.empty:
        df_display = df_live_tx.copy()
        df_display['Tx Hash'] = df_display['Tx Hash'].apply(
            lambda x: f"[{x[:10]}...{x[-8:]}](https://sepolia.basescan.org/tx/{x})"
        )
        df_display['Gönderen'] = df_display['Gönderen'].apply(
            lambda x: f"[{x[:6]}...{x[-4:]}](https://sepolia.basescan.org/address/{x})"
        )
        df_display['Alıcı'] = df_display['Alıcı'].apply(
            lambda x: f"[{x[:6]}...{x[-4:]}](https://sepolia.basescan.org/address/{x})"
        )
        
        st.markdown(df_display.to_markdown(index=False), unsafe_allow_html=True)
    else:
        st.info("Canlı zincir verileri yükleniyor veya son bloklarda transfer bulunamadı...")

with tab2:
    st.subheader("🧊 L2 Blokları ve Paketlenmiş İşlemler")
    blocks_data = []
    for b in reversed(l2.chain):
        blocks_data.append({
            "Blok #": b.index,
            "Timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(b.timestamp)),
            "İşlem Sayısı": len(b.transactions),
            "Sequencer": b.sequencer,
            "Batch Root": b.batch_root[:18] + "...",
            "Blok Hash": b.hash[:18] + "..."
        })
    st.dataframe(pd.DataFrame(blocks_data), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("💰 L2 Cüzdan Bakiyeleri (`continuum_l2_state.json`)")
    st.json(l2.balances)

with tab4:
    st.subheader("⛽ ERC-4337 Paymaster Sponsorluk Durumu")
    st.info(f"Paymaster Havuz Adresi: `{l2.paymaster.paymaster_address}`")
    st.progress(min(l2.paymaster.eth_gas_tank / 10.0, 1.0), text=f"L2 Gas Tankı Doluluğu: {l2.paymaster.eth_gas_tank:.4f} / 10.0 ETH")

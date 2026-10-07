import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../sequencer')))
import streamlit as st
import pandas as pd
import time

# Deployed Base Sepolia Kontrat Adresi
DEPLOYED_CONTRACT_ADDRESS = "0x078712Ac537F24B76a1AAB05624c02A9E0a28C13"

try:
    from continuum_network_3 import ContinuumL2Blockchain, CryptoEngine, CONTRACT_ADDRESS, FOUNDER_WALLET_ADDRESS
except ImportError as e:
    st.error(f"⚠️ 'continuum_network_3.py' yüklenirken hata oluştu: {e}")
    st.stop()

st.set_page_config(
    page_title="Continuum Network ($CTM) L2 Explorer",
    page_icon="⚡",
    layout="wide"
)

if "l2_chain" not in st.session_state:
    st.session_state.l2_chain = ContinuumL2Blockchain()

l2: ContinuumL2Blockchain = st.session_state.l2_chain


# YAN PANEL (Ağ Durumu & Ekosistem Linkleri)
st.sidebar.title("⚡ Continuum L2 Network")
st.sidebar.caption("Ağ Durumu: 🟢 CANLI (Base Sepolia Testnet)")

st.sidebar.markdown("---")
st.sidebar.subheader("🌐 Ekosistem & Linkler")

# Sosyal ve Uygulama Linkleri
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
    "ℹ️ **Explorer Modu:** Bu panel Continuum L2 ağ durumunu, bakiye durumunu ve L2 batch işlemlerini izler. "
    "Web3 cüzdan işlemleri için Web DApp istemcisini kullanabilirsiniz."
)

if st.sidebar.button("🔄 Ağ Durumunu Yenile", type="primary", use_container_width=True):
    l2.load_state()
    st.sidebar.success("Veriler güncellendi!")
    st.rerun()


# MAIN PANEL
st.title("⚡ Continuum Network ($CTM) - L2 EVM Explorer")

# HIZLI ERİŞİM BUTONLARI (TOP BANNER)
col_a, col_b, col_c, col_d, col_e = st.columns(5)
col_a.link_button("🌐 Web DApp", "https://0xcontinuum.github.io/continuum-network-l2/", use_container_width=True)
col_b.link_button("🤖 Faucet Bot", "https://t.me/ContinuumCTM_bot", use_container_width=True)
col_c.link_button("📢 Telegram", "https://t.me/ContinuumAnnouncements", use_container_width=True)
col_d.link_button("𝕏 Twitter", "https://x.com/ContinuumL2", use_container_width=True)
col_e.link_button("💻 GitHub", "https://github.com/0xContinuum/continuum-network-l2", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# METRİKLER
m1, m2, m3, m4, m5 = st.columns(5)

total_blocks = len(l2.chain)
total_supply = l2.TOTAL_SUPPLY
founder_bal = l2.balances.get(FOUNDER_WALLET_ADDRESS, 0.0)
paymaster_eth = l2.paymaster.eth_gas_tank
contract_short = f"{DEPLOYED_CONTRACT_ADDRESS[:6]}...{DEPLOYED_CONTRACT_ADDRESS[-4:]}"

m1.metric("L2 Toplam Blok", f"#{total_blocks}")
m2.metric("Toplam $CTM Arzı", f"{total_supply:,.0f}")
m3.metric("Kurucu Bakiye (%15)", f"{founder_bal:,.0f} CTM")
m4.metric("Paymaster Gas Deposu", f"{paymaster_eth:.4f} ETH")
m5.metric("Base Sepolia Kontratı", contract_short)

st.markdown("<br>", unsafe_allow_html=True)

# SEKMELER
tab1, tab2, tab3 = st.tabs(["🧊 L2 Blokları & Batchler", "💰 Cüzdan Bakiyeleri (State)", "⛽ Paymaster & Gas Sponsorluğu"])

with tab1:
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

with tab2:
    st.subheader("💰 L2 Cüzdan Bakiyeleri (`continuum_l2_state.json`)")
    st.json(l2.balances)

with tab3:
    st.subheader("⛽ ERC-4337 Paymaster Sponsorluk Durumu")
    st.info(f"Paymaster Havuz Adresi: `{l2.paymaster.paymaster_address}`")
    st.progress(min(l2.paymaster.eth_gas_tank / 10.0, 1.0), text=f"L2 Gas Tankı Doluluğu: {l2.paymaster.eth_gas_tank:.4f} / 10.0 ETH")

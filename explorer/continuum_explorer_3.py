"""
===============================================================================
CONTINUUM NETWORK ($CTM) - L2 EVM PUBLIC STREAMLIT EXPLORER (READ-ONLY)
===============================================================================
Run with:
    streamlit run continuum_explorer_3.py
===============================================================================
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../sequencer')))
import streamlit as st
import pandas as pd
import time
import json
import plotly.express as px

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


# YAN PANEL (Ağ Durumu & Güvenli Bilgilendirme)
st.sidebar.title("⚡ Continuum L2 Network")
st.sidebar.caption("Ağ Durumu: 🟢 CANLI (Testnet)")

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Ağ & Kontrat Bilgileri")

st.sidebar.text_input("Sepolia CTM Kontratı", value=CONTRACT_ADDRESS, disabled=True)
st.sidebar.text_input("Kurucu (Founder) Cüzdan", value=FOUNDER_WALLET_ADDRESS, disabled=True)
st.sidebar.text_input("Sequencer Düğümü", value="0xContinuum_Sequencer_Main", disabled=True)

st.sidebar.markdown("---")
st.sidebar.info(
    "ℹ️ **Salt Okunur Mod:** Bu explorer ağ durumunu ve L2 batch işlemlerini izlemek içindir. "
    "Testnet $CTM talepleri için Telegram Faucet Botunu kullanabilirsiniz."
)

if st.sidebar.button("🔄 Ağ Durumunu Yenile", type="primary", use_container_width=True):
    l2.load_state()
    st.sidebar.success("Veriler güncellendi!")
    st.rerun()


# MAIN PANEL
st.title("⚡ Continuum Network ($CTM) - L2 EVM Explorer")

m1, m2, m3, m4, m5 = st.columns(5)

total_blocks = len(l2.chain)
total_supply = l2.TOTAL_SUPPLY
founder_bal = l2.balances.get(FOUNDER_WALLET_ADDRESS, 0.0)
paymaster_eth = l2.paymaster.eth_gas_tank
contract_short = f"{l2.contract_address[:6]}...{l2.contract_address[-4:]}" if len(l2.contract_address) > 10 else l2.contract_address

m1.metric("L2 Toplam Blok", f"#{total_blocks}")
m2.metric("Toplam $CTM Arzı", f"{total_supply:,.0f}")
m3.metric("Kurucu Bakiye (%15)", f"{founder_bal:,.0f} CTM")
m4.metric("Paymaster Gas Deposu", f"{paymaster_eth:.4f} ETH")
m5.metric("Sepolia Kontratı", contract_short)

st.markdown("<br>", unsafe_allow_html=True)

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

import os
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

CMC_KEY = os.getenv("CMC_API_KEY")
OR_KEY = os.getenv("OPENROUTER_API_KEY")
CG_KEY = os.getenv("COINGECKO_API_KEY")
NEWS_KEY = os.getenv("NEWSDATA_API_KEY", os.getenv("CRYPTOPANIC_API_KEY", ""))

if CG_KEY:
    CG_HDR = {"x-cg-demo-api-key": CG_KEY}
else:
    CG_HDR = {}

st.set_page_config(layout="wide", page_title="Crypto Terminal", page_icon="₿")
st.markdown(
    "<style>.stApp {background:#0d1117;} h1,h2,h3,p,label,div {color:#c9d1d9!important;}</style>",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def get_cg_map():
    res = requests.get("https://api.coingecko.com/api/v3/coins/list", headers=CG_HDR)
    if res.status_code == 200:
        return {c["symbol"].upper(): c["id"] for c in res.json()}
    return {}


@st.cache_data(ttl=60)
def fetch_top_coins():
    params = {"limit": 100, "convert": "USD"}
    headers = {"X-CMC_PRO_API_KEY": CMC_KEY}
    res = requests.get(
        "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
        headers=headers,
        params=params,
    )
    if res.status_code != 200:
        return {"BTC": {"name": "Bitcoin", "cg_id": "bitcoin"}}

    cg_map = get_cg_map()
    coins_data = {}
    for c in res.json().get("data", []):
        symbol = c["symbol"]
        coins_data[symbol] = {
            "name": c["name"],
            "cg_id": cg_map.get(symbol, c["name"].lower()),
        }
    return coins_data


@st.cache_data(ttl=60)
def fetch_price_data(sym, cur):
    params = {"symbol": sym, "convert": cur}
    headers = {"X-CMC_PRO_API_KEY": CMC_KEY}
    res = requests.get(
        "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
        headers=headers,
        params=params,
    )
    if res.status_code != 200:
        raise Exception("CMC API Error")

    quote = res.json()["data"][sym]["quote"][cur]
    return {
        "price": quote["price"],
        "c1h": quote["percent_change_1h"],
        "c24h": quote["percent_change_24h"],
        "c7d": quote["percent_change_7d"],
        "mc": quote["market_cap"],
        "vol": quote["volume_24h"],
    }


@st.cache_data(ttl=300)
def fetch_chart_data(cg_id, days, cur):
    params = {"vs_currency": cur.lower(), "days": max(7, days)}
    res = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc",
        params=params,
        headers=CG_HDR,
    )
    if res.status_code != 200 or not isinstance(res.json(), list):
        return pd.DataFrame()

    df = pd.DataFrame(res.json(), columns=["ts", "open", "high", "low", "close"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms").dt.date
    agg_funcs = {"open": "first", "high": "max", "low": "min", "close": "last"}
    
    return df.groupby("date").agg(agg_funcs).reset_index().tail(days)


@st.cache_data(ttl=300)
def fetch_news(sym):
    params = {"auth_token": NEWS_KEY, "public": True, "currencies": sym}
    res = requests.get(
        "https://cryptopanic.com/api/developer/v2/posts/",
        params=params,
    )
    if res.status_code == 200:
        return res.json().get("results", [])[:5]
    return []


@st.cache_data(ttl=300)
def generate_ai_analysis(sym, px_str, news_titles):
    prompt = (
        f"Analyze sentiment for {sym}. Price/Metrics: {px_str}. "
        f"Recent news: {news_titles}. Give concise news sentiment summary, "
        "possible market impact, and overall tone (Bullish/Bearish/Neutral). "
        "Max 5 lines."
    )
    payload = {
        "model": "arcee-ai/trinity-large-preview:free",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
    }
    headers = {"Authorization": f"Bearer {OR_KEY}"}
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
    )
    
    if res.status_code == 200 and "choices" in res.json():
        return res.json()["choices"][0]["message"]["content"]
    return "AI Analysis Unavailable"


coins = fetch_top_coins()

with st.sidebar:
    st.header("⚙️ Controls")
    sym = st.selectbox(
        "Coin",
        list(coins.keys()),
        format_func=lambda x: f"{coins[x]['name']} ({x})",
    )
    cur = st.selectbox("Currency", ["USD", "EUR", "BTC", "USDT"])
    days = st.slider("History (Days)", 7, 30, 14)

try:
    data = fetch_price_data(sym, cur)
    hist = fetch_chart_data(coins[sym]["cg_id"], days, cur)
    news = fetch_news(sym)
except Exception as e:
    st.error(f"API Fetch Error. Details: {e}")
    st.stop()

main, right = st.columns([3, 1])

with main:
    st.header(f"📊 {coins[sym]['name']} ({sym})")
    cols = st.columns(5)
    metrics = [
        ("Price", f"${data['price']:.4f}"),
        ("1h %", f"{data['c1h']:.2f}%"),
        ("24h %", f"{data['c24h']:.2f}%"),
        ("7d %", f"{data['c7d']:.2f}%"),
        ("Volume", f"${data['vol']/1e9:.2f}B"),
    ]
    
    for c, (label, value) in zip(cols, metrics):
        c.metric(label, value)

    t1, t2 = st.tabs(["⚡ Dynamic Chart", "📺 TradingView"])
    
    with t1:
        if not hist.empty:
            c1, c2 = st.columns([5, 1])
            with c2:
                ctype = st.selectbox(
                    "Chart Style",
                    ["Candlestick", "Line", "Bar"],
                    label_visibility="collapsed",
                )
            with c1:
                if ctype == "Candlestick":
                    fig = go.Figure(
                        data=[
                            go.Candlestick(
                                x=hist["date"],
                                open=hist["open"],
                                high=hist["high"],
                                low=hist["low"],
                                close=hist["close"],
                                increasing_line_color="#3fb950",
                                decreasing_line_color="#f85149",
                            )
                        ]
                    )
                elif ctype == "Line":
                    fig = go.Figure(
                        data=[
                            go.Scatter(
                                x=hist["date"],
                                y=hist["close"],
                                mode="lines",
                                line=dict(color="#388bfd", width=2),
                            )
                        ]
                    )
                else:
                    fig = go.Figure(
                        data=[
                            go.Bar(
                                x=hist["date"],
                                y=hist["close"],
                                marker_color="#388bfd",
                            )
                        ]
                    )
                    
                fig.update_layout(
                    height=720,
                    margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor="#0d1117",
                    plot_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9"),
                    xaxis_rangeslider_visible=False,
                )
                st.plotly_chart(fig, use_container_width=True)
                
    with t2:
        tv_html = f'''
        <div class="tradingview-widget-container" style="height:720px;">
            <div id="tv_chart" style="height:calc(100% - 32px);width:100%"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
                new TradingView.widget({{
                    "autosize": true,
                    "symbol": "BINANCE:{sym}USDT",
                    "interval": "D",
                    "theme": "dark",
                    "style": "1",
                    "locale": "en",
                    "toolbar_bg": "#161b22",
                    "enable_publishing": false,
                    "hide_legend": false,
                    "container_id": "tv_chart",
                    "studies": ["RSI@tv-basicstudies", "MACD@tv-basicstudies"]
                }});
            </script>
        </div>
        '''
        components.html(tv_html, height=720)

with right:
    st.header("🧠 Intelligence")
    
    st.subheader("📰 News")
    news_str = " | ".join([n["title"] for n in news])
    for n in news:
        st.markdown(f"• **{n['title']}**", unsafe_allow_html=True)
    if not news:
        st.info("No recent news.")

    st.subheader("💡 AI Sentiment")
    if st.button("Generate Analysis") or f"ai_{sym}" in st.session_state:
        if f"ai_{sym}" in st.session_state and st.button("Refresh Analysis"):
            del st.session_state[f"ai_{sym}"]
            
        if f"ai_{sym}" not in st.session_state:
            with st.spinner("Analyzing..."):
                px = f"Price: {data['price']}, 24h: {data['c24h']}%"
                st.session_state[f"ai_{sym}"] = generate_ai_analysis(sym, px, news_str)
                
        if f"ai_{sym}" in st.session_state:
            formatted_ai_text = st.session_state[f"ai_{sym}"].replace("*", "")
            st.markdown(
                f'<div style="background:#161b22; padding:15px; border-radius:8px; border-left:4px solid #388bfd;">{formatted_ai_text}</div>',
                unsafe_allow_html=True,
            )

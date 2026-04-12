"""
app.py — NSE Trading Dashboard (Streamlit UI)
Main entry point: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data import fetch_stock_data
from indicators import add_all_indicators
from strategy import generate_signal
from risk import calculate_trade_plan, get_risk_warnings, export_trade_plan_to_excel

# ── Page Configuration ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="📊 NSE Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
        /* Sidebar dark background */
        [data-testid="stSidebar"] {
            background-color: #1e2130;
        }
        [data-testid="stSidebar"] * {
            color: #e0e0e0 !important;
        }
        /* Signal boxes */
        .signal-box {
            padding: 20px 30px;
            border-radius: 12px;
            text-align: center;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        .signal-buy  { background-color: #1a6b3c; color: #00ff88 !important; }
        .signal-sell { background-color: #6b1a1a; color: #ff6b6b !important; }
        .signal-hold { background-color: #5a4a00; color: #ffd700 !important; }
        /* Trade plan table */
        .trade-table td { padding: 6px 12px; }
        .trade-table tr:nth-child(even) { background-color: #f9f9f9; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

NIFTY50_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "KOTAKBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS",
    "BAJFINANCE.NS", "ASIANPAINT.NS", "LT.NS", "AXISBANK.NS", "TITAN.NS",
    "WIPRO.NS", "HCLTECH.NS", "MARUTI.NS", "NESTLEIND.NS", "ULTRACEMCO.NS",
    "Custom",
]

INTERVAL_OPTIONS = {
    "15 Minutes (15m)": "15m",
    "1 Hour (1h)": "1h",
    "1 Day (1d)": "1d",
    "1 Week (1wk)": "1wk",
}

# Max period supported by yfinance for each interval
INTERVAL_PERIODS = {
    "15m": "60d",
    "1h": "60d",
    "1d": "1y",
    "1wk": "5y",
}

with st.sidebar:
    st.title("📊 NSE Dashboard")
    st.markdown("---")

    # ── Ticker Selection ──────────────────────────────────────────────────────
    selected_ticker = st.selectbox(
        "🔤 Stock Ticker",
        options=NIFTY50_TICKERS,
        index=0,
        help="Select a popular Nifty 50 stock or choose 'Custom' to enter any ticker.",
    )

    if selected_ticker == "Custom":
        ticker = st.text_input(
            "Enter custom ticker",
            value="",
            placeholder="e.g. TATAMOTORS.NS",
            help="Enter any Yahoo Finance ticker symbol.",
        ).strip().upper()
    else:
        ticker = selected_ticker

    # ── Interval Selection ────────────────────────────────────────────────────
    interval_label = st.selectbox(
        "⏱️ Data Interval",
        options=list(INTERVAL_OPTIONS.keys()),
        index=2,
        help="Select the candle interval. Note: intraday intervals (15m, 1h) only support up to 60 days of history.",
    )
    interval = INTERVAL_OPTIONS[interval_label]

    st.markdown("---")

    # ── Capital & Risk ────────────────────────────────────────────────────────
    capital = st.number_input(
        "💰 Capital (₹)",
        min_value=10_000,
        value=100_000,
        step=5_000,
        format="%d",
        help="Total trading capital in Indian Rupees",
    )

    risk_percent = st.slider(
        "⚠️ Risk %",
        min_value=0.5,
        max_value=5.0,
        value=1.0,
        step=0.5,
        help="Percentage of capital you are willing to risk per trade",
    )

    st.markdown("---")

    # ── Indicator Parameters ──────────────────────────────────────────────────
    st.markdown("### 📐 Indicator Parameters")

    fast_ma = st.number_input(
        "Fast MA Period",
        min_value=2,
        max_value=100,
        value=20,
        step=1,
        help="Period for the fast Simple Moving Average (default: 20)",
    )

    slow_ma = st.number_input(
        "Slow MA Period",
        min_value=2,
        max_value=300,
        value=50,
        step=1,
        help="Period for the slow Simple Moving Average (default: 50)",
    )

    st.markdown("**RSI Oversold Zone**")
    oversold_min = st.number_input(
        "RSI Oversold Min",
        min_value=1,
        max_value=49,
        value=30,
        step=1,
        help="Lower bound of the RSI oversold recovery zone (default: 30)",
    )

    oversold_max = st.number_input(
        "RSI Oversold Max",
        min_value=2,
        max_value=50,
        value=40,
        step=1,
        help="Upper bound of the RSI oversold recovery zone (default: 40)",
    )

    overbought = st.number_input(
        "RSI Overbought",
        min_value=51,
        max_value=99,
        value=60,
        step=1,
        help="RSI threshold for the overbought / sell zone (default: 60)",
    )

    st.markdown("---")

    analyze_btn = st.button("🔍 Analyze Stock", use_container_width=True)

    st.markdown("---")
    st.caption(
        "⚠️ **Disclaimer:** For educational purposes only. "
        "Not financial advice. Always do your own research."
    )

# ── Main Area ─────────────────────────────────────────────────────────────────

st.title("📊 NSE Trading Dashboard")

if not analyze_btn:
    st.info(
        "👈 Enter a stock ticker and capital in the sidebar, "
        "then click **🔍 Analyze Stock** to begin."
    )
    st.stop()

if not ticker:
    st.error("Please enter a valid ticker symbol.")
    st.stop()

# Collect and display all parameter validation errors at once
validation_errors = []
if oversold_min >= oversold_max:
    validation_errors.append("RSI Oversold Min must be less than RSI Oversold Max.")
if oversold_max >= overbought:
    validation_errors.append("RSI Oversold Max must be less than RSI Overbought.")
if fast_ma >= slow_ma:
    validation_errors.append("Fast MA Period must be less than Slow MA Period.")
if validation_errors:
    for msg in validation_errors:
        st.error(msg)
    st.stop()

# ── Data Fetch ────────────────────────────────────────────────────────────────

period = INTERVAL_PERIODS.get(interval, "1y")

with st.spinner(f"Fetching data for **{ticker}**…"):
    try:
        df_raw = fetch_stock_data(ticker, period=period, interval=interval)
    except RuntimeError as err:
        st.error(str(err))
        st.stop()

# ── Indicators ────────────────────────────────────────────────────────────────

df = add_all_indicators(df_raw, fast_ma=fast_ma, slow_ma=slow_ma)

# ── Signal Generation ─────────────────────────────────────────────────────────

signal_data = generate_signal(
    df,
    oversold_min=oversold_min,
    oversold_max=oversold_max,
    overbought=overbought,
    fast_ma=fast_ma,
    slow_ma=slow_ma,
)
signal = signal_data["signal"]
confidence = signal_data["confidence"]
reasons = signal_data["reasons"]

# ── Trade Plan & Warnings ─────────────────────────────────────────────────────

try:
    trade_plan = calculate_trade_plan(df, capital, risk_percent)
    plan_error = None
except (ValueError, Exception) as err:
    trade_plan = None
    plan_error = str(err)

warnings = get_risk_warnings(trade_plan or {}, signal_data) if trade_plan else []

# ═════════════════════════════════════════════════════════════════════════════
# Section 2: Signal Box
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## 🎯 Trading Signal")

signal_class = {
    "BUY": "signal-buy",
    "SELL": "signal-sell",
    "HOLD": "signal-hold",
}.get(signal, "signal-hold")

signal_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal, "🟡")

st.markdown(
    f"""
    <div class="signal-box {signal_class}">
        {signal_icon} {signal} SIGNAL &nbsp;|&nbsp; Confidence: {confidence}
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("📋 Signal Reasoning", expanded=False):
    for r in reasons:
        st.markdown(f"• {r}")

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# Section 3: Risk Warnings
# ═════════════════════════════════════════════════════════════════════════════

if warnings:
    st.markdown("## ⚠️ Risk Warnings")
    for w in warnings:
        if w["type"] == "danger":
            st.error(w["message"])
        elif w["type"] == "success":
            st.success(w["message"])
        else:
            st.warning(w["message"])

# ═════════════════════════════════════════════════════════════════════════════
# Section 4: Trade Plan Table
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## 📋 Trade Plan")

if plan_error:
    st.error(f"Trade plan unavailable: {plan_error}")
elif trade_plan:
    col_left, col_right = st.columns(2)

    def _fmt(value: float) -> str:
        """Format a float as Indian currency string."""
        return f"₹{value:,.2f}"

    with col_left:
        st.table(
            {
                "Parameter": [
                    "Entry Price",
                    "Stop Loss",
                    "Target",
                    "Risk / Share",
                    "Reward / Share",
                ],
                "Value": [
                    _fmt(trade_plan["entry_price"]),
                    _fmt(trade_plan["stop_loss"]),
                    _fmt(trade_plan["target"]),
                    _fmt(trade_plan["risk_per_share"]),
                    _fmt(trade_plan["reward_per_share"]),
                ],
            }
        )

    with col_right:
        st.table(
            {
                "Parameter": [
                    "RR Ratio",
                    "Quantity",
                    "Total Investment",
                    "Potential Loss",
                    "Potential Profit",
                ],
                "Value": [
                    f"1:{trade_plan['rr_ratio']}",
                    f"{trade_plan['position_size']:,} shares",
                    _fmt(trade_plan["total_investment"]),
                    _fmt(trade_plan["potential_loss"]),
                    _fmt(trade_plan["potential_profit"]),
                ],
            }
        )

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# Section 5: Indicator Snapshot
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## 📈 Indicator Snapshot")

ind_status = signal_data.get("indicator_status", {})

col1, col2, col3, col4 = st.columns(4)

def _pass_icon(passed: bool) -> str:
    return "✅" if passed else "❌"


rsi_info = ind_status.get("rsi", {})
ma_info = ind_status.get("ma", {})
macd_info = ind_status.get("macd", {})
vol_info = ind_status.get("volume", {})

with col1:
    rsi_val = rsi_info.get("value", float("nan"))
    rsi_display = f"{rsi_val:.1f}" if pd.notna(rsi_val) else "N/A"
    st.metric(
        label=f"RSI (14) {_pass_icon(rsi_info.get('pass', False))}",
        value=rsi_display,
        delta=rsi_info.get("status", "N/A").capitalize(),
    )

with col2:
    st.metric(
        label=f"Price vs MA{slow_ma} {_pass_icon(ma_info.get('pass', False))}",
        value=ma_info.get("status", "N/A").capitalize(),
        delta=None,
    )

with col3:
    macd_status = macd_info.get("status", "neutral")
    st.metric(
        label=f"MACD {_pass_icon(macd_info.get('pass', False))}",
        value=macd_status.capitalize(),
        delta=None,
    )

with col4:
    vol_status = vol_info.get("status", "N/A")
    vol_label = "Above Avg" if vol_status == "above_avg" else "Below Avg"
    st.metric(
        label=f"Volume {_pass_icon(vol_info.get('pass', False))}",
        value=vol_label,
        delta=None,
    )

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# Section 6: Price Chart
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(f"## 📉 {ticker} — Price Chart with Moving Averages")

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.75, 0.25],
    subplot_titles=("Price & Moving Averages", "Volume"),
)

# Candlestick
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price",
        increasing_line_color="#00c896",
        decreasing_line_color="#ff4b5c",
    ),
    row=1,
    col=1,
)

# Fast MA
if "MA_FAST" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA_FAST"],
            name=f"MA{fast_ma} (Fast)",
            line={"color": "#1f77b4", "width": 1.5},
        ),
        row=1,
        col=1,
    )

# Slow MA
if "MA_SLOW" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA_SLOW"],
            name=f"MA{slow_ma} (Slow)",
            line={"color": "#ff7f0e", "width": 1.5},
        ),
        row=1,
        col=1,
    )

# Volume bars
vol_colors = [
    "#00c896" if c >= o else "#ff4b5c"
    for c, o in zip(df["Close"], df["Open"])
]
fig.add_trace(
    go.Bar(
        x=df.index,
        y=df["Volume"],
        name="Volume",
        marker_color=vol_colors,
        opacity=0.7,
    ),
    row=2,
    col=1,
)

# Volume average line
if "Vol_Avg" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Vol_Avg"],
            name="Vol Avg (20)",
            line={"color": "#9467bd", "width": 1.2, "dash": "dot"},
        ),
        row=2,
        col=1,
    )

fig.update_layout(
    height=650,
    xaxis_rangeslider_visible=False,
    legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    margin={"t": 40, "b": 20},
)

st.plotly_chart(fig, use_container_width=True, theme="streamlit")

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# Section 7: Export Button
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## 📥 Export")

if trade_plan:
    excel_buffer = export_trade_plan_to_excel(trade_plan, signal_data, warnings, ticker)
    st.download_button(
        label="📥 Download Trade Plan (Excel)",
        data=excel_buffer,
        file_name=f"{ticker}_trade_plan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
else:
    st.info("Trade plan not available — export disabled.")

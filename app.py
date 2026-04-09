"""
app.py — NSE Trading Dashboard (Streamlit UI)
Main entry point: streamlit run app.py
"""

import streamlit as st
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

with st.sidebar:
    st.title("📊 NSE Dashboard")
    st.markdown("---")

    ticker = st.text_input(
        "🔤 Stock Ticker",
        value="RELIANCE.NS",
        help="Enter NSE ticker symbol, e.g. RELIANCE.NS, TCS.NS, INFY.NS",
    ).strip().upper()

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

# ── Data Fetch ────────────────────────────────────────────────────────────────

with st.spinner(f"Fetching data for **{ticker}**…"):
    try:
        df_raw = fetch_stock_data(ticker)
    except RuntimeError as err:
        st.error(str(err))
        st.stop()

# ── Indicators ────────────────────────────────────────────────────────────────

df = add_all_indicators(df_raw)

# ── Signal Generation ─────────────────────────────────────────────────────────

signal_data = generate_signal(df)
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
        label=f"Price vs MA50 {_pass_icon(ma_info.get('pass', False))}",
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

# MA20
if "MA20" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA20"],
            name="MA20",
            line={"color": "#1f77b4", "width": 1.5},
        ),
        row=1,
        col=1,
    )

# MA50
if "MA50" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MA50"],
            name="MA50",
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
    template="plotly_dark",
)

st.plotly_chart(fig, use_container_width=True)

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

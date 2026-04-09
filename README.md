# 📊 NSE Trading Dashboard — by Tuhin

A **Python Streamlit** app that acts as a complete stock analysis and trading decision dashboard for Indian stocks (NSE). It fetches live market data, computes popular technical indicators, generates a BUY / SELL / HOLD signal, calculates a detailed trade plan with position sizing, and visualises everything in an interactive UI.

> ⚠️ **Disclaimer:** This tool is for **educational purposes only**. It does **not** execute trades, connect to any broker, or predict future prices. Always consult a qualified financial advisor before making investment decisions.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📡 Live Data | Fetches 1-year OHLCV data via `yfinance` for any NSE ticker |
| 📐 Indicators | RSI (14), MA 20/50/200, MACD (12,26,9), ATR (14), Volume Avg (20) |
| 🎯 Signals | Rule-based BUY / SELL / HOLD with High / Medium / Low confidence |
| 💰 Trade Plan | Entry, Stop Loss, Target, Position Size, R:R Ratio |
| ⚠️ Risk Warnings | Automated alerts for low R:R, low confidence, or no clear signal |
| 📉 Chart | Interactive Plotly candlestick with MA20, MA50, and Volume subplot |
| 📥 Export | Download full trade plan as a multi-sheet Excel file |

---

## 🖥️ Screenshot

> *(Screenshot placeholder — run the app locally and capture it here)*

---

## 🛠️ Installation

```bash
# 1. Clone the repository
git clone https://github.com/tuhinsbcl2-ctrl/Trading-indicator-by-Tuhin.git
cd Trading-indicator-by-Tuhin

# 2. (Optional) Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Usage

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`, enter a ticker such as `RELIANCE.NS`, set your capital and risk %, then click **🔍 Analyze Stock**.

---

## 📁 File Structure

```
Trading-indicator-by-Tuhin/
├── app.py            # Streamlit UI — main entry point
├── data.py           # Data fetching via yfinance
├── indicators.py     # RSI, MA, MACD, ATR, Volume calculations
├── strategy.py       # BUY / SELL / HOLD signal logic
├── risk.py           # Position sizing, risk warnings, Excel export
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## 📋 Signal Logic (Rule-Based, No ML)

| Signal | Conditions |
|--------|-----------|
| **BUY** | RSI 30–40 **AND** Close > MA50 **AND** MACD Hist > 0 |
| **SELL** | RSI > 60 **AND** Close < MA20 **AND** MACD Hist < 0 |
| **HOLD** | Anything else |

---

## 🔢 Supported Tickers (Examples)

`RELIANCE.NS` · `TCS.NS` · `INFY.NS` · `HDFCBANK.NS` · `ICICIBANK.NS` · `WIPRO.NS`

Any NSE ticker in `<SYMBOL>.NS` format is supported.

---

## 📦 Dependencies

```
streamlit
yfinance
pandas
plotly
openpyxl
```
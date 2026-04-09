"""
strategy.py — Signal Generation Logic
Generates BUY / SELL / HOLD signals based on technical indicator conditions.
"""

import pandas as pd


def generate_signal(df: pd.DataFrame) -> dict:
    """
    Analyse the latest candle and generate a trading signal.

    BUY conditions (ALL must hold):
        - RSI between 30 and 40
        - Close price above MA50
        - MACD Histogram > 0 (bullish momentum)

    SELL conditions (ALL must hold):
        - RSI above 60
        - Close price below MA20
        - MACD Histogram < 0 (bearish momentum)

    Otherwise: HOLD

    Confidence:
        High   → all four indicator checks (rsi, ma, macd, volume) align
        Medium → signal conditions met but volume doesn't confirm
        Low    → indicators are conflicting / not enough data

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with all indicators already added.

    Returns
    -------
    dict
        Signal dictionary with keys: signal, confidence, reasons,
        indicator_status.
    """
    required = ["Close", "RSI", "MA20", "MA50", "MACD_Hist", "Volume", "Vol_Avg"]
    if df is None or df.empty or not all(c in df.columns for c in required):
        return _hold_signal("Insufficient data for analysis.")

    # Use the last complete row
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    rsi = latest["RSI"]
    close = latest["Close"]
    ma20 = latest["MA20"]
    ma50 = latest["MA50"]
    macd_hist = latest["MACD_Hist"]
    prev_macd_hist = prev["MACD_Hist"]
    volume = latest["Volume"]
    vol_avg = latest["Vol_Avg"]

    # Guard against NaN values in key indicators
    if any(pd.isna(v) for v in [rsi, close, ma20, ma50, macd_hist, vol_avg]):
        return _hold_signal("Indicator values not yet available (insufficient history).")

    # ── Individual indicator statuses ────────────────────────────────────────
    # RSI
    if 30 <= rsi <= 40:
        rsi_status, rsi_pass = "bullish", True
    elif rsi > 60:
        rsi_status, rsi_pass = "bearish", True
    else:
        rsi_status, rsi_pass = "neutral", False

    # Price vs MA
    if close > ma50:
        ma_status, ma_pass = "bullish", True
        ma_desc = f"Close ({close:.2f}) > MA50 ({ma50:.2f})"
    elif close < ma20:
        ma_status, ma_pass = "bearish", True
        ma_desc = f"Close ({close:.2f}) < MA20 ({ma20:.2f})"
    else:
        ma_status, ma_pass = "neutral", False
        ma_desc = f"Close ({close:.2f}) between MA20 and MA50"

    # MACD
    if macd_hist > 0:
        macd_status, macd_pass = "bullish", True
        macd_crossover = (not pd.isna(prev_macd_hist)) and (prev_macd_hist <= 0)
        macd_desc = "Bullish crossover" if macd_crossover else "Bullish (MACD Hist > 0)"
    elif macd_hist < 0:
        macd_status, macd_pass = "bearish", True
        macd_crossover = (not pd.isna(prev_macd_hist)) and (prev_macd_hist >= 0)
        macd_desc = "Bearish crossover" if macd_crossover else "Bearish (MACD Hist < 0)"
    else:
        macd_status, macd_pass = "neutral", False
        macd_desc = "Neutral (MACD Hist = 0)"

    # Volume
    if volume > vol_avg:
        vol_status, vol_pass = "above_avg", True
        vol_desc = f"Volume ({int(volume):,}) > Avg ({int(vol_avg):,})"
    else:
        vol_status, vol_pass = "below_avg", False
        vol_desc = f"Volume ({int(volume):,}) ≤ Avg ({int(vol_avg):,})"

    indicator_status = {
        "rsi": {
            "value": round(rsi, 2),
            "status": rsi_status,
            "pass": rsi_pass,
        },
        "ma": {
            "value": ma_desc,
            "status": ma_status,
            "pass": ma_pass,
        },
        "macd": {
            "value": macd_desc,
            "status": macd_status,
            "pass": macd_pass,
        },
        "volume": {
            "value": vol_desc,
            "status": vol_status,
            "pass": vol_pass,
        },
    }

    # ── Signal determination ─────────────────────────────────────────────────
    buy_cond = (30 <= rsi <= 40) and (close > ma50) and (macd_hist > 0)
    sell_cond = (rsi > 60) and (close < ma20) and (macd_hist < 0)

    reasons = []

    if buy_cond:
        signal = "BUY"
        reasons.append(f"RSI ({rsi:.1f}) is in oversold-recovery zone (30–40)")
        reasons.append(f"Price is above MA50 — bullish trend")
        reasons.append(f"MACD histogram is positive — bullish momentum")
        if vol_pass:
            reasons.append("Volume confirms the move (above average)")
            confidence = "High"
        else:
            reasons.append("Volume is below average — confirmation weak")
            confidence = "Medium"

    elif sell_cond:
        signal = "SELL"
        reasons.append(f"RSI ({rsi:.1f}) is in overbought territory (> 60)")
        reasons.append(f"Price is below MA20 — short-term bearish")
        reasons.append(f"MACD histogram is negative — bearish momentum")
        if vol_pass:
            reasons.append("Volume confirms the sell pressure (above average)")
            confidence = "High"
        else:
            reasons.append("Volume is below average — confirmation weak")
            confidence = "Medium"

    else:
        signal = "HOLD"
        # Determine confidence based on how many conditions are met
        bull_score = sum([30 <= rsi <= 40, close > ma50, macd_hist > 0])
        bear_score = sum([rsi > 60, close < ma20, macd_hist < 0])

        if bull_score == 2 or bear_score == 2:
            confidence = "Medium"
            reasons.append("Most conditions partially met — waiting for full confirmation")
        else:
            confidence = "Low"
            reasons.append("Indicators are mixed — no clear directional signal")

        reasons.append(f"RSI at {rsi:.1f} (neutral zone or not in 30–40/60+ range)")

    return {
        "signal": signal,
        "confidence": confidence,
        "reasons": reasons,
        "indicator_status": indicator_status,
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _hold_signal(reason: str) -> dict:
    """Return a default HOLD signal with a given reason."""
    return {
        "signal": "HOLD",
        "confidence": "Low",
        "reasons": [reason],
        "indicator_status": {
            "rsi": {"value": float("nan"), "status": "neutral", "pass": False},
            "ma": {"value": "N/A", "status": "neutral", "pass": False},
            "macd": {"value": "N/A", "status": "neutral", "pass": False},
            "volume": {"value": "N/A", "status": "neutral", "pass": False},
        },
    }

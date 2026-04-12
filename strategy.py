"""
strategy.py — Signal Generation Logic
Generates BUY / SELL / HOLD signals based on technical indicator conditions.
"""

import pandas as pd


def generate_signal(df: pd.DataFrame,
                    oversold_min: int = 30,
                    oversold_max: int = 40,
                    overbought: int = 60,
                    fast_ma: int = 20,
                    slow_ma: int = 50) -> dict:
    """
    Analyse the latest candle and generate a trading signal.

    BUY conditions (ALL must hold):
        - RSI between oversold_min and oversold_max
        - Close price above MA_SLOW (slow moving average)
        - MACD Histogram > 0 (bullish momentum)

    SELL conditions (ALL must hold):
        - RSI above overbought
        - Close price below MA_FAST (fast moving average)
        - MACD Histogram < 0 (bearish momentum)

    Otherwise: HOLD

    Confidence:
        High   → the three signal conditions (rsi, ma, macd) are met AND volume
                  confirms (above average)
        Medium → the three signal conditions are met but volume doesn't confirm
        Low    → indicators are conflicting or insufficient data

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with all indicators already added.
    oversold_min : int
        Lower bound of the RSI oversold zone (default: 30).
    oversold_max : int
        Upper bound of the RSI oversold zone (default: 40).
    overbought : int
        RSI threshold for overbought territory (default: 60).
    fast_ma : int
        Period of the fast moving average; used only for display (default: 20).
    slow_ma : int
        Period of the slow moving average; used only for display (default: 50).

    Returns
    -------
    dict
        Signal dictionary with keys: signal, confidence, reasons,
        indicator_status.
    """
    required = ["Close", "RSI", "MA_FAST", "MA_SLOW", "MACD_Hist", "Volume", "Vol_Avg"]
    if df is None or df.empty or not all(c in df.columns for c in required):
        return _hold_signal("Insufficient data for analysis.")

    # Use the last complete row
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest

    rsi = latest["RSI"]
    close = latest["Close"]
    ma_fast = latest["MA_FAST"]
    ma_slow = latest["MA_SLOW"]
    macd_hist = latest["MACD_Hist"]
    prev_macd_hist = prev["MACD_Hist"]
    volume = latest["Volume"]
    vol_avg = latest["Vol_Avg"]

    # Guard against NaN values in key indicators
    if any(pd.isna(v) for v in [rsi, close, ma_fast, ma_slow, macd_hist, vol_avg]):
        return _hold_signal("Indicator values not yet available (insufficient history).")

    # ── Individual indicator statuses ────────────────────────────────────────
    # RSI
    if oversold_min <= rsi <= oversold_max:
        rsi_status, rsi_pass = "bullish", True
    elif rsi > overbought:
        rsi_status, rsi_pass = "bearish", True
    else:
        rsi_status, rsi_pass = "neutral", False

    # Price vs MA
    if close > ma_slow:
        ma_status, ma_pass = "bullish", True
        ma_desc = f"Close ({close:.2f}) > MA{slow_ma} ({ma_slow:.2f})"
    elif close < ma_fast:
        ma_status, ma_pass = "bearish", True
        ma_desc = f"Close ({close:.2f}) < MA{fast_ma} ({ma_fast:.2f})"
    else:
        ma_status, ma_pass = "neutral", False
        ma_desc = f"Close ({close:.2f}) between MA{fast_ma} and MA{slow_ma}"

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
    buy_cond = (oversold_min <= rsi <= oversold_max) and (close > ma_slow) and (macd_hist > 0)
    sell_cond = (rsi > overbought) and (close < ma_fast) and (macd_hist < 0)

    reasons = []

    if buy_cond:
        signal = "BUY"
        reasons.append(f"RSI ({rsi:.1f}) is in oversold-recovery zone ({oversold_min}–{oversold_max})")
        reasons.append(f"Price is above MA{slow_ma} — bullish trend")
        reasons.append(f"MACD histogram is positive — bullish momentum")
        if vol_pass:
            reasons.append("Volume confirms the move (above average)")
            confidence = "High"
        else:
            reasons.append("Volume is below average — confirmation weak")
            confidence = "Medium"

    elif sell_cond:
        signal = "SELL"
        reasons.append(f"RSI ({rsi:.1f}) is in overbought territory (> {overbought})")
        reasons.append(f"Price is below MA{fast_ma} — short-term bearish")
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
        bull_score = sum([oversold_min <= rsi <= oversold_max, close > ma_slow, macd_hist > 0])
        bear_score = sum([rsi > overbought, close < ma_fast, macd_hist < 0])

        if bull_score == 2 or bear_score == 2:
            confidence = "Medium"
            reasons.append("Most conditions partially met — waiting for full confirmation")
        else:
            confidence = "Low"
            reasons.append("Indicators are mixed — no clear directional signal")

        reasons.append(f"RSI at {rsi:.1f} (neutral zone or not in {oversold_min}–{oversold_max}/{overbought}+ range)")

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

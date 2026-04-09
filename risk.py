"""
risk.py — Position Sizing & Risk Management
Calculates trade plans, generates risk warnings, and exports to Excel.
"""

import math
from io import BytesIO

import pandas as pd


# ── Trade Plan ────────────────────────────────────────────────────────────────

def calculate_trade_plan(df: pd.DataFrame,
                         capital: float,
                         risk_percent: float = 1.0) -> dict:
    """
    Calculate a complete trade plan based on ATR-derived stop loss.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with at least 'Close' and 'ATR' columns.
    capital : float
        Total trading capital in INR.
    risk_percent : float
        Percentage of capital risked per trade (default 1.0%).

    Returns
    -------
    dict
        Trade plan with entry, stop loss, target, position size, etc.
    """
    if df is None or df.empty:
        raise ValueError("DataFrame is empty — cannot calculate trade plan.")

    required = ["Close", "ATR"]
    if not all(c in df.columns for c in required):
        raise ValueError(f"DataFrame must contain columns: {required}")

    latest = df.iloc[-1]
    entry_price = float(latest["Close"])
    atr = float(latest["ATR"])

    if pd.isna(atr) or atr <= 0:
        raise ValueError("ATR value is not available yet. "
                         "Fetch more historical data and try again.")

    stop_loss = entry_price - (1.5 * atr)
    risk_per_share = entry_price - stop_loss          # = 1.5 * ATR
    reward_per_share = 2 * risk_per_share             # 1:2 R:R
    target = entry_price + reward_per_share

    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0.0

    risk_amount = capital * risk_percent / 100
    position_size = math.floor(risk_amount / risk_per_share) if risk_per_share > 0 else 0

    total_investment = position_size * entry_price
    potential_loss = position_size * risk_per_share
    potential_profit = position_size * reward_per_share

    return {
        "entry_price": round(entry_price, 2),
        "stop_loss": round(stop_loss, 2),
        "target": round(target, 2),
        "risk_per_share": round(risk_per_share, 2),
        "reward_per_share": round(reward_per_share, 2),
        "rr_ratio": round(rr_ratio, 2),
        "risk_amount": round(risk_amount, 2),
        "position_size": position_size,
        "total_investment": round(total_investment, 2),
        "potential_loss": round(potential_loss, 2),
        "potential_profit": round(potential_profit, 2),
    }


# ── Risk Warnings ─────────────────────────────────────────────────────────────

def get_risk_warnings(trade_plan: dict, signal_data: dict) -> list:
    """
    Generate a list of risk warning messages.

    Parameters
    ----------
    trade_plan : dict
        Output of :func:`calculate_trade_plan`.
    signal_data : dict
        Output of :func:`strategy.generate_signal`.

    Returns
    -------
    list[dict]
        Each dict has keys 'type' ('danger'|'warning'|'success') and 'message'.
    """
    warnings = []

    rr = trade_plan.get("rr_ratio", 0)
    signal = signal_data.get("signal", "HOLD")
    confidence = signal_data.get("confidence", "Low")

    if signal == "HOLD":
        warnings.append({
            "type": "warning",
            "message": "⚠️ No clear signal → Wait for better setup",
        })
        return warnings

    if rr < 1.5:
        warnings.append({
            "type": "danger",
            "message": "❌ RR < 1.5 → Trade not recommended",
        })
    elif rr < 2.0:
        warnings.append({
            "type": "warning",
            "message": "⚠️ RR below 2.0 → Proceed with caution",
        })

    if confidence == "Low":
        warnings.append({
            "type": "warning",
            "message": "⚠️ Indicators not aligned → Low probability trade",
        })

    if rr >= 2.0 and confidence != "Low":
        warnings.append({
            "type": "success",
            "message": "✅ All conditions met → Valid setup",
        })

    return warnings


# ── Excel Export ──────────────────────────────────────────────────────────────

def export_trade_plan_to_excel(trade_plan: dict,
                               signal_data: dict,
                               warnings: list,
                               ticker: str) -> BytesIO:
    """
    Export trade plan, indicator statuses, and warnings to an Excel workbook.

    Parameters
    ----------
    trade_plan : dict
        Output of :func:`calculate_trade_plan`.
    signal_data : dict
        Output of :func:`strategy.generate_signal`.
    warnings : list
        Output of :func:`get_risk_warnings`.
    ticker : str
        Stock ticker symbol.

    Returns
    -------
    BytesIO
        In-memory Excel file buffer ready for download.
    """
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:  # type: ignore[abstract]
        # ── Sheet 1: Trade Plan ───────────────────────────────────────────────
        plan_rows = [
            ("Ticker", ticker),
            ("Signal", signal_data.get("signal", "N/A")),
            ("Confidence", signal_data.get("confidence", "N/A")),
            ("Entry Price (₹)", trade_plan["entry_price"]),
            ("Stop Loss (₹)", trade_plan["stop_loss"]),
            ("Target (₹)", trade_plan["target"]),
            ("Risk / Share (₹)", trade_plan["risk_per_share"]),
            ("Reward / Share (₹)", trade_plan["reward_per_share"]),
            ("RR Ratio", f"1:{trade_plan['rr_ratio']}"),
            ("Risk Amount (₹)", trade_plan["risk_amount"]),
            ("Position Size (shares)", trade_plan["position_size"]),
            ("Total Investment (₹)", trade_plan["total_investment"]),
            ("Potential Loss (₹)", trade_plan["potential_loss"]),
            ("Potential Profit (₹)", trade_plan["potential_profit"]),
        ]
        df_plan = pd.DataFrame(plan_rows, columns=["Parameter", "Value"])
        df_plan.to_excel(writer, sheet_name="Trade Plan", index=False)

        # ── Sheet 2: Indicators ───────────────────────────────────────────────
        ind_status = signal_data.get("indicator_status", {})
        ind_rows = []
        for ind_name, ind_info in ind_status.items():
            ind_rows.append({
                "Indicator": ind_name.upper(),
                "Value": ind_info.get("value", "N/A"),
                "Status": ind_info.get("status", "N/A"),
                "Pass": "✅" if ind_info.get("pass") else "❌",
            })
        df_indicators = pd.DataFrame(ind_rows)
        df_indicators.to_excel(writer, sheet_name="Indicators", index=False)

        # ── Sheet 3: Warnings ─────────────────────────────────────────────────
        warn_rows = [
            {"Type": w["type"].upper(), "Message": w["message"]}
            for w in warnings
        ]
        if not warn_rows:
            warn_rows = [{"Type": "INFO", "Message": "No warnings generated."}]
        df_warnings = pd.DataFrame(warn_rows)
        df_warnings.to_excel(writer, sheet_name="Warnings", index=False)

    buffer.seek(0)
    return buffer

"""
indicators.py — Technical Indicator Calculations
All functions accept a DataFrame and return it with new indicator columns added.
"""

import pandas as pd
import numpy as np


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate the Relative Strength Index (RSI).

    Adds column: RSI
    """
    df = df.copy()
    delta = df["Close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    return df


def calculate_moving_averages(df: pd.DataFrame,
                             fast_ma: int = 20,
                             slow_ma: int = 50) -> pd.DataFrame:
    """
    Calculate fast, slow, and 200 period Simple Moving Averages.

    The fast and slow periods are configurable; their results are stored in
    columns named ``MA_FAST`` and ``MA_SLOW`` respectively so downstream code
    always uses consistent column names regardless of the chosen periods.

    Adds columns: MA_FAST, MA_SLOW, MA200
    """
    df = df.copy()
    df["MA_FAST"] = df["Close"].rolling(window=fast_ma).mean()
    df["MA_SLOW"] = df["Close"].rolling(window=slow_ma).mean()
    df["MA200"] = df["Close"].rolling(window=200).mean()
    return df


def calculate_macd(df: pd.DataFrame,
                   fast: int = 12,
                   slow: int = 26,
                   signal: int = 9) -> pd.DataFrame:
    """
    Calculate MACD, Signal line, and Histogram.

    Adds columns: MACD, MACD_Signal, MACD_Hist
    """
    df = df.copy()
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()

    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    return df


def calculate_volume_avg(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Calculate the rolling average volume.

    Adds column: Vol_Avg
    """
    df = df.copy()
    df["Vol_Avg"] = df["Volume"].rolling(window=period).mean()
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate the Average True Range (ATR).

    Adds column: ATR
    """
    df = df.copy()
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = true_range.rolling(window=period).mean()

    return df


def add_all_indicators(df: pd.DataFrame,
                       fast_ma: int = 20,
                       slow_ma: int = 50) -> pd.DataFrame:
    """
    Master function — applies all indicators in sequence.

    Parameters
    ----------
    df : pd.DataFrame
        Raw OHLCV DataFrame.
    fast_ma : int
        Period for the fast moving average (default: 20).
    slow_ma : int
        Period for the slow moving average (default: 50).

    Adds columns: RSI, MA_FAST, MA_SLOW, MA200, MACD, MACD_Signal, MACD_Hist,
                  Vol_Avg, ATR
    """
    df = calculate_rsi(df)
    df = calculate_moving_averages(df, fast_ma=fast_ma, slow_ma=slow_ma)
    df = calculate_macd(df)
    df = calculate_volume_avg(df)
    df = calculate_atr(df)
    return df

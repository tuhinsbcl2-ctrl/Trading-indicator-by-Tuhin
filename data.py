"""
data.py — Data Fetching Module
Fetches OHLCV stock data from Yahoo Finance for NSE stocks.
"""

import yfinance as yf
import pandas as pd


def fetch_stock_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a given NSE stock ticker.

    Parameters
    ----------
    ticker : str
        NSE stock ticker symbol (e.g., 'RELIANCE.NS').
    period : str
        Data period to fetch (default: '1y' for 1 year).

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: Open, High, Low, Close, Volume.
        Returns an empty DataFrame on error.
    """
    try:
        if not ticker or not isinstance(ticker, str):
            raise ValueError("Ticker must be a non-empty string.")

        stock = yf.Ticker(ticker.strip())
        df = stock.history(period=period)

        if df is None or df.empty:
            raise ValueError(f"No data returned for ticker '{ticker}'. "
                             "Please check the ticker symbol.")

        # Keep only OHLCV columns
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

        # Drop rows with all NaN values
        df.dropna(how="all", inplace=True)

        # Ensure the index is a DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # Remove timezone info for cleaner display
        if df.index.tzinfo is not None:
            df.index = df.index.tz_localize(None)

        return df

    except Exception as exc:
        # Re-raise with a user-friendly message so callers can display it
        raise RuntimeError(f"Failed to fetch data for '{ticker}': {exc}") from exc

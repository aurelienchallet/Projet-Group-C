import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf


class DataHandler:
    def __init__(self):
        self.raw_sentiment_df = None
        self.raw_commodities_data_df = None
        self.processed_sentiment_df = None
        self.processed_commodities_data_df = None
        self.commodities_data_df_return = None
        self.annualized_returns = None
        self.covariance_matrix = None

    def load_data(self, sentiment_path: str, commodities_path: str):
        self.raw_sentiment_df = pd.read_csv(sentiment_path)
        self.raw_commodities_data_df = pd.read_csv(commodities_path)

        self._preprocess_data()

    def _preprocess_data(self):
        # Process sentiment data
        sentiment_df = self.raw_sentiment_df.copy()
        sentiment_df["Date"] = pd.to_datetime(
            sentiment_df["Date"].str.replace(".", "-", regex=False), errors="coerce"
        ).dt.tz_localize(None)
        sentiment_df = sentiment_df.set_index("Date")

        # Process commodities data
        commodities_data_df = self.raw_commodities_data_df.copy()
        commodities_data_df["Date"] = pd.to_datetime(
            commodities_data_df["Date"], errors="coerce"
        ).dt.tz_localize(None)

        # Calculate returns and covariance matrix
        commodities_data_df = commodities_data_df.set_index("Date")
        commodities_data_df_return = commodities_data_df.pct_change()
        commodities_data_df_return.columns = (
            commodities_data_df_return.columns.str.replace("Price_", "")
        )
        annualized_returns = commodities_data_df_return.mean() * 252

        covariance_matrix = (
            commodities_data_df_return.cov() * 252
        )  # Annualized covariance matrix

        # Store processed data
        self.processed_sentiment_df = sentiment_df
        self.processed_commodities_data_df = commodities_data_df
        self.commodities_data_df_return = commodities_data_df_return
        self.annualized_returns = annualized_returns
        self.covariance_matrix = covariance_matrix

    def get_sentiment_data(self):
        return self.processed_sentiment_df.copy()

    def get_commodities_data(self):
        return self.processed_commodities_data_df.copy()

    def get_commodities_returns(self):
        return self.commodities_data_df_return.copy()

    def get_annualized_returns(self):
        return self.annualized_returns.copy()

    def get_covariance_matrix(self):
        return self.covariance_matrix.copy()


class CurrentResults:
    def __init__(self):
        self.results = {}

    def set_result(self, key: str, value):
        self.results[key] = value

    def get_result(self, key: str, default=None):
        return self.results.get(key, default)

    def clear_results(self):
        self.results.clear()


@st.cache_data
def get_sp500_data(start, end):
    start_str = pd.Timestamp(start).strftime("%Y-%m-%d")
    end_str = pd.Timestamp(end).strftime("%Y-%m-%d")

    try:
        import requests
        from io import StringIO
        url = (
            f"https://fred.stlouisfed.org/graph/fredgraph.csv"
            f"?id=SP500&observation_start={start_str}&observation_end={end_str}"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        sp500_data = pd.read_csv(StringIO(resp.text), parse_dates=["observation_date"])
        sp500_data = sp500_data.rename(columns={"observation_date": "Date", "SP500": "Close"})
        sp500_data = sp500_data[sp500_data["Close"] != "."].copy()
        sp500_data["Close"] = sp500_data["Close"].astype(float)
        sp500_data = sp500_data.set_index("Date")
        sp500_data["Return"] = sp500_data["Close"].pct_change()
        sp500_data = sp500_data.dropna(subset=["Return"])
        sp500_data["Cumulative_Return"] = (1 + sp500_data["Return"]).cumprod()
        sp500_data["Year"] = sp500_data.index.year
        return sp500_data
    except Exception as e:
        st.warning(f"Impossible de charger les données S&P 500 : {e}")
        return pd.DataFrame()


def initialize_session_state():
    # Initialize DataHandler if not already in session_state
    if "data_handler" not in st.session_state:
        data_handler = DataHandler()
        data_handler.load_data(
            sentiment_path="resources/sentiment.csv",
            commodities_path="resources/cleaned_commodities_data.csv",
        )
        st.session_state["data_handler"] = data_handler

    # Initialize CurrentResults if not already in session_state
    if "current_results" not in st.session_state:
        st.session_state["current_results"] = CurrentResults()

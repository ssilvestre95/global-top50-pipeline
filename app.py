import os

import pandas as pd
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SNOWFLAKE_CONFIG = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
}
SNOWFLAKE_TABLE = os.getenv("SNOWFLAKE_TABLE", "TICKERS")

st.set_page_config(page_title="Stock Tickers Dashboard", layout="wide")


@st.cache_data(ttl=300)  # cache for 5 minutes, avoids hitting Snowflake on every interaction
def load_data():
    connection = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    try:
        query = f'SELECT * FROM "{SNOWFLAKE_TABLE.upper()}"'
        df = pd.read_sql(query, connection)
    finally:
        connection.close()
    return df


st.title("📈 Stock Tickers Dashboard")

df = load_data()

st.metric("Total tickers", len(df))
if "LOADED_AT" in df.columns and not df.empty:
    st.caption(f"Last updated: {df['LOADED_AT'].max()}")

# search/filter box
search = st.text_input("Search by symbol or description")
if search:
    mask = (
        df["SYMBOL"].str.contains(search, case=False, na=False)
        | df["DESCRIPTION"].str.contains(search, case=False, na=False)
    )
    df = df[mask]

st.dataframe(df, use_container_width=True)

# breakdown by exchange type (example chart)
if "TYPE" in df.columns:
    st.bar_chart(df["TYPE"].value_counts())
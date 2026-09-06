import os
from datetime import datetime, timezone

import requests
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

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

EXCHANGE = "US"

url = (
    f"https://finnhub.io/api/v1/stock/symbol"
    f"?exchange={EXCHANGE}"
    f"&token={FINNHUB_API_KEY}"
)

response = requests.get(url)
data = response.json()

if not isinstance(data, list):
    print("API Error:")
    print(data)
    tickers = []
else:
    tickers = data

print(f"Tickers fetched from Finnhub: {len(tickers)}")

example_ticker = {
    "symbol": "AAPL",
    "displaySymbol": "AAPL",
    "description": "APPLE INC",
    "type": "Common Stock",
    "currency": "USD",
    "figi": "BBG000B9XRY4",
    "mic": "XNAS",
    "shareClassFIGI": "BBG001S5N8V8",
}

columns = list(example_ticker.keys())
column_sql = ", ".join(f'"{column.upper()}" VARCHAR' for column in columns)
insert_columns = ", ".join(f'"{column.upper()}"' for column in columns)
placeholders = ", ".join("%s" for _ in columns)

# extra column for the load timestamp
column_sql += ', "LOADED_AT" TIMESTAMP_NTZ'
insert_columns += ', "LOADED_AT"'
placeholders += ", %s"

required_config = {
    name: value
    for name, value in SNOWFLAKE_CONFIG.items()
    if name != "role"
}
missing_config = [name for name, value in required_config.items() if not value]
if missing_config:
    raise RuntimeError(
        "Missing Snowflake environment variables: "
        + ", ".join(f"SNOWFLAKE_{name.upper()}" for name in missing_config)
    )

if not tickers:
    print("No data from Finnhub — skipping Snowflake load.")
else:
    loaded_at = datetime.now(timezone.utc)

    connection = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP TABLE IF EXISTS "{SNOWFLAKE_TABLE.upper()}"')
            cursor.execute(
                f'CREATE TABLE "{SNOWFLAKE_TABLE.upper()}" '
                f"({column_sql})"
            )
            cursor.executemany(
                f'INSERT INTO "{SNOWFLAKE_TABLE.upper()}" ({insert_columns}) '
                f"VALUES ({placeholders})",
                [
                    tuple(ticker.get(column) for column in columns) + (loaded_at,)
                    for ticker in tickers
                ],
            )
        connection.commit()
        print(f"Loaded {len(tickers)} tickers at {loaded_at.isoformat()}")
    except Exception as e:
        print(f"Error writing to Snowflake: {e}")
        raise
    finally:
        connection.close()
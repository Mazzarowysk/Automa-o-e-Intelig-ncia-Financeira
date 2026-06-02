import requests
import pandas as pd
from datetime import datetime, timedelta

URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados"
START = datetime(1995, 1, 1)
END = datetime(2026, 5, 28)
MAX_YEARS = 10

def fetch_window(start, end):
    params = {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
    }
    resp = requests.get(URL, params=params, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return pd.DataFrame(resp.json())

windows = []
cur = START
while cur < END:
    win_end = min(cur + timedelta(days=MAX_YEARS * 365 + 2), END)
    print(f"Fetching {cur.date()} to {win_end.date()}...")
    df = fetch_window(cur, win_end)
    df["data"] = pd.to_datetime(df["data"], dayfirst=True)
    df["valor"] = df["valor"].astype(float)
    windows.append(df)
    cur = win_end + timedelta(days=1)

usd = pd.concat(windows, ignore_index=True)
usd = usd.drop_duplicates(subset="data").sort_values("data").set_index("data")
usd.index.name = "date"

print(f"Shape: {usd.shape}")
print(f"Range: {usd.index.min()} to {usd.index.max()}")
print(usd.describe())

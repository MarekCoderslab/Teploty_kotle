import requests
import json
import time
import csv
from pathlib import Path

CLIENT_ID = "6986ceaef493ff65c90bd0c4"
CLIENT_SECRET = "6kay9rA1ZDbqqDlykzti35hZKb7vVY"

TOKEN_FILE = Path("/home/pi/netatmo/netatmo_tokens.json")

CSV_FILE = Path("netatmo_data.csv")


def load_tokens():
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None


def save_tokens(access, refresh):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"access_token": access, "refresh_token": refresh}, f)



def refresh_access_token(refresh_token):
    url = "https://api.netatmo.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    r = requests.post(url, data=data)
    r.raise_for_status()
    raw = r.json()

    access = raw["access_token"]
    refresh = raw["refresh_token"]

    # uložit ve STEJNÉM formátu jako climate skript
    save_tokens(access, refresh)

    return access



def get_access_token():
    tokens = load_tokens()
    if not tokens:
        raise RuntimeError("Chybí tokeny – vlož sem svůj refresh token poprvé ručně.")

    return refresh_access_token(tokens["refresh_token"])


def get_station_data(access_token):
    url = "https://api.netatmo.com/api/getstationsdata"
    headers = {"Authorization": f"Bearer {access_token}"}

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def save_to_csv(data):
    device = data["body"]["devices"][0]
    indoor = device["dashboard_data"]
    outdoor = device["modules"][0]["dashboard_data"]

    row = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(indoor["time_utc"])),
        "temp_indoor": indoor["Temperature"],
        "humidity_indoor": indoor["Humidity"],
        "co2": indoor["CO2"],
        "pressure": indoor["Pressure"],
        "temp_outdoor": outdoor["Temperature"],
        "humidity_outdoor": outdoor["Humidity"],
    }

    write_header = not CSV_FILE.exists()

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)


if __name__ == "__main__":
    access_token = get_access_token()
    data = get_station_data(access_token)
    save_to_csv(data)

    print("Uloženo do CSV.")


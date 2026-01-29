import requests
import time
import csv

# ---- VYPLŇ SVÉ ÚDAJE ----
CLIENT_ID = "6975d41d173e20a68d0a6585"
CLIENT_SECRET = "SDTuaVw1ZMC8xhJ8vlozLqx1a"
USERNAME = "marek.dejdar@gmail.com"
PASSWORD = "m.Dejdam1"
DEVICE_ID = "TVŮJ_DEVICE_ID"   # např. hlavní vnitřní modul
MODULE_ID = "TVŮJ_MODULE_ID"   # např. venkovní modul
# --------------------------

# 1) Získání access tokenu
def get_token():
    url = "https://api.netatmo.com/oauth2/token"
    data = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": USERNAME,
        "password": PASSWORD,
        "scope": "read_station"
    }
    r = requests.post(url, data=data)
    return r.json()["access_token"]

# 2) Stažení dat
def get_measurements(token, date_begin, date_end):
    url = "https://api.netatmo.com/api/getmeasure"
    params = {
        "access_token": token,
        "device_id": DEVICE_ID,
        "module_id": MODULE_ID,
        "scale": "max",
        "type": "temperature",
        "date_begin": date_begin,
        "date_end": date_end
    }
    r = requests.get(url, params=params)
    return r.json()

# 3) Uložení do CSV
def save_to_csv(data, filename="netatmo_data.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "temperature_C"])
        for ts, value in data["body"].items():
            writer.writerow([ts, value[0]])

# ---- SPUŠTĚNÍ ----
token = get_token()

# příklad: posledních 7 dní
now = int(time.time())
week_ago = now - 7 * 24 * 3600

data = get_measurements(token, week_ago, now)
save_to_csv(data)

print("Hotovo — data uložená v netatmo_data.csv")

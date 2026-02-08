
import json
import requests
import csv
from pathlib import Path

# ---------------------------------------------------------
# KONFIGURACE
# ---------------------------------------------------------

TOKEN_FILE = Path("/home/pi/netatmo/netatmo_climate_tokens.json")
CSV_FILE = Path("/home/pi/netatmo/netatmo_climate.csv")

CLIENT_ID = "6986ceaef493ff65c90bd0c4"
CLIENT_SECRET = "6kay9rA1ZDbqqDlykzti35hZKb7vVY"
HOME_ID = "5923ef916d1dbdb79a8b476c"


# ---------------------------------------------------------
# TOKEN MANAGEMENT
# ---------------------------------------------------------

def load_tokens():
    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


def save_tokens(access, refresh):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"access_token": access, "refresh_token": refresh}, f)


def refresh_access_token():
    tokens = load_tokens()
    refresh_token = tokens["refresh_token"]

    url = "https://api.netatmo.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    r = requests.post(url, data=data)
    r.raise_for_status()
    resp = r.json()

    access = resp["access_token"]
    refresh = resp["refresh_token"]

    save_tokens(access, refresh)
    return access


def get_access_token():
    return refresh_access_token()


# ---------------------------------------------------------
# API CALLS
# ---------------------------------------------------------

def get_climate_data(access_token, home_id):
    headers = {"Authorization": f"Bearer {access_token}"}

    # homesdata
    r1 = requests.get("https://api.netatmo.com/api/homesdata", headers=headers)
    r1.raise_for_status()
    home = r1.json()

    # homestatus
    r2 = requests.get(
        f"https://api.netatmo.com/api/homestatus?home_id={home_id}",
        headers=headers
    )
    r2.raise_for_status()
    status = r2.json()

    return home, status


# ---------------------------------------------------------
# PARSING
# ---------------------------------------------------------

def parse_climate_data(home, status):
    ts = status["time_server"]

    room = status["body"]["home"]["rooms"][0]
    temp_indoor = room["therm_measured_temperature"]
    setpoint = room["therm_setpoint_temperature"]

    modules = status["body"]["home"]["modules"]

    boiler_status = None
    temp_outdoor = None
    pressure = None

    for m in modules:
        if m["type"] == "NATherm1":
            boiler_status = m.get("boiler_status")

        if m["type"] == "NAMain":  # indoor modul
            pressure = m["pressure"]

        if m["type"] == "NAModule1":  # outdoor modul
            temp_outdoor = m["temperature"]

    return [ts, temp_indoor, temp_outdoor, setpoint, boiler_status, pressure]

# ---------------------------------------------------------
# CSV LOGGING
# ---------------------------------------------------------

def save_climate_csv(row):
    file_exists = CSV_FILE.exists()

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            # writer.writerow(["timestamp", "temperature", "setpoint", "mode", "boiler"])
            writer.writerow(["timestamp", "temp_indoor", "temp_outdoor", "setpoint", "boiler", "pressure"])

        writer.writerow(row)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    access_token = get_access_token()
    home, status = get_climate_data(access_token, HOME_ID)
    row = parse_climate_data(home, status)
    save_climate_csv(row)


if __name__ == "__main__":
    main()




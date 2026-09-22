import requests
import base64

GITHUB_TOKEN = "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"
REPO = "MarekCoderslab/Rx_Tx_new"
FILE_PATH = "traffic_log_dif.csv"
LOCAL_FILE = "/home/pi/traffic_log_dif.csv"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# 1) Získat SHA existujícího souboru
url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    sha = response.json()["sha"]
else:
    sha = None  # soubor ještě neexistuje

# 2) Načíst lokální CSV
with open(LOCAL_FILE, "rb") as f:
    content = f.read()

encoded = base64.b64encode(content).decode("utf-8")

# 3) Připravit payload
data = {
    "message": "Auto update",
    "content": encoded
}

if sha:
    data["sha"] = sha  # nutné pro update existujícího souboru

# 4) Upload / update
put_response = requests.put(url, json=data, headers=headers)
print(put_response.json())

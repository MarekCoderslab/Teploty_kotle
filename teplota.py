import time
import csv
import os
from datetime import datetime

# pevně dané ID čidla
sensor_id = "28-00000051daa5"

base_dir = '/sys/bus/w1/devices/'
device_file = f"{base_dir}{sensor_id}/w1_slave"

csv_file = "/home/pi/teplota_pradelna.csv"

def read_temp():
    with open(device_file, 'r') as f:
        lines = f.readlines()

    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        with open(device_file, 'r') as f:
            lines = f.readlines()

    temp_str = lines[1].split('t=')[1]
    return float(temp_str) / 1000.0

# vytvoř CSV pokud neexistuje
if not os.path.exists(csv_file):
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["datetime", "temperature_C"])

# jednorázové měření
temp = read_temp()
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with open(csv_file, "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([now, temp])


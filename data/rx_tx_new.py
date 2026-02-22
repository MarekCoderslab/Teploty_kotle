import os
import csv
import json
from datetime import datetime


# ---------- SNMP část ----------
def snmp_get(oid):
    from pysnmp.hlapi import SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity, getCmd
    iterator = getCmd(
        SnmpEngine(),
        CommunityData('omegadejdar', mpModel=0),
        UdpTransportTarget(('192.168.11.100', 161), timeout=3, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )
    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    if errorIndication or errorStatus:
        return None
    for varBind in varBinds:
        value = varBind[1]
        if isinstance(value, (int, float)):
            return int(value)
        elif hasattr(value, 'prettyPrint'):
            return value.prettyPrint()
        else:
            return str(value)

def snmp_ticks_to_hours(ticks):
    try:
        ms = int(float(ticks)) * 10
        return round(ms / 3_600_000, 2)
    except (TypeError, ValueError):
        return None

def safe_bytes_to_mb(current, previous=None, unit='binary', max_counter=2**32):
    try:
        current = int(current)
        if previous is not None:
            previous = int(previous)
            if current >= previous:
                delta = current - previous
            else:
                delta = (max_counter - previous) + current
        else:
            delta = current
        if unit == 'binary':
            return round(delta / (1024 * 1024), 2)
        elif unit == 'decimal':
            return round(delta / 1_000_000, 2)
        else:
            return None
    except (TypeError, ValueError):
        return None

# ---------- Absolutní cesty ----------
raw_log = '/home/pi/traffic_log.csv'
dif_log = '/home/pi/traffic_log_dif.csv'
state_file = '/home/pi/traffic_state.json'

# ---------- OID definice ----------
oids = {
    'WAN_IN': '1.3.6.1.2.1.2.2.1.10.2',
    'WAN_OUT': '1.3.6.1.2.1.2.2.1.16.2',
    'SYS_UPTIME': '1.3.6.1.2.1.1.3.0'
}

# ---------- Získání dat ----------
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
raw_isp_in = snmp_get(oids['WAN_IN'])
raw_lan_out = snmp_get(oids['WAN_OUT'])
raw_isp_uptime = snmp_get(oids['SYS_UPTIME'])
isp_uptime = snmp_ticks_to_hours(raw_isp_uptime)

# ---------- Načtení předchozího stavu ----------
if os.path.exists(state_file):
    with open(state_file, 'r') as f:
        state = json.load(f)
else:
    state = {}

# ---------- Výpočty ----------
delta_time_hr = None
delta_isp_in = None
delta_lan_out = None
restart = False

if 'timestamp' in state:
    prev_time = datetime.strptime(state['timestamp'], '%Y-%m-%d %H:%M:%S')
    delta_time_hr = round((datetime.now() - prev_time).total_seconds() / 3600, 2)

if 'uptime' in state and isp_uptime is not None:
    restart = isp_uptime < state['uptime']

if not restart:
    delta_isp_in = safe_bytes_to_mb(raw_isp_in, state.get('isp_in'))
    delta_lan_out = safe_bytes_to_mb(raw_lan_out, state.get('lan_out'))

# ---------- Zápis do traffic_log.csv ----------
write_header = not os.path.exists(raw_log) or os.path.getsize(raw_log) == 0

with open(raw_log, mode='a', newline='') as file:
    writer = csv.writer(file)
    if write_header:
        writer.writerow(['Time', 'RAW_ISP_IN', 'RAW_LAN_OUT', 'ISP_uptime'])
    writer.writerow([timestamp, raw_isp_in, raw_lan_out, isp_uptime])

# ---------- Zápis do traffic_log_dif.csv ----------
write_header_dif = not os.path.exists(dif_log) or os.path.getsize(dif_log) == 0
with open(dif_log, mode='a', newline='') as file:
    writer = csv.writer(file)
    if write_header_dif:
        writer.writerow(['Time', 'ISP_IN_MB', 'LAN_OUT_MB', 'ISP_uptime', 'Delta_ISP_IN_MB', 'Delta_LAN_OUT_MB', 'Delta_Time_hr', 'Restart'])
    writer.writerow([
        timestamp,
        safe_bytes_to_mb(raw_isp_in),
        safe_bytes_to_mb(raw_lan_out),
        isp_uptime,
        delta_isp_in,
        delta_lan_out,
        delta_time_hr,
        restart
    ])

# ---------- Uložení aktuálního stavu ----------
with open(state_file, 'w') as f:
    json.dump({
        'timestamp': timestamp,
        'isp_in': raw_isp_in,
        'lan_out': raw_lan_out,
        'uptime': isp_uptime
    }, f)

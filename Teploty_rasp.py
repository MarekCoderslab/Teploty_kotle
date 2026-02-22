import pathlib
import zoneinfo
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# ZÁKLADNÍ NASTAVENÍ
# ---------------------------------------------------------
st.set_page_config(
    page_title="Teploty kotle – Immergas",
    layout="wide"
)

TZ = "Europe/Prague"
tzinfo = zoneinfo.ZoneInfo(TZ)

PATH_NETATMO = "https://raw.githubusercontent.com/MarekCoderslab/Teploty_kotle/main/data/netatmo_climate.csv"
PATH_CLIMATE = "https://raw.githubusercontent.com/MarekCoderslab/Teploty_kotle/main/data/netatmo_climate.csv"
PATH_PRADELNA = "https://raw.githubusercontent.com/MarekCoderslab/Teploty_kotle/main/data/teplota_pradelna.csv"
PATH_KOTEL = "https://raw.githubusercontent.com/MarekCoderslab/Teploty_kotle/main/data/teplota_log.csv"

# ---------------------------------------------------------
# FUNKCE
# ---------------------------------------------------------
def compute_times(hours_back: int, end_date_value: datetime.date, end_hour_value: int):
    end_tz = pd.Timestamp(
        year=end_date_value.year,
        month=end_date_value.month,
        day=end_date_value.day,
        hour=end_hour_value,
        minute=0,
        second=0,
        tz=TZ,
    )
    start_tz = end_tz - pd.Timedelta(hours=hours_back)
    return start_tz, end_tz, start_tz.tz_localize(None), end_tz.tz_localize(None)


def hokejka3(temp_in: float) -> float:
    return -0.233333 * temp_in + 35.333333 if temp_in <= 10 else 33.0


@st.cache_data(ttl=300)
def load_netatmo(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert(TZ)
    df["timestamp_str"] = df["timestamp"].dt.strftime("%d.%m.%Y %H:%M:%S")
    df["Boiler_water_2"] = df["temp_outdoor"].apply(hokejka3)
    return df


@st.cache_data(ttl=300)
def load_climate(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["time_local"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert(TZ)
    df["time_local_str"] = df["time_local"].dt.strftime("%d.%m.%Y %H:%M:%S")
    df["time"] = pd.to_datetime(df["timestamp"], unit="s") + pd.to_timedelta(1, "h")
    return df


@st.cache_data(ttl=300)
def load_pradelna(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path, header=None, names=["cas", "tepl"])
    df["cas"] = pd.to_datetime(df["cas"], errors="coerce")
    df["tepl"] = pd.to_numeric(df["tepl"], errors="coerce")
    return df.dropna().sort_values("cas").drop_duplicates("cas")


@st.cache_data(ttl=300)
def load_kotel(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path, header=None, names=["Time", "Value"])
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df.dropna()


# ---------------------------------------------------------
# GRAFICKÉ FUNKCE (NEZMĚNĚNY)
# ---------------------------------------------------------
# ... (ponechávám přesně tak, jak jsi poslal – žádné změny)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.header("Časové okno")

if "hours_back" not in st.session_state:
    st.session_state.hours_back = 22
if "end_date" not in st.session_state:
    st.session_state.end_date = datetime.now(tzinfo).date()
if "end_hour" not in st.session_state:
    st.session_state.end_hour = (datetime.now(tzinfo).hour + 1) % 24

hours_back_input = st.sidebar.slider("Kolik hodin zpět", 1, 48, st.session_state.hours_back)
end_date_input = st.sidebar.date_input("End datum", st.session_state.end_date)
end_hour_input = st.sidebar.selectbox("End hodina", list(range(24)), index=st.session_state.end_hour)

if st.sidebar.button("Aktualizovat časové okno"):
    st.session_state.hours_back = hours_back_input
    st.session_state.end_date = end_date_input
    st.session_state.end_hour = end_hour_input

start_tz, end_tz, start_naive, end_naive = compute_times(
    st.session_state.hours_back,
    st.session_state.end_date,
    st.session_state.end_hour
)

# ---------------------------------------------------------
# NAČTENÍ DAT
# ---------------------------------------------------------
df_netatmo = load_netatmo(PATH_NETATMO)
df_climate = load_climate(PATH_CLIMATE)
df_pradelna = load_pradelna(PATH_PRADELNA)

try:
    df_kotel = load_kotel(PATH_KOTEL)
except Exception:
    df_kotel = None

# ---------------------------------------------------------
# HLAVNÍ OBSAH – VŠE V JEDNOM LEVÉM SLOUPCI
# ---------------------------------------------------------
col, _ = st.columns([1, 3])

with col:

    st.header("Teploty – Immergas Victix Zeus Superior (26)")
    st.markdown(f"Zobrazené období: **{start_naive:%d.%m.%Y %H:%M} – {end_naive:%d.%m.%Y %H:%M}**")

    st.header("Souhrn – poslední stav")
    st.markdown(build_last_status_block(df_netatmo))

    st.header("Boiler output vs ekvitermní teplota")
    if df_kotel is not None:
        st.pyplot(plot_kotel_vs_netatmo(df_kotel, df_netatmo, start_tz, end_tz, start_naive, end_naive))
    else:
        st.warning("Soubor teplota_log.csv nebyl načten.")

    st.header("Indoor teplota, setpoint a stav kotle")
    st.pyplot(plot_indoor_setpoint_boiler(df_climate, start_naive, end_naive))

    st.header("Venkovní teplota a ekvitermní křivka")
    st.pyplot(plot_temp_vs_ekviterm(df_netatmo, start_naive, end_naive))

    st.header("Tlak vzduchu")
    st.pyplot(plot_pressure(df_climate))

    st.header("Teplota v prádelně")
    st.pyplot(plot_pradelna(df_pradelna, start_naive, end_naive))

    st.subheader("Netatmo – posledních 10 záznamů")
    st.dataframe(
        df_netatmo[[
            "timestamp_str", "temp_outdoor", "pressure",
            "temp_indoor", "setpoint", "Boiler_water_2", "boiler"
        ]].tail(10),
        use_container_width=True
    )

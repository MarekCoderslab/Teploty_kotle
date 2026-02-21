import pathlib
import zoneinfo
from datetime import datetime, time, timedelta

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

BASE_PATH = pathlib.Path("/Users/Marek/Library/Mobile Documents/com~apple~CloudDocs/Documents/GitHub/Teploty_kotle")


PATH_NETATMO = BASE_PATH / "netatmo_climate.csv"
PATH_CLIMATE = BASE_PATH / "netatmo_climate.csv"  # používáš stejný soubor
PATH_PRADELNA = BASE_PATH / "teplota_pradelna.csv"
PATH_KOTEL = BASE_PATH / "teplota_log.csv"  # předpoklad – uprav podle reality

# ---------------------------------------------------------
# FUNKCE
# ---------------------------------------------------------
def compute_times(hours_back: int, end_date_value: datetime.date, end_hour_value: int):
    """Vrátí start/end v tz-aware i naive podobě."""
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

    start_naive = start_tz.tz_localize(None)
    end_naive = end_tz.tz_localize(None)

    return start_tz, end_tz, start_naive, end_naive


def hokejka3(temp_in: float) -> float:
    """Ekvitermní křivka podle bodů A(-20,15) a B(40,33)."""
    if temp_in <= 10:
        return -0.233333 * temp_in + 35.333333
    else:
        return 33.0


@st.cache_data
def load_netatmo(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # timestamp už máš v sekundách → převedeme na datetime s časovou zónou
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], unit="s", utc=True)
        .dt.tz_convert(TZ)
    )
    df["timestamp_str"] = df["timestamp"].dt.strftime("%d.%m.%Y %H:%M:%S")
    # ekvitermní teplota
    df["Boiler_water_2"] = df["temp_outdoor"].apply(hokejka3)
    return df


@st.cache_data
def load_climate(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["time_local"] = (
        pd.to_datetime(df["timestamp"], unit="s", utc=True)
        .dt.tz_convert(TZ)
    )
    df["time_local_str"] = df["time_local"].dt.strftime("%d.%m.%Y %H:%M:%S")
    # pro graf setpoint vs indoor posouváš o 1 hodinu a děláš naive
    df["time"] = pd.to_datetime(df["timestamp"], unit="s") + pd.to_timedelta(1, "h")
    return df


@st.cache_data
def load_pradelna(path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path, header=None, names=["cas", "tepl"])
    df["cas"] = pd.to_datetime(df["cas"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    df["tepl"] = pd.to_numeric(df["tepl"], errors="coerce")
    df = df.dropna().sort_values("cas").drop_duplicates("cas")
    return df


@st.cache_data
def load_kotel(path: pathlib.Path) -> pd.DataFrame:
    # CSV nemá hlavičku → header=None
    df = pd.read_csv(path, header=None, names=["Time", "Value"])
    
    # převod času
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    
    df = df.dropna()
    return df



def plot_kotel_vs_netatmo(df_kotel, df_netatmo, start_tz, end_tz, start_naive, end_naive):
    fig, ax = plt.subplots(figsize=(12, 5))

    # Kotel – do Europe/Prague
    if df_kotel["Time"].dt.tz is None:
        df_kotel["Time"] = df_kotel["Time"].dt.tz_localize(TZ)
    else:
        df_kotel["Time"] = df_kotel["Time"].dt.tz_convert(TZ)

    ax.plot(
        df_kotel["Time"],
        df_kotel["Value"],
        marker=".",
        color="blue",
        label="Boiler output",
    )

    # Netatmo – timestamp už je tz-aware v Europe/Prague
    df_netatmo["time_local"] = df_netatmo["timestamp"]

    ax.plot(
        df_netatmo["time_local"],
        df_netatmo["Boiler_water_2"],
        color="green",
        label="Ekviterm temp 3",
    )

    ax.set_xlim(start_tz, end_tz)

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%d.%m. %H:%M", tz=tzinfo)
    )
    plt.xticks(rotation=45)

    ax.set_title(
        f"Boiler Immergas Victix Zeus Superior (26) temperatures "
        f"{start_naive:%d.%m.%Y %H:%M} – {end_naive:%d.%m.%Y %H:%M}"
    )
    ax.set_xlabel("Time")
    ax.set_ylabel("Boiler temp [°C]")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_indoor_setpoint_boiler(df_climate, start_naive, end_naive):
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        df_climate["time"],
        df_climate["temp_indoor"],
        label="Indoor temp",
        color="tab:blue",
        linewidth=1.5,
    )
    ax.scatter(df_climate["time"], df_climate["temp_indoor"], s=8, color="tab:blue")

    ax.plot(
        df_climate["time"],
        df_climate["setpoint"],
        label="Setpoint",
        color="tab:red",
        linewidth=1.5,
    )
    ax.scatter(df_climate["time"], df_climate["setpoint"], s=8, color="tab:red")

    ax.plot(
        df_climate["time"],
        df_climate["boiler"] + 20.5,
        label="Boiler (on/off)",
        color="tab:green",
        linewidth=1.5,
    )

    ax.set_xlim(start_naive, end_naive)

    ax.set_title("Indoor temperature vs Setpoint - Boiler ON/OFF")
    ax.set_xlabel("Čas")
    ax.set_ylabel("°C")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d.%m. %H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def plot_temp_vs_ekviterm(df_netatmo, start_naive, end_naive):
    fig, ax = plt.subplots(figsize=(12, 5))

    df_netatmo["timestamp_shifted"] = df_netatmo["timestamp"] + pd.to_timedelta(1, "h")

    ax.plot(
        df_netatmo["timestamp_shifted"],
        df_netatmo["temp_outdoor"],
        color="blue",
        label="Teplota venku",
    )
    ax.set_ylabel("Teplota venku [°C]", color="blue")
    ax.tick_params(axis="y", labelcolor="blue")

    ax2 = ax.twinx()
    ax2.plot(
        df_netatmo["timestamp_shifted"],
        df_netatmo["Boiler_water_2"],
        color="green",
        label="Ekvitermní teplota",
    )
    ax2.set_ylabel("Teplota kotle [°C]", color="green")
    ax2.tick_params(axis="y", labelcolor="green")

    ax.set_title("Venkovní teplota vs. nastavené ekvitermní teploty")
    ax.set_xlabel("Čas")

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m. %H:%M"))
    ax.tick_params(axis="x", rotation=45)
    ax.set_xlim(start_naive, end_naive)

    ax2.legend(loc="upper left")
    ax.grid(True)
    fig.tight_layout()
    return fig


def plot_pressure(df_climate):
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        df_climate["time"],
        df_climate["pressure"],
        label="Pressure (hPa)",
        color="tab:green",
        linewidth=1.5,
    )
    ax.scatter(df_climate["time"], df_climate["pressure"], s=8, color="tab:green")

    ax.set_title("Pressure over time")
    ax.set_xlabel("Čas")
    ax.set_ylabel("Pressure [hPa]")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d.%m. %H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def plot_pradelna(df_pradelna, start_naive, end_naive):
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.set_ylim(9, 15)
    ax.set_title("Teplota v prádelně")

    ax.plot(df_pradelna["cas"], df_pradelna["tepl"], linestyle="-", marker=None)
    ax.set_xlim(start_naive, end_naive)

    ax.grid()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m. %H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def build_last_status_block(df_netatmo: pd.DataFrame):
    df_net = df_netatmo.sort_values("timestamp")

    starts = (df_net["boiler"] == True) & (df_net["boiler"].shift(1) == False)
    stops = (df_net["boiler"] == False) & (df_net["boiler"].shift(1) == True)

    last_start = df_net[starts].iloc[-1]["timestamp_str"] if starts.any() else "N/A"
    last_stop = df_net[stops].iloc[-1]["timestamp_str"] if stops.any() else "N/A"

    last_timestamp = df_net.iloc[-1]["timestamp_str"]
    last_temp_outdoor = df_net.iloc[-1]["temp_outdoor"]
    last_pressure = df_net.iloc[-1]["pressure"]

    if last_start <= last_stop:
        kotel_text = (
            f"🔥 Poslední start kotle: **{last_start}**  \n"
            f"❄️ Poslední odstavení kotle: **{last_stop}**  \n"
        )
    else:
        kotel_text = (
            f"❄️ Poslední odstavení kotle: **{last_stop}**  \n"
            f"🔥 Poslední start kotle: **{last_start}**  \n"
        )

    text = (
        f"🕒 Poslední záznam v logu: **{last_timestamp}**  \n"
        f"🌡️ Poslední venkovní teplota: **{last_temp_outdoor:.1f} °C**  \n"
        f"🌬️ Poslední tlak vzduchu: **{last_pressure:.1f} hPa**  \n"
        f"{kotel_text}"
    )
    return text


# ---------------------------------------------------------
# UI – SIDEBAR (s tlačítkem)
# ---------------------------------------------------------
st.sidebar.header("Časové okno")

# Inicializace session_state
if "hours_back" not in st.session_state:
    st.session_state.hours_back = 22
if "end_date" not in st.session_state:
    st.session_state.end_date = datetime.now(tzinfo).date()
if "end_hour" not in st.session_state:
    st.session_state.end_hour = datetime.now(tzinfo).hour

# Vstupy
hours_back_input = st.sidebar.slider(
    "Kolik hodin zpět",
    min_value=1,
    max_value=48,
    value=st.session_state.hours_back,
    step=1
)

end_date_input = st.sidebar.date_input(
    "End datum",
    value=st.session_state.end_date
)

end_hour_input = st.sidebar.selectbox(
    "End hodina",
    options=list(range(24)),
    index=st.session_state.end_hour
)

# TLAČÍTKO
if st.sidebar.button("Aktualizovat časové okno"):
    st.session_state.hours_back = hours_back_input
    st.session_state.end_date = end_date_input
    st.session_state.end_hour = end_hour_input

# Výpočet časů
start_tz, end_tz, start_naive, end_naive = compute_times(
    st.session_state.hours_back,
    st.session_state.end_date,
    st.session_state.end_hour
)

st.sidebar.markdown("---")
st.sidebar.write("**start_tz:**", start_tz)
st.sidebar.write("**end_tz:**", end_tz)



# ---------------------------------------------------------
# HLAVNÍ OBSAH
# ---------------------------------------------------------
st.header("Teploty – Immergas Victix Zeus Superior (26)")

st.markdown(
    f"Zobrazené období: **{start_naive:%d.%m.%Y %H:%M} – {end_naive:%d.%m.%Y %H:%M}**"
)

# Načtení dat
df_netatmo = load_netatmo(PATH_NETATMO)
df_climate = load_climate(PATH_CLIMATE)
df_pradelna = load_pradelna(PATH_PRADELNA)

# Kotel – pokud máš teplota_log.csv, jinak tu část zakomentuj / uprav
try:
    df_kotel = load_kotel(PATH_KOTEL)
except Exception:
    df_kotel = None


# ---------------------------------------------------------
# 1) Poslední stav kotle / Netatmo
# ---------------------------------------------------------
st.header("Souhrn – poslední stav")

st.markdown(build_last_status_block(df_netatmo))



# ---------------------------------------------------------
# 2) Kotel vs ekvitermní teplota
# ---------------------------------------------------------
st.header("Boiler output vs ekvitermní teplota")

if df_kotel is not None:
    fig1 = plot_kotel_vs_netatmo(df_kotel, df_netatmo, start_tz, end_tz, start_naive, end_naive)
    st.pyplot(fig1)
else:
    st.warning("Soubor teplota_log.csv nebyl načten – zkontroluj cestu PATH_KOTEL.")

# ---------------------------------------------------------
# 3) Indoor vs setpoint vs boiler ON/OFF
# ---------------------------------------------------------
st.header("Indoor teplota, setpoint a stav kotle")

fig2 = plot_indoor_setpoint_boiler(df_climate, start_naive, end_naive)
st.pyplot(fig2)

# ---------------------------------------------------------
# 4) Venkovní teplota vs ekvitermní teplota
# ---------------------------------------------------------
st.header("Venkovní teplota a ekvitermní křivka")

fig3 = plot_temp_vs_ekviterm(df_netatmo, start_naive, end_naive)
st.pyplot(fig3)

# ---------------------------------------------------------
# 1_1) Tabulka – posledních 10 záznamů z Netatmo (pro rychlý přehled)
# ---------------------------------------------------------st.subheader("Netatmo – posledních 10 záznamů")
st.subheader("Netatmo – posledních 10 záznamů")

df_show = df_netatmo[[
    "timestamp_str",
    "temp_outdoor",
    "pressure",
    "temp_indoor",
    "setpoint",
    "Boiler_water_2",
    "boiler"
]]

st.dataframe(df_show.tail(10), use_container_width=True)




# ---------------------------------------------------------
# 5) Tlak vzduchu
# ---------------------------------------------------------
st.header("Tlak vzduchu z Climate")

fig4 = plot_pressure(df_climate)
st.pyplot(fig4)

# ---------------------------------------------------------
# 6) Teplota v prádelně
# ---------------------------------------------------------
st.header("Teplota v prádelně")

fig5 = plot_pradelna(df_pradelna, start_naive, end_naive)
st.pyplot(fig5)

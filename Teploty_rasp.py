import pathlib
import zoneinfo
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import streamlit as st


# =========================================================
# ZÁKLADNÍ NASTAVENÍ
# =========================================================

st.set_page_config(
    page_title="Teploty kotle – Immergas",
    layout="wide"
)

st.markdown("""
<style>
[data-testid="stPlot"] {
    text-align: left !important;
    display: flex;
    justify-content: flex-start;
}
</style>
""", unsafe_allow_html=True)


TZ = "Europe/Prague"
tzinfo = zoneinfo.ZoneInfo(TZ)

PATH_NETATMO = (
    "https://raw.githubusercontent.com/MarekCoderslab/"
    "Teploty_kotle/master/data/netatmo_climate.csv"
)

PATH_CLIMATE = PATH_NETATMO

PATH_PRADELNA = (
    "https://raw.githubusercontent.com/MarekCoderslab/"
    "Teploty_kotle/master/data/teplota_pradelna.csv"
)

PATH_KOTEL = (
    "https://raw.githubusercontent.com/MarekCoderslab/"
    "Teploty_kotle/master/data/teplota_log.csv"
)


# =========================================================
# ČAS
# =========================================================

def compute_times(hours_back, end_date, end_hour):
    """Vrátí začátek a konec časového okna jako tz-aware datetime."""

    end_tz = pd.Timestamp(
        year=end_date.year,
        month=end_date.month,
        day=end_date.day,
        hour=end_hour,
        tz=TZ
    )

    start_tz = end_tz - pd.Timedelta(hours=hours_back)

    return start_tz, end_tz


# =========================================================
# EKVITERMNÍ KŘIVKA
# =========================================================

def hokejka3(temp_in):
    """Ekvitermní křivka."""

    if temp_in <= 10:
        return -0.233333 * temp_in + 35.333333

    return 33.0


# =========================================================
# NAČTENÍ DAT
# =========================================================

@st.cache_data(ttl=300)
def load_netatmo(path):

    df = pd.read_csv(path)

    # Původní UNIX timestamp ponecháváme beze změny

    # Jediný datetime používaný v grafech
    df["time_local"] = (
        pd.to_datetime(
            df["timestamp"],
            unit="s",
            utc=True,
            errors="coerce"
        )
        .dt.tz_convert(TZ)
    )

    # Text pro zobrazení
    df["timestamp_str"] = (
        df["time_local"]
        .dt.strftime("%d.%m.%Y %H:%M:%S")
    )

    # Ekvitermní teplota
    df["Boiler_water_2"] = (
        pd.to_numeric(df["temp_outdoor"], errors="coerce")
        .apply(hokejka3)
    )

    return df.dropna(subset=["time_local"])


@st.cache_data(ttl=300)
def load_climate(path):

    df = pd.read_csv(path)

    df["time_local"] = (
        pd.to_datetime(
            df["timestamp"],
            unit="s",
            utc=True,
            errors="coerce"
        )
        .dt.tz_convert(TZ)
    )

    df["time_local_str"] = (
        df["time_local"]
        .dt.strftime("%d.%m.%Y %H:%M:%S")
    )

    return df.dropna(subset=["time_local"])


@st.cache_data(ttl=300)
def load_pradelna(path):

    df = pd.read_csv(
        path,
        header=None,
        names=["cas", "tepl"]
    )

    df["cas"] = pd.to_datetime(
        df["cas"],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce"
    )

    df["tepl"] = pd.to_numeric(
        df["tepl"],
        errors="coerce"
    )

    return (
        df.dropna()
        .sort_values("cas")
        .drop_duplicates("cas")
    )


@st.cache_data(ttl=300)
def load_kotel(path):

    df = pd.read_csv(
        path,
        header=None,
        names=["Time", "Value"]
    )

    df["Time"] = pd.to_datetime(
        df["Time"],
        errors="coerce"
    )

    df["Value"] = pd.to_numeric(
        df["Value"],
        errors="coerce"
    )

    return df.dropna()


# =========================================================
# GRAF 1
# KOTEL VS EKVITERM
# =========================================================

def plot_kotel_vs_netatmo(
    df_kotel,
    df_netatmo,
    start_tz,
    end_tz
):

    fig, ax = plt.subplots(figsize=(12, 5))

    # -----------------------------------------------------
    # Kotel
    # -----------------------------------------------------

    kotel = df_kotel.copy()

    if kotel["Time"].dt.tz is None:
        kotel["Time"] = kotel["Time"].dt.tz_localize(TZ)
    else:
        kotel["Time"] = kotel["Time"].dt.tz_convert(TZ)

    kotel = kotel[
        (kotel["Time"] >= start_tz) &
        (kotel["Time"] <= end_tz)
    ]

    ax.plot(
        kotel["Time"],
        kotel["Value"],
        marker=".",
        color="blue",
        label="Boiler output"
    )

    # -----------------------------------------------------
    # Netatmo
    # -----------------------------------------------------

    net = df_netatmo[
        (df_netatmo["time_local"] >= start_tz) &
        (df_netatmo["time_local"] <= end_tz)
    ]

    ax.plot(
        net["time_local"],
        net["Boiler_water_2"],
        color="green",
        label="Ekviterm temp 3"
    )

    # -----------------------------------------------------

    ax.set_xlim(start_tz, end_tz)

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%d.%m. %H:%M",
            tz=tzinfo
        )
    )

    ax.tick_params(axis="x", rotation=45)

    ax.set_title(
        "Boiler Immergas Victix Zeus Superior (26) – "
        "Boiler output vs ekvitermní teplota"
    )

    ax.set_xlabel("Čas")
    ax.set_ylabel("Teplota [°C]")

    ax.grid(True)
    ax.legend()

    fig.tight_layout()

    return fig


# =========================================================
# GRAF 2
# INDOOR / SETPOINT / BOILER
# =========================================================

def plot_indoor_setpoint_boiler(
    df_climate,
    start_tz,
    end_tz
):

    fig, ax = plt.subplots(figsize=(12, 5))

    df = df_climate[
        (df_climate["time_local"] >= start_tz) &
        (df_climate["time_local"] <= end_tz)
    ]

    ax.plot(
        df["time_local"],
        df["temp_indoor"],
        label="Indoor temp",
        color="tab:blue",
        linewidth=1.5
    )

    ax.scatter(
        df["time_local"],
        df["temp_indoor"],
        s=8,
        color="tab:blue"
    )

    ax.plot(
        df["time_local"],
        df["setpoint"],
        label="Setpoint",
        color="tab:red",
        linewidth=1.5
    )

    ax.scatter(
        df["time_local"],
        df["setpoint"],
        s=8,
        color="tab:red"
    )

    ax.plot(
        df["time_local"],
        df["boiler"] + 20.5,
        label="Boiler (on/off)",
        color="tab:green",
        linewidth=1.5
    )

    ax.set_xlim(start_tz, end_tz)

    ax.set_title(
        "Indoor temperature vs Setpoint - Boiler ON/OFF"
    )

    ax.set_xlabel("Čas")
    ax.set_ylabel("°C")

    ax.grid(
        True,
        linestyle="--",
        alpha=0.4
    )

    ax.legend()

    ax.xaxis.set_major_locator(
        mdates.AutoDateLocator()
    )

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%a %d.%m. %H:%M",
            tz=tzinfo
        )
    )

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig


# =========================================================
# GRAF 3
# VENKOVNÍ TEPLOTA VS EKVITERM
# =========================================================

def plot_temp_vs_ekviterm(
    df_netatmo,
    start_tz,
    end_tz
):

    fig, ax = plt.subplots(figsize=(12, 5))

    df = df_netatmo[
        (df_netatmo["time_local"] >= start_tz) &
        (df_netatmo["time_local"] <= end_tz)
    ].copy()

    # -----------------------------------------------------
    # Venkovní teplota
    # -----------------------------------------------------

    ax.plot(
        df["time_local"],
        df["temp_outdoor"],
        color="blue",
        label="Teplota venku"
    )

    ax.set_ylabel(
        "Teplota venku [°C]",
        color="blue"
    )

    ax.tick_params(
        axis="y",
        labelcolor="blue"
    )

    # -----------------------------------------------------
    # Ekvitermní teplota
    # -----------------------------------------------------

    ax2 = ax.twinx()

    ax2.plot(
        df["time_local"],
        df["Boiler_water_2"],
        color="green",
        label="Ekvitermní teplota"
    )

    ax2.set_ylabel(
        "Teplota kotle [°C]",
        color="green"
    )

    ax2.tick_params(
        axis="y",
        labelcolor="green"
    )

    # -----------------------------------------------------

    ax.set_xlim(start_tz, end_tz)

    ax.set_title(
        "Venkovní teplota vs. nastavená ekvitermní teplota"
    )

    ax.set_xlabel("Čas")

    ax.xaxis.set_major_locator(
        mdates.AutoDateLocator()
    )

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%d.%m. %H:%M",
            tz=tzinfo
        )
    )

    ax.tick_params(
        axis="x",
        rotation=45
    )

    ax2.legend(
        loc="upper left"
    )

    ax.grid(True)

    fig.tight_layout()

    return fig


# =========================================================
# GRAF 4
# TLAK
# =========================================================

def plot_pressure(
    df_climate,
    start_tz,
    end_tz
):

    df = df_climate[
        (df_climate["time_local"] >= start_tz) &
        (df_climate["time_local"] <= end_tz)
    ]

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        df["time_local"],
        df["pressure"],
        label="Pressure (hPa)",
        color="tab:green",
        linewidth=1.5
    )

    ax.scatter(
        df["time_local"],
        df["pressure"],
        s=8,
        color="tab:green"
    )

    ax.set_title("Pressure over time")
    ax.set_xlabel("Čas")
    ax.set_ylabel("Pressure [hPa]")

    ax.grid(
        True,
        linestyle="--",
        alpha=0.4
    )

    ax.legend()

    ax.xaxis.set_major_locator(
        mdates.AutoDateLocator()
    )

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter(
            "%a %d.%m. %H:%M",
            tz=tzinfo
        )
    )

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig


# =========================================================
# GRAF 5
# PRÁDELNA
# =========================================================

def plot_pradelna(
    df_pradelna,
    start_tz,
    end_tz
):

    fig, ax = plt.subplots(figsize=(12, 5))

    df = df_pradelna[
        (df_pradelna["cas"] >= start_tz.tz_localize(None)) &
        (df_pradelna["cas"] <= end_tz.tz_localize(None))
    ]

    if len(df) > 0:

        current_temp = df["tepl"].iloc[-1]

        ax.set_ylim(
            current_temp - 2,
            current_temp + 2
        )

    ax.plot(
        df["cas"],
        df["tepl"]
    )

    ax.set_xlim(
        start_tz.tz_localize(None),
        end_tz.tz_localize(None)
    )

    ax.set_title("Teplota v prádelně")
    ax.set_xlabel("Čas")
    ax.set_ylabel("°C")

    ax.grid(True)

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%d.%m. %H:%M")
    )

    fig.autofmt_xdate()
    fig.tight_layout()

    return fig


# =========================================================
# SOUHRN POSLEDNÍHO STAVU
# =========================================================

def build_last_status_block(
    df_netatmo,
    df_kotel
):

    df_net = df_netatmo.sort_values(
        "time_local"
    ).copy()

    # -----------------------------------------------------
    # Poslední Netatmo hodnoty
    # -----------------------------------------------------

    last = df_net.iloc[-1]

    last_timestamp = last["timestamp_str"]
    last_temp_outdoor = last["temp_outdoor"]
    last_pressure = last["pressure"]

    # -----------------------------------------------------
    # Start / stop kotle
    # -----------------------------------------------------

    starts = (
        (df_net["boiler"] == True) &
        (df_net["boiler"].shift(1) == False)
    )

    stops = (
        (df_net["boiler"] == False) &
        (df_net["boiler"].shift(1) == True)
    )

    last_start = (
        df_net.loc[starts].iloc[-1]["timestamp_str"]
        if starts.any()
        else "N/A"
    )

    last_stop = (
        df_net.loc[stops].iloc[-1]["timestamp_str"]
        if stops.any()
        else "N/A"
    )

    # -----------------------------------------------------
    # Poslední hodnota kotle
    # -----------------------------------------------------

    if df_kotel is not None and len(df_kotel) > 0:

        kotel_last = df_kotel.iloc[-1]

        kotel_line = (
            f"Poslední teplota kotle (CSV): "
            f"**{kotel_last['Value']:.1f} °C** "
            f"(**{kotel_last['Time']:%H:%M}**)  \n"
        )

    else:

        kotel_line = (
            "Poslední teplota kotle (CSV): **N/A**  \n"
        )

    # -----------------------------------------------------
    # Stav kotle
    # -----------------------------------------------------

    if last_start != "N/A" and last_stop != "N/A":

        if last_start <= last_stop:

            kotel_state = (
                f"🔥 Poslední start kotle: **{last_start}**  \n"
                f"❄️ Poslední odstavení kotle: **{last_stop}**  \n"
            )

        else:

            kotel_state = (
                f"❄️ Poslední odstavení kotle: **{last_stop}**  \n"
                f"🔥 Poslední start kotle: **{last_start}**  \n"
            )

    else:

        kotel_state = (
            f"🔥 Poslední start kotle: **{last_start}**  \n"
            f"❄️ Poslední odstavení kotle: **{last_stop}**  \n"
        )

    return (
        f"🕒 Poslední záznam v logu: **{last_timestamp}**  \n"
        f"🌡️ Poslední venkovní teplota: "
        f"**{last_temp_outdoor:.1f} °C**  \n"
        f"🌬️ Poslední tlak vzduchu: "
        f"**{last_pressure:.1f} hPa**  \n"
        f"{kotel_line}"
        f"{kotel_state}"
    )


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Časové okno")

now = datetime.now(tzinfo)

if "hours_back" not in st.session_state:
    st.session_state.hours_back = 22

if "end_date" not in st.session_state:
    st.session_state.end_date = now.date()

if "end_hour" not in st.session_state:
    st.session_state.end_hour = (now.hour + 1) % 24


hours_back_input = st.sidebar.slider(
    "Kolik hodin zpět",
    min_value=1,
    max_value=48,
    value=st.session_state.hours_back
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


if st.sidebar.button("Aktualizovat časové okno"):

    st.session_state.hours_back = hours_back_input
    st.session_state.end_date = end_date_input
    st.session_state.end_hour = end_hour_input


start_tz, end_tz = compute_times(
    st.session_state.hours_back,
    st.session_state.end_date,
    st.session_state.end_hour
)


st.sidebar.markdown("---")

st.sidebar.write(
    "**Start:**",
    start_tz
)

st.sidebar.write(
    "**End:**",
    end_tz
)


# =========================================================
# HLAVNÍ OBSAH
# =========================================================

st.header(
    "Teploty – Immergas Victix Zeus Superior (26)"
)

st.markdown(
    f"Zobrazené období: "
    f"**{start_tz:%d.%m.%Y %H:%M} – "
    f"{end_tz:%d.%m.%Y %H:%M}**"
)


# =========================================================
# NAČTENÍ DAT
# =========================================================

df_netatmo = load_netatmo(PATH_NETATMO)
df_climate = load_climate(PATH_CLIMATE)
df_pradelna = load_pradelna(PATH_PRADELNA)

try:
    df_kotel = load_kotel(PATH_KOTEL)
except Exception:
    df_kotel = None


# =========================================================
# 1. POSLEDNÍ STAV
# =========================================================

st.header("Souhrn – poslední stav")

st.markdown(
    build_last_status_block(
        df_netatmo,
        df_kotel
    )
)


# =========================================================
# 2. KOTEL VS EKVITERM
# =========================================================

st.header(
    "Boiler output vs ekvitermní teplota"
)

if df_kotel is not None:

    fig1 = plot_kotel_vs_netatmo(
        df_kotel,
        df_netatmo,
        start_tz,
        end_tz
    )

    st.pyplot(fig1)

else:

    st.warning(
        "Soubor teplota_log.csv nebyl načten – "
        "zkontroluj PATH_KOTEL."
    )


# =========================================================
# 3. INDOOR / SETPOINT / BOILER
# =========================================================

st.header(
    "Indoor teplota, setpoint a stav kotle"
)

fig2 = plot_indoor_setpoint_boiler(
    df_climate,
    start_tz,
    end_tz
)

st.pyplot(fig2)


# =========================================================
# 4. VENKOVNÍ TEPLOTA VS EKVITERM
# =========================================================

st.header(
    "Venkovní teplota a ekvitermní křivka"
)

fig3 = plot_temp_vs_ekviterm(
    df_netatmo,
    start_tz,
    end_tz
)

st.pyplot(fig3)


# =========================================================
# 5. NETATMO TABULKA
# =========================================================

st.subheader(
    "Netatmo – posledních 10 záznamů"
)

df_show = df_netatmo[
    [
        "timestamp_str",
        "temp_outdoor",
        "pressure",
        "temp_indoor",
        "setpoint",
        "Boiler_water_2",
        "boiler"
    ]
]

st.dataframe(
    df_show.tail(10),
    use_container_width=True
)


# =========================================================
# 6. TLAK
# =========================================================

st.header(
    "Tlak vzduchu z Climate"
)

fig4 = plot_pressure(
    df_climate,
    start_tz,
    end_tz
)

st.pyplot(fig4)


# =========================================================
# 7. PRÁDELNA
# =========================================================

st.header(
    "Teplota u kotle"
)

fig5 = plot_pradelna(
    df_pradelna,
    start_tz,
    end_tz
)

st.pyplot(fig5)


# =========================================================
# PATIČKA
# =========================================================

st.markdown("---")

st.markdown(
    "<div style='text-align:center;'>"
    "<a href='mailto:marek.coderslab@gmail.com'>"
    "Created: marek.coderslab@gmail.com"
    "</a>"
    "</div>",
    unsafe_allow_html=True
)
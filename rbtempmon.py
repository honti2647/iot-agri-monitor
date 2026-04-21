#!/usr/bin/env python3
import sqlite3
import time
import adafruit_dht
import board
import datetime
import math
import adafruit_tsl2591
from adafruit_bme280 import basic as adafruit_bme280
import adafruit_bme680
import adafruit_veml7700

# Új importok az analóg szenzorhoz
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from influxdb import InfluxDBClient


# -----------------------------
#   VPD Számítás (Magnus-Tetens)
# -----------------------------
def calculate_vpd(temp_c, rh_percent):
    """
    Vapor Pressure Deficit számítása kPa-ban.
    Edge Computing: a számítás helyben történik.
    """
    # Telítési gőznyomás (SVP)
    svp = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    # Tényleges gőznyomás (AVP)
    avp = svp * (rh_percent / 100.0)
    # Deficit
    return round(svp - avp, 3)


# -----------------------------
#   DHT11 inicializálás
# -----------------------------
dht_device = adafruit_dht.DHT11(board.D4, use_pulseio=False)

def read_dht():
    """Megbízható DHT olvasás újrapróbálással."""
    for _ in range(10):  # max 10 próbálkozás
        try:
            temp = dht_device.temperature
            hum = dht_device.humidity
            if temp is not None and hum is not None:
                return temp, hum
        except Exception:
            time.sleep(2)
    return None, None

# -----------------------------
#   I2C inicializálás
# -----------------------------

i2c = board.I2C()

# --- Analóg Soil Szenzor (ADS1115) inicializálás ---
try:
    ads = ADS1115(i2c, address=0x48)
    soil_chan = AnalogIn(ads, 1) # CH1 / A1 láb
except Exception as e:
    print("ADS1115 inicializálási hiba:", e)
    ads = None

# -----------------------------
#   Szenzor olvasás
# -----------------------------

# -----------------------------
#   DHT11
# -----------------------------
temperature_c, humidity = read_dht()

if temperature_c is None or humidity is None:
    print("Hiba: nem sikerült kiolvasni a DHT11 értékeit.")
    try:
        dht_device.exit()
    except Exception:
        pass
    exit(1)

# -----------------------------
#   TSL2591
# -----------------------------
try:
    tsl = adafruit_tsl2591.TSL2591(i2c)
    tsl_lux = tsl.lux
    tsl_ir = tsl.infrared
    tsl_full = tsl.full_spectrum
    tsl_visible = tsl.visible
except Exception as e:
    print("TSL2591 hiba:", e)
    tsl_lux = tsl_ir = tsl_full = tsl_visible = None


# -----------------------------
#   BME280 (0x77)
# -----------------------------
try:
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x77)
    bme280_temp = bme280.temperature
    bme280_hum = bme280.humidity
    bme280_press = bme280.pressure
except Exception as e:
    print("BME280 hiba:", e)
    bme280_temp = bme280_hum = bme280_press = None


# -----------------------------
#   BME680 (0x76)
# -----------------------------
try:
    bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)
    bme680_temp = bme680.temperature
    bme680_hum = bme680.humidity
    bme680_press = bme680.pressure
    bme680_gas = bme680.gas
except Exception as e:
    print("BME680 hiba:", e)
    bme680_temp = bme680_hum = bme680_press = bme680_gas = None


# -----------------------------
#   VEML7700
# -----------------------------
veml = adafruit_veml7700.VEML7700(i2c)

# Lehetséges gain és IT értékek
gain_steps = [1/8, 1/4, 1, 2]
it_steps = [25, 50, 100, 200, 400, 800]

# Kezdő beállítás
veml.integration_time = 100
veml.gain = 1/8


def adjust_veml_range():
    """Automatikus gain/IT váltás a driver által számolt lux alapján."""
    als_lux = veml.light  # A driver már luxot ad!

    # Ha túl sötét → növelni kell az érzékenységet
    if als_lux < 100:
        # Gain növelése
        try:
            idx = gain_steps.index(veml.gain)
            if idx < len(gain_steps) - 1:
                veml.gain = gain_steps[idx + 1]
                return
        except Exception as e:
            print("VEML7700 gain növelés hiba:", e)

        # Ha gain már max → IT növelése
        try:
            idx = it_steps.index(veml.integration_time)
            if idx < len(it_steps) - 1:
                veml.integration_time = it_steps[idx + 1]
                return
        except Exception as e:
            print("VEML7700 IT növelés hiba:", e)

    # Ha túl világos → csökkenteni kell az érzékenységet
    if als_lux > 10000:
        # Gain csökkentése
        try:
            idx = gain_steps.index(veml.gain)
            if idx > 0:
                veml.gain = gain_steps[idx - 1]
                return
        except Exception as e:
            print("VEML7700 gain csökkentés hiba:", e)

        # Ha gain már minimum → IT csökkentése
        try:
            idx = it_steps.index(veml.integration_time)
            if idx > 0:
                veml.integration_time = it_steps[idx - 1]
                return
        except Exception as e:
            print("VEML7700 IT csökkentés hiba:", e)


try:
    # Automatikus tartományváltás
    adjust_veml_range()

    # A driver által számolt lux (helyes érték!)
    veml_lux = float(veml.light)

    # Fehér csatorna
    veml_white = veml.white

    # Ambient → nálad ez eddig is a fő fényérték volt
    veml_ambient = int(veml_lux)

except Exception as e:
    print("VEML7700 hiba:", e)
    veml_lux = veml_white = veml_ambient = None

# -----------------------------
#   Seesaw kapacitív talajnedvesség szenzor #1 (I2C multiplexerrel)
# -----------------------------
import adafruit_tca9548a
from adafruit_seesaw.seesaw import Seesaw

seesaw1_raw = None
seesaw1_pct = None
seesaw1_temp = None

try:
    # Multiplexer inicializálása (0x70)
    tca = adafruit_tca9548a.TCA9548A(i2c, address=0x70)

    # A Seesaw #1 szenzor csatornája (0–3)
    seesaw1_channel_index = 0
    seesaw1_channel = tca[seesaw1_channel_index]

    # Seesaw #1 inicializálása (0x36)
    ss1 = Seesaw(seesaw1_channel, addr=0x36)

    # Nyers kapacitív érték
    seesaw1_raw = ss1.moisture_read()

    # Hőmérséklet a Seesaw szenzorból
    seesaw1_temp = ss1.get_temp()

    # --- Kétlépcsős kalibráció ---
    # 0% = levegő (~330)
    DRY_AIR = 330
    # ~20% = nagyon száraz talaj (~720)
    DRY_SOIL = 720
    # 100% = nedves talaj (~1016)
    WET_SOIL = 1022

    if seesaw1_raw <= DRY_SOIL:
        # 0–20% tartomány
        seesaw1_pct = (seesaw1_raw - DRY_AIR) / (DRY_SOIL - DRY_AIR) * 20
    else:
        # 20–100% tartomány
        seesaw1_pct = 20 + (seesaw1_raw - DRY_SOIL) / (WET_SOIL - DRY_SOIL) * 80

    # 0–100% közé szorítás
    seesaw1_pct = max(0, min(100, seesaw1_pct))
    seesaw1_pct = round(seesaw1_pct, 1)

except Exception as e:
    print("Seesaw #1 talajnedvesség hiba:", e)


# --- Analóg Talajnedvesség olvasás (Vágott átlagolással) ---
soil_raw = soil_volt = soil_pct = None
if ads:
    try:
        readings = []
        for _ in range(11):
            readings.append(soil_chan.value)
            time.sleep(0.01)
        readings.sort()
        soil_raw = sum(readings[2:9]) / 7
        soil_volt = soil_chan.voltage

        # Szakaszos kalibráció: 2000->0%, 10700->10%, 20550->100%
        if soil_raw <= 2000: soil_pct = 0.0
        elif soil_raw >= 20550: soil_pct = 100.0
        elif soil_raw < 10700:
            soil_pct = (soil_raw - 2000) / (10700 - 2000) * 10
        else:
            soil_pct = 10 + (soil_raw - 10700) / (20550 - 10700) * 90
        soil_pct = round(soil_pct, 1)
    except Exception as e:
        print("Talajnedvesség mérés hiba:", e)

# VPD kiszámítása az olvasott adatokból
vpd_val = calculate_vpd(temperature_c, humidity)

now = datetime.datetime.now()
timestamp_unix = int(now.timestamp())
#timestamp_influx = now.isoformat()
timestamp_influx = time.time_ns()


# -----------------------------
#   Konzolos kiírás minden szenzorra
# -----------------------------

print("---- Szenzor adatok ----")

#DHT11
print(f"{now} Temp:{temperature_c:.1f} C | Humidity: {humidity}% | VPD: {vpd_val} kPa")

# TSL2591
print(f"TSL2591: Lux={tsl_lux:.1f} | IR={tsl_ir} | Full={tsl_full} | Visible={tsl_visible}")

# BME280
print(f"BME280: Temp={bme280_temp:.1f} °C | Humidity={bme280_hum:.2f}% | Pressure={bme280_press:.2f} hPa")

# BME680
print(f"BME680: Temp={bme680_temp:.1f} °C | Humidity={bme680_hum:.2f}% | Pressure={bme680_press:.2f} hPa | Gas={bme680_gas} Ω")

# VEML7700
print(f"VEML7700: Lux={veml_lux:.1f} | White={veml_white} | Ambient={veml_ambient}")

if soil_pct is not None:
    print(f"Analóg Soil 1: RAW={int(soil_raw)} | Volt={soil_volt:.1f}V | Nedvesség={soil_pct}%")

# Seesaw #1 kapacitív talajnedvesség
if seesaw1_raw is not None:
    print(f"Seesaw #1 Soil: RAW={seesaw1_raw} | Nedvesség={seesaw1_pct}% | Temp={seesaw1_temp:.1f}°C")

# -----------------------------
#   SQLite mentés (synced = 0)
# -----------------------------
try:
    conn = sqlite3.connect('/opt/rbtempmon.db')
    c = conn.cursor()
    c.execute(
        'INSERT INTO measure (temperature, humidity, vpd, date, synced, soil_an_1_raw, soil_an_1_volt, soil_an_1_pct, seesaw1_raw, seesaw1_pct, seesaw1_temp) VALUES (?,?,?,?,?,?,?,?,?,?,?);',
        (temperature_c, humidity, vpd_val, timestamp_unix, 0, soil_raw, soil_volt, soil_pct,seesaw1_raw, seesaw1_pct, seesaw1_temp
)
    )
    conn.commit()
    conn.close()
except Exception as db_err:
    print("SQLite adatbázis hiba:", db_err)

# -----------------------------
#   InfluxDB mentés (synced=false)
# -----------------------------
try:
    client = InfluxDBClient(
        host="localhost",
        port=changeme,
        username="changeme",
        password="changeme",
        database="local_metrics"
    )

    json_body = [
        {
            "measurement": "environment",
            "tags": {
                "location": "changeme"
            },
            "time": timestamp_influx,
            "fields": {
                # --- DHT11 ---
                "temperature": float(temperature_c),
                "humidity": float(humidity),
                "vpd": float(vpd_val),
                # --- TSL2591 ---
                "tsl_lux": tsl_lux if tsl_lux is not None else 0.0,
                "tsl_ir": tsl_ir if tsl_ir is not None else 0.0,
                "tsl_full": tsl_full if tsl_full is not None else 0.0,
                "tsl_visible": tsl_visible if tsl_visible is not None else 0.0,

                # --- BME280 ---
                "bme280_temp": bme280_temp if bme280_temp is not None else 0.0,
                "bme280_hum": bme280_hum if bme280_hum is not None else 0.0,
                "bme280_press": bme280_press if bme280_press is not None else 0.0,

                # --- BME680 ---
                "bme680_temp": bme680_temp if bme680_temp is not None else 0.0,
                "bme680_hum": bme680_hum if bme680_hum is not None else 0.0,
                "bme680_press": bme680_press if bme680_press is not None else 0.0,
                "bme680_gas": bme680_gas if bme680_gas is not None else 0.0,

                # --- VEML7700 ---
                "veml_lux": veml_lux if veml_lux is not None else 0.0,
                "veml_white": veml_white if veml_white is not None else 0.0,
                "veml_ambient": veml_ambient if veml_ambient is not None else 0.0,
                # Analóg talajnedvesség szenzor adatok
                "soil_an_1_raw": float(soil_raw) if soil_raw is not None else 0.0,
                "soil_an_1_volt": float(soil_volt) if soil_volt is not None else 0.0,
                "soil_an_1_pct": float(soil_pct) if soil_pct is not None else 0.0,
                #Seesaw talajnedvesség szenzor 1
                "seesaw1_raw": float(seesaw1_raw) if seesaw1_raw is not None else 0.0,
                "seesaw1_pct": float(seesaw1_pct) if seesaw1_pct is not None else 0.0,
                "seesaw1_temp": float(seesaw1_temp) if seesaw1_temp is not None else 0.0,
                "synced": False
            }
        }
    ]

    client.write_points(json_body)
except Exception as influx_err:
    print("InfluxDB hiba:", influx_err)

# -----------------------------
#   DHT driver lezárása
# -----------------------------
try:
    dht_device.exit()
except Exception:
    pass



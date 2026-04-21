import time
import board
import busio
import adafruit_tca9548a
from adafruit_seesaw.seesaw import Seesaw

# I2C busz inicializálása
i2c = busio.I2C(board.SCL, board.SDA)

# Multiplexer inicializálása (0x70 címen)
# Megjegyzés: A TCA9548A könyvtár kezeli a PCA9546-ot is!
tca = adafruit_tca9548a.TCA9548A(i2c, address=0x70)

# Itt add meg, melyik csatornára kötötted a szenzort (0-3 között)
# Például, ha a 0. csatornán van:
channel_index = 0
sensor_channel = tca[channel_index]

# Szenzor inicializálása a választott csatornán keresztül
# A Seesaw (A4026) címe 0x36
try:
    ss = Seesaw(sensor_channel, addr=0x36)
    print(f"Szenzor sikeresen inicializálva a(z) {channel_index}. csatornán!")
except Exception as e:
    print(f"Nem sikerült elérni a szenzort: {e}")
    print("Ellenőrizd a bekötést és a csatornaszámot!")
    exit()

print("Mérés indul... (Ctrl+C a leállításhoz)")

# --- KALIBRÁCIÓS PONTOK ---
# Ezeket a te méréseid alapján állítottuk be:

# 0% nedvesség – levegőben mért érték
DRY_AIR = 330

# ~20% nedvesség – nagyon száraz talaj
DRY_SOIL = 720

# 100% nedvesség – teljesen nedves talaj
WET_SOIL = 1020

# A kétlépcsős modell:
#  - 0–20% tartomány: DRY_AIR → DRY_SOIL
#  - 20–100% tartomány: DRY_SOIL → WET_SOIL

try:
    while True:
        # Nedvesség kiolvasása (nyers kapacitív érték)
        moisture = ss.moisture_read()

        # Hőmérséklet kiolvasása
        temp = ss.get_temp()

        # --- KÉTLÉPCSŐS NEDVESSÉG SZÁMÍTÁS ---

        if moisture <= DRY_SOIL:
            # 0–20% tartomány (levegő → száraz talaj)
            moisture_pct = (moisture - DRY_AIR) / (DRY_SOIL - DRY_AIR) * 20
        else:
            # 20–100% tartomány (száraz → nedves talaj)
            moisture_pct = 20 + (moisture - DRY_SOIL) / (WET_SOIL - DRY_SOIL) * 80

        # 0–100% közé szorítás
        if moisture_pct < 0:
            moisture_pct = 0
        if moisture_pct > 100:
            moisture_pct = 100

        # Kiírás
        print(
            f"Nedvesség: {moisture} | "
            f"Nedvesség (%): {moisture_pct:.1f}% | "
            f"Hőmérséklet: {temp:.1f}°C"
        )

        time.sleep(1)

except KeyboardInterrupt:
    print("\nMérés leállítva.")

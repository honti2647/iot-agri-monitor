#!/usr/bin/env python3
import board
import busio

# --- ADS1115 ---
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# --- TSL2591 ---
import adafruit_tsl2591

# --- BME280 ---
from adafruit_bme280 import basic as adafruit_bme280

# --- BME680 ---
import adafruit_bme680

# --- VEML7700 ---
import adafruit_veml7700


# I2C busz
i2c = board.I2C()


# -----------------------------
# ADS1115
# -----------------------------
def test_ads1115():
    print("=== ADS1115 (0x48) ===")
    try:
        ads = ADS1115(i2c, address=0x48)
        ch0 = AnalogIn(ads, 0)  # helyes modern API: 0 = A0
        ch1 = AnalogIn(ads, 1)
        ch2 = AnalogIn(ads, 2)
        ch3 = AnalogIn(ads, 3)
        print(f"CH0 voltage: {ch0.voltage:.4f} V")
        print(f"CH0 raw: {ch0.value}")
        print(f"CH1 voltage: {ch1.voltage:.4f} V")
        print(f"CH1 raw: {ch1.value}")
        print(f"CH2  voltage: {ch2.voltage:.4f} V")
        print(f"CH2 raw: {ch2.value}")
        print(f"CH3  voltage: {ch3.voltage:.4f} V")
        print(f"CH3 raw: {ch3.value}")


    except Exception as e:
        print("ADS1115 error:", e)
    print()


# -----------------------------
# TSL2591
# -----------------------------
def test_tsl2591():
    print("=== TSL2591 (0x29) ===")
    try:
        tsl = adafruit_tsl2591.TSL2591(i2c)
        print("Lux:", tsl.lux)
        print("Infrared:", tsl.infrared)
        print("Full spectrum:", tsl.full_spectrum)
        print("Visible:", tsl.visible)
    except Exception as e:
        print("TSL2591 error:", e)
    print()


# -----------------------------
# BME280
# -----------------------------
def test_bme280():
    print("=== BME280 (0x77) ===")
    try:
        bme = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x77)
        print(f"Temperature: {bme.temperature:.2f} °C")
        print(f"Humidity: {bme.humidity:.2f} %")
        print(f"Pressure: {bme.pressure:.2f} hPa")
    except Exception as e:
        print("BME280 error:", e)
    print()


# -----------------------------
# BME680
# -----------------------------
def test_bme680():
    print("=== BME680 (0x76) ===")
    try:
        bme = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)
        print(f"Temperature: {bme.temperature:.2f} °C")
        print(f"Humidity: {bme.humidity:.2f} %")
        print(f"Pressure: {bme.pressure:.2f} hPa")
        print(f"Gas: {bme.gas:.2f} ohm")
    except Exception as e:
        print("BME680 error:", e)
    print()


# -----------------------------
# VEML7700
# -----------------------------
def test_veml7700():
    print("=== VEML7700 (0x10) ===")
    try:
        veml = adafruit_veml7700.VEML7700(i2c)
        print("Lux:", veml.lux)
        print("White:", veml.white)
        print("Ambient :", veml.light)
    except Exception as e:
        print("VEML7700 error:", e)
    print()


# -----------------------------
# MAIN
# -----------------------------
def main():
    test_ads1115()
    test_tsl2591()
    test_bme280()
    test_bme680()
    test_veml7700()


if __name__ == "__main__":
    main()

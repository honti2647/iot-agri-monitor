#import board
#import busio
#import adafruit_bme280


import board
from adafruit_bme280 import basic as adafruit_bme280
i2c = board.I2C()  # uses board.SCL and board.SDA
#bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

#i2c = busio.I2C(board.SCL, board.SDA)

bme = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x77)

print("Temp:", bme.temperature)
print("Humidity:", bme.humidity)
print("Pressure:", bme.pressure)

# IoT Agri-Monitor

An open-source IoT monitoring system designed for horticultural environments. This project collects environmental data (temperature, humidity, soil moisture, light) using various sensors, provides a local API for data access, and synchronizes telemetry to an InfluxDB server for long-term storage and visualization.

## Table of Contents
- [Features](#features)
- [Hardware Components](#hardware-components)
- [File Structure & Components](#file-structure--components)
- [Installation & Setup](#installation--setup)
- [Usage](#usage)
- [Data Flow](#data-flow)
- [License](#license)

## Features

- **Multi-Sensor Support:** Integration for I2C-based environmental sensors and analog soil moisture probes.
- **Local Monitoring:** Real-time data collection and logging via Python services.
- **REST API:** A built-in API service to expose current sensor readings to other local or network clients.
- **Cloud/Server Sync:** Automated data synchronization to a remote InfluxDB instance for Grafana dashboards.
- **Robust Infrastructure:** Uses Telegraf for metrics collection and system health monitoring.

## Hardware Components

- **Controller:** Raspberry Pi Zero 2 W (compatible with Raspberry Pi 3, 4, or Zero W).
- **Sensors:**
  - I2C Environmental Sensors (e.g., SHT or BME series for temperature/humidity).
  - Capacitive/Resistive Soil Moisture Sensors.
- **Communication:** I2C Bus for digital sensors and ADC (Analog-to-Digital Converter) for analog probes.

## File Structure & Components

| File | Description |
| :--- | :--- |
| `rbtempmon.py` | The main monitoring service that polls sensor data at regular intervals. |
| `i2cbus_sensors.py` | Core module for handling I2C communication and specific sensor drivers. |
| `soilmoist.py` | For testing the soil moisture sensor.Logic for reading and calibrating soil moisture levels. Not needed.|
| `rbtempapi.py` | Flask-based API providing a local HTTP endpoint for real-time sensor data. |
| `influx_sync_to_server.py` | Handles the transmission of local logs to a remote InfluxDB server. |
| `telegraf.conf` | Configuration for the Telegraf agent to manage system and sensor metrics. |

## Installation & Setup


**Clone the repository**

git clone [https://github.com/honti2647/iot-agri-monitor.git](https://github.com/honti2647/iot-agri-monitor.git)
cd iot-agri-monitor

**Enable I2C on Raspberry Pi**

The system relies on the I2C bus. Enable it via the configuration tool:


sudo raspi-config
Navigate to: Interface Options -> I2C -> Enable -> Yes


Open telegraf.conf and update the [[outputs.influxdb_v2]] section with your server URL, organization, bucket, and token.


**Usage**

Starting the Monitoring Service

To begin background data collection and local logging:

python3 rbtempmon.py

Running the Local API

To start the API server (default port usually 5000) for data access:

python3 rbtempapi.py

Synchronizing Data to Server

You can run the sync script manually or set it up as a cron job or systemd to push data to your remote InfluxDB instance:

python3 influx_sync_to_server.py


**Data Flow**

Data Collection: The system polls digital sensors via the I2C bus (i2cbus_sensors.py).

Local Processing: The main service (rbtempmon.py) processes these readings and saves them to local logs.

Local Distribution: Clients can query the rbtempapi.py endpoint for immediate, real-time status updates.

Cloud Integration: The influx_sync script and telegraf ensure that all metrics are pushed to an InfluxDB database.

Visualization: Connect a Grafana instance to your InfluxDB bucket to create professional agricultural dashboards.

#!/usr/bin/env python3
import time
import os
import sys
import requests
from systemd import daemon

# -----------------------------------
#   KONFIGURÁCIÓ
# -----------------------------------

LOCAL_DB = {
    "url": "http://changeme/query",
    "username": "changeme",
    "password": "changeme",
}

# Szerver oldali InfluxDB 2.x
SERVER_URL = "changeme/api/v2/write"
ORG = "changeme"

BUCKET_ENV = "changeme"
BUCKET_SYS = "changeme"

TOKEN = "changeme"

# Lokális DB-k
DB_ENV = "local_metrics"
DB_SYS = "system_metrics"

# Last sync fájlok
SYNC_ENV = "/opt/influx_last_sync_environment.txt"
SYNC_SYS_DIR = "/opt/influx_last_sync_system"

BATCH_SIZE = 10000


# -----------------------------------
#   Watchdog ping
# -----------------------------------

def watchdog_ping():
    daemon.notify("WATCHDOG=1")


# -----------------------------------
#   Last sync kezelése
# -----------------------------------

def load_last_sync(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        ts = f.read().strip()
        return ts if ts else None


def save_last_sync(path, ts):
    with open(path, "w") as f:
        f.write(ts)


# -----------------------------------
#   Measurement lista lekérése
# -----------------------------------

def list_measurements(database):
    q = "SHOW MEASUREMENTS"
    try:
        resp = requests.post(
            f"{LOCAL_DB['url']}?db={database}",
            auth=(LOCAL_DB["username"], LOCAL_DB["password"]),
            data={"q": q}
        )
        data = resp.json()
        series = data["results"][0].get("series")
        if not series:
            return []
        return [m[0] for m in series[0]["values"]]
    except Exception as e:
        print("Hiba a measurement lista lekérésekor:", e)
        return []


# -----------------------------------
#   Adatok lekérése 1 measurementből
# -----------------------------------

def get_points(database, measurement, last_sync):
    if last_sync:
        time_filter = f"WHERE time > {last_sync}"
    else:
        time_filter = ""

    query = f"""
        SELECT *
        FROM "{measurement}"
        {time_filter}
        ORDER BY time DESC
        LIMIT {BATCH_SIZE}
    """

    try:
        resp = requests.post(
            f"{LOCAL_DB['url']}?db={database}&epoch=ns",
            auth=(LOCAL_DB["username"], LOCAL_DB["password"]),
            data={"q": query}
        )
        data = resp.json()
        series = data["results"][0].get("series")
        if not series:
            return None

        columns = series[0]["columns"]
        values = series[0]["values"]
        if not values:
            return None

        return (columns, values)

    except Exception as e:
        print(f"Hiba a lekérdezéskor ({measurement}):", e)
        return None


# -----------------------------------
#   Feltöltés a szerverre
# -----------------------------------

def upload_points(bucket, points, measurement):
    if not points:
        return True

    columns, values = points
    lines = []

    for row in values:
        timestamp = row[0]
#        timestamp -= 2 * 3600 * 1_000_000_000  # konvertáljuk UTC-re
        fields = []

        for col, val in zip(columns[1:], row[1:]):
            # csak numerikus fieldeket küldünk
            if isinstance(val, (int, float)):
                fields.append(f"{col}={val}")

        if not fields:
            continue

        # tag-ek: measurement + host
        line = f"{measurement},host=rbtemp {','.join(fields)} {timestamp}"
        lines.append(line)

    if not lines:
        return True

    data = "\n".join(lines)

    params = {
        "org": ORG,
        "bucket": bucket,
        "precision": "ns"
    }

    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "text/plain"
    }

    try:
        r = requests.post(SERVER_URL, params=params, headers=headers, data=data)
        if r.status_code != 204:
            print(f"Upload hiba ({measurement}): {r.status_code} {r.text}")
        return r.status_code == 204
    except Exception as e:
        print(f"Upload exception ({measurement}):", e)
        return False


# -----------------------------------
#   Környezet (environment) szinkron
# -----------------------------------

def sync_environment():
    last_sync = load_last_sync(SYNC_ENV)
    points = get_points(DB_ENV, "environment", last_sync)

    if not points:
        return

    if upload_points(BUCKET_ENV, points, "environment"):
        # utolsó sor timestampje
        _, values = points
        save_last_sync(SYNC_ENV, str(values[-1][0]))
        print("Environment szenzor szinkron OK")


# -----------------------------------
#   System metrics szinkron (measurementenként)
# -----------------------------------

def sync_system_metrics():
    if not os.path.exists(SYNC_SYS_DIR):
        os.makedirs(SYNC_SYS_DIR, exist_ok=True)

    measurements = list_measurements(DB_SYS)
    if not measurements:
        print("Nincs measurement a system_metrics DB-ben.")
        return

    for m in measurements:
        sync_file = f"{SYNC_SYS_DIR}/{m}.txt"
        last_sync = load_last_sync(sync_file)

        points = get_points(DB_SYS, m, last_sync)
        if not points:
            continue

        if upload_points(BUCKET_SYS, points, m):
            _, values = points
            save_last_sync(sync_file, str(values[-1][0]))
            print(f"System metric szinkron OK: {m}")


# -----------------------------------
#   MAIN LOOP
# -----------------------------------

def main():
    daemon.notify("READY=1")

    while True:
        watchdog_ping()

        sync_environment()
        watchdog_ping()

        sync_system_metrics()
        watchdog_ping()

        time.sleep(30)


if __name__ == "__main__":
    main()


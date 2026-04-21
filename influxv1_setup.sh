#!/bin/bash

# Adatbázis nevek
DB_SENSOR="local_metrics"
DB_SYSTEM="system_metrics"

echo "=== InfluxDB v1.x Konfiguráció Indítása ==="

# 1. Adatbázisok létrehozása
influx -execute "CREATE DATABASE $DB_SENSOR"
influx -execute "CREATE DATABASE $DB_SYSTEM"

# 2. Szenzor adatok megőrzése (local_metrics)
# A nyers adatokat 30 napig tároljuk
influx -execute "CREATE RETENTION POLICY \"raw_sensor_data\" ON \"$DB_SENSOR\" DURATION 30d REPLICATION 1 DEFAULT"
# Az aggregált (napi/heti) adatokat 1 évig (52 hét)
influx -execute "CREATE RETENTION POLICY \"long_term\" ON \"$DB_SENSOR\" DURATION 52w REPLICATION 1"

# 3. Rendszer adatok megőrzése (system_metrics)
# A CPU és egyéb metrikák általában 7 nap után már nem érdekesek, törölhetjük őket
influx -execute "CREATE RETENTION POLICY \"system_stats\" ON \"$DB_SYSTEM\" DURATION 7d REPLICATION 1 DEFAULT"

# 4. Continuous Queries (Automatikus napi átlagolás a szenzorokhoz)
influx -execute "CREATE CONTINUOUS QUERY \"cq_daily_env\" ON \"$DB_SENSOR\" BEGIN SELECT mean(*) INTO \"$DB_SENSOR\".\"long_term\".\"environment_daily\" FROM \"environment\" GROUP BY time(1d) END"

echo "=== Beállítás sikeresen befejeződött! ==="

from flask import Flask, jsonify, send_from_directory, request
from influxdb import InfluxDBClient
from dateutil import parser
from datetime import datetime

app = Flask(__name__)

# ---------------------------------------------------------
#  DASHBOARD HTML OLDALAK
# ---------------------------------------------------------

@app.route("/")
def dashboard():
    return send_from_directory("/opt/dashboard", "index.html")

@app.route("/averages")
def averages_page():
    return send_from_directory("/opt/dashboard", "averages.html")

@app.route("/sysmetrics")
def sysmetrics_page():
    return send_from_directory("/opt/dashboard", "sysmetrics.html")


# ---------------------------------------------------------
#  INFLUXDB KLIENSEK (KÉT ADATBÁZIS!)
# ---------------------------------------------------------

# Environment + averages → local_metrics
client_env = InfluxDBClient(
    host="localhost",
    port=changeme,
    username="changeme",
    password="changeme",
    database="local_metrics"
)

# System metrics (Telegraf) → system_metrics
client_sys = InfluxDBClient(
    host="localhost",
    port=changeme,
    username="changeme",
    password="changeme",
    database="system_metrics"
)


# ---------------------------------------------------------
#  SEGÉDFÜGGVÉNYEK
# ---------------------------------------------------------

def query_env(q):
    result = client_env.query(q)
    points = list(result.get_points())
    return points


def query_sys(q):
    result = client_sys.query(q)
    points = list(result.get_points())
    return points


# ---------------------------------------------------------
#  ENVIRONMENT API ENDPOINTOK (MEGLÉVŐK)
# ---------------------------------------------------------

@app.route("/api/window")
def window():
    minutes = int(request.args.get("minutes", 60))
    q = f"SELECT * FROM environment WHERE time > now() - {minutes}m"
    return jsonify(query_env(q))


@app.route("/api/last24h")
def last24h():
    q = "SELECT * FROM environment WHERE time > now() - 24h"
    return jsonify(query_env(q))


@app.route("/api/daily")
def daily():
    q = "SELECT * FROM environment_daily ORDER BY time DESC LIMIT 30"
    return jsonify(query_env(q))


@app.route("/api/weekly")
def weekly():
    q = "SELECT * FROM environment_weekly ORDER BY time DESC LIMIT 12"
    return jsonify(query_env(q))


@app.route("/api/monthly")
def monthly():
    q = "SELECT * FROM environment_monthly ORDER BY time DESC LIMIT 12"
    return jsonify(query_env(q))


@app.route("/api/yearly")
def yearly():
    q = "SELECT * FROM environment_yearly ORDER BY time DESC LIMIT 5"
    return jsonify(query_env(q))


@app.route("/api/daily_minmax")
def daily_minmax():
    q = "SELECT * FROM environment_daily_minmax ORDER BY time DESC LIMIT 30"
    return jsonify(query_env(q))


@app.route("/api/weekly_minmax")
def weekly_minmax():
    q = "SELECT * FROM environment_weekly_minmax ORDER BY time DESC LIMIT 12"
    return jsonify(query_env(q))


@app.route("/api/monthly_minmax")
def monthly_minmax():
    q = "SELECT * FROM environment_monthly_minmax ORDER BY time DESC LIMIT 12"
    return jsonify(query_env(q))


@app.route("/api/yearly_minmax")
def yearly_minmax():
    q = "SELECT * FROM environment_yearly_minmax ORDER BY time DESC LIMIT 5"
    return jsonify(query_env(q))


# ---------------------------------------------------------
#  SYSTEM METRICS API (ÚJ!)
# ---------------------------------------------------------

@app.route("/api/sysmetrics/<measurement>")
def sysmetrics_api(measurement):

    allowed = [
        "cpu_temperature_raw",
        "cpu",
        "mem",
        "disk",
        "diskio",
        "nstat",
        "service_telegraf",
        "service_influxd",
        "service_rbtempapi",
        "service_influx_sync",
        "service_reverse_tunnel"
    ]

    if measurement not in allowed:
        return jsonify({"error": "unknown measurement"}), 404

    q = f"SELECT * FROM {measurement} ORDER BY time DESC LIMIT 50"
    return jsonify(query_sys(q))


# ---------------------------------------------------------
#  FLASK INDÍTÁS
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


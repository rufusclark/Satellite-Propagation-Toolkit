# fmt: off
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from src import *

import time
import math
import json
import sqlite3
import traceback
import datetime

from flask import Flask, jsonify, request, Response, g
from flask_compress import Compress
# fmt: on

app = Flask(__name__)
# default is 'gzip', can also use 'brotli'
app.config['COMPRESS_ALGORITHM'] = 'gzip'
app.config['COMPRESS_LEVEL'] = 6  # gzip compression level (1-9)
app.config['COMPRESS_MIN_SIZE'] = 100  # compress smaller responses
Compress(app)

DATABASE = "./data/api_cache.db"
TRACKING_DATABASE = "./data/api_tracking.db"

"""
=
=
= Update below to configure the cache strategy
=
=
"""
# mins - check the cache for an update every X mins [0, 24*60]
CACHE_CHECK_DURATION = 15
PRE_CACHE_DURATION = 2  # days - cache this many days into the future [1, 7]
CACHE_TTL = 7  # days - how long a cache remains valid for [0, 14]
log_ips = False  # whether to log IP addresses in the tracking database - consider privacy implications


# key value pair for selecting the appropriate model for satellite sets
"""
Insert more MOCAT model files with keys here to expose them via the API
"""
MODEL_FILES = {
    "live": "live",
    "initial orbital capacity": "./data/MOCAT/initial orbital capacity.csv",
    "continue launch rate": "./data/MOCAT/results_Su_max_launch_2025.csv",
    "predicted mega constellations": "./data/MOCAT/results_Su_predict_launch_mega_2025.csv"
}

"""
Insert more MOCAT model files above
"""
MODELS = list(MODEL_FILES.keys())
FORMATS = ["cartesian", "keplerian"]
YEARS = [i for i in range(0, 105, 5)]


def get_db() -> sqlite3.Connection:  # type: ignore
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     year REAL NOT NULL,
                     format TEXT NOT NULL,
                     model TEXT NOT NULL,
                     expire_unix INTEGER NOT NULL,
                     data TEXT
                )
        """)
        # print(f"Connected to {DATABASE}")
    return g.db


def get_tracking_db() -> sqlite3.Connection:  # type: ignore
    if "tracking_db" not in g:
        g.tracking_db = sqlite3.connect(TRACKING_DATABASE)
        g.tracking_db.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                    ts TEXT,
                    endpoint TEXT,
                    method TEXT,
                    ip TEXT,
                    user_agent TEXT,
                    status_code INTEGER,
                    duration_ms REAL,
                    country TEXT,
                    city TEXT
                )
        """)
        if not log_ips:
            g.tracking_db.execute(
                "UPDATE usage SET ip = NULL, user_agent = NULL")
            g.tracking_db.commit()
        # print(f"Connected to {TRACKING_DATABASE}")
    return g.tracking_db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()
        # print(f"Closed connection to {DATABASE}")

    tracking_db = g.pop("tracking_db", None)
    if tracking_db:
        tracking_db.close()
        # print(f"Closed connection to {TRACKING_DATABASE}")


def get_output(
    years: float = 0,
    format: str = "cartesian",
    model: str = "live",
    *,
    _remove_empty_keys: bool = True,
    _current_time: float | None = None
) -> Response:
    """handle request for satellites sets from the API.

    handles input validation, checks sqlite3 cache and return cache or generates new outputs and returns/caches it

    Args:
        years: years in future for projected satellites. Defaults to 0.
        format: output format. Defaults to "cartesian".
        model: satellite set model. Defaults to "live".
        _remove_empty_keys: remove key:val pairs where val is empty. Defaults to True.
        _current_time: overwrite the current time for cache validation - supports generating new caches before they expire. Defaults to None.

    Returns:
        Flask.Response(): formatted json response
    """
    # enforce years if live
    if model == "live":
        years = 0

    # redirect future to a specific dataset
    if model == "future":
        model = "predicted mega constellations"

    # input validation
    if format not in FORMATS or model not in MODELS:
        return options()[0]

    # handle custom times
    if _current_time is None:
        _current_time = time.time()

    # check sqlite cache
    db = get_db()
    row = db.execute(
        "SELECT data FROM cache WHERE year = ? AND format = ? AND model = ? AND expire_unix > ?", (years, format, model, _current_time)).fetchone()
    print(
        f"[{datetime.datetime.now()}] sats request {years=} {format=} {model=} served-cached-response={row is not None}")
    if row:
        # return cached response
        # print(f"Returned response from cache")
        return Response(row[0].encode("utf-8"), content_type="application/json")

    # compute as not cached

    # get the correct satellite set based on the model
    if model == "live":
        sats = init_sats()
    else:
        sats = future.MOCATReader(MODEL_FILES[model]).read_yrs(
            years).to_SatelliteSet()

    # get satellite orbital positions
    positions = SGP4Propagation().propagate(sats, ts.now())

    # !: TLE/SGP4 is not currently supported
    # generate the output based on the format
    out = [
        {
            "name": position.sat.name,
            "category": position.sat.category,
            "launch date": position.sat.launch_date.isoformat() if isinstance(position.sat.launch_date, datetime.datetime) else "",
            "launch site": position.sat.launch_site,
            "launch country": position.sat.launch_country,
            "object type": position.sat.object_type,
            "operational status": position.sat.operational_status,
            "owner": position.sat.owner,
            "owner country": position.sat.owner_country,
            "constellation": position.sat.constellation,
            "orbit type": position.is_leo() and "LEO" or position.is_meo() and "MEO" or position.is_geo() and "GEO" or position.is_heo() and "HEO" or "",
            "tags": [tag for tag in position.sat.tags if tag.lower() not in [position.sat.category.lower(), (position.sat.operational_status or "").lower(), (position.sat.launch_site or "").lower(), (position.sat.launch_country or "").lower(), (position.sat.object_type or "").lower(), (position.sat.owner or "").lower(), ""]],
            **({
                "a": position.semi_major_axis,
                "e": position.eccentricity,
                "i": position.inclination,
                "Omega": position.Omega,
                "omega": position.omega,
                "M_0": position.mean_anomaly,
                "t_0": position.time.utc_iso(),
                "theta_g0": KeplerianPropagation._greenwich_sidereal_angle(position.sat.epoch)
            } if format == "keplerian" else {}
            ),
            **({
                "x": position.geo.x,
                "y": position.geo.y,
                "z": position.geo.z,
                "x_v": position.geo.x_v,
                "y_v": position.geo.y_v,
                "z_v": position.geo.z_v,
                "e": position.eccentricity,
                "i": position.inclination,
                "t_0": position.time.utc_iso()
            } if format == "cartesian" and not math.isnan(position.geo.x) else {}
            ),
            **({
                "tle": position.sat.to_tle()
            } if format == "sgp4" else {}
            )
        }
        for position in positions if True
    ]

    # remove empty value's keys
    if _remove_empty_keys:
        out = [{k: v for k, v in sat_out.items() if v} for sat_out in out]

    # convert to json
    json_out = json.dumps(out)

    # cached the reponse
    db.execute("INSERT OR REPLACE INTO cache (year, format, model, expire_unix, data) VALUES (?, ?, ?, ?, ?)",
               (years, format, model, time.time()+60*60*24*CACHE_TTL, json_out))
    db.commit()
    # print(f"Response computed live and cached for future calls")

    return Response(json_out, content_type="application/json")


def cache_updator():
    """updates all caches blocking"""
    unix_time = time.time() + 60*60*24*PRE_CACHE_DURATION
    for model in MODELS:
        for format in FORMATS:
            if model == "live":
                get_output(model=model, format=format, _current_time=unix_time)
            else:
                for year in YEARS:
                    get_output(years=year, model=model,
                               format=format, _current_time=unix_time)


def get_traffic_analysis() -> list:
    """get analysis of tracking data from the tracking database"""
    db = get_tracking_db()
    c = db.cursor()
    # depreciated - kept for reference
    # c.execute("""
    #     SELECT country, city, COUNT(DISTINCT ip || '|' || user_agent) AS unique_users, COUNT(*) as requests, AVG(duration_ms) AS avg_response_ms
    #     FROM USAGE
    #     GROUP BY country, city
    #     ORDER BY requests DESC
    # """)
    c.execute("""
        SELECT 
            DATE(ts) AS day,
            COUNT(*) AS api_calls,
            AVG(duration_ms) AS avg_response_time_ms
        FROM usage
        WHERE ts >= DATE('now', '-6 months')
        GROUP BY day
        ORDER BY day
    """)
    rows = c.fetchall()
    return rows


# cache commonly use satellite sets when debug = False
with app.app_context():
    print(f"{app.debug=}")


@app.route("/")
def root():
    """return basic api status including cache status"""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT MAX(expire_unix) FROM cache")
        max_expire_unix = cur.fetchone()[0]
        if max_expire_unix is not None:
            cache_expire_time = datetime.datetime.fromtimestamp(
                max_expire_unix).isoformat()
            cache_status = "valid" if max_expire_unix > time.time() else "expired"
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        print("Continuing...")
        # TODO: handle errors more usefully
        max_expire_unix = None
        cache_expire_time = "unknown"
        cache_status = "unknown"

    return jsonify({
        "status": "healthy" if cache_status != "expired" else "degraded",
        "cache": {
            "cache_expire_time": cache_expire_time,
            "cache_status": cache_status,
        },
    }), 200


@app.route("/sats/options", methods=["GET"])
def options():
    """return option details"""
    return jsonify({
        "model": [*MODELS, "future"],
        "format": FORMATS,
        "year": YEARS,
        "example": f"/sats?model={MODELS[0]}&format={FORMATS[0]}"
    }), 200


@app.route("/sats", methods=["GET"])
def sats():
    """api route with options

    i.e. `/sats?model=live&format=keplerian`
    or `/sats?model=initial orbital capacity&format=keplerian&year=10`"""
    model = request.args.get("model", "live")
    format = request.args.get("format", "keplerian")
    year = request.args.get("year", 0, type=float)

    # print(f"{model=} {format=} {year=}")

    try:
        return get_output(
            years=int(round(year, 1)),
            model=model,
            format=format
        ), 200
    except Warning as e:
        return jsonify({"error": str(e)}), 400


@app.route("/traffic", methods=["GET"])
def traffic():
    # ! generate your own password hash or remove if hosting yourself
    from werkzeug.security import check_password_hash

    key = request.args.get("key", None)
    if not key or not check_password_hash("scrypt:32768:8:1$ypqYQqVluJUgi2W3$60d2e133a7d9080c9c6f57d27a419ae1a29c261d9969afa67bd626a35a3733e0466bde91617e765569696dda1f2c66dd930801767db973d73f511b8658ee64ea", key):
        return jsonify({"error": "Unauthorised"}), 401

    # data = [{
    #     "country": row[0],
    #     "city": row[1],
    #     "unique users": row[2],
    #     "requests": row[3],
    #     "avg response [ms]": row[4]
    # } for row in get_traffic_analysis()]
    data = [{
        "day": row[0],
        "api calls": row[1],
        "avg response time [ms]": row[2]
    } for row in get_traffic_analysis()]
    return jsonify(data), 200


@app.errorhandler(Exception)
def handle_exception(e):
    traceback.print_tb(e.__traceback__)
    print("Continuing...")
    if app.debug:
        return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": ""}), 500


@app.before_request
def start_time():
    g.start_time = time.time()


@app.after_request
def log_request(response: Response) -> Response:
    duration_ms = (time.time() - g.start_time) * 1000
    if log_ips:
        user_agent = request.headers.get("User-Agent", "")
        ip: str = request.headers.get(
            "X-Forwarded-For", request.remote_addr)  # type: ignore
        try:
            import geocoder
            p = geocoder.ipinfo(ip)
            country = p.country or ""
            city = p.city or ""

        except Exception as e:
            traceback.print_tb(e.__traceback__)
            print("Continuing...")
            country, city = "", ""
    else:
        ip = ""
        country, city = "", ""
        user_agent = ""
    db = get_tracking_db()
    db.execute(
        "INSERT INTO usage (ts, endpoint, method, ip, user_agent, status_code, duration_ms, country, city) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.datetime.now().isoformat(),
            request.path,
            request.method,
            ip,
            user_agent,
            response.status_code,
            duration_ms,
            country,
            city
        )
    )
    db.commit()
    return response


if __name__ == "__main__":
    app.run(debug=True)

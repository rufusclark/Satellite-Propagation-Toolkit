# Unity

> ***Under Development***

This section of the project supports an effort to get a live SGP4 based model working within the unity game engine. This is intended to be used with AR/VR or large format projections.

## Methodology

Use the existing toolkit to generate intemediate values and combine metadata to provide a coherent API with all the data required for an external app to run.

The api pre-computes and caches the relevent data api responses based on SpaceTrac datasets and using sqlite3. The api responses can either be pre-computer (recommended to refresh the caches every 24 hours) or computed and cached live as they're called

### API

The API uses a cross-platform WGSI compatible server called waitress to server the API build with Flask. The API supports gzip compression and will use it if you're client does too. It's recommended to use this to keep the responses sizes managible (uncompressed can be as large as 50MB, compressed is usually 1-4MB depending on options).

#### Options

The different formats allow you to specify what form the returned data is, this is curretnly either keplerian or cartesian (ITRS).

The models allow you to specify what model is used to generate the data. The defaults options are:

* live - all currently active satellite tracked by CelesTrak
* future - a future constellation based on MOCAT outputs and the current trends of active satellites. Please provide a year as an option (0, 5, 10, 15, ..., 100). This datasets ships with the repositry.

Additional MOCAT datasets can be integrated with this API by adding the filepath and a name to the `MODELS` constant to [app.py](app.py). This will then be available via the API after a restart.

#### Endpoints

* Route (/) - returns device status in json

```json
{"status":"healthy"}
```

* Sats options (/sats/options) - returns all available options for calling the /sats endpoint

```json
{
  "example": "/sats?model=live&format=cartesian",
  "format": [
    "cartesian",
    "keplerian"
  ],
  "model": [
    "live",
    "initial orbital capacity",
    "future"
  ],
  "year": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
}
```

* Sats (/sats?key=val&key=val...) - returns a set of satellites information for the given parameters.

```json
/sats?model=future&year=15&format=keplerian
[
    {"name": "15SAT049388", "category": "15 year estimate", "a": 8346.896424931907, "e": 0.001736118002734481, "i": 1.0160988826244386, "Omega": 0.10866763962377365, "omega": 1.5666989006817706, "M_0": 4.397443229119363, "t_0": "2025-09-05T10:01:17Z", "theta_g0": 2.3577270682856124}, 
    {"name": "15SAT049389", "category": "15 year estimate", "a": 8365.513610100843, "e": 0.0014779336768586356, "i": 0.7542348668276888, "Omega": 5.741827948541315, "omega": 5.224138250979253, "M_0": 1.3661413939026077, "t_0": "2025-09-05T10:01:17Z", "theta_g0": 2.3577270682856124}, 
    {"name": "15SAT049390", "category": "15 year estimate", "a": 8331.491697715359, "e": 0.0003659220573104625, "i": 1.2300409957606209, "Omega": 4.437922974194369, "omega": 1.0028587037979515, "M_0": 5.580716666584325, "t_0": "2025-09-05T10:01:17Z", "theta_g0": 2.3577270682856124},
    ...
    ]
```

```json
/sats?model=live&format=cartesian
[
    {"name": "ZORKIY-2M 2", "category": "special-interest satellites", "launch date": "2024-02-29T00:00:00", "launch site": "Vostochny Cosmodrome, Russia", "launch country": "Russia", "object type": "Payload", "operational status": "Operational", "owner": "Commonwealth of Independent States (former USSR)", "tags": ["active"], "x": 525.8860764392999, "y": -6327.290981591794, "z": 2299.367906387115, "x_v": -1.2977248460078803, "y_v": -2.726327974053706, "z_v": -7.150719327872921, "e": 0.002470274703874417, "i": 1.6986359932624222, "t_0": "2025-09-05T09:53:10Z"},
    {"name": "ZY-1 02D", "category": "communications satellites", "launch date": "2019-09-12T00:00:00", "launch site": "Taiyuan Space Center, PRC", "launch country": "PRC", "object type": "Payload", "operational status": "Operational", "owner": "People's Republic of China", "tags": ["active", "special-interest satellites", "satnogs"], "x": -235.9588993762882, "y": 1033.8658247030367, "z": 7065.28789245571, "x_v": 7.536367297838214, "y_v": 0.22224982904233054, "z_v": 0.21855714710465404, "e": 0.0006469732491046516, "i": 1.7149885059455523, "t_0": "2025-09-05T09:53:10Z"},
    {"name": "ZY-1 02E", "category": "special-interest satellites", "launch date": "2021-12-26T00:00:00", "launch site": "Taiyuan Space Center, PRC", "launch country": "PRC", "object type": "Payload", "operational status": "Operational", "owner": "People's Republic of China", "tags": ["active"], "x": 530.1713946608418, "y": 1198.1295918869646, "z": 7023.151422881753, "x_v": 7.343697240908496, "y_v": 1.5249059893017864, "z_v": -0.8133455924603911, "e": 0.0005954324477519252, "i": 1.717324732250218, "t_0": "2025-09-05T09:53:10Z"},
    ...
]
```

#### Usage

To host the API get started by cloning the repo and installing the Python requirements (see [README](../README.md) this detailed instructions). Then from the repositries root directory in 2 seperate terminals start the API server and response caching scripts. It is possible to just use the API server although this will result in slow responses that have not been cached (up to 10 seconds on a fast internet connection).

```bash
waitress-server --port=8000 unity.app:app
python3 .\unity\update_cache.py
```

The API will be accessible at `127.0.0.1:8000` on your local network.

## Code

The following code has been developed to support the cartesian vector coordinate generated so far.

* [Python based unity backend - initial test](unity_backend.py)
* [C# based unity backend - runs entirely within C#](UnityScript/Program.cs)

The following code has been developed to support the api

* [API](app.py)
* [API response update](update_cache.py)

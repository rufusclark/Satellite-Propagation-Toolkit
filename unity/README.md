# Unity

> ***Under Development***

This section of the project supports an effort to get a live SGP4 based model working within the unity game engine. This is intended to be used with AR/VR or large format projections.

## Methodology

Use the existing toolkit to generate intemediate values and combine metadata to provide a coherent API with all the data required for an external app to run.

The api pre-computes and caches the relevent data api responses based on SpaceTrak datasets and using sqlite3. The api responses can either be pre-computer in advance or computed and cached live as they're called.

### API

The API uses a cross-platform WGSI compatible server called waitress to server the API build with Flask. The API supports gzip compression and will use it if you're client does too. It's recommended to use this to keep the responses sizes managible (uncompressed can be as large as 50MB, compressed is usually 1-4MB depending on options).

The API also logs all requests to a sqlite3 database. These can be view via [this script](analyse_tracking.py) or directly by querying the database with the sqlite3 console.

#### Options

The different formats allow you to specify what form the returned data is, this is curretnly either keplerian or cartesian (ITRS).

The models allow you to specify what model is used to generate the data. The defaults options are:

* live - all currently active satellite tracked by CelesTrak
* future - a future constellation based on MOCAT outputs and the current trends of active satellites. Please provide a year as an option (0, 5, 10, 15, ..., 100). This datasets ships with the repositry.

Additional MOCAT datasets can be integrated with this API by adding the filepath and a name to the `MODELS` constant to [app.py](app.py). This will then be available via the API after a restart.

#### Endpoints

* Route (/)

```html
API is running
```

* Route (/status) - returns device status in json

```json
{
  "cache": {
    "cache_expire_time": "2025-10-11T23:11:48.919772",
    "cache_status": "valid"
  },
  "status": "healthy"
}
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
  {"name": "15SAT046099", "category": "15 year estimate", "constellation": "15SAT046099", "orbit type": "LEO", "a": 8080.239351864671, "e": 0.002554218741210542, "i": 0.83575620657674, "Omega": 0.9347672604229559, "omega": 0.9794698843845798, "M_0": 3.312303303777852, "t_0": "2025-10-05T08:02:43Z", "theta_g0": 2.354994377080531},
  {"name": "15SAT046100", "category": "15 year estimate", "constellation": "15SAT046100", "orbit type": "LEO", "a": 8106.008084273389, "e": 0.0034466540487576454, "i": 1.513134714143146, "Omega": 0.9005415383337549, "omega": 1.6808706020447912, "M_0": 3.0173565163393, "t_0": "2025-10-05T08:02:43Z", "theta_g0": 2.354994450421491},
  {"name": "15SAT046101", "category": "15 year estimate", "constellation": "15SAT046101", "orbit type": "LEO", "a": 8104.336655609582, "e": 0.0012348891904784293, "i": 0.697819749827599, "Omega": 0.6925271463016947, "omega": 3.6530548954552278, "M_0": 5.539313606535149, "t_0": "2025-10-05T08:02:43Z", "theta_g0": 2.354994450421491},
  ...
]
```

```json
/sats?model=live&format=cartesian
[
  {"name": "STARLINK-5231", "category": "communications satellites", "launch date": "2022-10-28T00:00:00", "launch site": "Air Force Western Test Range, California, USA", "launch country": "USA", "object type": "Payload", "operational status": "Operational", "owner": "United States", "owner country": ["United States"], "constellation": "STARLINK", "orbit type": "LEO", "tags": ["active", "special-interest satellites", "starlink"], "x": 1688.8382881621626, "y": 3964.5141990258107, "z": -5419.292883623484, "x_v": -7.05491141767584, "y_v": 1.255399569639014, "z_v": -1.2813493646103402, "e": 0.0016256475241144647, "i": 0.9265915714952896, "t_0": "2025-10-05T08:00:46Z"}, 
  {"name": "STARLINK-5232", "category": "communications satellites", "launch date": "2023-02-17T00:00:00", "launch site": "Air Force Western Test Range, California, USA", "launch country": "USA", "object type": "Payload", "operational status": "Operational", "owner": "United States", "owner country": ["United States"], "constellation": "STARLINK", "orbit type": "LEO", "tags": ["active", "special-interest satellites", "starlink"], "x": -3480.452895924343, "y": -5991.708039819796, "z": 558.2184646647255, "x_v": 1.5191968385434889, "y_v": -1.5500231998234957, "z_v": -7.09207316308471, "e": 0.0010305827641009378, "i": 1.2213212568538965, "t_0": "2025-10-05T08:00:46Z"}, 
  {"name": "STARLINK-5233", "category": "communications satellites", "launch date": "2022-10-28T00:00:00", "launch site": "Air Force Western Test Range, California, USA", "launch country": "USA", "object type": "Payload", "operational status": "Operational", "owner": "United States", "owner country": ["United States"], "constellation": "STARLINK", "orbit type": "LEO", "tags": ["active", "special-interest satellites", "starlink"], "x": -3412.32532446202, "y": -3312.1705289323354, "z": 5014.530724215567, "x_v": 6.313411533982897, "y_v": -2.6032663990969422, "z_v": 2.5697612111436525, "e": 0.0008210588752918982, "i": 0.9265628284037115, "t_0": "2025-10-05T08:00:46Z"},
  ...
]
```

#### Usage

To host the API get started by cloning the repo and installing the Python requirements (see [README](../README.md) this detailed instructions). Then from the repositories root directory in 2 separate terminals start the API server and response caching scripts. It is possible to just use the API server although this will result in slow responses that have not been cached (up to 10 seconds on a fast internet connection).

Expect the first run to be very slow as all the data is downloaded and processed in the background.

```bash
waitress-serve --port=8000 unity.app:app
python3 .\unity\update_cache.py
```

The API will be accessible at `127.0.0.1:8000` on your local network.

## Code

The following code has been developed to support the cartesian vector coordinate generated so far.

* [Python based unity backend - initial test](unity_backend.py)
* [C# based unity backend - runs entirely within C#](UnityScript/Program.cs)

The following code has been developed to support the api

* [API](app.py)
* [API cache update](update_cache.py)

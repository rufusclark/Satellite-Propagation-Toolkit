using SGPdotNET.CoordinateSystem; 
using SGPdotNET.Observation;
using SGPdotNET.TLE;
using SGPdotNET.Util;

/*
This script download and caches live satellite tracking data form CelesTrak.com. This data is then cleaned to remove UNKNOWN and duplicate tracking objects. 

The cache automatically invalidates data after 7 days.

The tracking data is then used to propagate the objects to the current time. This script then prints position and velocity vectors in km and km/s respectively.

The vectors are for a ECI reference frame. See below for details.

ECI (Earth Centered Inertial) is centered about the Earth and fixed to a fixed point in the solar system, usually the barycenter of the solar system.

This relies on the [SGP.NET library](https://github.com/parzivail/SGP.NET).
*/

// Define all urls to download data
string[] groups = [
    "weather", "noaa", "goes", "resource", "sarsat", "dmc", "tdrss", "argos", "planet", "spire", "geo", "intelsat", "iridium", "starlink", "orbcomm", "swarm", "x-comm", "ses", "iridium-NEXT", "oneweb", "globalstar", "amateur", "other-comm", "satnogs", "gorizont", "raduga", "molniya", "gnss", "gps-ops", "glo-ops", "galileo", "beidou", "sbas", "nnss", "musson", "science", "geodetic", "engineering", "education", "military", "radar", "cubesat", "other", "stations", "visual", "active", "analyst"
];

CachingRemoteTleProvider provider;
Dictionary<int, Tle> tles = [], workingTles;

var urls = groups.Select(x => new NoradSource(x));
foreach (var url in urls) {
    Console.WriteLine(url.Url);

    // get files from tle
    provider = new CachingRemoteTleProvider(true, TimeSpan.FromDays(7), url.Filename, url.Url);

    workingTles = provider.GetTles();
    // remove duplicate tle objects and UNKNOWN objects
    foreach (var dict in workingTles) {
        if (dict.Value.Name == "UNKNOWN") continue;
        tles[dict.Key] = dict.Value;
    }
}

Console.WriteLine($"Loaded {tles.Count} satellites from {groups.Length} sources");

int id;
Tle tle;
Satellite sat;
EciCoordinate eciCoordinate;
Vector3 eciPosition, eciVelocity;
DateTime time = DateTime.UtcNow;

int count = 0;

SatelliteData[] satelliteDatas = new SatelliteData[tles.Count];

foreach (var dict in tles) {
    id = dict.Key;
    tle = dict.Value;

    sat = new Satellite(tle);
    eciCoordinate = sat.Predict(time);

    eciPosition = eciCoordinate.Position;
    eciVelocity = eciCoordinate.Velocity;

    satelliteDatas[count] = new SatelliteData(tle.Name, eciPosition.X, eciPosition.Y, eciPosition.Z, eciVelocity.X, eciVelocity.Y, eciVelocity.Z);

    count++;
}

Console.WriteLine($"Populated satelliteDatas with the name, position and velocity of {satelliteDatas.Length} satellites from most recent NORAD tracking data");

public class NoradSource {
    public string group;
    private string format = "tle";
    public NoradSource(string group) => this.group = group;
    public Uri Url
    {
        get {
            return new Uri($"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT={format}");
        }
    }
    public string Filename
    {
        get {
            return $"{group}.{format}";
        }
    }
}

public class Vector3Float {
    public float x;
    public float y;
    public float z;

    public Vector3Float(float x, float y, float z) {
        this.x = x;
        this.y = y;
        this.z = z; 
    }

    public Vector3Float(double x, double y,double z) {
        this.x = (float)x;
        this.y = (float)y;
        this.z = (float)z;
    }
}

public class SatelliteData {
    public Vector3Float position;
    public Vector3Float velocity;
    public string name;

    public SatelliteData(string name, double x, double y, double z, double x_v, double y_v, double z_v) {
        this.position = new Vector3Float(x, y, z);
        this.velocity = new Vector3Float(x_v, y_v, z_v);
        this.name = name;
    }
}
"""contains models required to proccess satellite data"""
from typing import Callable, List, Dict, Tuple
from typing_extensions import Self

from skyfield.api import EarthSatellite, load, wgs84
from skyfield.toposlib import GeographicPosition
from skyfield.timelib import Time


# Time scale for Earth Orbiting Satellites
ts = load.timescale()


class Sat:
    def __init__(self, fields, group: str = "", category: str = "") -> None:
        self.tags = [group.lower(), category.lower()]
        self._sat = EarthSatellite.from_omm(ts, fields)

    def add_tag(self, tag: str) -> None:
        """add an additional tag to the sat if it doesn't already exist

        Args:
            tag: str (e.g. active, debris)
        """
        if tag:
            tag = tag.lower()
            if tag not in self.tags:
                self.tags.append(tag)

    def add_tags(self, tags: List[str]) -> None:
        """an additional tags to the sat is they don't already exist

        Args:
            tags: [str, str, ...] (e.g. ["active", "debris"])
        """
        for tag in tags:
            self.add_tag(tag)

    def in_tags(self, word: str) -> bool:
        """whether the word is included in any satellite tags (case insensitive)

        Args:
            word: search word

        Returns:
            bool: whether the word exists in any tag
        """
        for tag in self.tags:
            if word in tag:
                return True
        return False

    @property
    def name(self) -> str:
        return self._sat.name  # type: ignore

    @property
    def epoch(self):
        """returns the datetime when the satellite was last tracked

        Returns:
            float: datetime of epoch
        """
        return self._sat.epoch

    @property
    def days_since_epoch(self) -> float:
        """returns how many days old the tracking information for an object is

        Notes:
            Objects are likely to only provide accurate tracking information around 2 weeks plus or minus the epoch date. Outside of these times propogations will be inaccurate and essentially useless

        Returns:
            float: days since last update
        """
        return ts.now() - self._sat.epoch

    def TEME_position_at(self, t=ts.now()):
        return self._sat.at(t)

    def projected_lat_lon_alt(self, t: Time = ts.now()) -> Tuple[float, float, float]:
        """calculate the projected latitude and longitude onto the WGS84 centeroid and the altitude above the wgs84 centeroid.

        This method will return bad data `(nan, nan, nan)` if the propogation is invalid. This can be checked with `math.isnan(lat)` etc.

        Usage:
            >>> t = ts.now()
            >>> lat, lon, alt = projected_lat_lon_alt(t)

        Args:
            t: time. Defaults to ts.now().

        Returns:
            latitude [degrees],
            longitude [degrees],
            altitude [km]
        """
        pos = self.TEME_position_at(t)
        geo_pos = wgs84.geographic_position_of(pos)
        lat = geo_pos.latitude.degrees
        lon = geo_pos.longitude.degrees
        alt = geo_pos.elevation.km

        return lat, lon, alt  # type: ignore

    def topocentric_position_at(self, observer: GeographicPosition, t=ts.now()):
        sat_from_topo = self._sat - observer
        return sat_from_topo.at(t)

    def topocentric_alt_azimuth_distance(self, observer: GeographicPosition, t: Time = ts.now()) -> Tuple[float, float, float]:
        """calculate the altitude angle, azimuth angle and distance from the topocentric observer

        Usage:
            >>> observer = wgs84.latlon(53.46, -2.233)
            >>> t = ts.now()
            >>> altitude, azimuth, distance = topocentric_alt_azimuth_distance(observer, t)

        Args:
            observer: Topocentric observer
            t: time. Defaults to ts.now().

        Returns:
            altitude [degrees],
            azimuth [degrees],
            distance [km]
        """
        pos = self.topocentric_position_at(observer, t)
        alt, azimuth, distance = pos.altaz()
        return alt.degrees, azimuth.degrees, distance.km  # type: ignore

    def __repr__(self) -> str:
        return f"<Sat {self.name} ({' - '.join(self.tags)})>"

    def generate_debris_tag(self) -> None:
        """generate a tag for this satellite if it is debris
        """
        if "deb" in self.name.lower() or self.in_tags("deb"):
            self.add_tag("debris")

    def add_tags_from_SATCAT(self, satcat: Dict[str, Dict]) -> None:
        """add additional tags to the sat object if additional information exists in the SATCAT (Satellite Catologue)

        Args:
            satcat: satcat data
        """
        from .datasources import SATCAT

        # ignore if not SATCAT data exists for sat
        if self.name not in satcat:
            return

        data = satcat[self.name]

        # add additional tags if they exist
        if data['OBJECT_TYPE']:
            self.add_tag(SATCAT.OBJECT_TYPE(data["OBJECT_TYPE"]))

        if data['OPS_STATUS_CODE']:
            self.add_tag(SATCAT.OPERATIONAL_STATUS(data['OPS_STATUS_CODE']))

        if data['OWNER']:
            self.add_tag(SATCAT.OPERATIONAL_STATUS(data['OWNER']))

        if data['LAUNCH_DATE']:
            self.launch_date = data['LAUNCH_DATE']

        if data['LAUNCH_SITE']:
            self.add_tag(SATCAT.LAUNCH_SITE(data['LAUNCH_SITE']))


class Sats:
    # Container for list of sets with helpful filter functions
    # TODO: Implement a version that converses memory by deleting old data
    def __init__(self, sats: List[Sat]) -> None:
        self._sats = sats

        # filter and analyse data
        self.remove_duplicates()
        for sat in self.sats:
            sat.generate_debris_tag()

    def __repr__(self) -> str:
        return f"<Sats n={len(self.sats)}>"

    def __len__(self) -> int:
        return len(self.sats)

    def add_tags_from_SATCAT(self, satcat) -> None:
        """add additional tags to sats from SATCAT data"""
        for sat in self.sats:
            sat.add_tags_from_SATCAT(satcat)

    def remove_duplicates(self):
        """removes all duplicate sats after combining tags
        """
        sats: Dict[str, Sat] = {}
        for sat in self.sats:
            if sat.name not in sats:
                sats[sat.name] = sat
            else:
                sats[sat.name].add_tags(sat.tags)

        self._sats = list(sats.values())

    @property
    def sats(self) -> List[Sat]:
        return self._sats

    def limit(self, n: int) -> Self:
        """returns a new Sats object containing the first n sats

        Args:
            n: number of satellites

        Returns:
            new Sats object
        """
        return self.__class__(self.sats[:n])

    def filter(self, fn: Callable[[Sat], bool]) -> Self:
        """returns a new Sats object containing all sats for which fn(sat) is true

        Usage:
            >>> is_comms(sat):
            >>>     return sat.category == "Communication"
            >>> comms_sats = sats.filter(is_comms)

        Args:
            fn: function as argument

        Returns:
            new Sats object
        """
        return self.__class__([sat for sat in self.sats if fn(sat)])

    def filter_old(self, age_days: float = 14.0) -> Self:
        """filter out data from sats older than age_days

        Args:
            age_days: maximum tracking data age. Defaults to 14.0.

        Returns:
            new Sats object
        """
        return self.filter(lambda sat: sat.days_since_epoch < age_days)

    def filter_only_debris(self) -> Self:
        return self.filter(lambda sat: "debris" in sat.tags)

    def filter_no_debris(self) -> Self:
        return self.filter(lambda sat: not "debris" in sat.tags)

    def print_all_tags(self) -> None:
        tags = {}
        # generate unique dict of all tags
        for sat in self.sats:
            for tag in sat.tags:
                tags[tag] = True

        tags = list(tags.keys())
        tags.sort()
        for tag in tags:
            print(tag, end=", ")


class Orbit:
    def __init__(self, name: str, alt: float) -> None:
        """represents a typical orbit

        Args:
            name: name of orbit
            alt: typical orbit altitude [km]
        """
        self.name = name
        self.alt = alt

    def __repr__(self) -> str:
        return f"<Orbit {self.name} {self.alt}km>"


class Orbits:
    """Utility object for calculating using common orbit data
    """

    def __init__(self) -> None:
        self.orbits = [
            Orbit("VLEO", 400),
            Orbit("Starlink", 550),
            Orbit("LEO", 2000),
            Orbit("GEO", 35768),
        ]

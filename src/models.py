"""contains models required to proccess satellite data"""
from typing import Callable, List, Dict, Tuple, Optional, TYPE_CHECKING
from typing_extensions import Self

from datetime import datetime, timedelta

from skyfield.api import EarthSatellite, load, wgs84, utc
from skyfield.toposlib import GeographicPosition
from skyfield.timelib import Time
from skyfield.framelib import itrs

from sgp4.api import Satrec, WGS84

from .orbital_utilities import true_to_mean_anomaly
from .const import *
import numpy as np

# Time scale for Earth Orbiting Satellites
ts = load.timescale()

# Autoincrement id for new Sats
counter = 100000


def get_next_id():
    global counter
    counter += 1
    if counter >= 339999:
        counter = 100000
    return counter


class Satellite:
    def __init__(self, sat: EarthSatellite, group: str = "", category: str = "") -> None:
        self.tags = list(filter(None, [group.lower(), category.lower()]))
        self._sat = sat
        self.group = group.lower()
        self.category = category.lower()
        self._object_type = None
        self._ops_status = None
        self._owner = None
        self._launch_date = None
        self._launch_site = None
        self._launch_country = None
        self._owner_country = None

    @classmethod
    def from_tle(cls, fields, group: str = "", category: str = "") -> Self:
        """See `datasources.py` for usage"""
        return cls(
            sat=EarthSatellite.from_omm(ts, fields),
            group=group,
            category=category
        )

    @classmethod
    def from_orbital_elements(
        cls,
        eccentricity: float,
        argument_of_perigee: float,
        inclination: float,
        true_anomaly: float,
        semi_major_axis: float,
        RAAN: float,
        name: str = ""
    ) -> Self:
        """create a new `Satellite` object from Keplerian orbital elements

        Args:
            eccentricity: eccentricity
            argument_of_perigee: argument of perigee [deg]
            inclination: inclination [deg]
            true_anomaly: true anomaly [deg]
            semi_major_axis: semi major axis [km]
            RAAN: right ascension of ascending node [deg]
            name: `Satellite` name

        Returns:
            new `Satellite` object
        """
        argument_of_perigee = np.radians(argument_of_perigee)
        inclination = np.radians(inclination)
        true_anomaly = np.radians(true_anomaly)
        RAAN = np.radians(RAAN)

        mean_motion = np.sqrt(MU / np.pow(semi_major_axis, 3)) * 60
        mean_anomaly = true_to_mean_anomaly(true_anomaly, eccentricity)
        return cls.from_tle_orbital_elements(
            eccentricity=eccentricity,
            argument_of_perigee=argument_of_perigee,
            inclination=inclination,
            mean_anomaly=mean_anomaly,
            mean_motion=mean_motion,
            RAAN=RAAN,
            name=name
        )

    @classmethod
    def from_tle_orbital_elements(
        cls,
        eccentricity: float,
        argument_of_perigee: float,
        inclination: float,
        mean_anomaly: float,
        mean_motion: float,
        RAAN: float,
        epoch: Optional[datetime] = None,
        bstar: float = 0,
        ndot: float = 0,
        nndot: float = 0,
        name: str = "",
        group: str = "",
        category: str = ""
    ) -> Self:
        """generate a new `Satellite` object from orbital parameters

        Args:
            eccentricity: eccentricity
            argument_of_perigee: argument of perigee [rad]
            inclination: inclination [rad]
            mean_anomaly: mean anomaly [rad]
            mean_motion: mean motion [rad/min]
            RAAN: right ascension of ascending node [rad]
            epoch: epoch `datetime` of orbital parameters. Defaults to None.
            bstar: drag coefficient [/r_E]. Defaults to 0.
            ndot: ballistic coefficient [rad/min^2]. Defaults to 0.
            nndot: second derivative of mean motion [rad/min^3]. Defaults to 0.
            group: group tag. Defaults to "".
            category: category string. Defaults to "".

        Returns:
            `Satellite` object
        """
        # TODO: Add name to `Satellite` object

        # calculate the number of days since epoch
        if not epoch:
            epoch = datetime.now(tz=utc)
        epoch_days = (
            epoch - datetime(1949, 12, 31, 0, 0, 0, tzinfo=utc)
        ).total_seconds() / 86400

        # create SPG4 object
        satrec = Satrec()
        satrec.sgp4init(
            WGS84,            # gravity model
            'i',              # 'a' = old AFSPC mode, 'i' = improved mode
            get_next_id(),    # satnum: Satellite number
            epoch_days,        # epoch: days since 1949 December 31 00:00 UT
            bstar,       # bstar: drag coefficient (/earth radii)
            ndot,  # ndot: ballistic coefficient (radians/minute^2)
            # nddot: second derivative of mean motion (radians/minute^3)
            nndot,
            eccentricity,        # ecco: eccentricity
            argument_of_perigee,  # argpo: argument of perigee (radians)
            inclination,  # inclo: inclination (radians)
            mean_anomaly,  # mo: mean anomaly (radians)
            mean_motion,  # no_kozai: mean motion (radians/minute)
            # nodeo: right ascension of ascending node (radians)
            RAAN,
        )

        # wrap in skyfield object
        sat = cls(
            sat=EarthSatellite.from_satrec(satrec, ts),
            group=group,
            category=category
        )

        # manually add name to the sat
        sat._sat.name = name

        return sat

    def to_tle(self) -> list[str]:
        # !
        # !
        # !
        # ! Change of implementation - store tle on creation or generate reasonable data for Satellites made with other methods
        # !
        # !
        # !

        raise NotImplementedError(
            "This feature is yet to be completely implemented"
        )

        # TODO: Implement tle f-strings

        # line two
        # satellite number
        sat_no = f"{self.satellite_number:05}" if self.satellite_number <= 99999 else "00000"
        # TODO: Implement line two

        # line three
        i = f"{rad2deg(self.inclination):07.4f}" if rad2deg(
            self.inclination) <= 999 else "000.0000"  # inclination degrees
        RAAN = f"{rad2deg(self.right_ascension_of_ascending_node):07.4f}" if rad2deg(
            self.right_ascension_of_ascending_node) <= 999 else "000.0000"  # RAAN degrees
        e = f"{self.eccentricity*10000000:07d}" if self.eccentricity <= 1 else "0000000"
        argument_of_perigee = f"{rad2deg(self.argument_of_perigee):07.4f}" if rad2deg(
            self.argument_of_perigee) <= 999 else "000.0000"  # argument of perigee degrees
        mean_anomaly = f"{rad2deg(self.mean_anomaly):07.4f}" if rad2deg(
            self.mean_anomaly) <= 999 else "000.0000"  # mean anomaly degrees
        mean_motion = f"{self.mean_motion*(720/pi):011.8f}" if self.mean_motion else "00.00000000"
        rev_num = ...
        checksum = ...

        return [
            self.name,
            f"1 {sat_no}U",
            f"2 {sat_no} {i} {RAAN} {e} {argument_of_perigee} {mean_anomaly} {mean_motion}{rev_num}{checksum}"
        ]

    @property
    def constellation(self) -> str:
        """return the constellation extracted from the name if it exists"""
        try:
            # strip constellation from name
            constellation = self.name.upper().split("-")[0].split(" ")[0]
            # ignore if constellation is just a number - probably the launch year
            if constellation.isdigit():
                return ""
            return constellation
        except Exception as e:
            print(e)
            return ""

    @property
    def object_type(self) -> str | None:
        return self._object_type

    @property
    def operational_status(self) -> str | None:
        return self._ops_status

    @property
    def element_set_no(self) -> int:
        return self._sat.model.elnum

    @property
    def ndot(self) -> float:
        """first time derivative of the mean motion

        ignored by SPG4"""
        return self._sat.model.ndot

    @property
    def owner(self) -> str | None:
        return self._owner

    @property
    def launch_date(self) -> datetime | None:
        return self._launch_date

    @property
    def launch_age(self) -> timedelta:
        if not self.launch_date:
            return timedelta(-1)
        return (datetime.now() - self.launch_date)

    @property
    def launch_site(self) -> str | None:
        return self._launch_site

    @property
    def owner_country(self) -> List[str] | None:
        """this represents the owner countries not the launch country, although they may be the same"""
        return self._owner_country

    @property
    def launch_country(self) -> str | None:
        """this represents the launch site country not the owner, although they may be the same"""
        return self._launch_country

    @property
    def norad_cat_id(self) -> int:
        return self._sat.model.satnum

    @property
    def b_star(self) -> float:
        """ballistic drag coefficient B* in inverse earth radii"""
        return self._sat.model.bstar

    @property
    def inclination(self) -> float:
        """inclination [radians]"""
        return self._sat.model.inclo

    @property
    def right_ascension_of_ascending_node(self) -> float:
        """right ascension of ascending node [radians]"""
        return self._sat.model.nodeo

    @property
    def eccentricity(self) -> float:
        return self._sat.model.ecco

    @property
    def argument_of_perigee(self) -> float:
        """argument of perigee [radians]"""
        return self._sat.model.argpo

    @property
    def mean_anomaly(self) -> float:
        """mean anomaly [radians]"""
        return self._sat.model.mo

    @property
    def mean_motion(self) -> float:
        """mean motion [radians per minute]"""
        return self._sat.model.no_kozai

    @property
    def revolution_number_at_epoch(self) -> int:
        """revelotion number at epoch [Revs]"""
        return self._sat.model.revnum

    def details_to_dict(self) -> dict:
        return {
            "details": {
                "name": self.name,
                "launch date": self.launch_date.date().isoformat() if self.launch_date else "Unknown",
                "group": self.group,
                "category": self.category,
                "NORAD CAT ID": self.norad_cat_id,
                "launch site": self.launch_site if self.launch_site else "Unknown",
                "owner": self.owner if self.owner else "Unknown",
                "object type": self.object_type if self.object_type else "Unknown",
                "operational status": self.operational_status if self.operational_status else "Unknown",
                "tags": self.tags
            }
        }

    def orbital_parameters_to_dict(self) -> dict:
        return {
            "inclination [rads]": self.inclination,
            "ballastic drag coefficient (B*) [inverse earth radii]": self.b_star,
            "right ascension of ascending node [rads]": self.right_ascension_of_ascending_node,
            "eccentricity": self.eccentricity,
            "argument of perigee [rads]": self.argument_of_perigee,
            "mean anomaly [rads]": self.mean_anomaly,
            "mean motion [rads/min]": self.mean_motion,
            "revolution number at epoch [revs]": self.revolution_number_at_epoch

        }

    def to_dict(self) -> dict:
        out = self.details_to_dict()
        out["orbital parameters"] = self.orbital_parameters_to_dict()
        return out

    def info(self) -> str:
        """return information about each satellite

        Returns:
            str information output
        """
        from pprint import pformat
        return pformat(self.to_dict())

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
    def id(self) -> int:
        return self.norad_cat_id

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

    def __repr__(self) -> str:
        return f"<Sat {self.name} ({' - '.join(self.tags)})>"

    def generate_debris_tag(self) -> None:
        """generate a tag for this satellite if it is debris

        Please note the NORAD dataset contains a negligible amount of debris
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
            self._object_type = SATCAT.OBJECT_TYPE(data["OBJECT_TYPE"])
            self.add_tag(self._object_type)

        if data['OPS_STATUS_CODE']:
            self._ops_status = SATCAT.OPERATIONAL_STATUS(
                data["OPS_STATUS_CODE"])
            self.add_tag(self._ops_status)

        if data['OWNER']:
            self._owner = SATCAT.OWNER(data["OWNER"])
            self.add_tag(self._owner)
        else:
            self._owner = ""
        self._owner_country = SATCAT.COUNTRY(self._owner)

        if data['LAUNCH_DATE']:
            self._launch_date = datetime.strptime(
                data['LAUNCH_DATE'], '%Y-%m-%d')

        if data['LAUNCH_SITE']:
            self._launch_site = SATCAT.LAUNCH_SITE(data["LAUNCH_SITE"])
            self.add_tag(self._launch_site)

            # generate launch country
            self._launch_country = SATCAT.LAUNCH_COUNTRY(self._launch_site)


class SatelliteSet:
    """Container for multiple Sat objects with helpful methods for filtering, sorting and handling Sat data
    """

    def __init__(self, sats: List[Satellite]) -> None:
        self._sats = sats

        # filter and analyse data
        self.remove_duplicate_tags()
        self.remove_duplicate_sats_by_NORAD()
        for sat in self.sats:
            sat.generate_debris_tag()

    def __repr__(self) -> str:
        return f"<Sats n={len(self.sats)}>"

    def __len__(self) -> int:
        return len(self.sats)

    def __add__(self, other: Self | list[Satellite]) -> Self:
        if isinstance(other, SatelliteSet):
            return self.__class__(self._sats + other._sats)
        else:
            return self.__class__(self._sats + other)

    def sort(self):
        self._sats.sort(key=lambda sat: sat.name)

    def append(self, other: Satellite):
        self._sats.append(other)

    def add_tags_from_SATCAT(self, satcat) -> None:
        """add additional tags to sats from SATCAT data"""
        for sat in self.sats:
            sat.add_tags_from_SATCAT(satcat)

    def remove_duplicate_sats_by_NORAD(self) -> None:
        """remove all duplicate satellites by NORAD CAT ID"""
        out_sats: dict[int, Satellite] = {}
        for sat in self.sats:
            if sat.norad_cat_id not in out_sats:
                out_sats[sat.norad_cat_id] = sat
        self._sats = list(out_sats.values())

    def remove_duplicate_tags(self):
        """removes all duplicate sats after combining tags
        """
        sats: Dict[str, Satellite] = {}
        for sat in self.sats:
            if sat.name not in sats:
                sats[sat.name] = sat
            else:
                # preserve category
                sats[sat.name].category = sats[sat.name].category if "special" not in sats[sat.name].category else sat.category

                # combine tags
                sats[sat.name].add_tags(sat.tags)

        self._sats = list(sats.values())

    @property
    def sats(self) -> List[Satellite]:
        return self._sats

    def limit(self, n: int, random_order=True) -> Self:
        """returns a new Sats object containing the first n sats

        Args:
            n: number of satellites

        Returns:
            new Sats object
        """
        if random_order:
            return self.__class__(self.randomise_order().sats[:n])
        else:
            return self.__class__(self.sats[:n])

    def randomise_order(self) -> Self:
        """returns a new `SatelliteSet` object with the same sats in a different order.

        Returns:
            new `SatelliteSat` object
        """
        from random import sample
        return self.__class__(sample(self.sats, len(self.sats)))

    def filter(self, fn: Callable[[Satellite], bool]) -> Self:
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

    def all_tags_dict(self) -> dict[str, int]:
        """return a dictionary with all tags and the number of occorances"""
        tags = {}
        # generate unique dict of all tags
        for sat in self.sats:
            for tag in sat.tags:
                tags[tag] = tags.get(tag, 0) + 1

        return tags

    def print_all_tags(self) -> None:
        from pprint import pprint
        pprint(self.all_tags_dict())

    def get_all_categories(self) -> dict[str, int]:
        """return an dictionary of all categories and the number of their satellites in that category"""
        categories = {}
        for sat in self.sats:
            categories[sat.category] = categories.get(sat.category, 0) + 1
        return categories

    def print_all_categories(self) -> None:
        """print all satellite categories with count"""
        from pprint import pprint
        pprint(self.get_all_categories())

    def print_all_constellations(self, min=2) -> None:
        """print all satellite constellations with count with at least `min` satellites

        Args:
            min: minimum number in constellations to show. Defaults to 2.
        """
        from pprint import pprint
        constellations = {}
        for sat in self.sats:
            constellations[sat.constellation] = constellations.get(
                sat.constellation, 0) + 1
        constellations = {k: v for k, v in constellations.items() if v >= min}
        constellations = dict(sorted(constellations.items(),
                                     key=lambda item: item[1], reverse=True))
        del constellations[""]
        pprint(constellations)

    def get_by_name(self, name: str) -> Satellite:
        """get a `Satellite` object by name, for example "ISS (ZARYA)"

        Args:
            name: name of satellite

        Returns:
            `Satellite` object if found otherwise `None`
        """
        for sat in self.sats:
            if sat.name == name:
                return sat
        return None # type: ignore

    def get_by_NORAD_CAT_ID(self, id: int) -> Satellite:
        """get a `Satellite` object by NORAD CAT ID, for example, 25544 for the ISS
        
        Args:
            id: NORAD CAT ID of satellite
            
        Returns:
            `Satellite` object if found otherwise `None`
        """
        for sat in self.sats:
            if sat.norad_cat_id == id:
                return sat
        return None # type: ignore
    
    def filter_category(self, category: str) -> Self:
        """create a new instance of `SatelliteSet` that only includes satellites with category `category`"""
        is_cat = lambda sat: sat.category == category

        return self.filter(is_cat)

class Orbit:    
    def __init__(self, name: str, alt: float) -> None:
        """represents a typical orbit

        Args:
            name: name of orbit
            alt: typical orbit altitude[km]
        """
        self.name = name
        self.alt = alt

    def __repr__(self) -> str:
        return f"<Orbit {self.name} {self.alt}km>"

    def to_dict(self) -> dict:
        return {"name": self.name, "altitude [km]": self.alt}


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

    def to_dict(self) -> dict:
        return {"orbits": [orbit.to_dict() for orbit in self.orbits]}

"""downloads, caches and loads data from CelesTrak"""
from typing import List, Dict

import os
import functools
import pickle
from csv import DictReader

from skyfield.api import load

from .models import Satellite, SatelliteSet


class NORADSource:
    """NORADSource represents a source (data query results) from CelesTrak

    This is used internally by NORAD to manage all sources from CelesTrak

    Usage:
        >>> active_sources = NORADSource("active")
    """

    def __init__(self, group: str, category: str, format: str = "csv") -> None:
        self.group = group.lower()
        self.category = category.lower()
        self._format = format.lower()

    @property
    def url(self) -> str:
        return f"https://celestrak.org/NORAD/elements/gp.php?GROUP={self.group}&FORMAT={self._format}"

    @property
    def filename(self) -> str:
        return f"{self.group}.{self._format}"

    def __repr__(self) -> str:
        return f"group: {self.group}, category: {self.category}, format: {self._format}, url: {self.url}"


class NORAD:
    """NORAD Satellite tracking data source container

    Notes:
        Data is retrieved from CelesTrak
    """

    def __init__(self, path: str = "./data/NORAD/", cache_TTL: float = 7.0, filetype: str = "csv") -> None:
        """Object to haddle downloading NORAD data from CelesTrak

        Notes:
            Data older than a few weeks will be inaccurate due to the instantaneous nature of radar tracking. Data from CelesTrak and by extension NORAD is only updated when available, as such there may not be any recent or accurate data available for some satellites. Data is unlikely to be updated more than once a day.

        Args:
            path: path to save cached data. Defaults to "./data/NORAD/".
            cache_TTL: time to use cached data before refreshing, in days. Defaults to 7.0.
        """
        self.path = path
        self._cache_TTL = cache_TTL
        self.filetype = filetype
        self._sources_by_group = {}

        # CelesTrak retry backoff
        self.retry_number = 0
        self.wait_until = 0

    def get_source_groups_from_celesTrak(self) -> None:
        """get the source groups from celesTrak and cache the data in a pickle"""
        import requests
        import requests.exceptions
        from bs4 import BeautifulSoup
        import time

        url = f"https://celestrak.org/NORAD/elements/index.php?FORMAT={self.filetype}"
        sources_by_group: Dict[str, NORADSource] = {}

        if self.wait_until > time.time():
            raise TimeoutError(
                f"Backing off request to CelesTrak after {self.retry_number} rejected requests for the next {self.wait_until - time.time()} seconds")

        try:
            # get webpage data and raise HTTPError is the response was unsuccessful
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            self.retry_number = 0
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            # update backoff wait period
            self.retry_number += 1

            MAX_WAIT = 12 * 60 * 60  # 12 hours
            BACKOFF_FACTOR = 4  # 4 seconds

            backoff_period = min(
                MAX_WAIT, BACKOFF_FACTOR * 2**(self.retry_number))
            self.wait_until = time.time() + backoff_period

            # parse html
        soup = BeautifulSoup(response.text, "html.parser")

        for table in soup.find_all('table', class_='striped'):
            try:
                # get group name
                header = table.find("th").get_text(  # type: ignore
                    strip=True)

                # get groups from the table
                links = table.find_all("a", title="Table")  # type: ignore
                urls = [link.get("href") for link in links]  # type: ignore
                groups = [url.split("=", 1)[1].split("&FORMAT=", 1)[  # type: ignore
                    0] for url in urls]

                # create NORADSource to allow further processing
                for group in groups:
                    sources_by_group[group] = NORADSource(
                        group, header, self.filetype)
            except Exception as e:
                print(e)

        self._sources_by_group = sources_by_group
        print("Using source groups from CelesTrak")

        # cache groups
        if self._sources_by_group:
            try:
                with open(f"{self.path}NORAD.pkl", "wb") as f:
                    pickle.dump(self._sources_by_group, f)
                    print("NORAD groups cached")
            except Exception as e:
                print(f"Error caching NORAD groups: {e}")

    def get_source_groups_from_cache(self) -> None:
        """get the source groups from the pickle cache"""
        with open(f"{self.path}NORAD.pkl", "rb") as f:
            self._sources_by_group = pickle.load(f)
        print("Using cached source groups")

    def get_source_groups_from_historic_data(self) -> None:
        """get the source groups from historical data - this may not download all current data"""
        self._sources_by_group = {
            **{group: NORADSource(group, "weather & earth resources", self.filetype) for group in ["weather", "noaa", "goes", "resource", "sarsat", "dmc", "tdrss", "argos", "planet", "spire"]},
            **{group: NORADSource(group, "communications", self.filetype) for group in ["geo", "gpz", "intelsat", "iridium", "starlink", "orbcomm", "swarm", "x-comm", "gpz-plus", "ses", "iridium-NEXT", "oneweb", "globalstar", "amateur", "other-comm", "satnogs", "gorizont", "raduga", "molniya"]},
            **{group: NORADSource(group, "navigation", self.filetype) for group in ["gnss", "gps-ops", "glo-ops", "galileo", "beidou", "sbas", "nnss", "musson"]},
            **{group: NORADSource(group, "scientific", self.filetype) for group in ["science", "geodetic", "engineering", "education"]},
            **{group: NORADSource(group, "miscellaneous", self.filetype) for group in ["military", "radar", "cubesat", "other"]},
            **{group: NORADSource(group, "special-interest", self.filetype) for group in ["stations", "visual", "active", "analyst", "cosmos-1408-debris", "fengyun-1c-debris", "iridium-33-debris", "cosmos-2251-debris"]}}
        print("Using historical source groups (Some satellites may be missing or missing metadata)")

    def get_source_groups(self) -> None:
        try:
            self.get_source_groups_from_cache()
            return
        except Exception as e:
            print(
                f"Exception occurred whilst getting source groups from cache. This may be because the cache hasn't been created yet: {e}\nContinuing as expected..."
            )

        try:
            self.get_source_groups_from_celesTrak()
            return
        except Exception as e:
            print(
                f"Exception occurred whilst getting source groups from CelesTrak. This may be due to network issues: {e}\nContinuing as expected..."
            )

        try:
            self.get_source_groups_from_historic_data()
            return
        except Exception as e:
            print(
                f"Exception occurred whilst getting source groups from historic data. {e}"
            )

        raise RuntimeError("Unable to get source groups")

    def source_by_group(self, group: str) -> NORADSource:
        return self._sources_by_group[group]

    def get_source_names(self) -> List[str]:
        return list(self._sources_by_group.keys())

    @property
    def sources(self) -> List[NORADSource]:
        return list(self._sources_by_group.values())

    def update_sources(self) -> None:
        # create source directory if not exists
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        # cache NORAD groups if any NORAD sources are out of date
        if self.sources:
            for source in self.sources:
                try:
                    filepath = self.path + source.filename
                    if not load.exists(filepath) or load.days_old(filepath) >= self._cache_TTL:
                        print("NORAD groups out-of-date: updating from CelesTrak")
                        self.get_source_groups_from_celesTrak()
                        break
                except Exception as e:
                    print(e)

        # update sources
        for source in self.sources:
            try:
                filepath = self.path + source.filename
                if not load.exists(filepath) or load.days_old(filepath) >= self._cache_TTL:
                    load.download(source.url, filepath)
                    print(f"Updated {source.group} NORAD data sources")
            except Exception as e:
                print(e)

    def load_sats(self, sources: List[NORADSource]) -> SatelliteSet:
        # load specified sources
        sats = []

        for source in sources:
            filepath = self.path + source.filename
            with load.open(filepath, mode="r") as f:
                data = list(DictReader(f))

                sats.extend([Satellite.from_tle(
                    fields, source.group, source.category
                ) for fields in data])
                print(
                    f"Loaded {source.group} NORAD data sources {' '*40}",
                    end="\r"
                )

        print(f"Loaded all {len(sources)} NORAD data sources {' '*40}")

        return SatelliteSet(sats)

    def load_all_sats(self) -> SatelliteSet:
        # load sats all sats
        return self.load_sats(self.sources)


class SATCATSource:
    def __init__(self, url: str, filename: str) -> None:
        self.url = url
        self.filename = filename


class SATCAT:
    def __init__(self, path: str = "./data/SATCAT/", cache_TTL: float = 7.0) -> None:
        self.path = path
        self._cache_TTL = cache_TTL
        self.sources = [SATCATSource(
            "https://celestrak.org/pub/satcat.csv", "satcat.csv")]

    def update_sources(self) -> None:
        """updates the SATCAT sources from CelesTrak if they are older than cache_TTL
        """
        # create source directory if not exists
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        # update sources
        for source in self.sources:
            filepath = self.path + source.filename
            if not load.exists(filepath) or load.days_old(filepath) >= self._cache_TTL:
                load.download(source.url, filepath)
                print(f"Updated SATCAT data sources")

    def load(self) -> Dict[str, Dict]:
        """load all SATCAT data and return n a dict of dicts indexed by sat name

        Returns:
            SATCAT data indexed by Sat name
        """
        sats = []

        for source in self.sources:
            filepath = self.path + source.filename
            with load.open(filepath, mode="r") as f:
                data = list(DictReader(f))

                sats.extend(data)
                print(f"Loaded {source.filename} SATCAT data source")

        return {sat['OBJECT_NAME']: sat for sat in sats}

    @classmethod
    def OBJECT_TYPE(cls, object_type: str) -> str:
        """returns the object type from the SATCAT lookup table

        Args:
            object_type: string code from SATCAT

        Returns:
            Human readable description
        """
        lookup_table = {
            "PAY": "Payload", "R/B": "Rocket body",
            "DEB": "Other debris", "UNK": "Unknown"
        }
        if object_type in lookup_table:
            return lookup_table[object_type]
        return ""

    @classmethod
    def OPERATIONAL_STATUS(cls, operational_status: str) -> str:
        """returns the operational status from the SATCAT lookup table

        Args:
            operational_status: string code from SATCAT

        Returns:
            Human readable operational status
        """
        lookup_table = {
            "+": "Operational", "-": "Nonoperational",
            "P": "Partially Operational*Partially fulfilling primary mission or secondary mission(s)*", "B": "Backup/Standby*Previously operational satellite put into reserve status*", "S": "Spare*New satellite awaiting full activation*", "X": "Extended Mission", "D": "Decayed", "?": "Unknown"
        }
        if operational_status in lookup_table:
            return lookup_table[operational_status]
        return ""

    @classmethod
    def OWNER(cls, owner: str) -> str:
        """returns the owner from the SATCAT lookup table

        Args:
            owner: string code from SATCAT

        Returns:
            Human readable owner
        """
        lookup_table = {
            "AB": "Arab Satellite Communications Organization", "ABS": "Asia Broadcast Satellite", "AC": "Asia Satellite Telecommunications Company (ASIASAT)",
            "ALG": "Algeria", "ANG": "Angola", "ARGN": "Argentina", "ARM": "Republic of Armenia", "ASRA": "Austria", "AUS": "Australia", "AZER": "Azerbaijan", "BEL": "Belgium", "BELA": "Belarus", "BERM": "Bermuda", "BGD": "Peoples Republic of Bangladesh", "BHUT": "Kingdom of Bhutan", "BOL": "Bolivia", "BRAZ": "Brazil", "BUL": "Bulgaria", "CA": "Canada", "CHBZ": "China/Brazil", "CHTU": "China/Turkey", "CHLE": "Chile", "CIS": "Commonwealth of Independent States (former USSR)", "COL": "Colombia", "CRI": "Republic of Costa Rica", "CZCH": "Czech Republic (former Czechoslovakia)", "DEN": "Denmark", "DJI": "Republic of Djibouti", "ECU": "Ecuador", "EGYP": "Egypt", "ESA": "European Space Agency", "ESRO": "European Space Research Organization", "EST": "Estonia", "ETH": "Ethiopia", "EUME": "European Organization for the Exploitation of Meteorological Satellites (EUMETSAT)", "EUTE": "European Telecommunications Satellite Organization (EUTELSAT)", "FGER": "France/Germany", "FIN": "Finland", "FR": "France", "FRIT": "France/Italy", "GER": "Germany", "GHA": "Republic of Ghana", "GLOB": "Globalstar", "GREC": "Greece", "GRSA": "Greece/Saudi Arabia", "GUAT": "Guatemala", "HUN": "Hungary", "IM": "International Mobile Satellite Organization (INMARSAT)", "IND": "India", "INDO": "Indonesia", "IRAN": "Iran", "IRAQ": "Iraq", "IRID": "Iridium", "IRL": "Ireland", "ISRA": "Israel", "ISRO": "Indian Space Research Organisation", "ISS": "International Space Station", "IT": "Italy", "ITSO": "International Telecommunications Satellite Organization (INTELSAT)", "JPN": "Japan", "KAZ": "Kazakhstan", "KEN": "Republic of Kenya", "LAOS": "Laos", "LKA": "Democratic Socialist Republic of Sri Lanka", "LTU": "Lithuania", "LUXE": "Luxembourg", "MA": "Morroco", "MALA": "Malaysia", "MCO": "Principality of Monaco", "MDA": "Republic of Moldova", "MEX": "Mexico", "MMR": "Republic of the Union of Myanmar", "MNG": "Mongolia", "MUS": "Mauritius", "NATO": "North Atlantic Treaty Organization", "NETH": "Netherlands", "NICO": "New ICO", "NIG": "Nigeria", "NKOR": "Democratic People's Republic of Korea", "NOR": "Norway", "NPL": "Federal Democratic Republic of Nepal", "NZ": "New Zealand", "O3B": "O3b Networks", "ORB": "ORBCOMM", "PAKI": "Pakistan", "PERU": "Peru", "POL": "Poland", "POR": "Portugal", "PRC": "People's Republic of China", "PRY": "Republic of Paraguay", "PRES": "People's Republic of China/European Space Agency", "QAT": "State of Qatar", "RASC": "RascomStar-QAF", "ROC": "Taiwan (Republic of China)", "ROM": "Romania", "RP": "Philippines (Republic of the Philippines)", "RWA": "Republic of Rwanda", "SAFR": "South Africa", "SAUD": "Saudi Arabia", "SDN": "Republic of Sudan", "SEAL": "Sea Launch", "SES": "SES", "SGJP": "Singapore/Japan", "SING": "Singapore", "SKOR": "Republic of Korea", "SPN": "Spain", "STCT": "Singapore/Taiwan", "SVN": "Slovenia", "SWED": "Sweden", "SWTZ": "Switzerland", "TBD": "To Be Determined", "THAI": "Thailand", "TMMC": "Turkmenistan/Monaco", "TUN": "Republic of Tunisia", "TURK": "Turkey", "UAE": "United Arab Emirates", "UK": "United Kingdom", "UKR": "Ukraine", "UNK": "Unknown", "URY": "Uruguay", "US": "United States", "USBZ": "United States/Brazil", "VAT": "Vatican City State", "VENZ": "Venezuela", "VTNM": "Vietnam", "ZWE": "Republic of Zimbabwe"
        }
        if owner in lookup_table:
            return lookup_table[owner]
        return ""

    @classmethod
    def LAUNCH_SITE(cls, launch_site: str) -> str:
        """returns the launch site from the SATCAT lookup tables

        Args:
            launch_site: string code from SATCAT

        Returns:
            Human readable launch site
        """
        lookup_table = {
            "AFETR": "Air Force Eastern Test Range, Florida, USA", "AFWTR": "Air Force Western Test Range, California, USA", "CAS": "Canaries Airspace", "DLS": "Dombarovskiy Launch Site, Russia", "ERAS": "Eastern Range Airspace", "FRGUI": "Europe's Spaceport, Kourou, French Guiana", "HGSTR": "Hammaguira Space Track Range, Algeria", "JJSLA": "Jeju Island Sea Launch Area, Republic of Korea", "JSC": "Jiuquan Space Center, PRC", "KODAK": "Kodiak Launch Complex, Alaska, USA", "KSCUT": "Uchinoura Space Center(Fomerly Kagoshima Space Center—University of Tokyo, Japan)", "KWAJ": "US Army Kwajalein Atoll (USAKA)", "KYMSC": "Kapustin Yar Missile and Space Complex, Russia", "NSC": "Naro Space Complex, Republic of Korea", "PLMSC": "Plesetsk Missile and Space Complex, Russia", "RLLB": "Rocket Lab Launch Base, Mahia Peninsula, New Zealand", "SCSLA": "South China Sea Launch Area, PRC", "SEAL": "Sea Launch Platform (mobile)", "SEMLS": "Semnan Satellite Launch Site, Iran", "SMTS": "Shahrud Missile Test Site, Iran", "SNMLP": "San Marco Launch Platform, Indian Ocean (Kenya)", "SPKII": "Space Port Kii, Japan", "SRILR": "Satish Dhawan Space Centre, India(Formerly Sriharikota Launching Range)", "SUBL": "Submarine Launch Platform (mobile)", "SVOBO": "Svobodnyy Launch Complex, Russia", "TAISC": "Taiyuan Space Center, PRC", "TANSC": "Tanegashima Space Center, Japan", "TYMSC": "Tyuratam Missile and Space Center, Kazakhstan (Also known as Baikonur Cosmodrome)", "UNK": "Unknown", "VOSTO": "Vostochny Cosmodrome, Russia", "WLPIS": "Wallops Island, Virginia, USA", "WOMRA": "Woomera, Australia", "WRAS": "Western Range Airspace", "WSC": "Wenchang Satellite Launch Site, PRC", "XICLF": "Xichang Launch Facility, PRC", "YAVNE": "Yavne Launch Facility, Israel", "YSLA": "Yellow Sea Launch Area, PRC", "YUN": "Yunsong Launch Site (Sohae Satellite Launching Station), Democratic People's Republic of Korea (North Korea)"
        }
        if launch_site in lookup_table:
            return lookup_table[launch_site]
        return ""

    @classmethod
    def LAUNCH_COUNTRY(cls, launch_site: str) -> str:
        """returns the launch country when given the launch_site (output of `cls.LAUNCH_SITE()`)"""
        lookup_table = {
            'Air Force Eastern Test Range, Florida, USA': 'USA', 'Air Force Western Test Range, California, USA': 'USA', 'Canaries Airspace': 'Canaries Airspace', 'Dombarovskiy Launch Site, Russia': 'Russia', 'Eastern Range Airspace': 'USA', "Europe's Spaceport, Kourou, French Guiana": 'French Guiana', 'Hammaguira Space Track Range, Algeria': 'Algeria', 'Jeju Island Sea Launch Area, Republic of Korea': 'Republic of Korea', 'Jiuquan Space Center, PRC': 'PRC', 'Kodiak Launch Complex, Alaska, USA': 'USA', 'Uchinoura Space Center(Fomerly Kagoshima Space Center—University of Tokyo, Japan)': 'Japan)', 'US Army Kwajalein Atoll (USAKA)': 'USA', 'Kapustin Yar Missile and Space Complex, Russia': 'Russia', 'Naro Space Complex, Republic of Korea': 'Republic of Korea', 'Plesetsk Missile and Space Complex, Russia': 'Russia', 'Rocket Lab Launch Base, Mahia Peninsula, New Zealand': 'New Zealand', 'South China Sea Launch Area, PRC': 'PRC', 'Sea Launch Platform (mobile)': 'Sea Launch Platform (mobile)', 'Semnan Satellite Launch Site, Iran': 'Iran', 'Shahrud Missile Test Site, Iran': 'Iran', 'San Marco Launch Platform, Indian Ocean (Kenya)': 'Kenya', 'Space Port Kii, Japan': 'Japan', 'Satish Dhawan Space Centre, India(Formerly Sriharikota Launching Range)': 'India', 'Submarine Launch Platform (mobile)': 'Sea Launch Platform (mobile)', 'Svobodnyy Launch Complex, Russia': 'Russia', 'Taiyuan Space Center, PRC': 'PRC', 'Tanegashima Space Center, Japan': 'Japan', 'Tyuratam Missile and Space Center, Kazakhstan (Also known as Baikonur Cosmodrome)': 'Kazakhstan', 'Unknown': 'Unknown', 'Vostochny Cosmodrome, Russia': 'Russia', 'Wallops Island, Virginia, USA': 'USA', 'Woomera, Australia': 'Australia', 'Western Range Airspace': 'USA', 'Wenchang Satellite Launch Site, PRC': 'PRC', 'Xichang Launch Facility, PRC': 'PRC', 'Yavne Launch Facility, Israel': 'Israel', 'Yellow Sea Launch Area, PRC': 'PRC', "Yunsong Launch Site (Sohae Satellite Launching Station), Democratic People's Republic of Korea (North Korea)": " Democratic People's Republic of Korea (North Korea)"
        }
        if launch_site in lookup_table:
            return lookup_table[launch_site]
        return ""

    @classmethod
    def ORBIT_TYPE(cls, orbit_type: str) -> str:
        """returns the orbit type from the SATCAT lookup tables

        Args:
            orbit_type: string code from SATCAT

        Returns:
            Human readable orbit type
        """
        lookup_table = {
            "ORB": "Orbit", "LAN": "Landing",
            "IMP": "Impact", "DOC": "Docked", "R/T": "Roundtrip"
        }
        if orbit_type in lookup_table:
            return lookup_table[orbit_type]
        return ""

    @classmethod
    def COUNTRY(cls, owner: str) -> list[str]:
        """returns the country from internal lookup table

        Args:
            owner: string code from SATCAT
        """
        lookup_table = {
            'Asia Broadcast Satellite': ['Hong Kong'],
            'Saudi Arabia': ['Saudi Arabia'],
            'Kazakhstan': ['Kazakhstan'],
            'Slovenia': ['Slovenia'],
            'European Telecommunications Satellite Organization (EUTELSAT)': ['France'],
            'Nigeria': ['Nigeria'],
            'Belarus': ['Belarus'],
            'Israel': ['Israel'],
            'Finland': ['Finland'],
            'Singapore/Taiwan': ['Singapore', 'Taiwan'],
            'Colombia': ['Colombia'],
            'RascomStar-QAF': ['Côte d’Ivoire'],
            'Japan': ['Japan'],
            'Australia': ['Australia'],
            'Singapore': ['Singapore'],
            'France': ['France'],
            'Philippines': ['Philippines'],
            'Portugal': ['Portugal'],
            'Czech Republic': ['Czech Republic'],
            'Sweden': ['Sweden'],
            'Djibouti': ['Djibouti'],
            'Pakistan': ['Pakistan'],
            'China/Brazil': ['China', 'Brazil'],
            'United States': ['United States'],
            'Bulgaria': ['Bulgaria'],
            'Hungary': ['Hungary'],
            'Luxembourg': ['Luxembourg'],
            'SES': ['Luxembourg'],
            'Arab Satellite Communications Organization': [
                'Saudi Arabia', 'Algeria', 'Bahrain', 'Egypt', 'Iraq', 'Jordan',
                'Kuwait', 'Lebanon', 'Libya', 'Mauritania', 'Morocco', 'Oman',
                'Palestine', 'Qatar', 'Sudan', 'Syria', 'Tunisia', 'United Arab Emirates', 'Yemen'
            ],
            'Lithuania': ['Lithuania'],
            'Malaysia': ['Malaysia'],
            'New Zealand': ['New Zealand'],
            'South Korea': ['South Korea'],
            'International Space Station': [
                'United States', 'Russia', 'Japan', 'Canada', 'France', 'Germany', 'Italy', 'United Kingdom'
            ],
            'Bangladesh': ['Bangladesh'],
            'North Korea': ['North Korea'],
            'Brazil': ['Brazil'],
            'Vietnam': ['Vietnam'],
            'Egypt': ['Egypt'],
            'Turkmenistan/Monaco': ['Turkmenistan', 'Monaco'],
            'Ukraine': ['Ukraine'],
            'Rwanda': ['Rwanda'],
            'Argentina': ['Argentina'],
            'Morocco': ['Morocco'],
            'Turkey': ['Turkey'],
            'Ethiopia': ['Ethiopia'],
            'China': ['China'],
            'Azerbaijan': ['Azerbaijan'],
            'Indonesia': ['Indonesia'],
            'Angola': ['Angola'],
            'United Arab Emirates': ['United Arab Emirates'],
            'Estonia': ['Estonia'],
            'Norway': ['Norway'],
            'Iraq': ['Iraq'],
            'Canada': ['Canada'],
            'Thailand': ['Thailand'],
            'South Africa': ['South Africa'],
            'Taiwan': ['Taiwan'],
            'Denmark': ['Denmark'],
            'Laos': ['Laos'],
            'Netherlands': ['Netherlands'],
            'Peru': ['Peru'],
            'International Mobile Satellite Organization (INMARSAT)': ['United Kingdom'],
            'Iran': ['Iran'],
            'United Kingdom': ['United Kingdom'],
            'Greece': ['Greece'],
            'Zimbabwe': ['Zimbabwe'],
            'Mexico': ['Mexico'],
            'Germany': ['Germany'],
            'International Telecommunications Satellite Organization (INTELSAT)': [
                'United States', 'United Kingdom', 'France', 'Germany', 'Japan', 'Brazil'
            ],
            'Greece/Saudi Arabia': ['Greece', 'Saudi Arabia'],
            'Algeria': ['Algeria'],
            'Commonwealth of Independent States': [
                'Armenia', 'Azerbaijan', 'Belarus', 'Kazakhstan', 'Kyrgyzstan',
                'Moldova', 'Russia', 'Tajikistan', 'Uzbekistan'
            ],
            'India': ['India'],
            'Poland': ['Poland'],
            'Bolivia': ['Bolivia'],
            'France/Italy': ['France', 'Italy'],
            'Switzerland': ['Switzerland'],
            'O3b Networks': ['Luxembourg'],
            'New ICO': ['United Kingdom'],
            'Venezuela': ['Venezuela'],
            'Globalstar': ['United States'],
            'European Organization for the Exploitation of Meteorological Satellites (EUMETSAT)': ['Germany'],
            'ORBCOMM': ['United States'],
            'Ecuador': ['Ecuador'],
            'European Space Agency': [
                'Austria', 'Belgium', 'Czech Republic', 'Denmark', 'Estonia', 'Finland', 'France',
                'Germany', 'Greece', 'Hungary', 'Ireland', 'Italy', 'Luxembourg', 'Netherlands',
                'Norway', 'Poland', 'Portugal', 'Romania', 'Spain', 'Sweden', 'Switzerland',
                'United Kingdom'
            ],
            'Asia Satellite Telecommunications Company (ASIASAT)': ['Hong Kong'],
            'Belgium': ['Belgium'],
            'Italy': ['Italy'],
            'Spain': ['Spain'],
            'Austria': ['Austria'],
            'Chile': ['Chile']
        }
        if owner in lookup_table:
            return lookup_table[owner]
        return [""]


@functools.lru_cache(1)
def init_sats() -> SatelliteSet:
    """load and sats, update data from CelesTrak (NORAD) and add metadata from SATCAT

    Note this function also removes all sats with data older than 14 days as they will give inaccurate propogation data.

    Greater control is available my calling the methods individually

    The result of this function is cached. This shouldn't present an issue for scripting. If this is expected to run continously, please restart it every 24 hours to keep the data fresh

    Returns:
        Sats object containing all objects
    """
    # load all sats and update if old
    norad = NORAD()
    norad.get_source_groups()
    norad.update_sources()
    sats = norad.load_all_sats()

    # load all SATCAT data and update if old
    satcat = SATCAT()
    satcat.update_sources()
    satcat_data = satcat.load()

    # add tags to sats from SATCAT
    sats.add_tags_from_SATCAT(satcat_data)

    # sort sats by name
    sats.sort()

    return sats

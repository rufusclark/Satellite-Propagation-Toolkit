"""downloads, caches and loads data from CelesTrak"""
from typing import List, Dict

import os
from csv import DictReader

from skyfield.api import load

from .models import Sat, Sats


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
        self._sources_by_group = {
            **{group: NORADSource(group, "weather & earth resources", filetype) for group in ["weather", "noaa", "goes", "resource", "sarsat", "dmc", "tdrss", "argos", "planet", "spire"]},
            **{group: NORADSource(group, "communications", filetype) for group in ["geo", "gpz", "intelsat", "iridium", "starlink", "orbcomm", "swarm", "x-comm", "gpz-plus", "ses", "iridium-NEXT", "oneweb", "globalstar", "amateur", "other-comm", "satnogs", "gorizont", "raduga", "molniya"]},
            **{group: NORADSource(group, "navigation", filetype) for group in ["gnss", "gps-ops", "glo-ops", "galileo", "beidou", "sbas", "nnss", "musson"]},
            **{group: NORADSource(group, "scientific", filetype) for group in ["science", "geodetic", "engineering", "education"]},
            **{group: NORADSource(group, "miscellaneous", filetype) for group in ["military", "radar", "cubesat", "other"]},
            **{group: NORADSource(group, "special-interest", filetype) for group in ["stations", "visual", "active", "analyst", "cosmos-1408-debris", "fengyun-1c-debris", "iridium-33-debris", "cosmos-2251-debris"]}}

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

        # update sources
        for source in self.sources:
            filepath = self.path + source.filename
            if not load.exists(filepath) or load.days_old(filepath) >= self._cache_TTL:
                load.download(source.url, filepath)
                print(f"Updated {source.group} NORAD data sources")

    def load_sats(self, sources: List[NORADSource]) -> Sats:
        # load specified sources
        sats = []

        for source in sources:
            filepath = self.path + source.filename
            with load.open(filepath, mode="r") as f:
                data = list(DictReader(f))

                sats.extend([Sat(fields, source.group, source.category)
                            for fields in data])
                print(f"Loaded {source.group} NORAD data sources {' '*40}",
                      end="\r")

        print(f"Loaded all {len(sources)} NORAD data sources {' '*40}")

        return Sats(sats)

    def load_all_sats(self) -> Sats:
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
            "AFETR": "Air Force Eastern Test Range, Florida, USA", "AFWTR": "Air Force Western Test Range, California, USA", "CAS": "Canaries Airspace", "DLS": "Dombarovskiy Launch Site, Russia", "ERAS": "Eastern Range Airspace", "FRGUI": "Europe's Spaceport, Kourou, French Guiana", "HGSTR": "Hammaguira Space Track Range, Algeria", "JJSLA": "Jeju Island Sea Launch Area, Republic of Korea", "JSC": "Jiuquan Space Center, PRC", "KODAK": "Kodiak Launch Complex, Alaska, USA", "KSCUT": "Uchinoura Space Center(Fomerly Kagoshima Space Center—University of Tokyo, Japan)", "KWAJ": "US Army Kwajalein Atoll (USAKA)", "KYMSC": "Kapustin Yar Missile and Space Complex, Russia", "NSC": "Naro Space Complex, Republic of Korea", "PLMSC": "Plesetsk Missile and Space Complex, Russia", "RLLB": "Rocket Lab Launch Base, Mahia Peninsula, New Zealand", "SCSLA": "South China Sea Launch Area, PRC", "SEAL": "Sea Launch Platform (mobile)", "SEMLS": "Semnan Satellite Launch Site, Iran", "SMTS": "Shahrud Missile Test Site, Iran", "SNMLP": "San Marco Launch Platform, Indian Ocean (Kenya)", "SPKII": "Space Port Kii, Japan", "SRILR": "Satish Dhawan Space Centre, India(Formerly Sriharikota Launching Range)", "SUBL": "Submarine Launch Platform (mobile)", "SVOBO": "Svobodnyy Launch Complex, Russia", "TAISC": "Taiyuan Space Center, PRC", "TANSC": "Tanegashima Space Center, Japan", "TYMSC": "Tyuratam Missile and Space Center, Kazakhstan(Also known as Baikonur Cosmodrome)", "UNK": "Unknown", "VOSTO": "Vostochny Cosmodrome, Russia", "WLPIS": "Wallops Island, Virginia, USA", "WOMRA": "Woomera, Australia", "WRAS": "Western Range Airspace", "WSC": "Wenchang Satellite Launch Site, PRC", "XICLF": "Xichang Launch Facility, PRC", "YAVNE": "Yavne Launch Facility, Israel", "YSLA": "Yellow Sea Launch Area, PRC", "YUN": "Yunsong Launch Site(Sohae Satellite Launching Station),Democratic People's Republic of Korea (North Korea)"
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

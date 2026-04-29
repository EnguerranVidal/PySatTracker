class GroundStation:
    def __init__(self, name: str ="", latitude=0.0, longitude=0.0, altitude=0.0, countryLocation: str ="", countryOwnership: str ="", agency: str =""):
        self.name, self.countryLocation, self.countryOwnership, self.agency = name, countryLocation, countryOwnership, agency
        self.longitude, self.latitude, self.altitude = longitude, latitude, altitude

    def toDictionary(self):
        return {"NAME": self.name, "LONGITUDE": self.longitude, "LATITUDE": self.latitude, "ALTITUDE": self.altitude, "COUNTRY_LOCATION": self.countryLocation, "COUNTRY_OWNERSHIP": self.countryOwnership, "AGENCY": self.agency}

    @classmethod
    def fromDictionary(cls, station: dict):
        longitude, latitude, altitude = float(station["LONGITUDE"]), float(station["LATITUDE"]), float(station["ALTITUDE"])
        countryLocation, countryOwnership, agency = station["COUNTRY_LOCATION"], station["COUNTRY_OWNERSHIP"], station["AGENCY"]
        return cls(name=station["NAME"], latitude=latitude, longitude=longitude, altitude=altitude, countryLocation=countryLocation, countryOwnership=countryOwnership, agency=agency)


class GroundStationRegistry:
    def __init__(self):
        self.groundStations = {}
        self.userGroundStations = {}
        self._buildGroundStations()

    def _buildGroundStations(self):
        self.groundStations = {
            "GOLDSTONE": GroundStation(name="Goldstone", longitude=-116.8895, latitude=35.4259, altitude=1002, countryLocation="US", countryOwnership="US", agency="NASA"),
            "CANBERRA": GroundStation(name="Canberra", longitude=148.9813, latitude=-35.4024, altitude=690, countryLocation="AU", countryOwnership="AU", agency="NASA"),
            "MADRID": GroundStation(name="Madrid", longitude=-4.2480, latitude=40.4312, altitude=866, countryLocation="ES", countryOwnership="ES", agency="NASA"),
            "NEW_NORCIA": GroundStation(name="New Norcia", longitude=116.1919, latitude=-31.0481, altitude=250, countryLocation="AU", countryOwnership="AU", agency="ESA"),
            "KIRUNA": GroundStation(name="Kiruna", longitude=20.9643, latitude=67.8570, altitude=400, countryLocation="SE", countryOwnership="SE", agency="ESA"),
            "CEBREROS": GroundStation(name="Cebreros", longitude=-4.3681, latitude=40.4531, altitude=780, countryLocation="ES", countryOwnership="ES", agency="ESA"),
            "MALARGUE": GroundStation(name="Malargüe", longitude=-69.3981, latitude=-35.7761, altitude=1500, countryLocation="AR", countryOwnership="AR", agency="ESA"),
            "KOUROU": GroundStation(name="Kourou", longitude=-52.8047, latitude=5.2511, altitude=10, countryLocation="GF", countryOwnership="FR", agency="ESA"),
            "REDU": GroundStation(name="Redu", longitude=5.1453, latitude=50.0005, altitude=220, countryLocation="BE", countryOwnership="BE", agency="ESA"),
            "SANTA_MARIA": GroundStation(name="Santa Maria", longitude=-25.1357, latitude=36.9973, altitude=200, countryLocation="PT", countryOwnership="PT", agency="ESA"),
            "MASPALOMAS": GroundStation(name="Maspalomas", longitude=-15.6338, latitude=27.7629, altitude=100, countryLocation="ES", countryOwnership="ES", agency="ESA"),
            "USUDA": GroundStation(name="Usuda", longitude=138.3628, latitude=36.1324, altitude=1533, countryLocation="JP", countryOwnership="JP", agency="JAXA"),
            "TROMSO": GroundStation(name="Tromsø", longitude=18.9423, latitude=69.6620, altitude=100, countryLocation="NO", countryOwnership="NO", agency="KSAT"),
            "SVALBARD_SVALSAT": GroundStation(name="Svalbard SvalSat", longitude=15.4078, latitude=78.2298, altitude=450, countryLocation="NO", countryOwnership="NO", agency="KSAT"),
            "TROLLSAT": GroundStation(name="TrollSat", longitude=2.5333, latitude=-72.0167, altitude=1300, countryLocation="AQ", countryOwnership="NO", agency="KSAT"),
            "HARTEBEESTHOEK": GroundStation(name="Hartebeesthoek", longitude=27.685, latitude=-25.887, altitude=1543, countryLocation="ZA", countryOwnership="ZA", agency="KSAT/SANSA"),
            "SINGAPORE_KSAT": GroundStation(name="Singapore KSAT", longitude=103.85, latitude=1.35, altitude=10, countryLocation="SG", countryOwnership="SG", agency="KSAT"),
            "DUBAI_KSAT": GroundStation(name="Dubai KSAT", longitude=55.38, latitude=25.25, altitude=50, countryLocation="AE", countryOwnership="AE", agency="KSAT"),
            "MAURITIUS_KSAT": GroundStation(name="Mauritius KSAT", longitude=57.55, latitude=-20.28, altitude=100, countryLocation="MU", countryOwnership="MU", agency="KSAT"),
            "CLEWISTON": GroundStation(name="Clewiston", longitude=-81.05, latitude=26.75, altitude=5, countryLocation="US", countryOwnership="US", agency="SSC"),
            "SOUTH_POINT_HAWAII": GroundStation(name="South Point Hawaii", longitude=-155.6667, latitude=19.0167, altitude=367, countryLocation="US", countryOwnership="US", agency="SSC"),
            "NORTH_POLE_ALASKA": GroundStation(name="North Pole Alaska", longitude=-147.50, latitude=64.80, altitude=149, countryLocation="US", countryOwnership="US", agency="SSC"),
            "INUVIK_SSC": GroundStation(name="Inuvik SSC", longitude=-133.55, latitude=68.32, altitude=100, countryLocation="CA", countryOwnership="CA", agency="SSC"),
            "PUNTA_ARENAS": GroundStation(name="Punta Arenas", longitude=-70.85, latitude=-52.93, altitude=50, countryLocation="CL", countryOwnership="CL", agency="SSC"),
            "IRBENE": GroundStation(name="Irbene", longitude=21.86, latitude=56.56, altitude=50, countryLocation="LV", countryOwnership="LV", agency="SSC"),
            "WESTERN_AUSTRALIA_SPACE_CENTRE": GroundStation(name="Western Australia Space Centre", longitude=115.35, latitude=-29.05, altitude=50, countryLocation="AU", countryOwnership="AU", agency="SSC"),
            "STOCKHOLM_TELEPORT": GroundStation(name="Stockholm Teleport", longitude=18.08, latitude=59.21, altitude=50, countryLocation="SE", countryOwnership="SE", agency="SSC"),
            "ESRange": GroundStation(name="Esrange", longitude=21.07, latitude=67.88, altitude=450, countryLocation="SE", countryOwnership="SE", agency="SSC"),
            "THULE_PITUFFIK": GroundStation(name="Thule / Pituffik", longitude=-68.6000, latitude=76.51583, altitude=100, countryLocation="GL", countryOwnership="US", agency="US Space Force"),
            "KAENA_POINT": GroundStation(name="Kaena Point Hawaii", longitude=-158.15, latitude=21.57, altitude=100, countryLocation="US", countryOwnership="US", agency="US Space Force"),
            "DIEGO_GARCIA": GroundStation(name="Diego Garcia", longitude=72.40, latitude=-7.31, altitude=10, countryLocation="IO", countryOwnership="US", agency="US Space Force"),
            "GUAM_ANDERSEN": GroundStation(name="Guam Andersen", longitude=144.85, latitude=13.58, altitude=100, countryLocation="GU", countryOwnership="US", agency="US Space Force"),
            "NEW_BOSTON": GroundStation(name="New Boston", longitude=-71.68, latitude=42.95, altitude=200, countryLocation="US", countryOwnership="US", agency="US Space Force"),
            "KASHGAR": GroundStation(name="Kashgar", longitude=76.7122, latitude=38.4234, altitude=1300, countryLocation="CN", countryOwnership="CN", agency="CLTC / CNSA"),
            "JIAMUSI": GroundStation(name="Jiamusi", longitude=130.7704, latitude=46.4934, altitude=100, countryLocation="CN", countryOwnership="CN", agency="CLTC / CNSA"),
            "NEUQUEN_ESPACIO_LEJANO": GroundStation(name="Neuquén Espacio Lejano", longitude=-70.149, latitude=-38.193, altitude=1000, countryLocation="AR", countryOwnership="CN", agency="CLTC / CNSA"),
            "SHADNAGAR": GroundStation(name="Shadnagar", longitude=78.1884, latitude=17.0283, altitude=650, countryLocation="IN", countryOwnership="IN", agency="ISRO"),
        }

    def getStation(self, key: str):
        if key in self.userGroundStations:
            return self.userGroundStations[key]
        return self.groundStations.get(key)

    def getAllStations(self):
        combined = self.groundStations.copy()
        combined.update(self.userGroundStations)
        return combined

    def addUserStation(self, key: str, station: dict):
        station = GroundStation().fromDictionary(station)
        self.userGroundStations[key] = station

    def loadUserStations(self, stations):
        self.userGroundStations.clear()
        for key, value in stations.items():
            self.addUserStation(key, value)

    def exportUserStations(self):
        return {station.toDictionary() for key, station in self.userGroundStations.items()}

    def editUserStation(self, key: str, station: dict):
        if key in self.userGroundStations:
            station = GroundStation().fromDictionary(station)
            self.userGroundStations[key] = station
        else:
            print(f"Station {key} not found.")
            self.addUserStation(key, station)

    def removeUserStation(self, key):
        if key in self.userGroundStations:
            del self.userGroundStations[key]
        elif key in self.groundStations:
            print(f"Warning: Cannot remove built-in station {key}.")
        else:
            print(f"Station {key} not found.")

    def clearUserStations(self):
        self.userGroundStations.clear()

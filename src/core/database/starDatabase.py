import os
import gzip
import shutil
import requests
import pandas as pd


class StarDatabase:
    CATALOGUE_URL = "https://www.astronexus.com/downloads/catalogs/hygdata_v42.csv.gz"

    def __init__(self, dataDir: str = "data", statusCallback=None):
        self.dataDir = dataDir
        self.starDataDir = os.path.join(dataDir, "stars")
        self.statusCallback = statusCallback
        self.catalogArchive = os.path.join(self.starDataDir, "hygdata_v42.csv.gz")
        self.catalogFile = os.path.join(self.starDataDir, "hygdata_v42.csv")
        os.makedirs(self.starDataDir, exist_ok=True)
        self._ensureData()
        if self.statusCallback:
            self.statusCallback("Loading HYG v4.2 catalog...")
        self.starCatalog = self.loadCatalog()

    def _ensureData(self):
        if not os.path.exists(self.catalogFile):
            if self.statusCallback:
                self.statusCallback("Downloading HYG v4.2 catalog...")
            self._downloadFile(self.CATALOGUE_URL, self.catalogArchive)
            if self.statusCallback:
                self.statusCallback("Extracting HYG v4.2 catalog...")
            self._extractArchive(self.catalogArchive, self.catalogFile)

    @staticmethod
    def _downloadFile(url: str, file_path: str):
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to download {url} (status: {response.status_code})")
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    @staticmethod
    def _extractArchive(archivePath: str, outPath: str, deleteAfter: bool = True):
        with gzip.open(archivePath, "rb") as infile:
            with open(outPath, "wb") as outfile:
                shutil.copyfileobj(infile, outfile)
        if deleteAfter:
            try:
                os.remove(archivePath)
            except OSError:
                pass

    def loadCatalog(self):
        df = pd.read_csv(self.catalogFile, dtype={"id": "Int64", "hip": "Int64", "hd": "Int64", "hr": "Int64", "mag": "float64", "dist": "float64", "x": "float64", "y": "float64", "z": "float64",}, low_memory=False,)
        df.columns = [col.strip() for col in df.columns]
        for column in ["proper", "bayer", "flam", "con", "spect"]:
            if column in df.columns:
                df[column] = df[column].astype(str).str.strip().replace("nan", "")
        return df

    def findByCommonName(self, commonStarName: str):
        if not commonStarName:
            return pd.DataFrame()
        commonStarName = commonStarName.lower().strip()
        mask = self.starCatalog["proper"].str.lower().str.strip() == commonStarName
        if not mask.any():
            mask = self.starCatalog["proper"].str.lower().str.contains(commonStarName, na=False)
        result = self.starCatalog[mask].copy()
        if not result.empty:
            result["display_name"] = result["proper"].where(result["proper"] != "", result["bayer"].fillna("") + " " + result["con"].fillna("")).str.strip()
        return result

    def findByBayer(self, bayer: str, constellation: str = None):
        bayer = bayer.lower().strip()
        mask = self.starCatalog["bayer"].str.lower().str.strip() == bayer
        if constellation:
            const = constellation.upper().strip()
            mask &= self.starCatalog["con"].str.upper().str.strip() == const
        return self.starCatalog[mask]

    def getBrightStars(self, maximumMagnitude: float = 6.0):
        return self.starCatalog[self.starCatalog["mag"] <= maximumMagnitude].sort_values("mag")

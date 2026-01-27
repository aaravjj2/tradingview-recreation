from abc import ABC, abstractmethod
from typing import List, Dict, Any, Generator
from datetime import date

class DataSource(ABC):
    @abstractmethod
    def download_month(self, symbol: str, year: int, month: int, output_dir: str) -> str:
        """
        Downloads data for a specific symbol/month.
        Returns the path to the downloaded file.
        Raises exception on failure.
        """
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Returns the expected schema/mappings for normalization.
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique name of the data source.
        """
        pass

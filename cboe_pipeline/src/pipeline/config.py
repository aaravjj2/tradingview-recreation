import yaml
from pathlib import Path
from typing import List, Dict, Any

class Config:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self._cfg = yaml.safe_load(f)
        
    @property
    def start_month(self) -> str:
        return self._cfg['start_month']

    @property
    def end_month(self) -> str:
        return self._cfg['end_month']

    @property
    def underlyings(self) -> List[str]:
        return self._cfg['underlyings']

    @property
    def filters(self) -> Dict[str, Any]:
        return self._cfg['filters']

    @property
    def storage(self) -> Dict[str, str]:
        return self._cfg['storage']

    @property
    def download(self) -> Dict[str, Any]:
        return self._cfg['download']

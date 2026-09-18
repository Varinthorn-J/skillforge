from abc import ABC, abstractmethod
import pandas as pd


class StoragePort(ABC):
    @abstractmethod
    def read_sample(self, file_path: str, num_rows: int = 3) -> str:
        """Read header and a few sample rows as text."""
        pass

    @abstractmethod
    def save_csv(self, file_path: str, df: pd.DataFrame) -> None:
        """Save a DataFrame to a CSV file."""
        pass

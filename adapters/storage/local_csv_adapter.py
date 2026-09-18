import os
import pandas as pd
from port.storage_port import StoragePort


class LocalCSVStorageAdapter(StoragePort):
    def read_sample(self, file_path: str, num_rows: int = 3) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")

        sample_df = pd.read_csv(file_path, nrows=num_rows)
        return sample_df.to_csv(index=False)

    def save_csv(self, file_path: str, df: pd.DataFrame) -> None:
        output_dir = os.path.dirname(file_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        df.to_csv(file_path, index=False)
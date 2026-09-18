from abc import ABC, abstractmethod
import pandas as pd
from domain.models import MappingPlan


class ExecutionEnginePort(ABC):
    @abstractmethod
    def transform(self, input_file_path: str, plan: MappingPlan) -> pd.DataFrame:
        """Apply MappingPlan rules to the full source file using Pandas."""
        pass

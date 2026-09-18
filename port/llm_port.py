from abc import ABC, abstractmethod
from domain.models import MappingPlan


class LLMPort(ABC):
    @abstractmethod
    def generate_mapping_plan(self, sample_input: str, target_schema_spec: str) -> MappingPlan:
        """Receive sample data and target spec, return a validated MappingPlan."""
        pass

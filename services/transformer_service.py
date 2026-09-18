from domain.models import MappingPlan
from port.llm_port import LLMPort
from port.storage_port import StoragePort
from port.execution_port import ExecutionEnginePort


class TransformerService:
    def __init__(
        self,
        llm: LLMPort,
        storage: StoragePort,
        engine: ExecutionEnginePort
    ):
        self.llm = llm
        self.storage = storage
        self.engine = engine

    def run_pipeline(
        self,
        input_file_path: str,
        target_schema_spec: str,
        output_file_path: str
    ) -> MappingPlan:
        print("[1/4] Reading sample source data...")
        sample_csv = self.storage.read_sample(input_file_path, num_rows=3)

        print("[2/4] Generating mapping plan via LLM...")
        plan = self.llm.generate_mapping_plan(sample_csv, target_schema_spec)
        print(f"      Plan generated: {plan.plan_name}")
        for rule in plan.rules:
            print(f"      - {rule.target_column} <- {rule.source_column or 'None'} ({rule.action})")

        print("[3/4] Transforming full dataset...")
        result_df = self.engine.transform(input_file_path, plan)

        print(f"[4/4] Saving output to {output_file_path}...")
        self.storage.save_csv(output_file_path, result_df)

        print("Pipeline finished successfully!")
        return plan

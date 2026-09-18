import pandas as pd
from domain.models import MappingPlan
from port.execution_port import ExecutionEnginePort


class PandasExecutionEngine(ExecutionEnginePort):
    def transform(self, input_file_path: str, plan: MappingPlan) -> pd.DataFrame:
        """Read the source CSV and transform columns according to the MappingPlan."""
        source_df = pd.read_csv(input_file_path)
        target_df = pd.DataFrame()

        for rule in plan.rules:
            target_col = rule.target_column

            if rule.action == "DIRECT":
                if rule.source_column and rule.source_column in source_df.columns:
                    target_df[target_col] = source_df[rule.source_column]
                else:
                    target_df[target_col] = None

            elif rule.action == "DEFAULT":
                target_df[target_col] = rule.default_value

            elif rule.action == "FORMAT_DATE":
                if rule.source_column and rule.source_column in source_df.columns:
                    date_series = pd.to_datetime(source_df[rule.source_column], errors="coerce")
                    fmt = rule.date_format or "%Y-%m-%d"
                    target_df[target_col] = date_series.dt.strftime(fmt)
                else:
                    target_df[target_col] = None

        return target_df

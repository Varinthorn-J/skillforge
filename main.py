from adapters.llm.openai_adapter import LMStudioAdapter
from adapters.storage.local_csv_adapter import LocalCSVStorageAdapter
from adapters.engine.pandas_engine import PandasExecutionEngine
from services.transformer_service import TransformerService


def main():
    llm_adapter = LMStudioAdapter(
        base_url="http://127.0.0.1:1234/v1",
        model_name="qwen2.5-coder-3b-instruct"
    )
    storage_adapter = LocalCSVStorageAdapter()
    engine_adapter = PandasExecutionEngine()

    service = TransformerService(
        llm=llm_adapter,
        storage=storage_adapter,
        engine=engine_adapter
    )

    input_file = "test_data/legacy_pos.csv"
    output_file = "test_data/output_oracle_ap.csv"
    target_schema = """
    Target Schema: Oracle AP Invoice
    Columns required:
    - INVOICE_NUM (Target column for invoice numbers)
    - INVOICE_DATE (Target column for date, must be FORMAT_DATE as %Y-%m-%d)
    - AMOUNT (Target column for invoice amount)
    - SOURCE (Target column, must be DEFAULT with value 'POS_LEGACY')
    """

    print("=== Starting Transformation Pipeline ===")
    service.run_pipeline(
        input_file_path=input_file,
        target_schema_spec=target_schema,
        output_file_path=output_file
    )


if __name__ == "__main__":
    main()

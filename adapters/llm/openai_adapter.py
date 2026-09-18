import json
import re
from openai import OpenAI
from domain.models import MappingPlan
from port.llm_port import LLMPort


class LMStudioAdapter(LLMPort):
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        model_name: str = "qwen2.5-coder-3b-instruct"
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model_name = model_name

    def _extract_json(self, text: str) -> str:
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def generate_mapping_plan(self, sample_input: str, target_schema_spec: str) -> MappingPlan:
        system_prompt = (
            "You are an expert Data Engineer. Output ONLY valid JSON conforming to the schema.\n"
            "STRICT RULES:\n"
            "1. You must map each required target column to the most semantically relevant column in the Source CSV.\n"
            "2. If action is 'DIRECT' or 'FORMAT_DATE', 'source_column' MUST be filled with the exact header name from Source CSV (NEVER null).\n"
            "3. If action is 'DEFAULT', 'source_column' MUST be null and 'default_value' must be provided.\n"
            "4. For date conversions, set action='FORMAT_DATE' and extract the date source column."
        )

        user_prompt = (
            f"=== Source CSV Sample ===\n{sample_input.strip()}\n\n"
            f"=== Target Requirements ===\n{target_schema_spec.strip()}\n\n"
            "Generate the MappingPlan now:"
        )

        json_schema_payload = {
            "type": "json_schema",
            "json_schema": {
                "name": "MappingPlan",
                "strict": "true",
                "schema": MappingPlan.model_json_schema()
            }
        }

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            response_format=json_schema_payload
        )

        content = response.choices[0].message.content.strip()
        cleaned_json = self._extract_json(content)

        try:
            raw_dict = json.loads(cleaned_json)
        except json.JSONDecodeError as err:
            raise ValueError(f"LLM returned invalid JSON:\n{content}") from err

        return MappingPlan.model_validate(raw_dict)
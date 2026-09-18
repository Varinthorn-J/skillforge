from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ColumnRule(BaseModel):
    source_column: Optional[str] = Field(
        default=None,
        description="Exact column name from Source CSV. MUST NOT be null if action is DIRECT or FORMAT_DATE."
    )
    target_column: str = Field(
        ...,
        description="Target column name as specified in schema."
    )
    action: Literal["DIRECT", "DEFAULT", "FORMAT_DATE"] = Field(
        ...,
        description="DIRECT = copy from source, DEFAULT = use static default_value, FORMAT_DATE = parse and format date."
    )
    default_value: Optional[str] = Field(
        default=None,
        description="Static value string when action is DEFAULT. Null otherwise."
    )
    date_format: Optional[str] = Field(
        default=None,
        description="Target date format like '%Y-%m-%d' when action is FORMAT_DATE. Null otherwise."
    )


class MappingPlan(BaseModel):
    plan_name: str = Field(..., description="Short name of this mapping plan")
    rules: List[ColumnRule] = Field(..., description="Mapping rule for each target column")
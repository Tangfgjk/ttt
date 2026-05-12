from pydantic import BaseModel, ConfigDict


class DictionaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class GradeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grade_index: int
    grade_code: str | None = None
    grade_name: str
    edu_stage: str | None = None


class KnowledgeTypeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type_code: str
    source_type_name: str


class CognitiveLevelItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    level_order: int


class CompetencyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    display_order: int

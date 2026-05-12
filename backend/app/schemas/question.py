from pydantic import BaseModel, ConfigDict

from app.schemas.pagination import PageMeta


class SubjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class GradeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grade_index: int
    grade_name: str
    edu_stage: str | None = None


class QuestionTypeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class QuestionContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stem_text: str
    stem_html: str | None = None
    answer_text: str | None = None
    solution_text: str | None = None


class ExternalRefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_question_id: str
    external_type: str | None = None
    is_primary: bool
    data_source_code: str
    data_source_name: str


class QuestionKnowledgePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_point_id: int
    knowledge_point_name: str
    priority: int
    is_core: bool
    is_exam_point: bool
    is_last_exam_point: bool


class QuestionCatalogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    catalog_id: int
    catalog_name: str
    school_code: str | None = None


class QuestionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    difficulty_level: int | None = None
    blank_count: int
    has_subquestions: bool
    source_status: str
    annotation_status: str
    required_annotations: int
    annotation_count: int
    latest_embedding_version: str | None = None
    subject: SubjectSummary
    grade: GradeSummary | None = None
    question_type: QuestionTypeSummary | None = None
    content: QuestionContentOut | None = None


class QuestionListResponse(BaseModel):
    items: list[QuestionListItem]
    meta: PageMeta


class QuestionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    difficulty_level: int | None = None
    blank_count: int
    has_subquestions: bool
    source_status: str
    annotation_status: str
    required_annotations: int
    annotation_count: int
    latest_embedding_version: str | None = None
    subject: SubjectSummary
    grade: GradeSummary | None = None
    question_type: QuestionTypeSummary | None = None
    content: QuestionContentOut | None = None
    external_refs: list[ExternalRefOut]
    knowledge_points: list[QuestionKnowledgePointOut]
    catalogs: list[QuestionCatalogOut]

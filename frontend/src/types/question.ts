export type PageMeta = {
  page: number;
  page_size: number;
  total: number;
};

export type QuestionListItem = {
  id: number;
  difficulty_level: number | null;
  blank_count: number;
  has_subquestions: boolean;
  source_status: string;
  annotation_status: string;
  required_annotations: number;
  annotation_count: number;
  latest_embedding_version: string | null;
  subject: {
    id: number;
    code: string;
    name: string;
  };
  grade?: {
    id: number;
    grade_index: number;
    grade_name: string;
    edu_stage?: string | null;
  } | null;
  question_type?: {
    id: number;
    code: string;
    name: string;
  } | null;
  content?: {
    stem_text: string;
    stem_html?: string | null;
    answer_text?: string | null;
    solution_text?: string | null;
  } | null;
};

export type QuestionListResponse = {
  items: QuestionListItem[];
  meta: PageMeta;
};

export type QuestionListParams = {
  page?: number;
  page_size?: number;
  keyword?: string;
  subject_id?: number;
  grade_id?: number;
  question_type_id?: number;
  annotation_status?: string;
  source_status?: string;
   question_ids?: number[];
};

export type QuestionExternalRef = {
  id: number;
  external_question_id: string;
  external_type?: string | null;
  is_primary: boolean;
  data_source_code: string;
  data_source_name: string;
};

export type QuestionKnowledgePoint = {
  id: number;
  knowledge_point_id: number;
  knowledge_point_name: string;
  priority: number;
  is_core: boolean;
  is_exam_point: boolean;
  is_last_exam_point: boolean;
};

export type QuestionCatalog = {
  id: number;
  catalog_id: number;
  catalog_name: string;
  school_code?: string | null;
};

export type QuestionDetail = QuestionListItem & {
  external_refs: QuestionExternalRef[];
  knowledge_points: QuestionKnowledgePoint[];
  catalogs: QuestionCatalog[];
};

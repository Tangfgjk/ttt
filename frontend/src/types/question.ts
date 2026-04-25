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
  } | null;
  question_type?: {
    id: number;
    code: string;
    name: string;
  } | null;
  content?: {
    stem_text: string;
    answer_text?: string | null;
    solution_text?: string | null;
  } | null;
};

export type QuestionListResponse = {
  items: QuestionListItem[];
  meta: PageMeta;
};

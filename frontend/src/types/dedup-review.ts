export type DuplicateReviewItem = {
  candidate_id: number;
  review_status: string;
  match_type: string;
  confidence_score: string | number;
  comparison_snapshot: Record<string, unknown>;
  source_record: {
    source_record_id: number;
    import_batch_id: number;
    batch_no: string;
    data_source_code: string;
    data_source_name: string;
    source_record_key: string;
    parse_status: string;
    source_stem_text: string;
    source_answer_text?: string | null;
    normalized_question_id?: number | null;
  };
  candidate_question: {
    question_id: number;
    stem_text: string;
    answer_text?: string | null;
  };
  reviewer_name?: string | null;
  reviewed_at?: string | null;
};

export type ReviewDecisionResponse = {
  message: string;
  source_record_id: number;
  normalized_question_id: number;
  parse_status: string;
  review_status: string;
};

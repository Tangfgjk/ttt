export type ImportBatch = {
  id: number;
  data_source_id: number;
  data_source_code: string;
  data_source_name: string;
  batch_no: string;
  file_name: string;
  import_status: string;
  total_records: number;
  success_records: number;
  failed_records: number;
  error_message?: string | null;
  created_at: string;
  finished_at?: string | null;
};

export type ImportBatchSummary = {
  total_records: number;
  raw_imported: number;
  created_new_question: number;
  matched_by_external_id: number;
  matched_by_content_hash: number;
  pending_review: number;
  failed: number;
};

export type ImportSourceRecord = {
  id: number;
  source_record_key: string;
  record_type: string;
  parse_status: string;
  normalized_hash?: string | null;
  normalized_question_id?: number | null;
  duplicate_candidate_count: number;
  error_message?: string | null;
};

export type ImportBatchDetail = {
  batch: ImportBatch;
  summary: ImportBatchSummary;
  records: ImportSourceRecord[];
};

export type ImportRunResponse = {
  batch: ImportBatch;
  summary: ImportBatchSummary;
  imported_records: number;
};

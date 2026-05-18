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
  total_file_count: number;
  uploaded_file_count: number;
  processed_file_count: number;
  expected_records?: number | null;
  error_message?: string | null;
  created_at: string;
  processing_started_at?: string | null;
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
  source_preview?: string | null;
  normalized_question_preview?: string | null;
  raw_payload?: Record<string, unknown> | null;
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

export type ImportSourceRecordListResponse = {
  items: ImportSourceRecord[];
  meta: {
    page: number;
    page_size: number;
    total: number;
  };
};

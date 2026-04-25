export type ImportBatch = {
  id: number;
  data_source_id: number;
  batch_no: string;
  file_name: string;
  import_status: string;
  total_records: number;
  success_records: number;
  failed_records: number;
  error_message?: string | null;
};

from pydantic import BaseModel, ConfigDict, Field


class LocalImportRequest(BaseModel):
    data_source_code: str = Field(description="数据源编码")
    file_path: str = Field(description="本机文件路径")


class ImportBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_source_id: int
    batch_no: str
    file_name: str
    import_status: str
    total_records: int
    success_records: int
    failed_records: int
    error_message: str | None = None


class ImportRunResponse(BaseModel):
    batch: ImportBatchOut
    imported_records: int

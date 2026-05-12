from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Centralized app settings.

    Keep settings small and explicit in the first version. This makes later
    refactors safer because config changes stay visible instead of hiding in
    scattered module-level constants.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="TTT Annotation Backend", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")

    database_url: str = Field(
        default="mysql+pymysql://root:password@127.0.0.1:3306/ttt_annotation",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://127.0.0.1:6379/1",
        alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://127.0.0.1:6379/2",
        alias="CELERY_RESULT_BACKEND",
    )
    import_upload_dir: str = Field(
        default="uploads/imports",
        alias="IMPORT_UPLOAD_DIR",
    )
    embedding_model_path: str = Field(
        default="E:/zhuanli/rePretrain/math_mlm_model",
        alias="EMBEDDING_MODEL_PATH",
    )
    embedding_model_code: str = Field(
        default="math-roberta-mlm-v1",
        alias="EMBEDDING_MODEL_CODE",
    )
    embedding_model_name: str = Field(
        default="Math Roberta MLM",
        alias="EMBEDDING_MODEL_NAME",
    )
    embedding_batch_size: int = Field(default=16, alias="EMBEDDING_BATCH_SIZE")
    visualization_max_points: int = Field(default=50000, alias="VISUALIZATION_MAX_POINTS")
    active_learning_checkpoint_dir: str = Field(
        default="artifacts/active_learning",
        alias="ACTIVE_LEARNING_CHECKPOINT_DIR",
    )
    active_learning_torch_threads: int = Field(
        default=1,
        alias="ACTIVE_LEARNING_TORCH_THREADS",
    )
    active_learning_worker_python: str | None = Field(
        default=None,
        alias="ACTIVE_LEARNING_WORKER_PYTHON",
    )
    active_learning_gpu_worker_python: str | None = Field(
        default=None,
        alias="ACTIVE_LEARNING_GPU_WORKER_PYTHON",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

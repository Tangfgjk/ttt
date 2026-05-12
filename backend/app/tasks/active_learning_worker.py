from __future__ import annotations

import argparse
import os
import sys

from app.core.config import get_settings
from app.services.active_learning_service import (
    _run_coreset_job,
    _run_prediction_job,
    _run_training_job,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an active learning background job.")
    parser.add_argument("job_type", choices=["training", "prediction", "coreset"])
    parser.add_argument("run_id", type=int)
    args = parser.parse_args()

    settings = get_settings()
    thread_count = str(max(1, settings.active_learning_torch_threads))
    os.environ.setdefault("OMP_NUM_THREADS", thread_count)
    os.environ.setdefault("MKL_NUM_THREADS", thread_count)
    os.environ.setdefault("NUMEXPR_NUM_THREADS", thread_count)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", thread_count)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    if args.job_type == "training":
        _run_training_job(args.run_id)
    elif args.job_type == "prediction":
        _run_prediction_job(args.run_id)
    else:
        _run_coreset_job(args.run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())

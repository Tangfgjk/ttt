from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib.util import find_spec

ML_RUNTIME_PACKAGES = ("torch", "transformers")
ML_UNAVAILABLE_MESSAGE = (
    "当前服务器未安装机器学习运行环境，请在本地环境使用模型训练、"
    "CoreSet 选题和低置信度预测功能。"
)


@dataclass(frozen=True)
class MlRuntimeCapability:
    available: bool
    missing_packages: tuple[str, ...]
    message: str


def detect_ml_runtime(
    package_finder: Callable[[str], object | None] | None = None,
) -> MlRuntimeCapability:
    finder = package_finder or find_spec
    missing_packages = tuple(
        package_name
        for package_name in ML_RUNTIME_PACKAGES
        if not _package_available(package_name, finder)
    )
    if missing_packages:
        return MlRuntimeCapability(
            available=False,
            missing_packages=missing_packages,
            message=ML_UNAVAILABLE_MESSAGE,
        )
    return MlRuntimeCapability(
        available=True,
        missing_packages=(),
        message="机器学习运行环境可用。",
    )


def _package_available(
    package_name: str,
    package_finder: Callable[[str], object | None],
) -> bool:
    try:
        return package_finder(package_name) is not None
    except (ImportError, ValueError):
        return False

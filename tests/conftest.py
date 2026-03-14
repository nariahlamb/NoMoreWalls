from __future__ import annotations

from pathlib import Path

import pytest

from quality.config import LocalQualityConfig, load_repo_categories
from quality.models import NodeSnapshot, load_snapshot_jsonl


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def sample_snapshot_path(fixture_dir: Path) -> Path:
    return fixture_dir / "sample_snapshot.jsonl"


@pytest.fixture(scope="session")
def sample_snapshot_records(sample_snapshot_path: Path) -> list[NodeSnapshot]:
    lines = sample_snapshot_path.read_text(encoding="utf-8").splitlines()
    return load_snapshot_jsonl(lines)


@pytest.fixture()
def sample_snapshot_record(sample_snapshot_records: list[NodeSnapshot]) -> NodeSnapshot:
    return sample_snapshot_records[0]


@pytest.fixture(scope="session")
def local_quality_config() -> LocalQualityConfig:
    return LocalQualityConfig.default(repo_categories=load_repo_categories())

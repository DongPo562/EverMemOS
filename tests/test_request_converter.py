"""Tests for request conversion utilities."""

from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

datetime_utils = ModuleType("common_utils.datetime_utils")
datetime_utils.get_now_with_timezone = lambda: None
datetime_utils.from_iso_format = lambda value: value
datetime_utils.to_iso_format = lambda value: value
datetime_utils.get_timezone = lambda: "UTC"
sys.modules.setdefault("common_utils.datetime_utils", datetime_utils)

core_logger = ModuleType("core.observation.logger")
core_logger.get_logger = lambda _name: SimpleNamespace(
    debug=lambda *args, **kwargs: None,
    info=lambda *args, **kwargs: None,
    error=lambda *args, **kwargs: None,
)
sys.modules.setdefault("core.observation.logger", core_logger)

from api_specs.memory_models import MemoryType
from api_specs.request_converter import (
    convert_dict_to_fetch_mem_request,
    convert_dict_to_retrieve_mem_request,
)


def test_convert_fetch_mem_request_strips_memory_type_whitespace():
    request = convert_dict_to_fetch_mem_request(
        {"user_id": "user_1", "memory_type": " episodic_memory "}
    )

    assert request.memory_type == MemoryType.EPISODIC_MEMORY


def test_convert_retrieve_mem_request_strips_memory_type_entries():
    request = convert_dict_to_retrieve_mem_request(
        {"user_id": "user_1", "memory_types": [" event_log ", "foresight"]}
    )

    assert request.memory_types == [MemoryType.EVENT_LOG, MemoryType.FORESIGHT]


def test_convert_retrieve_mem_request_strips_include_metadata_string():
    request = convert_dict_to_retrieve_mem_request(
        {"user_id": "user_1", "include_metadata": " true "}
    )

    assert request.include_metadata is True


def test_convert_retrieve_mem_request_preserves_pending_exclude_group_id():
    request = convert_dict_to_retrieve_mem_request(
        {
            "user_id": "user_1",
            "pending_exclude_group_id": "user_1:chat_001",
        }
    )

    assert request.pending_exclude_group_id == "user_1:chat_001"

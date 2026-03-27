from pathlib import Path
from types import SimpleNamespace, ModuleType
import sys

import pytest

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

datetime_utils = ModuleType("common_utils.datetime_utils")
datetime_utils.to_iso_format = lambda value: value
datetime_utils.from_iso_format = lambda value: value
datetime_utils.get_now_with_timezone = lambda: None
sys.modules.setdefault("common_utils.datetime_utils", datetime_utils)

core_di = ModuleType("core.di")
core_di.service = lambda _name: (lambda cls: cls)
sys.modules.setdefault("core.di", core_di)

core_di_utils = ModuleType("core.di.utils")
core_di_utils.get_bean_by_type = lambda _cls: None
sys.modules.setdefault("core.di.utils", core_di_utils)

core_logger = ModuleType("core.observation.logger")
core_logger.get_logger = lambda _name: SimpleNamespace(
    debug=lambda *args, **kwargs: None,
    info=lambda *args, **kwargs: None,
    error=lambda *args, **kwargs: None,
)
sys.modules.setdefault("core.observation.logger", core_logger)

core_context = ModuleType("core.context.context")
core_context.get_current_app_info = lambda: {}
sys.modules.setdefault("core.context.context", core_context)

core_constants = ModuleType("core.oxm.constants")
core_constants.MAGIC_ALL = "__all__"
sys.modules.setdefault("core.oxm.constants", core_constants)

api_dtos = ModuleType("api_specs.dtos")
api_dtos.MemorizeRequest = object
api_dtos.RawData = object
api_dtos.PendingMessage = lambda **kwargs: SimpleNamespace(**kwargs)
sys.modules.setdefault("api_specs.dtos", api_dtos)

memory_request_log_document = ModuleType(
    "infra_layer.adapters.out.persistence.document.request.memory_request_log"
)
memory_request_log_document.MemoryRequestLog = object
sys.modules.setdefault(
    "infra_layer.adapters.out.persistence.document.request.memory_request_log",
    memory_request_log_document,
)

memory_request_log_repository = ModuleType(
    "infra_layer.adapters.out.persistence.repository.memory_request_log_repository"
)
memory_request_log_repository.MemoryRequestLogRepository = object
sys.modules.setdefault(
    "infra_layer.adapters.out.persistence.repository.memory_request_log_repository",
    memory_request_log_repository,
)

from service.memory_request_log_service import MemoryRequestLogService

for module_name in [
    "common_utils.datetime_utils",
    "core.di",
    "core.di.utils",
    "core.observation.logger",
    "core.context.context",
    "core.oxm.constants",
    "api_specs.dtos",
    "infra_layer.adapters.out.persistence.document.request.memory_request_log",
    "infra_layer.adapters.out.persistence.repository.memory_request_log_repository",
]:
    sys.modules.pop(module_name, None)


@pytest.mark.anyio
async def test_get_cross_group_pending_messages_excludes_current_group_id_and_keeps_message_id():
    service = MemoryRequestLogService()
    service.get_pending_request_logs = _async_return(
        [
            SimpleNamespace(
                id="mongo_same",
                request_id="req_same",
                message_id="msg_same",
                group_id="user_123:chat_001",
                user_id="user_123",
                sender="user_123",
                sender_name="User",
                group_name="Chat 001",
                content="当前会话 pending",
                refer_list=None,
                message_create_time="2026-03-28T10:00:00+08:00",
                created_at=None,
                updated_at=None,
            ),
            SimpleNamespace(
                id="mongo_cross",
                request_id="req_cross",
                message_id="msg_cross",
                group_id="user_123:chat_999",
                user_id="user_123",
                sender="user_123",
                sender_name="User",
                group_name="Chat 999",
                content="跨会话 pending",
                refer_list=None,
                message_create_time="2026-03-28T09:00:00+08:00",
                created_at=None,
                updated_at=None,
            ),
        ]
    )

    result = await service.get_cross_group_pending_messages(
        user_id="user_123",
        exclude_group_id="user_123:chat_001",
        limit=1000,
    )

    assert [item.group_id for item in result] == ["user_123:chat_999"]
    assert [item.message_id for item in result] == ["msg_cross"]
    assert [item.content for item in result] == ["跨会话 pending"]


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner

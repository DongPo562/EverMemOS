#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
GDP - Clear Users Data
================================================================================

【脚本用途】
按用户或按 all 清理当前项目里的聊天/记忆相关数据，并始终保留默认用户 `web_user`。

【启动方式】
    python gdp-clear-users-data.py <user_id|all>

【示例】
    python gdp-clear-users-data.py liuliu03
    python gdp-clear-users-data.py all

【说明】
- 传入具体用户时：删除该用户相关聊天/记忆数据，并从 `web_mvp/data/users.json` 中移除该用户
- 传入 `all` 时：清空所有聊天/记忆数据，并把用户列表重置为只保留默认用户 `web_user`
- 默认用户 `web_user` 作为用户入口会被保留，但 `all` 模式下它的聊天/记忆数据也会被清空
- 单用户模式下，Redis 不做按用户定向删除；原因是当前仓库没有稳定的按用户 Redis key 契约，强删容易误伤其他用户
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import socket
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_USER_ID = "web_user"
DEFAULT_USER_DISPLAY_NAME = "默认用户"
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
EVERMEMOS_SRC_DIR = SCRIPT_DIR / "src"
USERS_FILE_PATH = PROJECT_ROOT / "web_mvp" / "data" / "users.json"
DEFAULT_REDIS_PORT = 6379
FALLBACK_REDIS_PORT = 16379
MONGO_GROUP_COLLECTIONS = [
    "memory_request_logs",
    "conversation_metas",
    "conversation_status",
    "memcells",
    "episodic_memories",
    "event_log_records",
    "foresight_records",
    "user_profiles",
    "group_profiles",
    "group_core_profile_memory",
    "cluster_states",
]
MONGO_DELETE_PLAN = {
    "memory_request_logs": "user_or_group",
    "conversation_metas": "group_only",
    "conversation_status": "group_only",
    "memcells": "group_only",
    "episodic_memories": "user_or_group",
    "event_log_records": "user_or_group",
    "foresight_records": "user_or_group",
    "user_profiles": "user_or_group",
    "global_user_profiles": "user_only",
    "group_profiles": "group_only",
    "group_core_profile_memory": "user_or_group",
    "cluster_states": "group_only",
}
SEARCH_BACKEND_MEMORY_COLLECTIONS = {
    "episodic_memories": "episodic",
    "event_log_records": "event_log",
    "foresight_records": "foresight",
}


def build_group_prefix(user_id: str) -> str:
    return f"{user_id}:chat_"


def belongs_to_user_chat_group(group_id: str | None, user_id: str) -> bool:
    if not group_id:
        return False
    return group_id.startswith(build_group_prefix(user_id))


def normalize_target_user_ids(
    target: str,
    user_state: dict,
    default_user_id: str = DEFAULT_USER_ID,
) -> list[str]:
    normalized = str(target or "").strip()
    if not normalized:
        raise ValueError("target user_id cannot be empty")

    user_ids = [str(item.get("user_id", "")).strip() for item in user_state.get("users", [])]
    existing_user_ids = [item for item in user_ids if item]

    if normalized == "all":
        return [item for item in existing_user_ids if item != default_user_id]

    if normalized == default_user_id:
        raise ValueError(f"default user cannot be deleted: {default_user_id}")

    if normalized not in existing_user_ids:
        raise ValueError(f"user_id not found: {normalized}")

    return [normalized]


def remove_users_from_state(
    user_state: dict,
    target_user_ids: list[str],
    default_user_id: str = DEFAULT_USER_ID,
) -> dict:
    payload = deepcopy(user_state)
    target_set = {item for item in target_user_ids if item}

    remaining_users = [
        dict(item)
        for item in payload.get("users", [])
        if item.get("user_id") not in target_set
    ]

    payload["users"] = remaining_users

    active_user_id = payload.get("active_user_id")
    remaining_user_ids = {item.get("user_id") for item in remaining_users}
    if active_user_id not in remaining_user_ids:
        payload["active_user_id"] = default_user_id

    return payload


def collect_target_group_ids(
    group_ids: list[str | None],
    target_user_ids: list[str],
) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in group_ids:
        if not value:
            continue
        if any(belongs_to_user_chat_group(value, user_id) for user_id in target_user_ids):
            if value not in seen:
                seen.add(value)
                result.append(value)
    return result


def build_milvus_id_delete_expr(doc_ids: list[str]) -> str:
    compact_ids = json.dumps(doc_ids, ensure_ascii=False, separators=(",", ":"))
    return f"id in {compact_ids}"


def chunk_list(values: list[str], chunk_size: int = 200) -> list[list[str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    return [values[index:index + chunk_size] for index in range(0, len(values), chunk_size)]


def build_default_user_record() -> dict[str, Any]:
    return {
        "user_id": DEFAULT_USER_ID,
        "display_name": DEFAULT_USER_DISPLAY_NAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_default_user_state(existing_default_user: dict[str, Any] | None = None) -> dict[str, Any]:
    default_user = dict(existing_default_user) if existing_default_user else build_default_user_record()
    return {
        "active_user_id": default_user["user_id"],
        "users": [default_user],
    }


def ensure_default_user_in_state(payload: dict[str, Any]) -> dict[str, Any]:
    users = [dict(item) for item in payload.get("users", []) if item.get("user_id")]
    default_user = next((item for item in users if item["user_id"] == DEFAULT_USER_ID), None)
    if default_user is None:
        default_user = build_default_user_record()
        users.insert(0, default_user)

    payload = {
        "active_user_id": payload.get("active_user_id") or DEFAULT_USER_ID,
        "users": users,
    }
    if payload["active_user_id"] not in {item["user_id"] for item in users}:
        payload["active_user_id"] = DEFAULT_USER_ID
    return payload


def load_user_state(file_path: Path = USERS_FILE_PATH) -> dict[str, Any]:
    if not file_path.exists():
        payload = build_default_user_state()
        save_user_state(payload, file_path=file_path)
        return payload

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    payload = ensure_default_user_in_state(payload)
    save_user_state(payload, file_path=file_path)
    return payload


def save_user_state(payload: dict[str, Any], file_path: Path = USERS_FILE_PATH) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ensure_runtime_paths() -> None:
    for path in (str(SCRIPT_DIR), str(EVERMEMOS_SRC_DIR), str(PROJECT_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)


def build_redis_port_candidates(
    env_port: str | None,
    default_port: int = DEFAULT_REDIS_PORT,
    fallback_port: int = FALLBACK_REDIS_PORT,
) -> list[int]:
    candidates: list[int] = []
    if env_port:
        try:
            candidates.append(int(env_port))
        except ValueError:
            pass
    for port in (default_port, fallback_port):
        if port not in candidates:
            candidates.append(port)
    return candidates


def resolve_runtime_redis_port(host: str = "127.0.0.1") -> int:
    candidates = build_redis_port_candidates(os.getenv("REDIS_PORT"))
    for port in candidates:
        try:
            with socket.create_connection((host, port), timeout=1):
                return port
        except OSError:
            continue
    return candidates[0]


async def setup_runtime() -> None:
    ensure_runtime_paths()
    from bootstrap import setup_project_context

    current_workdir = Path.cwd()
    os.chdir(SCRIPT_DIR)
    try:
        os.environ["REDIS_PORT"] = str(resolve_runtime_redis_port())
        await setup_project_context()
    finally:
        os.chdir(current_workdir)


def build_group_regexes(target_user_ids: list[str]) -> list[dict[str, Any]]:
    return [
        {"group_id": {"$regex": f"^{re.escape(build_group_prefix(user_id))}"}}
        for user_id in target_user_ids
    ]


def build_delete_query(
    mode: str,
    target_user_ids: list[str],
    target_group_ids: list[str],
) -> dict[str, Any] | None:
    user_clause = {"user_id": {"$in": target_user_ids}} if target_user_ids else None
    group_clause = {"group_id": {"$in": target_group_ids}} if target_group_ids else None

    if mode == "user_only":
        return user_clause
    if mode == "group_only":
        return group_clause
    if mode == "user_or_group":
        clauses = [item for item in (user_clause, group_clause) if item]
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$or": clauses}
    raise ValueError(f"unsupported delete mode: {mode}")


async def discover_target_group_ids(db, target_user_ids: list[str]) -> list[str]:
    regex_filters = build_group_regexes(target_user_ids)
    if not regex_filters:
        return []

    discovered: list[str | None] = []
    for collection_name in MONGO_GROUP_COLLECTIONS:
        collection = db[collection_name]
        try:
            values = await collection.distinct("group_id", {"$or": regex_filters})
        except Exception:
            continue
        discovered.extend(values)

    return collect_target_group_ids(discovered, target_user_ids)


async def collect_memory_doc_ids(
    db,
    target_user_ids: list[str],
    target_group_ids: list[str],
) -> dict[str, list[str]]:
    result = {value: [] for value in SEARCH_BACKEND_MEMORY_COLLECTIONS.values()}
    for collection_name, memory_type in SEARCH_BACKEND_MEMORY_COLLECTIONS.items():
        query = build_delete_query("user_or_group", target_user_ids, target_group_ids)
        if query is None:
            continue
        cursor = db[collection_name].find(query, {"_id": 1})
        docs = await cursor.to_list(length=None)
        result[memory_type] = [str(item["_id"]) for item in docs]
    return result


async def clear_mongodb_for_users(
    db,
    target_user_ids: list[str],
    target_group_ids: list[str],
) -> dict[str, int]:
    summary: dict[str, int] = {}
    for collection_name, mode in MONGO_DELETE_PLAN.items():
        query = build_delete_query(mode, target_user_ids, target_group_ids)
        if query is None:
            summary[collection_name] = 0
            continue
        delete_result = await db[collection_name].delete_many(query)
        summary[collection_name] = delete_result.deleted_count if delete_result else 0
    return summary


async def clear_elasticsearch_for_ids(doc_ids_by_type: dict[str, list[str]]) -> dict[str, dict[str, Any]]:
    ensure_runtime_paths()
    from infra_layer.adapters.out.search.elasticsearch.memory.episodic_memory import (
        EpisodicMemoryDoc,
    )
    from infra_layer.adapters.out.search.elasticsearch.memory.event_log import EventLogDoc
    from infra_layer.adapters.out.search.elasticsearch.memory.foresight import ForesightDoc

    mappings = {
        "episodic": EpisodicMemoryDoc,
        "event_log": EventLogDoc,
        "foresight": ForesightDoc,
    }

    summary: dict[str, dict[str, Any]] = {}
    for memory_type, doc_cls in mappings.items():
        ids = doc_ids_by_type.get(memory_type, [])
        alias = doc_cls.get_index_name()
        if not ids:
            summary[memory_type] = {"alias": alias, "deleted": 0}
            continue

        es_client = doc_cls.get_connection()
        deleted_total = 0
        try:
            exists = await es_client.indices.exists_alias(name=alias)
            if not exists:
                summary[memory_type] = {"alias": alias, "deleted": 0, "skipped": "alias_not_found"}
                continue

            for chunk in chunk_list(ids):
                response = await es_client.delete_by_query(
                    index=alias,
                    query={"ids": {"values": chunk}},
                    refresh=True,
                    conflicts="proceed",
                )
                deleted_total += int(response.get("deleted", 0))

            summary[memory_type] = {"alias": alias, "deleted": deleted_total}
        except Exception as exc:
            summary[memory_type] = {
                "alias": alias,
                "deleted": deleted_total,
                "error": str(exc),
            }
    return summary


def clear_milvus_for_ids(doc_ids_by_type: dict[str, list[str]]) -> dict[str, dict[str, Any]]:
    ensure_runtime_paths()
    from pymilvus import Collection, utility

    from infra_layer.adapters.out.search.milvus.memory.episodic_memory_collection import (
        EpisodicMemoryCollection,
    )
    from infra_layer.adapters.out.search.milvus.memory.event_log_collection import (
        EventLogCollection,
    )
    from infra_layer.adapters.out.search.milvus.memory.foresight_collection import (
        ForesightCollection,
    )

    mappings = {
        "episodic": EpisodicMemoryCollection,
        "event_log": EventLogCollection,
        "foresight": ForesightCollection,
    }

    summary: dict[str, dict[str, Any]] = {}
    for memory_type, collection_cls in mappings.items():
        ids = doc_ids_by_type.get(memory_type, [])
        manager = collection_cls()
        alias = manager.name
        if not ids:
            summary[memory_type] = {"alias": alias, "deleted": 0}
            continue

        deleted_total = 0
        errors: list[str] = []
        try:
            all_collections = utility.list_collections(using=manager.using)
        except Exception as exc:
            summary[memory_type] = {"alias": alias, "deleted": 0, "error": str(exc)}
            continue

        related_names = [
            real_name
            for real_name in all_collections
            if real_name == alias or real_name.startswith(f"{alias}_")
        ]
        if not related_names:
            summary[memory_type] = {"alias": alias, "deleted": 0, "skipped": "collection_not_found"}
            continue

        for real_name in related_names:
            try:
                collection = Collection(name=real_name, using=manager.using)
                collection.load()
                for chunk in chunk_list(ids):
                    result = collection.delete(expr=build_milvus_id_delete_expr(chunk))
                    deleted_total += int(getattr(result, "delete_count", 0) or 0)
                collection.flush()
            except Exception as exc:
                errors.append(f"{real_name}: {exc}")

        summary[memory_type] = {
            "alias": alias,
            "deleted": deleted_total,
            "errors": errors,
        }
    return summary


async def clear_redis_for_users(
    target_user_ids: list[str],
    target_group_ids: list[str],
) -> dict[str, Any]:
    return {
        "deleted": 0,
        "mode": "skipped",
        "reason": "当前项目没有稳定的按用户 Redis key 契约，单用户模式下不做定向 Redis 删除",
        "target_user_ids": list(target_user_ids),
        "target_group_ids": list(target_group_ids),
    }


async def clear_all_mode(user_state: dict[str, Any]) -> dict[str, Any]:
    ensure_runtime_paths()
    from demo.tools.clear_all_data import clear_all_memories

    current_default_user = next(
        (item for item in user_state.get("users", []) if item.get("user_id") == DEFAULT_USER_ID),
        None,
    )
    cleanup_result = await clear_all_memories(verbose=True, rebuild_es=False, drop_milvus=False)
    rewritten_state = build_default_user_state(existing_default_user=current_default_user)
    save_user_state(rewritten_state)

    return {
        "mode": "all",
        "cleared_all_user_data": True,
        "removed_user_ids": [
            item["user_id"]
            for item in user_state.get("users", [])
            if item.get("user_id") != DEFAULT_USER_ID
        ],
        "mongodb": cleanup_result["mongodb"],
        "milvus": cleanup_result["milvus"],
        "elasticsearch": cleanup_result["elasticsearch"],
        "redis": cleanup_result["redis"],
        "users_file": rewritten_state,
    }


async def clear_specific_users_mode(
    target_user_ids: list[str],
    user_state: dict[str, Any],
) -> dict[str, Any]:
    ensure_runtime_paths()
    from core.component.mongodb_client_factory import MongoDBClientFactory
    from core.di import get_bean_by_type

    mongo_factory = get_bean_by_type(MongoDBClientFactory)
    mongo_wrapper = await mongo_factory.get_default_client()
    db = mongo_wrapper.database

    target_group_ids = await discover_target_group_ids(db, target_user_ids)
    doc_ids_by_type = await collect_memory_doc_ids(db, target_user_ids, target_group_ids)
    mongodb_summary = await clear_mongodb_for_users(db, target_user_ids, target_group_ids)
    elasticsearch_summary = await clear_elasticsearch_for_ids(doc_ids_by_type)
    milvus_summary = clear_milvus_for_ids(doc_ids_by_type)
    redis_summary = await clear_redis_for_users(target_user_ids, target_group_ids)

    rewritten_state = ensure_default_user_in_state(
        remove_users_from_state(user_state, target_user_ids, default_user_id=DEFAULT_USER_ID)
    )
    save_user_state(rewritten_state)

    return {
        "mode": "user",
        "removed_user_ids": list(target_user_ids),
        "target_group_ids": target_group_ids,
        "mongodb": mongodb_summary,
        "elasticsearch": elasticsearch_summary,
        "milvus": milvus_summary,
        "redis": redis_summary,
        "users_file": rewritten_state,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按用户或 all 清理当前项目中的聊天/记忆数据，并保留默认用户 web_user。",
    )
    parser.add_argument(
        "target",
        help="要删除的 user_id，或 all",
    )
    return parser


def print_summary(summary: dict[str, Any]) -> None:
    print("=" * 80)
    print("GDP 用户数据清理结果")
    print("=" * 80)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("=" * 80)


async def async_main(target: str) -> int:
    user_state = load_user_state()
    await setup_runtime()

    if target == "all":
        summary = await clear_all_mode(user_state)
        print_summary(summary)
        return 0

    target_user_ids = normalize_target_user_ids(target, user_state)
    summary = await clear_specific_users_mode(target_user_ids, user_state)
    print_summary(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(async_main(args.target))
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

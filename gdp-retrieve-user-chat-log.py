#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
GDP - Retrieve User Chat Log
================================================================================

【脚本用途】
根据用户名导出该用户在 EverMemOS 系统中的所有对话记录和记忆数据。

【数据来源】
1. MongoDB - 主数据库，存储完整数据
   - memcells: 记忆单元
   - episodic_memories: 情景记忆
   - event_log_records: 事件日志
   - foresight_records: 预见记录
   - user_profiles: 用户画像
   - conversation_metas: 会话元数据
   - 等其他集合

2. Elasticsearch - 搜索引擎，存储用于全文检索的数据
   - episodic-memory: 情景记忆索引
   - event-log: 事件日志索引
   - foresight: 预见记录索引

【依赖环境】
- Python 3.10+
- pymongo: MongoDB 驱动
- requests: HTTP 请求库
- 项目使用 uv 管理依赖

【启动方式】
    uv run python gdp-retrieve-user-chat-log.py <用户名>

【示例】
    uv run python gdp-retrieve-user-chat-log.py mimi01

【输出结构】
    users-chat-logs/
    ├── sese_20260317_201148/              # MongoDB 数据
    │   ├── README.md
    │   ├── memcells.md
    │   ├── episodic_memories.md
    │   └── ...
    │
    └── sese_elasticsearch_20260317_201148/    # ES 数据
        ├── README.md
        ├── es_episodic_memory.md
        ├── es_event_log.md
        └── es_foresight.md

【注意事项】
- 需要确保 MongoDB 和 Elasticsearch 服务已启动
- 数据库连接配置在脚本底部的 CONFIG 区域
- 作者: EverMemOS Team
- 创建日期: 2026-03-17
================================================================================
"""

import sys
import os
import json
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import requests
from requests.auth import HTTPBasicAuth

# ================================================================================
# 配置区域 - 根据实际环境修改
# ================================================================================

# MongoDB 配置
MONGO_URI = 'mongodb://admin:memsys123@localhost:27017/memsys?authSource=admin'
MONGO_DATABASE = 'memsys'

# Elasticsearch 配置
ES_URL = 'http://localhost:19200'
ES_AUTH = ('elastic', 'elastic123')

# Elasticsearch 索引名称 (格式: {类型}-memsys-{租户ID})
ES_INDICES = {
    'episodic-memory-memsys-20260221182927288367': 'es_episodic_memory',
    'event-log-memsys-20260221182928498674': 'es_event_log',
    'foresight-memsys-20260221182928108109': 'es_foresight',
}

# 输出目录
OUTPUT_BASE_DIR = 'users-chat-logs'

# MongoDB 搜索字段
SEARCH_FIELDS = ['user_id', 'group_id', 'participants', 'speaker_id', 'user_ids']

# ================================================================================
# 工具函数
# ================================================================================

def serialize(obj):
    """序列化 MongoDB 特殊类型"""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize(v) for v in obj]
    return obj


def write_doc_to_md(f, doc, doc_num):
    """将文档写入 Markdown 文件"""
    f.write(f"## 记录 #{doc_num}\n\n")
    for key, value in doc.items():
        if key == 'vector':
            f.write(f"**{key}**: [{len(value)} 维向量]\n\n")
        elif key == 'search_content':
            f.write(f"**{key}**: [{len(value)} 个分词]\n\n")
        elif isinstance(value, str) and len(value) > 500:
            f.write(f"**{key}**: {value[:500]}...\n\n")
        elif isinstance(value, dict):
            f.write(f"**{key}**:\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```\n\n")
        elif isinstance(value, list) and len(value) > 10:
            f.write(f"**{key}**: {value[:10]}... (共{len(value)}项)\n\n")
        else:
            f.write(f"**{key}**: {value}\n\n")
    f.write("---\n\n")


# ================================================================================
# MongoDB 导出
# ================================================================================

def export_mongodb(username):
    """导出 MongoDB 数据"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(OUTPUT_BASE_DIR, f"{username}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[MongoDB] 正在查询用户: {username}")
    print(f"[MongoDB] 输出目录: {output_dir}")
    print("-" * 50)

    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE]

    search_patterns = [
        {field: {'$regex': username, '$options': 'i'}}
        for field in SEARCH_FIELDS
    ]

    collections = db.list_collection_names()
    total = 0
    stats = []

    for coll_name in sorted(collections):
        coll = db[coll_name]

        or_conditions = []
        for pattern in search_patterns:
            field = list(pattern.keys())[0]
            if coll.count_documents({field: {'$exists': True}}, limit=1) > 0:
                or_conditions.append(pattern)

        if not or_conditions:
            continue

        query = {'$or': or_conditions}
        count = coll.count_documents(query)

        if count > 0:
            docs = list(coll.find(query).sort('created_at', 1))
            docs = [serialize(d) for d in docs]

            output_path = os.path.join(output_dir, f"{coll_name}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {coll_name}\n\n记录数: {len(docs)}\n\n---\n\n")
                for i, doc in enumerate(docs, 1):
                    write_doc_to_md(f, doc, i)

            print(f"  导出 {coll_name}: {len(docs)} 条记录")
            stats.append((coll_name, len(docs)))
            total += len(docs)

    # 创建 README
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"# {username} 用户数据导出 (MongoDB)\n\n")
        f.write(f"用户名: {username}\n")
        f.write(f"导出时间: {datetime.now().isoformat()}\n\n")
        f.write("## 集合统计\n\n| 集合名 | 记录数 |\n|--------|--------|\n")
        for coll_name, count in sorted(stats, key=lambda x: -x[1]):
            f.write(f"| {coll_name} | {count} |\n")
        f.write(f"| **总计** | **{total}** |\n")

    client.close()

    print("-" * 50)
    print(f"[MongoDB] 导出完成! 共 {total} 条记录")

    return output_dir, stats


# ================================================================================
# Elasticsearch 导出
# ================================================================================

def export_elasticsearch(username):
    """导出 Elasticsearch 数据"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(OUTPUT_BASE_DIR, f"{username}_elasticsearch_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[Elasticsearch] 正在查询用户: {username}")
    print(f"[Elasticsearch] 输出目录: {output_dir}")
    print("-" * 50)

    total = 0
    stats = []

    for index_name, output_name in ES_INDICES.items():
        # 滚动查询获取所有数据
        query = {
            'query': {
                'wildcard': {
                    'group_id': f'*{username}*'
                }
            },
            'size': 100
        }

        all_docs = []
        scroll_id = None

        try:
            # 初始查询
            resp = requests.post(
                f'{ES_URL}/{index_name}/_search?scroll=1m',
                auth=HTTPBasicAuth(ES_AUTH[0], ES_AUTH[1]),
                headers={'Content-Type': 'application/json'},
                data=json.dumps(query),
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()

            hits = result.get('hits', {}).get('hits', [])
            scroll_id = result.get('_scroll_id')
            all_docs.extend(hits)

            # 滚动获取剩余数据
            while len(hits) > 0:
                scroll_query = {'scroll': '1m', 'scroll_id': scroll_id}
                resp = requests.post(
                    f'{ES_URL}/_search/scroll',
                    auth=HTTPBasicAuth(ES_AUTH[0], ES_AUTH[1]),
                    headers={'Content-Type': 'application/json'},
                    data=json.dumps(scroll_query),
                    timeout=30
                )
                resp.raise_for_status()
                result = resp.json()
                hits = result.get('hits', {}).get('hits', [])
                all_docs.extend(hits)

            # 清除滚动上下文
            if scroll_id:
                requests.delete(
                    f'{ES_URL}/_search/scroll',
                    auth=HTTPBasicAuth(ES_AUTH[0], ES_AUTH[1]),
                    headers={'Content-Type': 'application/json'},
                    data=json.dumps({'scroll_id': scroll_id}),
                    timeout=10
                )

        except Exception as e:
            print(f"  警告: 索引 {index_name} 查询失败 - {e}")
            continue

        if all_docs:
            # 写入文件
            output_path = os.path.join(output_dir, f"{output_name}.md")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {output_name} (Elasticsearch)\n\n")
                f.write(f"索引: {index_name}\n")
                f.write(f"记录数: {len(all_docs)}\n\n---\n\n")

                for i, hit in enumerate(all_docs, 1):
                    doc = hit.get('_source', {})
                    doc['_id'] = hit.get('_id')
                    doc['_score'] = hit.get('_score')
                    write_doc_to_md(f, doc, i)

            print(f"  导出 {output_name}: {len(all_docs)} 条记录")
            stats.append((output_name, len(all_docs)))
            total += len(all_docs)

    # 创建 README
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"# {username} 用户数据导出 (Elasticsearch)\n\n")
        f.write(f"用户名: {username}\n")
        f.write(f"导出时间: {datetime.now().isoformat()}\n\n")
        f.write("## 索引统计\n\n| 索引 | 记录数 |\n|------|--------|\n")
        for index_name, count in sorted(stats, key=lambda x: -x[1]):
            f.write(f"| {index_name} | {count} |\n")
        f.write(f"| **总计** | **{total}** |\n")

    print("-" * 50)
    print(f"[Elasticsearch] 导出完成! 共 {total} 条记录")

    return output_dir, stats


# ================================================================================
# 主函数
# ================================================================================

def main(username):
    """主函数"""
    if not username:
        print("=" * 60)
        print("错误: 请提供用户名")
        print("=" * 60)
        print("\n用法: uv run python gdp-retrieve-user-chat-log.py <用户名>")
        print("示例: uv run python gdp-retrieve-user-chat-log.py sese")
        print("\n输出目录: users-chat-logs/")
        sys.exit(1)

    print("=" * 60)
    print(f"EverMemOS 用户数据导出工具")
    print(f"用户: {username}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 确保输出目录存在
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

    # 导出 MongoDB 数据
    mongo_dir, mongo_stats = export_mongodb(username)

    # 导出 Elasticsearch 数据
    es_dir, es_stats = export_elasticsearch(username)

    # 汇总
    mongo_total = sum(c for _, c in mongo_stats)
    es_total = sum(c for _, c in es_stats)

    print("\n" + "=" * 60)
    print("导出完成汇总")
    print("=" * 60)
    print(f"MongoDB:      {mongo_total} 条记录 → {mongo_dir}/")
    print(f"Elasticsearch: {es_total} 条记录 → {es_dir}/")
    print(f"总计:         {mongo_total + es_total} 条记录")
    print("=" * 60)


if __name__ == '__main__':
    username = sys.argv[1] if len(sys.argv) > 1 else None
    main(username)
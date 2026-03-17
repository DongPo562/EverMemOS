#!/usr/bin/env python3
"""
GDP - Retrieve User Chat Log
根据用户名导出 MongoDB 中该用户的所有记录

用法: python gdp-retrieve-user-chat-log.py <用户名>
示例: uv run python gdp-retrieve-user-chat-log.py mimi01
"""

import sys
import os
import json
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# 配置
MONGO_URI = 'mongodb://admin:memsys123@localhost:27017/memsys?authSource=admin'
OUTPUT_BASE_DIR = 'users-chat-logs'

# 搜索字段
SEARCH_FIELDS = ['user_id', 'group_id', 'participants', 'speaker_id', 'user_ids']


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


def export_collection(db, coll_name, query, output_dir):
    """导出单个集合"""
    coll = db[coll_name]
    docs = list(coll.find(query).sort('created_at', 1))

    if not docs:
        return 0

    docs = [serialize(d) for d in docs]

    output_path = os.path.join(output_dir, f"{coll_name}.md")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {coll_name}\n\n")
        f.write(f"记录数: {len(docs)}\n\n")
        f.write("---\n\n")

        for i, doc in enumerate(docs, 1):
            f.write(f"## 记录 #{i}\n\n")
            for key, value in doc.items():
                if key == 'vector':
                    f.write(f"**{key}**: [{len(value)} 维向量]\n\n")
                elif isinstance(value, str) and len(value) > 500:
                    f.write(f"**{key}**: {value[:500]}...\n\n")
                elif isinstance(value, dict):
                    f.write(f"**{key}**:\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```\n\n")
                elif isinstance(value, list) and len(value) > 10:
                    f.write(f"**{key}**: {value[:10]}... (共{len(value)}项)\n\n")
                else:
                    f.write(f"**{key}**: {value}\n\n")
            f.write("---\n\n")

    return len(docs)


def main(username):
    """主函数"""
    if not username:
        print("错误: 请提供用户名")
        print("用法: python gdp-retrieve-user-chat-log.py <用户名>")
        sys.exit(1)

    # 创建输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(OUTPUT_BASE_DIR, f"{username}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"正在查询用户: {username}")
    print(f"输出目录: {output_dir}")
    print("-" * 50)

    # 连接数据库
    client = MongoClient(MONGO_URI)
    db = client['memsys']

    # 构建查询条件
    search_patterns = [
        {field: {'$regex': username, '$options': 'i'}}
        for field in SEARCH_FIELDS
    ]

    # 获取所有集合并导出
    collections = db.list_collection_names()
    total = 0
    stats = []

    for coll_name in sorted(collections):
        coll = db[coll_name]

        # 检查字段是否存在
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
            print(f"导出 {coll_name}: {count} 条记录...")
            exported = export_collection(db, coll_name, query, output_dir)
            stats.append((coll_name, exported))
            total += exported

    # 创建 README
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"# {username} 用户数据导出\n\n")
        f.write(f"用户名: {username}\n")
        f.write(f"导出时间: {datetime.now().isoformat()}\n\n")
        f.write("## 集合统计\n\n")
        f.write("| 集合名 | 记录数 |\n")
        f.write("|--------|--------|\n")
        for coll_name, count in sorted(stats, key=lambda x: -x[1]):
            f.write(f"| {coll_name} | {count} |\n")
        f.write(f"| **总计** | **{total}** |\n")

    client.close()

    print("-" * 50)
    print(f"导出完成!")
    print(f"总计: {total} 条记录")
    print(f"输出: {output_dir}/")


if __name__ == '__main__':
    username = sys.argv[1] if len(sys.argv) > 1 else None
    main(username)
# EverMemOS 文档导航指南

> 本导航文档旨在帮助 AI 编程助手快速定位所需文档，了解 EverMemOS 的各项功能与细节。

---

## 一、快速入门

| 文档 | 路径 | 说明 |
|------|------|------|
| **项目概览** | [OVERVIEW.md](OVERVIEW.md) | 系统核心愿景、框架设计、独特优势（连贯叙事、循证感知、动态画像） |
| **架构设计** | [ARCHITECTURE.md](ARCHITECTURE.md) | 六层架构详解、项目结构、技术栈、数据流向 |
| **安装指南** | [installation/SETUP.md](installation/SETUP.md) | 完整安装流程、Docker 部署、环境配置 |
| **快速开始** | [dev_docs/getting_started.md](dev_docs/getting_started.md) | 开发环境搭建、bootstrap 启动方式 |

---

## 二、API 参考

### 核心 Memory API

| 功能 | 文档位置 | 详情 |
|------|----------|------|
| **API 完整规范** | [api_docs/memory_api.md](api_docs/memory_api.md) | 所有端点定义、请求/响应格式、错误码 |
| **存储单条记忆** | `POST /api/v1/memories` | 必填字段：message_id, create_time, sender, content |
| **检索记忆** | `GET /api/v1/memories/search` | 支持 keyword/vector/hybrid/rrf/agentic 五种检索模式 |
| **删除记忆** | `DELETE /api/v1/memories` | 按 user_id 或 group_id 批量删除 |

### 检索策略

| 检索模式 | 文档位置 | 适用场景 |
|----------|----------|----------|
| **轻量检索** | [advanced/RETRIEVAL_STRATEGIES.md](advanced/RETRIEVAL_STRATEGIES.md) | keyword/vector/hybrid/rrf - 低延迟场景 |
| **Agentic 检索** | [dev_docs/agentic_retrieval_guide.md](dev_docs/agentic_retrieval_guide.md) | LLM 引导的多轮检索、复杂查询场景 |
| **策略对比** | [advanced/RETRIEVAL_STRATEGIES.md](advanced/RETRIEVAL_STRATEGIES.md) | 各策略性能指标、延迟对比、选择建议 |

---

## 三、记忆类型系统

| 类型 | 文档位置 | 说明 |
|------|----------|------|
| **MemCell** | [dev_docs/memory_types_guide.md](dev_docs/memory_types_guide.md) | 记忆原子单元，包含 content、embedding、metadata |
| **Episode** | [dev_docs/memory_types_guide.md](dev_docs/memory_types_guide.md) | 分为 GroupEpisode（群体）和 PersonalEpisode（个人） |
| **Foresight** | [dev_docs/memory_types_guide.md](dev_docs/memory_types_guide.md) | 预见性记忆，包含 valid_after/valid_until 时间窗口 |
| **EventLog** | [dev_docs/memory_types_guide.md](dev_docs/memory_types_guide.md) | 事件日志，记录系统行为和用户交互 |
| **Profile** | [dev_docs/memory_types_guide.md](dev_docs/memory_types_guide.md) | 用户画像，存储长期稳定的个人信息 |

---

## 四、使用示例与 Demo

| 文档 | 路径 | 内容 |
|------|------|------|
| **使用示例总览** | [usage/USAGE_EXAMPLES.md](usage/USAGE_EXAMPLES.md) | 所有使用方式：Demo、API、批处理、评估测试 |
| **Demo 演示指南** | [usage/DEMOS.md](usage/DEMOS.md) | Simple Demo（2 步快速体验）、Full Demo（完整流程） |
| **批处理操作** | [usage/BATCH_OPERATIONS.md](usage/BATCH_OPERATIONS.md) | GroupChatFormat 数据格式、run_memorize.py 脚本使用 |

### Demo 快速入口

- **Simple Demo**: `uv run python src/bootstrap.py demo/simple_demo.py`
- **Full Demo**: 先运行 `demo/extract_memory.py` 提取记忆，再运行 `demo/chat_with_memory.py` 交互对话

---

## 五、配置指南

| 配置项 | 文档位置 | 说明 |
|--------|----------|------|
| **环境变量完整配置** | [usage/CONFIGURATION_GUIDE.md](usage/CONFIGURATION_GUIDE.md) | LLM、Vectorize、Rerank、数据库所有配置项详解 |
| **LLM 配置** | 配置指南 §1 | LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, LLM_API_KEY |
| **Vectorize 配置** | 配置指南 §2 | 支持 DeepInfra 和 vLLM 两种提供商 |
| **Rerank 配置** | 配置指南 §3 | 重排序服务配置 |
| **数据库配置** | 配置指南 §4 | MongoDB、Elasticsearch、Milvus、Redis |
| **MongoDB 安装** | [usage/MONGODB_GUIDE.md](usage/MONGODB_GUIDE.md) | 本地安装 MongoDB（非 Docker 方式） |

---

## 六、高级功能

| 功能 | 文档位置 | 说明 |
|------|----------|------|
| **群聊功能** | [advanced/GROUP_CHAT_GUIDE.md](advanced/GROUP_CHAT_GUIDE.md) | group_id 使用、多用户对话、数据格式要求 |
| **元数据控制** | [advanced/METADATA_CONTROL.md](advanced/METADATA_CONTROL.md) | conversation_meta 管理、user_details 配置 |

---

## 七、开发指南

| 主题 | 文档位置 | 内容 |
|------|----------|------|
| **开发环境搭建** | [dev_docs/getting_started.md](dev_docs/getting_started.md) | uv 安装、依赖同步、bootstrap 启动 |
| **开发规范** | [dev_docs/development_standards.md](dev_docs/development_standards.md) | 代码风格、异步标准、时区处理、导入规范 |
| **开发指南** | [dev_docs/development_guide.md](dev_docs/development_guide.md) | 接口定义、Mock 实现、依赖注入最佳实践 |
| **API 使用指南** | [dev_docs/api_usage_guide.md](dev_docs/api_usage_guide.md) | 高级 API 使用模式、集成示例 |

---

## 八、基础设施

| 服务 | 文档位置 | 说明 |
|------|----------|------|
| **Docker 配置** | [installation/DOCKER_SETUP.md](installation/DOCKER_SETUP.md) | docker-compose 服务配置、端口映射、数据卷 |
| **MongoDB** | DOCKER_SETUP.md + MONGODB_GUIDE.md | 主数据库，存储 MemCell、Profile、Episode |
| **Elasticsearch** | DOCKER_SETUP.md | 关键词检索（BM25） |
| **Milvus** | DOCKER_SETUP.md | 向量检索、语义搜索 |
| **Redis** | DOCKER_SETUP.md | 缓存、分布式锁 |

---

## 九、数据格式

| 格式 | 文档位置 | 用途 |
|------|----------|------|
| **GroupChatFormat** | [usage/BATCH_OPERATIONS.md](usage/BATCH_OPERATIONS.md) §数据格式规范 | 批处理操作的标准数据格式 |
| **conversation_meta** | 同上 | 群组元数据：group_id, name, user_details |
| **conversation_list** | 同上 | 消息列表：message_id, create_time, sender, content |

---

## 十、评估与测试

| 文档 | 路径 | 内容 |
|------|------|------|
| **评估框架** | [usage/USAGE_EXAMPLES.md](usage/USAGE_EXAMPLES.md) §3 | LoCoMo、LongMemEval、PersonaMem 数据集评估 |
| **Smoke Test** | 同上 | 快速验证：`--smoke` 参数 |
| **完整评估** | 同上 | 全数据集评估、检查点恢复 |

---

## 十一、竞赛入门包

| 文档 | 路径 | 内容 |
|------|------|------|
| **Starter Kit** | [STARTER_KIT.md](STARTER_KIT.md) | 竞赛入门、API 速查表、示例项目 |

---

## 十二、版本历史

| 文档 | 路径 | 内容 |
|------|------|------|
| **更新日志** | [CHANGELOG.md](CHANGELOG.md) | v1.0.0 ~ v1.2.0 版本更新记录 |

---

## 按功能快速查找

### 我想了解...

| 需求 | 推荐文档 |
|------|----------|
| **系统整体架构** | OVERVIEW.md → ARCHITECTURE.md |
| **如何安装部署** | installation/SETUP.md |
| **API 接口规范** | api_docs/memory_api.md |
| **如何存储记忆** | api_docs/memory_api.md §POST /api/v1/memories |
| **如何检索记忆** | advanced/RETRIEVAL_STRATEGIES.md + api_docs/memory_api.md §GET /api/v1/memories/search |
| **记忆类型有哪些** | dev_docs/memory_types_guide.md |
| **如何处理群聊数据** | advanced/GROUP_CHAT_GUIDE.md + usage/BATCH_OPERATIONS.md |
| **Agentic 检索原理** | dev_docs/agentic_retrieval_guide.md |
| **配置环境变量** | usage/CONFIGURATION_GUIDE.md |
| **运行 Demo 示例** | usage/DEMOS.md |
| **批处理导入数据** | usage/BATCH_OPERATIONS.md |
| **开发规范与标准** | dev_docs/development_standards.md |
| **评估系统性能** | usage/USAGE_EXAMPLES.md §3 |

---

## 关键入口文件

| 文件 | 路径 | 作用 |
|------|------|------|
| **应用入口** | `src/run.py` | 启动 API 服务器 |
| **核心内存管理器** | `src/agentic_layer/memory_manager.py` | MemoryManager 核心实现 |
| **API 控制器** | `src/infra_layer/adapters/input/api/` | REST API 端点定义 |
| **Prompt 模板** | `src/memory_layer/prompts/` | EN/ZH 双语提示词 |

---

> 最后更新：2026-03-19
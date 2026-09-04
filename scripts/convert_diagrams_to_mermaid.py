# -*- coding: utf-8 -*-
"""需求文档 ASCII 图表批量转换为 Mermaid 脚本

用途：将《项目1_智法通_企业级智能法律顾问平台_项目需求文档.md》中的
ASCII 字符画图（box-drawing 图）替换为 Typora 1.2.3 可渲染的 Mermaid 图表。

兼容性设计（Typora 1.2.3 内置 Mermaid 9.x）：
- 仅使用经典语法：graph / stateDiagram-v2
- 节点标签全部使用双引号包裹（避免特殊字符解析问题）
- 使用 classDef / style 着色实现炫酷视觉效果
- 避免 <、>、>= 等符号出现在标签与连线文字中

替换策略：以章节标题为锚点，替换其后第一个无语言标注的代码围栏块。
"""
import io
import sys

DOC = r"e:\临时项目\3_大模型项目_实施\项目1_智法通_企业级智能法律顾问平台\项目1_智法通_企业级智能法律顾问平台_项目需求文档.md"

# ==================== Mermaid 图表定义（锚点 → 图表内容） ====================
# 锚点为章节标题行（不含前后空白）；替换该标题之后第一个 ``` 围栏块
DIAGRAMS = {}

DIAGRAMS["## 3.1 整体架构图"] = '''```mermaid
graph TB
    subgraph L1["接入层 Access Layer"]
        A1["Web前端 Vue3+TS"]
        A2["移动端 H5"]
        A3["开放 API RESTful"]
        A4["企业微信/钉钉集成"]
    end
    NG["Nginx / API Gateway<br/>统一接入 · 认证 · 限流"]
    subgraph L2["服务层 Service Layer"]
        S1["用户服务<br/>认证 / 权限 / 租户"]
        S2["核心业务服务<br/>问答 SSE流 · 合同审查<br/>知识库管理 · 文书起草"]
        S3["多Agent服务<br/>主审 · 复核 · 反方<br/>LangGraph编排 · MCP工具"]
    end
    subgraph L3["编排层 Orchestration Layer"]
        O1["RAG Pipeline<br/>检索→重排→生成"]
        O2["GraphRAG<br/>图谱+向量融合"]
        O3["LangSmith<br/>追踪 / 评估"]
    end
    subgraph L4["基础设施层 Infrastructure Layer"]
        I1["向量数据库<br/>Chroma开发 / Milvus生产"]
        I2["知识图谱<br/>Neo4j 5"]
        I3["关系数据库<br/>MySQL 8.0"]
        I4["LLM服务<br/>Ollama qwen2.5:1.5b"]
        I5["缓存服务<br/>Redis 7"]
        I6["对象存储<br/>本地文件系统"]
    end
    subgraph L5["可观测层 Observability Layer"]
        M1["LangSmith<br/>LLM追踪"]
        M2["Prometheus<br/>系统监控"]
        M3["结构化日志<br/>loguru"]
    end
    L1 --> NG
    NG --> L2
    L2 --> L3
    L3 --> L4
    L4 --> L5
    classDef gateway fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef node fill:#0f3460,color:#ffffff,stroke:#00d2ff
    class NG gateway
    class A1,A2,A3,A4,S1,S2,S3,O1,O2,O3,I1,I2,I3,I4,I5,I6,M1,M2,M3 node
    style L1 fill:#16213e,stroke:#00d2ff,stroke-width:2px
    style L2 fill:#16213e,stroke:#e94560,stroke-width:2px
    style L3 fill:#16213e,stroke:#00d2ff,stroke-width:2px
    style L4 fill:#16213e,stroke:#533483,stroke-width:2px
    style L5 fill:#16213e,stroke:#00d2ff,stroke-width:2px
```'''

DIAGRAMS["### 3.4.1 法律问答数据流（含 GraphRAG 融合）"] = '''```mermaid
graph TD
    U["用户问题"] --> GW["API Gateway<br/>认证 / 限流"]
    GW --> QS["QA Service"]
    QS --> P1["查询重写"]
    QS --> P2["子查询分解"]
    QS --> P3["实体提取"]
    P1 --> RS["RAG Service"]
    P2 --> RS
    P3 --> RS
    QS --> GS["Graph Service"]
    RS --> D1["稠密检索<br/>Chroma ANN"]
    RS --> D2["稀疏检索<br/>BM25"]
    GS --> D3["图谱关联<br/>Neo4j"]
    D1 --> F["结果融合<br/>RRF + Cross-Encoder Rerank<br/>+ 图谱加权"]
    D2 --> F
    D3 --> F
    F --> G["LLM生成回答<br/>SSE 流式"]
    G --> SE["自评估"]
    G --> CV["法条引用校验"]
    SE --> RET["返回用户<br/>+ LangSmith记录"]
    CV --> RET
    classDef startNode fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef parallel fill:#0f3460,color:#ffffff,stroke:#00d2ff
    classDef core fill:#16213e,color:#00d2ff,stroke:#e94560,stroke-width:2px
    classDef leaf fill:#0f3460,color:#ffffff,stroke:#533483
    class U startNode
    class P1,P2,P3,D1,D2,D3 parallel
    class GW,QS,RS,GS,RET core
    class F,G,SE,CV leaf
```'''

DIAGRAMS["### 3.4.2 多 Agent 对抗式合同审查数据流"] = '''```mermaid
graph TD
    UP["合同文件上传"] --> CS["Contract Service"]
    CS --> OSS["本地对象存储<br/>文件持久化"]
    CS --> DP["文档解析<br/>PDF / Word / OCR<br/>纯文本 + 结构化"]
    DP --> WF["LangGraph<br/>多 Agent 工作流"]
    WF --> SC["条款拆分节点"]
    SC --> CLS["条款分类节点"]
    CLS --> PA["主审Agent<br/>完整性检查 · 风险识别<br/>合规检查"]
    CLS --> RA["复核Agent<br/>规则复检 · 合规校验<br/>一致性检查"]
    CLS --> AA["反方Agent<br/>弱势方立场<br/>质疑每条条款<br/>提出反对意见"]
    PA --> SUM["三方意见汇总"]
    RA --> SUM
    AA --> SUM
    SUM --> DB{"对抗辩论节点<br/>主审必须回应反方意见"}
    DB -->|未达成共识| ARB["仲裁节点"]
    ARB --> RSK["风险评分与分级"]
    DB -->|达成共识| RSK
    RSK --> SG["修改建议生成"]
    SG --> RP["审查报告输出<br/>主审 / 复核 / 反方意见 + 推理链"]
    classDef startN fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef agents fill:#0f3460,color:#ffffff,stroke:#e94560,stroke-width:2px
    classDef nodeN fill:#16213e,color:#00d2ff,stroke:#00d2ff,stroke-width:2px
    classDef endN fill:#1a1a2e,color:#00d2ff,stroke:#00d2ff,stroke-width:2px,font-weight:bold
    class UP startN
    class PA,RA,AA agents
    class DB nodeN
    class RP endN
```'''

DIAGRAMS["## 3.5 部署架构设计"] = '''```mermaid
graph TB
    subgraph DC["Docker Compose · Windows 11 + Docker Desktop"]
        ING["Ingress<br/>Nginx 反向代理 + SSE"]
        GW["Gateway<br/>FastAPI"]
        BE["Backend API<br/>FastAPI"]
        FE["Frontend Web<br/>Vue3 + Nginx"]
        LLM["LLM Service<br/>Ollama qwen2.5:1.5b<br/>CPU/GPU 自适应<br/>兼容 OpenAI API"]
        VDB["向量数据库<br/>Chroma 开发 / Milvus 生产"]
        MY["MySQL 8.0"]
        RD["Redis 7-alpine"]
        NEO["Neo4j 5 Community<br/>法律知识图谱"]
    end
    ING --> GW
    ING --> BE
    ING --> FE
    BE --> LLM
    BE --> VDB
    BE --> MY
    BE --> RD
    BE --> NEO
    classDef ingress fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef app fill:#0f3460,color:#ffffff,stroke:#00d2ff,stroke-width:2px
    classDef infra fill:#16213e,color:#00d2ff,stroke:#533483
    class ING ingress
    class GW,BE,FE app
    class LLM,VDB,MY,RD,NEO infra
    style DC fill:#1a1a2e,stroke:#e94560,stroke-width:2px
```'''

DIAGRAMS["#### 反向代理架构"] = '''```mermaid
graph TB
    subgraph NG["Nginx 反向代理层 · 80 端口"]
        S1["静态资源服务<br/>/assets/* · /index.html"]
        S2["API 反向代理<br/>/api/* 转发后端<br/>负载均衡分发"]
        S3["SSE 流式转发<br/>/api/v1/qa/stream"]
        UP["upstream 池<br/>多后端实例"]
    end
    S1 --> UP
    S2 --> UP
    S3 --> UP
    UP --> B1["backend:8000<br/>实例 1"]
    UP --> B2["backend:8000<br/>实例 2"]
    UP --> B3["backend:8000<br/>实例 3"]
    classDef svc fill:#0f3460,color:#ffffff,stroke:#00d2ff,stroke-width:2px
    classDef pool fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef inst fill:#16213e,color:#00d2ff,stroke:#533483
    class S1,S2,S3 svc
    class UP pool
    class B1,B2,B3 inst
    style NG fill:#1a1a2e,stroke:#00d2ff,stroke-width:2px
```'''

DIAGRAMS["## 3.8 安全架构设计"] = '''```mermaid
graph TB
    UR["用户请求"] -->|"WAF 防火墙"| AG["API Gateway<br/>TLS 1.3 终止 · JWT 验证<br/>RBAC 鉴权 · 限流熔断"]
    AG --> DS["数据安全<br/>传输加密 TLS 1.3<br/>存储加密 AES-256-GCM<br/>敏感字段动态脱敏<br/>多租户数据隔离<br/>Ollama 仅监听 127.0.0.1"]
    AG --> AC["审计与合规<br/>操作审计日志（结构化 JSON）<br/>数据访问日志<br/>AI 生成内容标识<br/>定期安全扫描"]
    classDef user fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef gw fill:#16213e,color:#00d2ff,stroke:#e94560,stroke-width:2px
    classDef sec fill:#0f3460,color:#ffffff,stroke:#00d2ff,stroke-width:2px
    class UR user
    class AG gw
    class DS,AC sec
```'''

DIAGRAMS["### 4.3.3 LangGraph 多 Agent 工作流状态图"] = '''```mermaid
stateDiagram-v2
    [*] --> parse_doc
    parse_doc --> split_clauses
    split_clauses --> primary_review
    split_clauses --> review_check
    split_clauses --> adverse_attack
    primary_review --> debate
    review_check --> debate
    adverse_attack --> debate
    debate --> consensus
    consensus --> arbitrate : 未达成共识
    consensus --> risk_score : 达成共识
    arbitrate --> suggestions
    risk_score --> suggestions
    suggestions --> report_generate
    report_generate --> [*]
    note right of parse_doc : 合同解析：提取文本·识别当事方·分类合同类型
    note right of split_clauses : 条款拆分：按条款结构拆分合同文本
    note right of debate : 对抗辩论：主审必须回应反方意见
    note right of risk_score : 风险评分与分级
    note right of report_generate : 报告生成：含推理链 + 三方意见
```'''

DIAGRAMS["**训练数据构建流程**："] = '''```mermaid
graph LR
    A1["法律问答对<br/>10万+对"] -->|"清洗"| B1["质量过滤<br/>去重 / 去噪"] -->|"格式化"| C1["SFT 训练集<br/>instruction / input / output"]
    A2["合同审查标注数据<br/>5万+份"] -->|"专家标注 · 风险标注"| B1
    A2 -->|"格式化"| C1
    A3["法律文书<br/>20万+篇"] -->|"改写"| B2["偏好标注<br/>A/B 对比 · 质量排序"] -->|"格式化"| C2["RLHF 偏好集<br/>prompt / chosen / rejected"]
    classDef src fill:#0f3460,color:#ffffff,stroke:#00d2ff,stroke-width:2px
    classDef proc fill:#16213e,color:#00d2ff,stroke:#533483
    classDef out fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    class A1,A2,A3 src
    class B1,B2 proc
    class C1,C2 out
```'''

DIAGRAMS["## 5.1 法律问答业务流程"] = '''```mermaid
graph TD
    U["用户输入法律问题"] --> C1{"是否包含指代？"}
    C1 -->|"是"| CR["指代消解<br/>利用对话历史"]
    C1 -->|"否"| RW["查询重写<br/>口语化 → 法律术语规范化"]
    CR --> RW
    RW --> C2{"是否复杂问题？"}
    C2 -->|"是"| SQ["子查询分解<br/>拆解为多个子问题"]
    C2 -->|"否"| SR["单次检索"]
    SQ --> PR["三路并行检索"]
    SR --> PR
    PR --> D1["稠密检索<br/>Chroma"]
    PR --> D2["稀疏检索<br/>BM25"]
    PR --> D3["图谱检索<br/>Neo4j"]
    D1 --> RRF["RRF 三路融合"]
    D2 --> RRF
    D3 --> RRF
    RRF --> CE["Cross-Encoder Rerank"]
    CE --> CT["上下文构建<br/>检索结果 + 对话历史 + 系统提示"]
    CT --> LLM["LLM 生成回答<br/>SSE 流式 + 法条引用标注"]
    LLM --> EV{"自评估<br/>置信度检查"}
    EV -->|"置信度低于 0.6<br/>（最多重试 2 次）"| PR
    EV -->|"置信度达标"| RU["返回用户<br/>回答 + 引用来源 + 置信度"]
    RU --> LS["LangSmith 记录<br/>全链路追踪 + 指标采集"]
    classDef userN fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef decision fill:#1a1a2e,color:#00d2ff,stroke:#e94560,stroke-width:2px
    classDef retrieve fill:#0f3460,color:#ffffff,stroke:#00d2ff
    classDef gen fill:#16213e,color:#00d2ff,stroke:#533483,stroke-width:2px
    class U userN
    class C1,C2,EV decision
    class D1,D2,D3,RRF,CE retrieve
    class LLM,RU,LS gen
```'''

DIAGRAMS["## 5.2 多 Agent 对抗式合同审查业务流程"] = '''```mermaid
graph TD
    UP["用户上传合同文件<br/>Word / PDF / TXT / 图片"] --> F1{"文件格式检测"}
    F1 -->|"不支持格式"| ERR["返回错误提示"]
    F1 -->|"支持格式"| DP["文档解析<br/>PDF OCR / Word解析 / 图片OCR → 纯文本"]
    DP --> TR["合同类型识别<br/>买卖 / 租赁 / 劳动 / 服务"]
    TR --> W1["条款拆分 → 条款分类"]
    W1 --> W2["三方并行审查<br/>主审Agent：风险识别 + 合规检查<br/>复核Agent：规则引擎复检<br/>反方Agent：弱势方立场质疑"]
    W2 --> W3{"对抗辩论节点<br/>主审回应反方质疑"}
    W3 -->|"达成共识"| W4["风险评分与分级"]
    W3 -->|"未达成共识"| W3A["仲裁节点"]
    W3A --> W4
    W4 --> W5["修改建议生成"]
    W5 --> W6["审查报告生成<br/>含三方意见 + 推理链"]
    W6 --> RP["审查报告输出<br/>风险清单 + 评分 + 修改建议 + 反方意见"]
    RP --> RL{"风险等级判断"}
    RL -->|"风险评分不低于 80"| HM["标记需人工复核"]
    RL -->|"常规风险"| UC["用户确认 / 修改<br/>接受 / 拒绝 / 修改建议"]
    HM --> UC
    classDef startN fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef decision fill:#1a1a2e,color:#00d2ff,stroke:#e94560,stroke-width:2px
    classDef stepN fill:#0f3460,color:#ffffff,stroke:#00d2ff
    classDef errN fill:#e94560,color:#ffffff,stroke:#1a1a2e,stroke-width:2px
    class UP startN
    class F1,W3,RL decision
    class ERR errN
```

> 工作流支持中断恢复：辩论前可暂停，等待人工确认后继续。'''

DIAGRAMS["## 5.3 知识库更新业务流程（含图谱同步）"] = '''```mermaid
graph TD
    T["法规更新事件触发<br/>API 推送 / 定时爬取"] --> CD["变更检测<br/>与现有知识库比对<br/>识别新增 / 修订 / 废止"]
    CD --> C1{"是否有变更？"}
    C1 -->|"无变更"| END1["结束"]
    C1 -->|"有变更"| ID["增量数据处理<br/>清洗 → 分块 → 元数据标注"]
    ID --> EM["Embedding 计算<br/>BGE-M3 向量化"]
    EM --> DW["双写：向量库 + 知识图谱"]
    DW --> CU["Chroma upsert<br/>向量库"]
    DW --> NM["Neo4j MERGE<br/>知识图谱"]
    CU --> AB["废止法条处理<br/>标记已废止 · 移出默认检索范围<br/>图谱添加 SUPERSEDED_BY 关系"]
    NM --> AB
    AB --> IR["索引刷新<br/>Chroma rebuild + Neo4j 索引重建"]
    IR --> UV["更新验证<br/>抽样检索验证更新正确性"]
    UV --> NU["通知用户<br/>知识库版本更新日志"]
    classDef trigger fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px,font-weight:bold
    classDef decision fill:#1a1a2e,color:#00d2ff,stroke:#e94560,stroke-width:2px
    classDef store fill:#0f3460,color:#ffffff,stroke:#00d2ff,stroke-width:2px
    classDef stepN fill:#16213e,color:#00d2ff,stroke:#533483
    class T trigger
    class C1 decision
    class CU,NM store
```'''

DIAGRAMS["## 5.4 模型微调与迭代流程"] = '''```mermaid
graph TB
    DA["数据采集<br/>用户反馈"] --> DE["数据工程<br/>清洗标注"] --> DQ["数据质量评估"]
    DQ -->|"质量达标"| SFT["SFT 微调<br/>LoRA / QLoRA"]
    DQ -->|"质量不达标"| DA
    SFT --> AV["评估验证<br/>自动 + 人工"]
    AV -->|"发现问题"| DA
    AV --> GR["灰度发布<br/>A/B 测试"]
    GR -->|"指标提升"| GO["全量上线<br/>Ollama 部署"]
    GR -->|"指标未提升"| DA
    GO --> OM["线上监控<br/>LangSmith"]
    OM --> RLHF["RLHF 对齐<br/>DPO 训练"]
    RLHF -->|"数据积累"| DA
    classDef dataN fill:#0f3460,color:#ffffff,stroke:#00d2ff
    classDef trainN fill:#533483,color:#ffffff,stroke:#e94560,stroke-width:2px
    classDef opsN fill:#16213e,color:#00d2ff,stroke:#533483,stroke-width:2px
    class DA,DE,DQ dataN
    class SFT,RLHF,AV trainN
    class GR,GO,OM opsN
```'''


def replace_block_after_anchor(lines: list, anchor: str, new_block: str) -> tuple:
    """替换 anchor 行之后第一个无语言标注的 ``` 围栏块

    Args:
        lines: 文档行列表
        anchor: 章节标题锚点（精确匹配，忽略行尾空白）
        new_block: 新的完整围栏块（含 ```mermaid 起止围栏）

    Returns:
        (是否替换成功, 替换位置信息)
    """
    for i, line in enumerate(lines):
        if line.rstrip() == anchor:
            # 向后查找第一个无语言标注的代码围栏起点
            j = i + 1
            while j < len(lines):
                if lines[j].rstrip() == "```":
                    # 找到围栏起点，寻找闭合围栏
                    k = j + 1
                    while k < len(lines):
                        if lines[k].rstrip() == "```":
                            # 校验旧块内容确实为 ASCII 图（包含制表符画字符）
                            old_content = "".join(lines[j : k + 1])
                            if any(ch in old_content for ch in ("┌", "└", "│", "▼", "◀")):
                                new_lines = new_block.splitlines(keepends=True)
                                lines[j : k + 1] = new_lines
                                return True, f"行 {j + 1}-{k + 1}"
                            return False, f"锚点「{anchor}」后的块不含 ASCII 图，跳过"
                        k += 1
                    return False, f"锚点「{anchor}」后的代码块未闭合"
                # 跳过带语言标注的围栏（如 ```python）与普通文本行
                if lines[j].startswith("```") and lines[j].rstrip() != "```":
                    # 跳过整个带语言围栏块，继续向后找
                    m = j + 1
                    while m < len(lines) and lines[m].rstrip() != "```":
                        m += 1
                    j = m
                j += 1
            return False, f"锚点「{anchor}」后未找到无标注代码块"
    return False, f"未找到锚点「{anchor}」"


def main() -> int:
    with io.open(DOC, "r", encoding="utf-8") as f:
        content = f.read()
    # 统一换行符处理：按行拆分（保留原始行结尾）
    lines = content.splitlines(keepends=True)

    ok_count = 0
    fail_msgs = []
    for anchor, block in DIAGRAMS.items():
        ok, info = replace_block_after_anchor(lines, anchor, block)
        if ok:
            ok_count += 1
            print(f"[OK] {anchor}（{info}）")
        else:
            fail_msgs.append(info)
            print(f"[FAIL] {info}")

    if fail_msgs:
        print("\n失败明细：")
        for m in fail_msgs:
            print(f"  - {m}")
        return 1

    with io.open(DOC, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))
    print(f"\n全部 {ok_count}/{len(DIAGRAMS)} 个图表转换完成，已写回文档")
    return 0


if __name__ == "__main__":
    sys.exit(main())

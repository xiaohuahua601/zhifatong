"""
智法通 - 法律知识图谱服务（Neo4j）

基于项目真实法律数据（法条库 law_articles.json + 案例库 cases.json）
构建 Neo4j 实体关系图谱：

节点类型：
    Law(法律) / Article(法条) / Case(案例) / Concept(法律概念)

关系类型（均为真实数据推导，非写死）：
    Law  -[HAS_ARTICLE]->  Article   法条归属法律（law_articles.json）
    Case -[REFERENCES]->   Article   案例引用法条（cases.json 适用法条字段）
    Article -[MENTIONS]->  Concept   法条提及概念（law_articles.json 关键词）
    Case -[INVOLVES]->     Concept   案例涉及概念（cases.json 关键词）

查询接口返回 ECharts graph 可直接渲染的 {nodes, links} 结构，
节点大小按度数（关联关系数量）动态计算。
Neo4j 不可用时自动降级为内存计算（同样的真实数据，无图谱持久化）。
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# 法律数据文件目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_servers", "data")

# 节点标签 -> ECharts 分类索引（与前端图例顺序一致：法律/法条/案例/概念）
LABEL_CATEGORY = {"Law": 0, "Article": 1, "Case": 2, "Concept": 3}
LABEL_NAME = {"Law": "法律", "Article": "法条", "Case": "案例", "Concept": "概念"}

# 节点基础大小（按类型分级：法律 > 概念/法条 > 案例）
BASE_SIZE = {"Law": 56, "Article": 30, "Case": 26, "Concept": 28}

# Neo4j 异步驱动（懒加载单例）
_driver: Optional[Any] = None
_driver_lock = asyncio.Lock()


# ==================== 数据加载 ====================

def _load_json(filename: str) -> dict:
    """加载法律数据JSON文件"""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_raw_data() -> tuple[list[dict], list[dict]]:
    """加载法条与案例原始数据"""
    articles = _load_json("law_articles.json").get("法律数据", [])
    cases = _load_json("cases.json").get("案例数据", [])
    return articles, cases


# ==================== Neo4j 驱动管理 ====================

async def _get_driver():
    """获取Neo4j异步驱动单例（懒加载）"""
    global _driver
    if _driver is None:
        async with _driver_lock:
            if _driver is None:
                from neo4j import AsyncGraphDatabase
                _driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                    connection_timeout=5,
                    max_connection_pool_size=10,
                )
                await _driver.verify_connectivity()
    return _driver


async def close_driver():
    """关闭Neo4j驱动连接"""
    global _driver
    if _driver is not None:
        try:
            await _driver.close()
        except Exception:
            pass
        _driver = None


# ==================== 图谱构建（写入Neo4j）====================

async def build_graph(retries: int = 3) -> dict:
    """从项目法律数据构建Neo4j知识图谱（MERGE幂等，可重复执行）

    Returns:
        dict: {"laws": n, "articles": n, "cases": n, "concepts": n,
               "relationships": n, "source": "neo4j"}
    """
    articles, cases = _load_raw_data()
    driver = await _get_driver()

    law_names: set[str] = set()
    article_codes: set[str] = set()
    concept_names: set[str] = set()
    case_nos: set[str] = set()
    rel_count = 0

    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        # ---- Law / Article 节点及 HAS_ARTICLE / MENTIONS 关系 ----
        for art in articles:
            law_name = art.get("法律名称", "").strip()
            code = art.get("法条编号", "").strip()
            if not law_name or not code:
                continue
            law_names.add(law_name)
            article_codes.add(code)

            # 章节 -> 概念（真实编章结构推导的关联）
            chapter = art.get("编章", "")

            await session.run(
                """
                MERGE (l:Law {name: $law_name})
                MERGE (a:Article {code: $code})
                SET a.title = $code,
                    a.law = $law_name,
                    a.chapter = $chapter,
                    a.content = $content
                MERGE (l)-[r:HAS_ARTICLE]->(a)
                """,
                law_name=law_name,
                code=code,
                chapter=chapter,
                content=art.get("条款内容", "")[:200],  # 截断避免节点过大
            )
            rel_count += 1

            # 法条关键词 -> 概念（MENTIONS）
            for kw in art.get("关键词", []):
                kw = kw.strip()
                if not kw:
                    continue
                concept_names.add(kw)
                await session.run(
                    """
                    MERGE (a:Article {code: $code})
                    MERGE (c:Concept {name: $kw})
                    MERGE (a)-[r:MENTIONS]->(c)
                    """,
                    code=code,
                    kw=kw,
                )
                rel_count += 1

        # ---- Case 节点及 REFERENCES / INVOLVES 关系 ----
        for case in cases:
            case_no = case.get("案号", "").strip()
            if not case_no:
                continue
            case_nos.add(case_no)

            await session.run(
                """
                MERGE (cs:Case {no: $case_no})
                SET cs.cause = $cause,
                    cs.court = $court,
                    cs.summary = $summary
                """,
                case_no=case_no,
                cause=case.get("案由", ""),
                court=case.get("法院", ""),
                summary=case.get("核心要点", "")[:200],
            )

            # 案例 -> 适用法条（REFERENCES，真实引用关系）
            for ref in case.get("适用法条", []):
                ref = ref.strip()
                if not ref:
                    continue
                article_codes.add(ref)
                await session.run(
                    """
                    MERGE (cs:Case {no: $case_no})
                    MERGE (a:Article {code: $ref})
                    MERGE (cs)-[r:REFERENCES]->(a)
                    """,
                    case_no=case_no,
                    ref=ref,
                )
                rel_count += 1

            # 案例 -> 关键词概念（INVOLVES）
            for kw in case.get("关键词", []):
                kw = kw.strip()
                if not kw:
                    continue
                concept_names.add(kw)
                await session.run(
                    """
                    MERGE (cs:Case {no: $case_no})
                    MERGE (c:Concept {name: $kw})
                    MERGE (cs)-[r:INVOLVES]->(c)
                    """,
                    case_no=case_no,
                    kw=kw,
                )
                rel_count += 1

    stats = {
        "laws": len(law_names),
        "articles": len(article_codes),
        "cases": len(case_nos),
        "concepts": len(concept_names),
        "relationships": rel_count,
        "source": "neo4j",
    }
    logger.info(f"🕸️ Neo4j知识图谱构建完成：{stats}")
    return stats


async def ensure_graph_built() -> bool:
    """确保图谱已构建：Neo4j为空图时自动从本地法律数据构建

    带重试等待（容器编排场景下Neo4j可能仍在启动中）。
    """
    for attempt in range(retries := 3):
        try:
            driver = await _get_driver()
            async with driver.session(database=settings.NEO4J_DATABASE) as session:
                result = await session.run("MATCH (n) RETURN count(n) AS cnt")
                record = await result.single()
                if record and record["cnt"] > 0:
                    return True  # 图谱已存在
            # 空图，构建
            await build_graph()
            return True
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(
                    f"⏳ 等待Neo4j就绪...（第 {attempt + 1}/3 次尝试）：{e}"
                )
                await asyncio.sleep(5)
            else:
                logger.warning(f"⚠️ Neo4j不可用，知识图谱降级为内存模式：{e}")
                await close_driver()
    return False


# ==================== 图谱查询 ====================

async def query_graph(limit: int = 250) -> dict:
    """查询Neo4j知识图谱，返回ECharts graph渲染结构

    优先从Neo4j查询真实实体关系；Neo4j不可用时降级为
    内存计算（同一份真实法律数据，仅无持久化）。

    Args:
        limit: 最大返回节点数（按度数降序取TopN，避免大图卡顿）

    Returns:
        {"nodes": [...], "links": [...], "source": "neo4j"|"local",
         "total_nodes": n, "total_links": n}
    """
    try:
        return await _query_from_neo4j(limit)
    except Exception as e:
        logger.warning(f"⚠️ Neo4j查询失败，知识图谱降级为内存计算：{e}")
        await close_driver()
        return _build_local_graph(limit)


async def _query_from_neo4j(limit: int) -> dict:
    """从Neo4j查询实体与关系"""
    driver = await _get_driver()

    async with driver.session(database=settings.NEO4J_DATABASE) as session:
        # 节点 + 度数（按度数降序取TopN）
        # 使用业务键作为节点标识（Law.name / Article.code / Case.no / Concept.name），
        # 避免 Neo4j 内部 id() 弃用告警，且跨请求保持稳定
        nodes_result = await session.run(
            """
            MATCH (n)
            WHERE any(label IN labels(n) WHERE label IN ['Law', 'Article', 'Case', 'Concept'])
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) AS degree
            ORDER BY degree DESC
            LIMIT $limit
            RETURN labels(n)[0] AS label,
                   coalesce(n.name, n.code, n.no, '') AS key,
                   coalesce(n.chapter, n.cause, '') AS subtitle,
                   degree
            """,
            limit=limit,
        )
        node_records = await nodes_result.data()

        if not node_records:
            raise RuntimeError("Neo4j图谱为空")

        # 度数归一化，动态计算节点大小：base + degree加权
        max_degree = max((r["degree"] for r in node_records), default=1) or 1
        nodes = []
        id_set = set()
        for r in node_records:
            node_id = r["key"]
            label = r["label"]
            if label not in LABEL_CATEGORY or not node_id:
                continue
            id_set.add(node_id)
            # 度数越大节点越大，上限约束避免遮挡
            size = BASE_SIZE.get(label, 26) + (r["degree"] / max_degree) * 24
            nodes.append({
                "id": node_id,
                "name": _shorten_name(node_id, label),
                "category": LABEL_CATEGORY[label],
                "symbolSize": round(min(size, 80), 1),
                "value": f"{LABEL_NAME[label]} · 关联{r['degree']}条" + (f" · {r['subtitle']}" if r["subtitle"] else ""),
                "degree": r["degree"],
            })

        # 关系（仅保留两端节点均在TopN内的边）
        links_result = await session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE any(label IN labels(a) WHERE label IN ['Law', 'Article', 'Case', 'Concept'])
              AND any(label IN labels(b) WHERE label IN ['Law', 'Article', 'Case', 'Concept'])
            RETURN coalesce(a.name, a.code, a.no, '') AS source_key,
                   coalesce(b.name, b.code, b.no, '') AS target_key,
                   type(r) AS rel_type
            """
        )
        link_records = await links_result.data()

        links = []
        for r in link_records:
            source, target = r["source_key"], r["target_key"]
            if source in id_set and target in id_set:
                links.append({
                    "source": source,
                    "target": target,
                    "value": r["rel_type"],
                })

        return {
            "nodes": nodes,
            "links": links,
            "source": "neo4j",
            "total_nodes": len(nodes),
            "total_links": len(links),
        }


def _build_local_graph(limit: int) -> dict:
    """降级方案：内存中从法律数据直接计算图结构（不经Neo4j）"""
    articles, cases = _load_raw_data()

    # 邻接表构建：node_id -> 属性；degree计数
    nodes: dict[str, dict] = {}
    links: list[dict] = []
    link_keys: set[tuple[str, str]] = set()

    def add_node(node_id: str, label: str, name: str, subtitle: str = ""):
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "name": _shorten_name(name, label),
                "category": LABEL_CATEGORY[label],
                "symbolSize": BASE_SIZE.get(label, 26),
                "value": f"{LABEL_NAME[label]} · {subtitle or name}",
                "degree": 0,
                "_label": label,
            }

    def add_link(source: str, target: str, rel: str):
        if (source, target) not in link_keys:
            link_keys.add((source, target))
            links.append({"source": source, "target": target, "value": rel})
            if source in nodes:
                nodes[source]["degree"] += 1
            if target in nodes:
                nodes[target]["degree"] += 1

    for art in articles:
        law_name = art.get("法律名称", "").strip()
        code = art.get("法条编号", "").strip()
        if not law_name or not code:
            continue
        law_id = f"law_{law_name}"
        art_id = f"art_{code}"
        add_node(law_id, "Law", law_name)
        add_node(art_id, "Article", code, art.get("编章", ""))
        add_link(law_id, art_id, "HAS_ARTICLE")
        for kw in art.get("关键词", []):
            kw = kw.strip()
            if kw:
                cid = f"concept_{kw}"
                add_node(cid, "Concept", kw)
                add_link(art_id, cid, "MENTIONS")

    for case in cases:
        case_no = case.get("案号", "").strip()
        if not case_no:
            continue
        case_id = f"case_{case_no}"
        add_node(case_id, "Case", case_no, case.get("案由", ""))
        for ref in case.get("适用法条", []):
            ref = ref.strip()
            if ref:
                art_id = f"art_{ref}"
                add_node(art_id, "Article", ref, "案例引用")
                add_link(case_id, art_id, "REFERENCES")
        for kw in case.get("关键词", []):
            kw = kw.strip()
            if kw:
                cid = f"concept_{kw}"
                add_node(cid, "Concept", kw)
                add_link(case_id, cid, "INVOLVES")

    # 按度数截断到limit
    all_nodes = sorted(nodes.values(), key=lambda n: n["degree"], reverse=True)
    if len(all_nodes) > limit:
        keep_ids = {n["id"] for n in all_nodes[:limit]}
        all_nodes = all_nodes[:limit]
        links = [
            l for l in links if l["source"] in keep_ids and l["target"] in keep_ids
        ]

    # 动态大小：base + degree加权
    max_degree = max((n["degree"] for n in all_nodes), default=1) or 1
    for n in all_nodes:
        size = n["symbolSize"] + (n["degree"] / max_degree) * 24
        n["symbolSize"] = round(min(size, 80), 1)
        n["value"] = f"{n['value']} · 关联{n['degree']}条"
        del n["_label"]

    return {
        "nodes": all_nodes,
        "links": links,
        "source": "local",
        "total_nodes": len(all_nodes),
        "total_links": len(links),
    }


def _shorten_name(name: str, label: str) -> str:
    """节点显示名称缩短处理（长名换行，避免遮挡）"""
    # 法律名去掉"中华人民共和国"前缀
    if label == "Law" and name.startswith("中华人民共和国"):
        name = name[7:]
    # 案号过长截断
    if label == "Case" and len(name) > 14:
        name = name[:13] + "…"
    # 法条编号转为短格式："民法典第585条" -> "第585条"
    if label == "Article":
        for prefix in ("民法典", "劳动合同法", "公司法", "著作权法", "反不正当竞争法"):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
    # 长名称换行
    if len(name) > 6 and "\n" not in name:
        mid = (len(name) + 1) // 2
        name = name[:mid] + "\n" + name[mid:]
    return name

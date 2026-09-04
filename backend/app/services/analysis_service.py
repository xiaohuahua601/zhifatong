"""
智法通 - 分析服务模块

提供热点分析、引用统计、用户聚类和趋势数据的业务逻辑。
"""

import json
from itertools import combinations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from datetime import datetime, timedelta
from typing import Optional
from collections import Counter

from app.models.analysis import QueryLog, CitationStat
from app.models.knowledge import LegalDocument
from app.models.qa import QAFeedback, Message
from app.models.user import User
from app.models.contract import Contract


class AnalysisService:
    """数据分析服务类

    封装热点分析、引用统计、用户聚类等数据分析业务逻辑。
    """

    def __init__(self, db: AsyncSession):
        """初始化分析服务

        Args:
            db: 异步数据库会话
        """
        self.db = db

    async def get_hot_topics(self, days: int = 30, top_n: int = 10) -> list[dict]:
        """获取热点法律问题分析

        统计指定时间段内的热门法律问题分类。

        Args:
            days: 统计天数
            top_n: 返回数量

        Returns:
            热点话题列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # 按分类统计查询次数
        result = await self.db.execute(
            select(
                QueryLog.category,
                func.count(QueryLog.id).label("count"),
            )
            .where(
                QueryLog.created_at >= start_date,
                QueryLog.category.isnot(None),
            )
            .group_by(QueryLog.category)
            .order_by(func.count(QueryLog.id).desc())
            .limit(top_n)
        )

        topics = []
        for row in result.all():
            category, count = row

            # 获取该分类的示例查询
            sample_result = await self.db.execute(
                select(QueryLog.query_text)
                .where(
                    QueryLog.category == category,
                    QueryLog.created_at >= start_date,
                )
                .limit(3)
            )
            sample_queries = [r[0] for r in sample_result.all()]

            # 计算趋势（对比前一个周期）
            prev_start = start_date - timedelta(days=days)
            prev_count_result = await self.db.execute(
                select(func.count(QueryLog.id)).where(
                    QueryLog.category == category,
                    QueryLog.created_at.between(prev_start, start_date),
                )
            )
            prev_count = prev_count_result.scalar() or 0

            if prev_count == 0:
                trend = "up"
            elif count > prev_count * 1.1:
                trend = "up"
            elif count < prev_count * 0.9:
                trend = "down"
            else:
                trend = "stable"

            topics.append({
                "category": category,
                "count": count,
                "trend": trend,
                "sample_queries": sample_queries,
            })

        return topics

    async def get_citation_stats(self, days: int = 30, top_n: int = 20) -> list[dict]:
        """获取法律文档引用统计

        Args:
            days: 统计天数
            top_n: 返回数量

        Returns:
            引用统计列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # 按文档统计引用次数
        result = await self.db.execute(
            select(
                CitationStat.document_id,
                func.sum(CitationStat.citation_count).label("total_citations"),
                func.sum(CitationStat.positive_feedback_count).label("total_positive"),
                func.sum(CitationStat.negative_feedback_count).label("total_negative"),
                func.avg(CitationStat.avg_confidence).label("avg_conf"),
            )
            .where(CitationStat.stat_date >= start_date)
            .group_by(CitationStat.document_id)
            .order_by(func.sum(CitationStat.citation_count).desc())
            .limit(top_n)
        )

        stats = []
        for row in result.all():
            doc_id, citations, positive, negative, avg_conf = row
            total_feedback = (positive or 0) + (negative or 0)
            positive_rate = (positive or 0) / total_feedback * 100 if total_feedback > 0 else 0.0

            # 查询文档标题
            doc = await self.db.get(LegalDocument, doc_id)
            doc_title = doc.title if doc else "未知文档"

            stats.append({
                "document_id": doc_id,
                "document_title": doc_title,
                "citation_count": citations or 0,
                "positive_rate": round(positive_rate, 2),
                "avg_confidence": round(avg_conf, 2) if avg_conf else None,
            })

        return stats

    async def get_user_clusters(self, days: int = 30, n_clusters: int = 5) -> dict:
        """用户聚类分析（K-Means）

        基于用户行为特征进行K-Means聚类，识别不同类型的用户群体。
        参考4.6.3节：从 query_logs 和 contracts 表聚合用户行为特征。

        Args:
            days: 统计天数
            n_clusters: 聚类数量（默认5）

        Returns:
            包含聚类概况、标签、分布和散点数据的字典：
            - cluster_profiles: 各聚类中心特征
            - cluster_labels: 聚类ID到名称的映射
            - cluster_distribution: 各聚类用户数
            - scatter_data: 散点图数据
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # 1. 查询用户特征数据：查询次数、领域多样性、平均会话时长
        query_features = await self.db.execute(
            select(
                QueryLog.user_id,
                func.count(QueryLog.id).label("query_count"),
                func.count(func.distinct(QueryLog.category)).label("domain_diversity"),
                func.avg(QueryLog.latency_ms).label("avg_latency"),
            )
            .where(
                QueryLog.created_at >= start_date,
                QueryLog.user_id.isnot(None),
            )
            .group_by(QueryLog.user_id)
        )

        # 合同审查次数
        contract_features = await self.db.execute(
            select(
                Contract.user_id,
                func.count(Contract.id).label("contract_count"),
            )
            .where(Contract.created_at >= start_date)
            .group_by(Contract.user_id)
        )

        # 构建用户特征字典
        user_features: dict[int, dict] = {}
        for row in query_features.all():
            user_id, query_count, domain_diversity, avg_latency = row
            user_features[user_id] = {
                "query_count": query_count or 0,
                "contract_review_count": 0,
                "legal_domain_diversity": domain_diversity or 0,
                "avg_session_duration": float(avg_latency or 0),
            }

        for row in contract_features.all():
            user_id, contract_count = row
            if user_id in user_features:
                user_features[user_id]["contract_review_count"] = contract_count or 0
            else:
                user_features[user_id] = {
                    "query_count": 0,
                    "contract_review_count": contract_count or 0,
                    "legal_domain_diversity": 0,
                    "avg_session_duration": 0.0,
                }

        # 空数据兜底
        if not user_features:
            return {
                "cluster_profiles": [],
                "cluster_labels": {
                    0: "高频法务用户",
                    1: "合同审查为主用户",
                    2: "法律咨询入门用户",
                    3: "合规监测企业用户",
                    4: "低活跃潜在用户",
                },
                "cluster_distribution": {},
                "scatter_data": [],
            }

        # 2. 准备特征矩阵
        user_ids = list(user_features.keys())
        feature_names = [
            "query_count",
            "contract_review_count",
            "legal_domain_diversity",
            "avg_session_duration",
        ]
        features_matrix = [
            [user_features[uid][fn] for fn in feature_names]
            for uid in user_ids
        ]

        # 3. 特征标准化与K-Means聚类
        actual_n_clusters = min(n_clusters, len(user_ids))

        try:
            from sklearn.preprocessing import StandardScaler
            from sklearn.cluster import KMeans
            from sklearn.decomposition import PCA

            # 特征标准化（StandardScaler）
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features_matrix)

            # K-Means聚类
            kmeans = KMeans(n_clusters=actual_n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features_scaled)
            cluster_centers = kmeans.cluster_centers_

            # PCA降维用于可视化散点图
            if len(feature_names) > 2 and actual_n_clusters > 1:
                pca = PCA(n_components=2)
                coords_2d = pca.fit_transform(features_scaled)
            else:
                coords_2d = features_scaled[:, :2] if features_scaled.shape[1] >= 2 else features_scaled
        except ImportError:
            # sklearn不可用，使用简单的z-score标准化
            n = len(features_matrix)
            col_sums = [0.0] * len(feature_names)
            col_sq_sums = [0.0] * len(feature_names)
            for row in features_matrix:
                for i, val in enumerate(row):
                    col_sums[i] += val
                    col_sq_sums[i] += val * val

            means = [col_sums[i] / n for i in range(len(feature_names))]
            stds = [
                (col_sq_sums[i] / n - means[i] ** 2) ** 0.5
                for i in range(len(feature_names))
            ]

            features_scaled = []
            for row in features_matrix:
                scaled_row = [
                    (row[i] - means[i]) / stds[i] if stds[i] > 0 else 0.0
                    for i in range(len(feature_names))
                ]
                features_scaled.append(scaled_row)

            # 基于规则的聚类：按查询频率分组
            sorted_indices = sorted(
                range(len(user_ids)),
                key=lambda i: features_matrix[i][0],
                reverse=True,
            )
            cluster_labels = [0] * len(user_ids)
            group_size = max(1, len(user_ids) // actual_n_clusters)
            for rank, idx in enumerate(sorted_indices):
                cluster_labels[idx] = min(rank // group_size, actual_n_clusters - 1)

            # 使用前两个标准化特征作为散点坐标
            coords_2d = [[row[0], row[1]] for row in features_scaled]

            # 计算聚类中心
            cluster_centers = []
            for c in range(actual_n_clusters):
                members = [
                    features_scaled[i]
                    for i in range(len(features_scaled))
                    if cluster_labels[i] == c
                ]
                if members:
                    center = [sum(col) / len(members) for col in zip(*members)]
                else:
                    center = [0.0] * len(feature_names)
                cluster_centers.append(center)

        # 4. 聚类标签映射
        cluster_label_names = {
            0: "高频法务用户",
            1: "合同审查为主用户",
            2: "法律咨询入门用户",
            3: "合规监测企业用户",
            4: "低活跃潜在用户",
        }

        # 5. 构建聚类概况与分布
        cluster_profiles = []
        cluster_distribution: dict[int, int] = {}
        for c in range(actual_n_clusters):
            member_indices = [
                i for i in range(len(user_ids)) if cluster_labels[i] == c
            ]
            member_count = len(member_indices)
            cluster_distribution[c] = member_count

            # 计算该聚类的平均特征（原始值）
            avg_features = {}
            for fi, fn in enumerate(feature_names):
                if member_indices:
                    vals = [features_matrix[i][fi] for i in member_indices]
                    avg_features[fn] = round(sum(vals) / len(vals), 2)
                else:
                    avg_features[fn] = 0.0

            cluster_profiles.append({
                "cluster_id": c,
                "cluster_name": cluster_label_names.get(c, f"用户群体{c + 1}"),
                "user_count": member_count,
                "avg_features": avg_features,
                "center": (
                    [round(float(v), 4) for v in cluster_centers[c]]
                    if c < len(cluster_centers) else []
                ),
            })

        # 6. 构建散点数据
        scatter_data = []
        for i, uid in enumerate(user_ids):
            c = int(cluster_labels[i])
            scatter_data.append({
                "user_id": uid,
                "cluster_id": c,
                "cluster_name": cluster_label_names.get(c, f"用户群体{c + 1}"),
                "x": round(float(coords_2d[i][0]), 4),
                "y": round(float(coords_2d[i][1]), 4),
                "query_count": user_features[uid]["query_count"],
                "contract_count": user_features[uid]["contract_review_count"],
            })

        return {
            "cluster_profiles": cluster_profiles,
            "cluster_labels": cluster_label_names,
            "cluster_distribution": cluster_distribution,
            "scatter_data": scatter_data,
        }

    async def get_co_citation_network(
        self,
        days: int = 30,
        top_n: int = 50,
        min_co_occurrence: int = 2,
    ) -> dict:
        """法条共引网络分析

        分析法律文档在同一AI回答中被共同引用的关系，构建知识图谱。
        参考4.6.2节：基于消息引用字段解析共引关系。

        Args:
            days: 统计天数
            top_n: 返回的节点数量上限
            min_co_occurrence: 最小共引次数阈值

        Returns:
            包含节点和边的字典，用于知识图谱可视化：
            - nodes: 文档节点列表
            - edges: 共引关系边列表
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # 查询包含引用的AI回答消息
        result = await self.db.execute(
            select(Message.citations, Message.id)
            .where(
                Message.created_at >= start_date,
                Message.citations.isnot(None),
                Message.role == "assistant",
            )
            .order_by(Message.created_at.desc())
            .limit(1000)
        )

        # 解析引用，构建共引关系
        doc_citation_count: Counter = Counter()
        co_occurrence: Counter = Counter()

        for row in result.all():
            citations_json, _ = row
            if not citations_json:
                continue
            try:
                citations = json.loads(citations_json)
            except (json.JSONDecodeError, TypeError):
                continue

            # 提取文档ID集合
            doc_ids: set = set()
            if isinstance(citations, list):
                for cite in citations:
                    if isinstance(cite, dict):
                        doc_id = cite.get("document_id") or cite.get("doc_id") or cite.get("id")
                        if isinstance(doc_id, int):
                            doc_ids.add(doc_id)
                    elif isinstance(cite, int):
                        doc_ids.add(cite)
            elif isinstance(citations, dict):
                doc_id = citations.get("document_id") or citations.get("doc_id") or citations.get("id")
                if isinstance(doc_id, int):
                    doc_ids.add(doc_id)

            # 统计单文档引用次数
            for doc_id in doc_ids:
                doc_citation_count[doc_id] += 1

            # 统计共引次数（文档两两组合）
            for doc_a, doc_b in combinations(sorted(doc_ids), 2):
                co_occurrence[(doc_a, doc_b)] += 1

        if not doc_citation_count:
            return {"nodes": [], "edges": []}

        # 取引用次数最多的top_n个文档
        top_docs = {doc_id for doc_id, _ in doc_citation_count.most_common(top_n)}

        # 查询文档标题与类型
        doc_result = await self.db.execute(
            select(LegalDocument.id, LegalDocument.title, LegalDocument.doc_type)
            .where(LegalDocument.id.in_(top_docs))
        )
        doc_info: dict[int, dict] = {}
        for row in doc_result.all():
            doc_id, title, doc_type = row
            doc_info[doc_id] = {"title": title, "doc_type": doc_type}

        # 构建节点
        nodes = []
        for doc_id in top_docs:
            info = doc_info.get(doc_id, {"title": f"文档{doc_id}", "doc_type": None})
            count = doc_citation_count[doc_id]
            nodes.append({
                "id": doc_id,
                "label": info["title"],
                "doc_type": info["doc_type"],
                "citation_count": count,
                "size": min(50, 10 + count * 2),
            })

        # 构建边（过滤共引次数 >= min_co_occurrence 且两端均在top_docs中）
        edges = []
        for (doc_a, doc_b), weight in co_occurrence.most_common():
            if doc_a not in top_docs or doc_b not in top_docs:
                continue
            if weight < min_co_occurrence:
                continue
            edges.append({
                "source": doc_a,
                "target": doc_b,
                "weight": weight,
                "width": min(10, 1 + weight),
            })

        return {
            "nodes": nodes,
            "edges": edges,
        }

    async def get_trend_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day",
    ) -> list[dict]:
        """获取查询趋势数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            granularity: 粒度（day/week/month）

        Returns:
            趋势数据列表
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # 按日期统计查询数据
        result = await self.db.execute(
            select(QueryLog).where(
                QueryLog.created_at.between(start_date, end_date)
            ).order_by(QueryLog.created_at)
        )
        logs = result.scalars().all()

        # 按日期聚合
        date_data = {}
        for log in logs:
            if granularity == "week":
                # 按周聚合
                key = (log.created_at - timedelta(days=log.created_at.weekday())).strftime("%Y-%m-%d")
            elif granularity == "month":
                key = log.created_at.strftime("%Y-%m")
            else:
                key = log.created_at.strftime("%Y-%m-%d")

            if key not in date_data:
                date_data[key] = {
                    "query_count": 0,
                    "positive_count": 0,
                    "total_feedback": 0,
                    "confidence_sum": 0.0,
                    "confidence_count": 0,
                }

            date_data[key]["query_count"] += 1
            if log.feedback_score == 1:
                date_data[key]["positive_count"] += 1
            if log.feedback_score != 0:
                date_data[key]["total_feedback"] += 1
            if log.confidence:
                date_data[key]["confidence_sum"] += log.confidence
                date_data[key]["confidence_count"] += 1

        # 格式化输出
        trends = []
        for date_key in sorted(date_data.keys()):
            data = date_data[date_key]
            positive_rate = (
                data["positive_count"] / data["total_feedback"] * 100
                if data["total_feedback"] > 0
                else 0.0
            )
            avg_confidence = (
                data["confidence_sum"] / data["confidence_count"]
                if data["confidence_count"] > 0
                else 0.0
            )

            trends.append({
                "date": date_key,
                "query_count": data["query_count"],
                "positive_feedback_rate": round(positive_rate, 2),
                "avg_confidence": round(avg_confidence, 2),
            })

        return trends

    async def get_overview(self) -> dict:
        """获取数据分析概览

        Returns:
            包含关键指标的字典
        """
        # 总查询数
        total_queries_result = await self.db.execute(
            select(func.count(QueryLog.id))
        )
        total_queries = total_queries_result.scalar() or 0

        # 今日查询数
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_queries_result = await self.db.execute(
            select(func.count(QueryLog.id)).where(QueryLog.created_at >= today_start)
        )
        today_queries = today_queries_result.scalar() or 0

        # 平均置信度
        avg_conf_result = await self.db.execute(
            select(func.avg(QueryLog.confidence)).where(QueryLog.confidence.isnot(None))
        )
        avg_confidence = avg_conf_result.scalar() or 0.0

        # 正面反馈率
        positive_result = await self.db.execute(
            select(func.count(QueryLog.id)).where(QueryLog.feedback_score == 1)
        )
        total_feedback_result = await self.db.execute(
            select(func.count(QueryLog.id)).where(QueryLog.feedback_score != 0)
        )
        positive_count = positive_result.scalar() or 0
        total_feedback = total_feedback_result.scalar() or 0
        positive_rate = (positive_count / total_feedback * 100) if total_feedback > 0 else 0.0

        # 热门分类
        top_categories_result = await self.db.execute(
            select(QueryLog.category, func.count(QueryLog.id).label("count"))
            .where(QueryLog.category.isnot(None))
            .group_by(QueryLog.category)
            .order_by(func.count(QueryLog.id).desc())
            .limit(5)
        )
        top_categories = [
            {"category": row[0], "count": row[1]}
            for row in top_categories_result.all()
        ]

        return {
            "total_queries": total_queries,
            "today_queries": today_queries,
            "avg_confidence": round(avg_confidence, 2),
            "positive_feedback_rate": round(positive_rate, 2),
            "top_categories": top_categories,
        }

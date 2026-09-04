"""
智法通 - 重排序器模块（两阶段检索架构 - 精排阶段）

使用Cross-Encoder精排模型对粗排召回的候选文档进行重排序，
显著提升最终返回结果的相关性。

模型说明：
    - 模型名称：BAAI/bge-reranker-v2-m3
    - 模型类型：Cross-Encoder（查询和文档拼接后联合编码，精度优于双塔）
    - 调用方式：本地Docker容器 my-rerank 提供HTTP API（/rerank端点）
    - API格式：POST /rerank，body含query/documents/top_n，返回score排序结果

架构设计：
    1. 首选方案：调用本地Rerank服务（Cross-Encoder，一次批量调用，快速精准）
    2. 回退方案：LLM逐条打分（Rerank服务不可用时的降级方案）

两阶段检索流程：
    粗排（EmbeddingService向量检索召回Top-K候选）→ 精排（本模块Cross-Encoder重排序）

性能对比（vs 旧方案LLM逐条打分）：
    - 旧方案：N个候选 = N次串行LLM调用，延迟随N线性增长（20候选≈20次HTTP请求≈10秒）
    - 新方案：1次批量HTTP请求，所有候选一起送入Cross-Encoder（20候选≈1次请求≈0.5秒）
    - 精度提升：Cross-Encoder联合编码精度远优于LLM打分提示
"""

import httpx
import logging
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)


class Reranker:
    """重排序器类

    两阶段检索架构的精排阶段实现。
    优先调用本地Rerank服务（BAAI/bge-reranker-v2-m3 Cross-Encoder），
    服务不可用时回退到LLM逐条打分方案。

    设计要点：
        - 服务健康检测：首次调用时检测Rerank服务可用性，结果缓存
        - 批量调用：一次HTTP请求处理所有候选文档（vs 旧方案N次串行请求）
        - 自动降级：Rerank服务不可用时回退到LLM打分，保证系统可用性
    """

    def __init__(self):
        """初始化重排序器"""
        # Rerank服务地址（本地Docker容器 my-rerank）
        self.rerank_url = settings.RERANK_SERVICE_URL.rstrip("/")
        self.rerank_timeout = settings.RERANK_TIMEOUT
        # LLM回退方案配置
        self.llm_base_url = settings.OLLAMA_BASE_URL
        self.llm_model = settings.OLLAMA_MODEL
        self.llm_timeout = settings.OLLAMA_TIMEOUT
        # Rerank服务可用性缓存（None=未检测, True=可用, False=不可用）
        self._rerank_available = None

    async def _check_rerank_service(self) -> bool:
        """检测Rerank服务是否可用

        发送一个最小化测试请求检测服务连通性。
        结果缓存到self._rerank_available，避免每次请求都检测。

        Returns:
            True=Rerank服务可用，False=不可用需回退LLM方案
        """
        if self._rerank_available is not None:
            return self._rerank_available
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # 发送最小化测试请求
                resp = await client.post(
                    f"{self.rerank_url}/rerank",
                    json={
                        "query": "测试",
                        "documents": ["测试文档"],
                        "top_n": 1,
                    },
                )
                if resp.status_code == 200 and "results" in resp.json():
                    self._rerank_available = True
                    logger.info(f"✅ Rerank服务可用 | URL={self.rerank_url}")
                else:
                    self._rerank_available = False
                    logger.warning(
                        f"⚠️ Rerank服务响应异常 HTTP {resp.status_code}，回退到LLM打分"
                    )
        except Exception as e:
            self._rerank_available = False
            logger.warning(f"⚠️ Rerank服务连接失败，回退到LLM打分: {e}")
        return self._rerank_available

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_n: int = None,
    ) -> list[dict]:
        """对检索结果进行重排序（精排阶段核心方法）

        两阶段检索架构的第二阶段：
        1. 粗排阶段已通过ANN检索召回Top-K候选（此方法的documents参数）
        2. 本阶段用Cross-Encoder对所有候选与query联合编码打分
        3. 按分数降序排列，返回top_n个最相关的结果

        Args:
            query: 查询文本（用户问题或重写后的查询）
            documents: 粗排召回的候选文档列表，每个文档应包含content字段
            top_n: 返回前N个结果，None时使用配置默认值RAG_RERANK_TOP_N

        Returns:
            重排序后的文档列表，每个文档增加rerank_score字段
        """
        if not documents:
            return []

        if top_n is None:
            top_n = settings.RAG_RERANK_TOP_N

        # 优先使用Cross-Encoder Rerank服务（批量调用，快速精准）
        if await self._check_rerank_service():
            result = await self._rerank_with_cross_encoder(query, documents, top_n)
            if result is not None:
                return result
            # Cross-Encoder调用失败，降级到LLM方案
            logger.warning("Cross-Encoder调用失败，降级到LLM打分方案")

        # 回退方案：LLM逐条打分
        return await self._rerank_with_llm(query, documents, top_n)

    async def _rerank_with_cross_encoder(
        self,
        query: str,
        documents: list[dict],
        top_n: int,
    ) -> list[dict] | None:
        """使用Cross-Encoder Rerank服务进行精排

        调用本地Docker容器 my-rerank 的 /rerank 端点，
        一次性将所有候选文档送入BAAI/bge-reranker-v2-m3模型打分。

        API请求格式：
            POST /rerank
            {
                "query": "查询文本",
                "documents": ["文档1", "文档2", ...],
                "top_n": 5
            }

        API响应格式：
            {
                "results": [
                    {"index": 0, "score": 0.95, "document": "文档1"},
                    {"index": 1, "score": 0.12, "document": "文档2"},
                ],
                "total": 2,
                "model": "BAAI/bge-reranker-v2-m3"
            }

        Args:
            query: 查询文本
            documents: 候选文档列表
            top_n: 返回前N个

        Returns:
            重排序后的文档列表，或None（调用失败时）
        """
        try:
            # 提取文档内容列表
            doc_contents = [doc.get("content", "") for doc in documents]

            async with httpx.AsyncClient(timeout=self.rerank_timeout) as client:
                response = await client.post(
                    f"{self.rerank_url}/rerank",
                    json={
                        "query": query,
                        "documents": doc_contents,
                        "top_n": top_n,
                    },
                )
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                if not results:
                    logger.warning("Rerank服务返回空结果")
                    return None

                # 将Rerank服务返回的score映射回原始文档
                # results中的index对应doc_contents中的位置
                reranked = []
                for r in results:
                    idx = r["index"]
                    if 0 <= idx < len(documents):
                        doc = documents[idx].copy()
                        doc["rerank_score"] = r["score"]
                        reranked.append(doc)

                logger.info(
                    f"Cross-Encoder精排完成 | 输入{len(documents)}篇 | "
                    f"返回{len(reranked)}篇 | top_score={results[0]['score']:.4f}"
                )
                return reranked

        except Exception as e:
            logger.error(f"Cross-Encoder Rerank调用失败: {e}")
            return None

    async def _rerank_with_llm(
        self,
        query: str,
        documents: list[dict],
        top_n: int,
    ) -> list[dict]:
        """LLM逐条打分重排序（降级方案）

        当Cross-Encoder Rerank服务不可用时使用此方案。
        对每个文档调用LLM打分，返回0-1之间的相关性分数。

        性能说明：
            - N个候选需要N次串行LLM调用，延迟随N线性增长
            - 适用于Rerank服务不可用的降级场景，不推荐作为主方案

        Args:
            query: 查询文本
            documents: 候选文档列表
            top_n: 返回前N个

        Returns:
            按分数降序排列的文档列表
        """
        scored_docs = []
        for doc in documents:
            score = await self._score_document_with_llm(query, doc.get("content", ""))
            doc_with_score = doc.copy()
            doc_with_score["rerank_score"] = score
            scored_docs.append(doc_with_score)

        # 按重排序分数降序排列
        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored_docs[:top_n]

    async def _score_document_with_llm(self, query: str, document: str) -> float:
        """使用LLM对单个文档与查询的相关性打分（降级方案内部方法）

        Args:
            query: 查询文本
            document: 文档内容

        Returns:
            相关性分数（0-1），解析失败返回0.5
        """
        # 截断过长的文档
        max_doc_len = 500
        truncated_doc = document[:max_doc_len] + "..." if len(document) > max_doc_len else document

        prompt = f"""请评估以下法律文档片段与查询的相关性，给出0到1之间的分数。
0表示完全不相关，1表示高度相关。
只返回分数数字，不要返回其他内容。

查询：{query}

文档片段：{truncated_doc}

相关性分数："""

        try:
            async with httpx.AsyncClient(timeout=self.llm_timeout) as client:
                response = await client.post(
                    f"{self.llm_base_url}/api/generate",
                    json={
                        "model": self.llm_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # 低温度，确保输出稳定
                            "num_predict": 10,    # 只需要返回分数
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                score_text = data.get("response", "0.5").strip()

                # 尝试解析分数
                try:
                    score = float(score_text)
                    return max(0.0, min(1.0, score))  # 限制在0-1范围
                except ValueError:
                    return 0.5  # 解析失败返回默认分数

        except Exception:
            return 0.5  # 异常时返回默认分数

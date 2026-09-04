"""
智法通 - 混合检索器模块

实现稠密检索（向量相似度）+ BM25稀疏检索 + RRF融合的混合检索策略，
提高检索的准确性和召回率。
"""

import math
from typing import Optional
from collections import defaultdict

from app.rag.vector_store import ChromaVectorStore
from app.rag.embedding import EmbeddingService
from app.config import settings

# 尝试导入jieba分词器，失败则回退到字符级分词
# jieba对中文分词效果显著优于字符级分词，能大幅提升BM25检索质量
try:
    import jieba
    _JIEBA_AVAILABLE = True
except ImportError:
    _JIEBA_AVAILABLE = False


class HybridRetriever:
    """混合检索器类

    结合稠密检索和稀疏检索的优势，使用RRF（Reciprocal Rank Fusion）
    算法融合两路检索结果。

    V2.0增强：
    - BM25分词改用jieba（不可用时回退到字符级分词）
    - retrieve方法默认过滤已废止法条（effectiveness="有效"），可通过where参数覆盖
    """

    def __init__(self):
        """初始化混合检索器"""
        self.vector_store = ChromaVectorStore()
        self.embedding_service = EmbeddingService()
        self.rrf_k = settings.RAG_RRF_K  # RRF融合参数K

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """混合检索

        同时执行稠密检索和BM25稀疏检索，使用RRF融合结果。

        V2.0增强：默认过滤已废止法条（effectiveness="有效"），
        调用方可通过传入where参数覆盖默认过滤条件。

        Args:
            query: 查询文本
            top_k: 返回结果数量
            where: 元数据过滤条件。若为None则默认过滤 effectiveness="有效"，
                   若调用方传入where则使用调用方的过滤条件

        Returns:
            融合后的检索结果列表，按相关性排序
        """
        # 若调用方未指定过滤条件，默认启用效力状态过滤，排除已废止法条
        # 这符合V2.0文档对法条时效性管理的要求
        if where is None:
            where = {"effectiveness": "有效"}

        # 1. 稠密检索（向量相似度）
        dense_results = await self._dense_search(query, top_k * 2, where)

        # 2. 稀疏检索（BM25）
        sparse_results = await self._sparse_search(query, top_k * 2, where)

        # 3. RRF融合
        fused_results = self._rrf_fuse(dense_results, sparse_results)

        # 4. 返回top_k结果
        return fused_results[:top_k]

    async def _dense_search(
        self,
        query: str,
        n_results: int,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """稠密检索（向量相似度搜索）

        Args:
            query: 查询文本
            n_results: 返回数量
            where: 过滤条件

        Returns:
            检索结果列表
        """
        # 生成查询向量
        query_embedding = await self.embedding_service.embed_text(query)

        # 向量检索
        results = self.vector_store.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

        # 格式化结果
        formatted = []
        if results and results.get("ids") and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted.append({
                    "id": doc_id,
                    "content": results["documents"][0][i] if results.get("documents") else "",
                    "score": results["distances"][0][i] if results.get("distances") else 0.0,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "source": "dense",
                })

        return formatted

    async def _sparse_search(
        self,
        query: str,
        n_results: int,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """稀疏检索（BM25算法）

        使用简化的BM25算法对文档进行关键词匹配评分。

        Args:
            query: 查询文本
            n_results: 返回数量
            where: 过滤条件

        Returns:
            检索结果列表
        """
        # 从向量数据库获取所有文档（带过滤条件）
        all_docs = self.vector_store.get(where=where, limit=1000)

        if not all_docs or not all_docs.get("ids"):
            return []

        # BM25参数
        k1 = 1.5   # 词频饱和参数
        b = 0.75    # 文档长度归一化参数

        # 分词（V2.0：优先使用jieba，回退到字符级分词）
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        # 预先对所有文档分词，避免重复计算
        # 同时使用分词后的词项数作为文档长度，保证与分词方式一致
        documents = all_docs.get("documents") or []
        doc_token_lists = []  # 每个文档的词项列表
        doc_lengths = []      # 每个文档的长度（词项数）
        for doc in documents:
            if doc:
                tokens = self._tokenize(doc)
                doc_token_lists.append(tokens)
                doc_lengths.append(len(tokens))
            else:
                doc_token_lists.append([])
                doc_lengths.append(0)

        # 计算文档平均长度
        avg_dl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1

        # 计算IDF（逆文档频率）
        N = len(all_docs["ids"])
        df = defaultdict(int)  # 每个词出现在多少文档中

        for tokens in doc_token_lists:
            # 使用set去重，统计每个词出现在多少篇文档中
            for term in set(tokens):
                df[term] += 1

        # 计算每个文档的BM25分数
        scored_docs = []
        for i, doc_id in enumerate(all_docs["ids"]):
            doc = documents[i] if i < len(documents) else ""
            if not doc:
                continue

            doc_terms = doc_token_lists[i]
            doc_length = doc_lengths[i]
            tf = defaultdict(int)
            for term in doc_terms:
                tf[term] += 1

            score = 0.0
            for term in query_terms:
                if term not in df:
                    continue
                # IDF计算
                idf = math.log((N - df[term] + 0.5) / (df[term] + 0.5) + 1)
                # TF计算（带饱和和长度归一化）
                tf_val = tf.get(term, 0)
                tf_norm = (tf_val * (k1 + 1)) / (tf_val + k1 * (1 - b + b * doc_length / avg_dl))
                score += idf * tf_norm

            if score > 0:
                scored_docs.append({
                    "id": doc_id,
                    "content": doc,
                    "score": score,
                    "metadata": all_docs["metadatas"][i] if all_docs.get("metadatas") and i < len(all_docs["metadatas"]) else {},
                    "source": "sparse",
                })

        # 按分数降序排列
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:n_results]

    def _rrf_fuse(
        self,
        dense_results: list[dict],
        sparse_results: list[dict],
    ) -> list[dict]:
        """RRF（Reciprocal Rank Fusion）融合

        将稠密检索和稀疏检索的结果按排名倒数融合，
        公式：RRF(d) = Σ 1/(k + rank_i(d))

        Args:
            dense_results: 稠密检索结果
            sparse_results: 稀疏检索结果

        Returns:
            融合后的结果列表
        """
        # 计算每个文档的RRF分数
        rrf_scores = defaultdict(float)
        doc_data = {}  # 存储文档内容，避免重复

        # 稠密检索排名
        for rank, result in enumerate(dense_results, start=1):
            doc_id = result["id"]
            rrf_scores[doc_id] += 1.0 / (self.rrf_k + rank)
            doc_data[doc_id] = result

        # 稀疏检索排名
        for rank, result in enumerate(sparse_results, start=1):
            doc_id = result["id"]
            rrf_scores[doc_id] += 1.0 / (self.rrf_k + rank)
            if doc_id not in doc_data:
                doc_data[doc_id] = result

        # 按RRF分数排序
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # 组装结果
        fused_results = []
        for doc_id in sorted_ids:
            result = doc_data[doc_id].copy()
            result["rrf_score"] = rrf_scores[doc_id]
            fused_results.append(result)

        return fused_results

    def _tokenize(self, text: str) -> list[str]:
        """中文分词

        V2.0增强：优先使用jieba进行专业中文分词，
        若jieba不可用则回退到字符级分词。

        jieba分词能正确识别法律术语、专有名词等，
        相比字符级分词可显著提升BM25检索的准确率和召回率。

        Args:
            text: 待分词文本

        Returns:
            词项列表（已小写化、去停用词、去标点）
        """
        if not text:
            return []

        # 优先使用jieba分词
        if _JIEBA_AVAILABLE:
            try:
                # 使用精确模式（cut=False 即精确模式）
                # cut_all=False 表示非全模式，输出更精确的词
                raw_tokens = jieba.lcut(text, cut_all=False)
                tokens = []
                for token in raw_tokens:
                    token = token.strip().lower()
                    # 过滤空字符串、纯空白、纯标点符号
                    # 保留中文词、英文词、数字
                    if not token:
                        continue
                    # 跳过纯标点和空白
                    if all(
                        (not ('\u4e00' <= ch <= '\u9fff')) and
                        (not ch.isalnum())
                        for ch in token
                    ):
                        continue
                    # 跳过单字符的非中文非字母数字（如标点）
                    if len(token) == 1 and not (
                        '\u4e00' <= token <= '\u9fff' or token.isalnum()
                    ):
                        continue
                    tokens.append(token)
                return tokens
            except Exception:
                # jieba调用异常时回退到字符级分词
                pass

        # 回退方案：字符级分词（中文按字，英文按字符）
        # 这是V1.0的实现，作为兜底保证可用性
        tokens = []
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                tokens.append(char)
            elif char.isalnum():  # 英文和数字
                tokens.append(char.lower())
        return tokens

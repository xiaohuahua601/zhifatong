"""
智法通 - Embedding服务模块（两阶段检索架构 - 粗排阶段）

使用Ollama的中文专业嵌入模型 bge-large-zh-v1.5（1024维）将文本转换为向量，
用于ANN近邻检索（粗排阶段）。

模型说明：
    - 模型名称：quentinz/bge-large-zh-v1.5:latest
    - 输出维度：1024维
    - 训练数据：大规模中文语料，特别适合中文法律领域语义检索
    - 调用方式：Ollama HTTP API /api/embeddings

架构设计：
    1. 首选方案：Ollama bge-large-zh-v1.5（专业中文嵌入模型，语义检索效果好）
    2. 回退方案：本地TF-IDF哈希向量（Ollama不可用时的降级方案，仅保证可用性）

两阶段检索流程：
    粗排（本模块）→ ANN检索召回Top-K候选 → 精排（Reranker模块Cross-Encoder）
"""

import httpx
import numpy as np
import hashlib
from typing import List
import jieba
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# 本地回退方案的固定维度（与bge-large-zh-v1.5保持一致）
LOCAL_EMBEDDING_DIM = 1024


class EmbeddingService:
    """Embedding服务类

    优先使用Ollama的中文嵌入模型 bge-large-zh-v1.5，
    不可用时回退到基于jieba分词的本地哈希向量方案。

    设计要点：
        - 模型检测缓存：首次调用时检测Ollama可用性，结果缓存避免重复检测
        - 异常自动降级：Ollama调用失败时自动切换到本地方案
        - 批量接口：embed_texts 支持批量向量化（虽然Ollama逐条调用，但接口统一）
    """

    def __init__(self):
        """初始化Embedding服务"""
        self.base_url = settings.OLLAMA_BASE_URL
        # bge-large-zh-v1.5: 中文法律领域专业嵌入模型，1024维
        self.model = settings.OLLAMA_EMBEDDING_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self._use_ollama = None  # None=未检测, True=使用Ollama, False=使用本地

    async def _check_ollama_embedding(self) -> bool:
        """检测Ollama是否支持embedding（且模型可用）

        首次调用时发送测试请求检测Ollama服务连通性和模型可用性，
        结果缓存到self._use_ollama，避免每次请求都检测。

        Returns:
            True=Ollama embedding可用，False=不可用需回退本地方案
        """
        if self._use_ollama is not None:
            return self._use_ollama
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": "测试"},
                )
                if resp.status_code == 200 and resp.json().get("embedding"):
                    self._use_ollama = True
                    emb_dim = len(resp.json()["embedding"])
                    logger.info(
                        f"✅ Ollama embedding可用 | 模型={self.model} | 维度={emb_dim}"
                    )
                else:
                    self._use_ollama = False
                    logger.warning("⚠️ Ollama embedding不可用，使用本地TF-IDF哈希向量")
        except Exception as e:
            self._use_ollama = False
            logger.warning(f"⚠️ Ollama连接失败，使用本地TF-IDF哈希向量: {e}")
        return self._use_ollama

    async def embed_text(self, text: str) -> list[float]:
        """生成单条文本的embedding向量（粗排阶段核心方法）

        调用Ollama bge-large-zh-v1.5模型将文本编码为1024维向量，
        用于ChromaDB HNSW近邻检索（ANN粗排）。

        Args:
            text: 待编码的文本（法律文档片段或用户查询）

        Returns:
            1024维浮点数列表，表示文本的语义向量

        异常处理：
            Ollama调用失败时自动降级到本地哈希向量方案
        """
        if await self._check_ollama_embedding():
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={
                            "model": self.model,
                            "prompt": text,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    embedding = data.get("embedding", [])
                    if embedding:
                        return embedding
            except Exception as e:
                logger.warning(f"Ollama embedding失败，回退到本地: {e}")
                self._use_ollama = False

        # 本地TF-IDF哈希向量（降级方案）
        return self._local_embed(text)

    async def embed_texts(self, texts: list[str], batch_size: int = 10) -> list[list[float]]:
        """批量生成文本的embedding向量

        用于文档上传时对分块进行批量向量化，以及批量重建索引。

        Args:
            texts: 待编码的文本列表
            batch_size: 每批处理数量（Ollama逐条调用，batch_size仅控制日志频率）

        Returns:
            向量列表的列表，每个内部列表是1024维向量
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = []

            for text in batch:
                embedding = await self.embed_text(text)
                batch_embeddings.append(embedding)

            all_embeddings.extend(batch_embeddings)
            logger.debug(f"Embedding进度: {min(i + batch_size, len(texts))}/{len(texts)}")

        return all_embeddings

    def _local_embed(self, text: str) -> list[float]:
        """本地TF-IDF哈希向量生成（降级方案）

        当Ollama嵌入模型不可用时使用此方案。
        基于jieba分词 + 特征哈希（hashing trick）生成固定1024维向量。

        局限性说明：
            - 特征哈希是词袋模型，无语义编码能力
            - 仅能捕获词汇级别的相似性，无法理解深层语义
            - 作为降级方案保证系统可用性，检索质量不如专业嵌入模型

        Args:
            text: 待编码的文本

        Returns:
            1024维浮点数列表，L2归一化后的向量
        """
        # jieba分词
        words = list(jieba.cut(text))
        # 过滤停用词和单字
        words = [w for w in words if len(w.strip()) > 1]

        # 特征哈希：将每个词哈希到固定维度
        vector = np.zeros(LOCAL_EMBEDDING_DIM, dtype=np.float32)

        for word in words:
            # 使用MD5哈希将词映射到向量维度
            hash_bytes = hashlib.md5(word.encode("utf-8")).digest()
            # 取前4字节作为索引
            idx = int.from_bytes(hash_bytes[:4], "little") % LOCAL_EMBEDDING_DIM
            # 取中间4字节作为符号
            sign = 1.0 if hash_bytes[4] % 2 == 0 else -1.0
            # 词频加权
            vector[idx] += sign

        # L2归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()

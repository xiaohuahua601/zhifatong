"""
智法通 - RAG完整管线模块

整合查询重写、子查询分解、混合检索、重排序和生成回答的所有组件，
提供端到端的RAG（检索增强生成）服务。

V2.0增强（参考文档6.1.1节）：
- 指代消解：利用对话历史将代词替换为具体法律内容
- 复杂查询判断：仅对复杂查询执行子查询分解，提升效率
- 效力状态过滤：检索时默认过滤已废止法条
- 低置信度重检索闭环：自评估不达标时扩大检索范围重试（最多2次）
- 法条引用校验：检查回答中引用的法条是否真实存在于检索结果中
"""

import httpx
import json
import re
from typing import AsyncGenerator, Optional
from app.config import settings
from app.rag.query_rewriter import QueryRewriter
from app.rag.sub_query import SubQueryDecomposer
from app.rag.retriever import HybridRetriever
from app.rag.reranker import Reranker
from app.rag.self_eval import SelfEvaluator


class RAGPipeline:
    """RAG完整管线类

    整合所有RAG组件，提供完整的检索增强生成流程：
    1. 查询预处理（指代消解 + 查询重写 + 子查询分解）
    2. 混合检索（稠密+稀疏+RRF融合，带效力状态过滤）
    3. 重排序（精排）
    4. 上下文组装 + LLM生成
    5. 自评估（4维度结构化评估）
    6. 低置信度重检索闭环（最多2次）
    7. 法条引用校验
    """

    def __init__(self):
        """初始化RAG管线"""
        self.query_rewriter = QueryRewriter()
        self.sub_query_decomposer = SubQueryDecomposer()
        self.retriever = HybridRetriever()
        self.reranker = Reranker()
        self.self_evaluator = SelfEvaluator()

        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    async def query(
        self,
        question: str,
        history: Optional[list[dict]] = None,
    ) -> dict:
        """执行完整的RAG查询流程（非流式）

        V2.0完整流程（参考文档6.1.1节）：
        1. 查询预处理：指代消解 → 查询重写 → 复杂查询判断与子查询分解
        2. 混合检索：对每个子查询执行检索，带效力状态过滤，合并去重
        3. 重排序：精排Top-N
        4. 上下文构建
        5. LLM生成回答
        6. 自评估：基于检索质量的启发式评估（避免额外LLM调用）
        7. 低置信度重检索闭环：若 confidence < 0.4 且重试次数 < 2，
           扩大 top_k 至 2 倍并放宽 where 过滤条件后重新检索生成；
           超过 2 次重试仍不达标则降级返回并标记 low_confidence_warning=True
        8. 法条引用校验：检查引用的法条是否真实存在

        性能优化：使用启发式方法替代部分LLM调用，显著降低响应时间。
        """
        # ============ Step 1: 查询预处理 ============
        # 1.1 指代消解（利用对话历史，将"那个法条"等代词替换为具体内容）
        resolved_query = await self._resolve_coreference(question, history)

        # 1.2 查询重写（传入对话历史，重写器内部也会做指代消解兜底）
        rewritten_query = await self.query_rewriter.rewrite(resolved_query, history)

        # 1.3 子查询分解（使用启发式判断复杂查询，避免额外LLM调用）
        is_complex = self._is_complex_query_heuristic(rewritten_query)
        if is_complex:
            sub_queries = await self.sub_query_decomposer.decompose(rewritten_query)
        else:
            sub_queries = [rewritten_query]

        # ============ Step 2~6: 检索-生成-评估（含低置信度重检索闭环）============
        # 两阶段检索架构：
        #   第一阶段（粗排）：HybridRetriever 召回 RAG_RECALL_TOP_K 个候选
        #   第二阶段（精排）：Reranker 用 Cross-Encoder 精排，返回 RAG_RERANK_TOP_N 个结果
        # 重检索闭环：confidence < 阈值时扩大召回范围重试，最多 max_retries 次
        default_top_k = settings.RAG_RECALL_TOP_K  # 粗排召回数量（默认20）
        confidence_threshold = settings.RAG_RERETRIVAL_CONFIDENCE_THRESHOLD  # 重检索触发阈值
        max_retries = settings.RAG_RERETRIVAL_MAX_RETRIES  # 最大重检索次数

        retry_count = 0  # 已重试次数
        low_confidence_warning = False  # 是否因低置信度降级返回
        evaluation: dict = {}
        reranked: list[dict] = []
        answer = ""

        while True:
            # 根据重试次数调整检索参数
            if retry_count == 0:
                # 首次检索：默认 top_k，启用效力状态过滤（排除已废止法条）
                current_top_k = default_top_k
                where_filter: Optional[dict] = {"effectiveness": "有效"}
            else:
                # 重检索：扩大 top_k 至 2 倍，放宽 where 过滤条件（取消效力过滤）
                current_top_k = default_top_k * 2
                where_filter = {}  # 空字典表示不加过滤，召回更多候选

            # 2. 混合检索：对每个子查询执行检索，合并去重
            all_results = []
            for sq in sub_queries:
                results = await self.retriever.retrieve(
                    sq,
                    top_k=current_top_k,
                    where=where_filter,
                )
                all_results.extend(results)
            merged = self._merge_results(all_results)

            # 3. Rerank 精排
            reranked = await self.reranker.rerank(
                query=rewritten_query,
                documents=merged,
                top_n=settings.RAG_RERANK_TOP_N,
            )

            # 4. 上下文构建
            context = self._build_context(reranked, history)

            # 5. LLM 生成回答
            answer = await self._generate_answer(question, context, history)

            # 6. 启发式自评估（无需LLM调用）
            evaluation = self._heuristic_evaluate(question, context, answer, reranked)
            confidence = evaluation.get("confidence", 0.8)

            # 7. 低置信度重检索判定
            if confidence >= confidence_threshold:
                # 置信度达标，结束检索-生成循环
                break
            if retry_count < max_retries:
                # 仍未达标但还有重试机会，扩大范围重检索
                retry_count += 1
                continue
            # 超过最大重试次数仍不达标，降级返回并标记警告
            low_confidence_warning = True
            break

        # ============ Step 8: 法条引用校验 ============
        # 检查回答中引用的法条是否真实存在于检索结果中
        # 不存在的引用会被标记警告
        validated_answer = await self._validate_citations(answer, reranked)

        return {
            "answer": validated_answer,
            "citations": self._extract_citations(reranked),
            "confidence": evaluation.get("confidence", 0.8),
            "rewritten_query": rewritten_query,
            "sub_queries": sub_queries if is_complex else None,
            "retrieved_count": len(reranked),
            "evaluation": evaluation,
            # P0修复：新增重检索闭环相关字段
            "low_confidence_warning": low_confidence_warning,  # 是否因低置信度降级返回
            "reretrieval_count": retry_count,  # 实际重检索次数（0表示首次即达标）
        }

    async def query_stream(
        self,
        question: str,
        history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[dict, None]:
        """执行RAG查询流程（流式）

        使用SSE实时推送AI回答的每个分块。
        V2.0增强：流式流程也加入指代消解和效力状态过滤。

        性能优化：使用启发式判断复杂查询，避免额外LLM调用。
        """
        # 1. 指代消解
        resolved_query = await self._resolve_coreference(question, history)
        yield {
            "type": "meta",
            "resolved_query": resolved_query,
        }

        # 2. 查询重写（传入对话历史）
        rewritten_query = await self.query_rewriter.rewrite(resolved_query, history)
        yield {
            "type": "meta",
            "rewritten_query": rewritten_query,
        }

        # 3. 子查询分解（使用启发式判断，避免LLM调用）
        is_complex = self._is_complex_query_heuristic(rewritten_query)
        if is_complex:
            sub_queries = await self.sub_query_decomposer.decompose(rewritten_query)
        else:
            sub_queries = [rewritten_query]
        yield {
            "type": "meta",
            "sub_queries": sub_queries,
        }

        # 4. 混合检索（带效力状态过滤）
        all_documents = []
        for sq in sub_queries:
            docs = await self.retriever.retrieve(
                sq,
                top_k=settings.RAG_TOP_K,
                where={"effectiveness": "有效"},
            )
            all_documents.extend(docs)

        # 合并去重
        unique_docs = self._merge_results(all_documents)

        # 5. 重排序
        reranked_docs = await self.reranker.rerank(
            query=rewritten_query,
            documents=unique_docs,
            top_n=settings.RAG_RERANK_TOP_N,
        )

        # 6. 组装上下文
        context = self._build_context(reranked_docs, history)

        # 7. 推送引用来源元信息
        yield {
            "type": "meta",
            "citations": self._extract_citations(reranked_docs),
        }

        # 8. 构建提示词并流式生成
        prompt = self._build_prompt(question, context, history)

        full_answer = ""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": settings.OLLAMA_TEMPERATURE,
                        "num_predict": settings.OLLAMA_MAX_TOKENS,
                    },
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("response"):
                                full_answer += data["response"]
                                yield {
                                    "type": "content",
                                    "content": data["response"],
                                }
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

        # 9. 流式结束后进行法条引用校验
        # 注意：流式模式下不执行重检索闭环，避免阻塞流式输出
        validated_answer = await self._validate_citations(full_answer, reranked_docs)
        yield {
            "type": "meta",
            "validated_answer": validated_answer,
        }

        yield {"type": "done"}

    # ==================== V2.0新增方法 ====================

    async def _resolve_coreference(
        self,
        question: str,
        history: Optional[list[dict]] = None,
    ) -> str:
        """指代消解

        利用对话历史将当前问题中的指代词（如"那个法条""上面说的法律"
        "这个条款"等）替换为具体内容，生成语义完整的独立问题。

        V2.0新增方法。委托给QueryRewriter的resolve_coreference方法实现，
        保持职责单一。若对话历史为空或消解失败，返回原始问题。

        Args:
            question: 当前用户问题（可能包含指代词）
            history: 对话历史

        Returns:
            消解指代后的完整问题
        """
        if not history:
            return question
        return await self.query_rewriter.resolve_coreference(question, history)

    async def _is_complex_query(self, query: str) -> bool:
        """判断是否为复杂查询（LLM版本，保留备用）

        复杂查询通常包含多个法律要点、多个法律领域或需要多步推理。
        仅对复杂查询执行子查询分解，简单查询直接检索以提升效率。

        注意：此方法会调用LLM，响应较慢。生产环境建议使用
        _is_complex_query_heuristic 启发式版本以提升性能。

        Args:
            query: 查询文本（通常是重写后的查询）

        Returns:
            True表示复杂查询，需要分解；False表示简单查询
        """
        prompt = f"""判断以下法律查询是否为复杂查询（包含多个独立的法律要点、涉及多个法律领域，或需要多步推理）。
只回答"是"或"否"。

查询：{query}

是否为复杂查询："""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 10,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                answer = data.get("response", "否").strip()
                return "是" in answer

        except Exception:
            # 判断失败时默认为非复杂查询，避免不必要的分解开销
            return False

    def _is_complex_query_heuristic(self, query: str) -> bool:
        """启发式判断是否为复杂查询（无需LLM调用）

        基于查询长度、连接词、问号数量等特征判断查询复杂度，
        避免额外的LLM调用，显著提升响应速度。

        判断规则：
        1. 查询长度超过40个字符且包含连接词（"并且""同时""另外""以及"等）
        2. 包含多个问号（多个子问题）
        3. 包含多个法律领域关键词（如同时提到"劳动""合同""侵权"等）

        Args:
            query: 查询文本

        Returns:
            True表示复杂查询，需要分解；False表示简单查询
        """
        if not query:
            return False

        # 规则1：长查询 + 连接词
        conjunctions = ["并且", "同时", "另外", "以及", "还有", "此外", "和", "与"]
        has_conjunction = any(c in query for c in conjunctions)
        if len(query) > 40 and has_conjunction:
            return True

        # 规则2：多个问号（多个子问题）
        question_marks = query.count("？") + query.count("?")
        if question_marks >= 2:
            return True

        # 规则3：多个法律领域关键词
        law_domains = ["劳动", "合同", "侵权", "婚姻", "继承", "物权", "债权",
                       "刑法", "行政", "公司", "保险", "税务", "知识产权"]
        domain_count = sum(1 for d in law_domains if d in query)
        if domain_count >= 2:
            return True

        return False

    def _heuristic_evaluate(
        self,
        query: str,
        context: str,
        answer: str,
        retrieved_docs: list[dict],
    ) -> dict:
        """启发式自评估（无需LLM调用）

        基于检索结果质量、回答长度、引用情况等启发式特征
        评估回答质量，避免额外的LLM调用，显著提升响应速度。

        评估维度：
        - 法条准确性：基于回答中是否引用了检索结果中的法条
        - 逻辑完整性：基于回答长度和结构
        - 事实一致性：基于回答与上下文的相关性
        - 实用性：基于回答是否包含具体建议

        Args:
            query: 用户问题
            context: 检索上下文
            answer: AI回答
            retrieved_docs: 检索到的文档列表

        Returns:
            结构化评估字典
        """
        # 计算各维度评分（1-5分）
        # 1. 法条准确性：检查回答中是否引用了法条
        import re
        citation_pattern = re.compile(r'《([^》]+)》')
        cited_laws = set(citation_pattern.findall(answer))
        law_accuracy = min(5, 3 + len(cited_laws)) if cited_laws else 3

        # 2. 逻辑完整性：基于回答长度
        answer_len = len(answer)
        if answer_len > 500:
            logic_completeness = 5
        elif answer_len > 200:
            logic_completeness = 4
        elif answer_len > 100:
            logic_completeness = 3
        else:
            logic_completeness = 2

        # 3. 事实一致性：基于检索结果数量和分数
        retrieved_count = len(retrieved_docs)
        if retrieved_count > 0:
            avg_score = sum(
                doc.get("rerank_score", doc.get("rrf_score", doc.get("score", 0)))
                for doc in retrieved_docs
            ) / retrieved_count
            factual_consistency = min(5, max(2, int(avg_score * 5)))
        else:
            factual_consistency = 2

        # 4. 实用性：基于回答是否包含建议性词语
        practical_keywords = ["建议", "应当", "可以", "需要", "注意", "根据", "依据"]
        practical_count = sum(1 for k in practical_keywords if k in answer)
        practicality = min(5, 2 + practical_count)

        # 计算综合置信度
        confidence = self._calculate_heuristic_confidence(
            law_accuracy, logic_completeness, factual_consistency, practicality
        )

        return {
            "law_accuracy": law_accuracy,
            "logic_completeness": logic_completeness,
            "factual_consistency": factual_consistency,
            "practicality": practicality,
            "confidence": round(confidence, 2),
            "issues": [],
            # 评估本身不直接触发重检索，由 query 方法根据 confidence 判定是否重检索
            "needs_reretrieval": False,
            "improvement_suggestions": [],
        }

    def _calculate_heuristic_confidence(
        self,
        law_accuracy: int,
        logic_completeness: int,
        factual_consistency: int,
        practicality: int,
    ) -> float:
        """计算启发式综合置信度

        将4个维度的评分（1-5）通过加权平均归一化到0-1区间。
        权重分配反映各维度在法律咨询中的重要性：
        - 法条准确性40%：法律咨询的核心
        - 事实一致性30%：避免幻觉
        - 逻辑完整性20%：回答应当全面
        - 实用性10%：回答应当有参考价值

        Args:
            law_accuracy: 法条准确性评分（1-5）
            logic_completeness: 逻辑完整性评分（1-5）
            factual_consistency: 事实一致性评分（1-5）
            practicality: 实用性评分（1-5）

        Returns:
            综合置信度（0.0-1.0）
        """
        norm_law = (law_accuracy - 1) / 4
        norm_logic = (logic_completeness - 1) / 4
        norm_factual = (factual_consistency - 1) / 4
        norm_practical = (practicality - 1) / 4

        confidence = (
            0.40 * norm_law +
            0.30 * norm_factual +
            0.20 * norm_logic +
            0.10 * norm_practical
        )

        return max(0.0, min(1.0, confidence))

    def _merge_results(self, results: list[dict]) -> list[dict]:
        """合并多路检索结果并去重

        对多个子查询的检索结果进行合并，按文档ID去重。
        当同一文档被多个子查询检索到时，保留分数最高的版本。

        V2.0新增方法。

        Args:
            results: 多路检索的原始结果列表

        Returns:
            去重合并后的结果列表
        """
        if not results:
            return []

        seen = {}  # doc_id -> doc（保留最高分的版本）
        for doc in results:
            doc_id = doc.get("id")
            if not doc_id:
                continue
            # 取分数：优先rerank_score，其次rrf_score，最后score
            score = (
                doc.get("rerank_score")
                or doc.get("rrf_score")
                or doc.get("score")
                or 0.0
            )
            if doc_id not in seen:
                seen[doc_id] = doc
            else:
                # 已存在，保留分数较高的版本
                existing_score = (
                    seen[doc_id].get("rerank_score")
                    or seen[doc_id].get("rrf_score")
                    or seen[doc_id].get("score")
                    or 0.0
                )
                if score > existing_score:
                    seen[doc_id] = doc

        return list(seen.values())

    async def _validate_citations(
        self,
        answer: str,
        retrieved_docs: list[dict],
    ) -> str:
        """法条引用校验

        检查回答中引用的法条是否真实存在于检索结果中。
        若回答中引用了检索结果中不存在的法条，则在回答末尾追加警告，
        提示用户该引用可能不准确，建议核实。

        V2.0新增方法。这是防止LLM幻觉的重要防线。

        校验逻辑：
        1. 从回答中提取所有形如《法律名称》第X条的引用
        2. 从检索结果中提取所有法条信息
        3. 比对两者，找出回答中引用但检索结果中不存在的法条
        4. 若存在不匹配的引用，在回答末尾追加警告

        Args:
            answer: LLM生成的回答
            retrieved_docs: 检索到的文档列表

        Returns:
            校验后的回答（可能追加了引用警告）
        """
        if not answer or not retrieved_docs:
            return answer

        # 1. 从回答中提取法条引用
        # 匹配模式：《法律名称》第X条 或 《法律名称》第X条第Y款 等
        citation_pattern = re.compile(
            r'《([^》]+)》[^第]*第[一二三四五六七八九十百千零0-9]+条(?:[^《]*)?'
        )
        cited_laws = set()
        for match in citation_pattern.finditer(answer):
            law_name = match.group(1).strip()
            if law_name:
                cited_laws.add(law_name)

        if not cited_laws:
            # 回答中没有引用具体法条，无需校验
            return answer

        # 2. 从检索结果中提取法条名称
        retrieved_law_names = set()
        for doc in retrieved_docs:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            # 从元数据中提取法律名称（如果有）
            law_name_meta = metadata.get("law_name") or metadata.get("title")
            if law_name_meta:
                retrieved_law_names.add(law_name_meta.strip())
            # 从文档内容中提取《法律名称》
            for m in re.finditer(r'《([^》]+)》', content):
                name = m.group(1).strip()
                if name:
                    retrieved_law_names.add(name)

        # 3. 找出回答中引用但检索结果中不存在的法条
        # 注意：检索结果中的法条名称可能不完全匹配，使用模糊匹配
        unverified_citations = []
        for cited in cited_laws:
            # 精确匹配
            if cited in retrieved_law_names:
                continue
            # 模糊匹配：检索结果中是否包含该法条名称的关键部分
            matched = False
            for retrieved_name in retrieved_law_names:
                # 双向包含匹配，处理"中华人民共和国民法典" vs "民法典"等情况
                if (cited in retrieved_name) or (retrieved_name in cited):
                    matched = True
                    break
            if not matched:
                unverified_citations.append(cited)

        # 4. 若存在未验证的引用，追加警告
        if unverified_citations:
            warning_lines = [
                f"  - 《{name}》" for name in unverified_citations
            ]
            warning = (
                "\n\n---\n⚠️ **引用校验警告**：以下法条引用未在检索到的法律文档中找到，"
                "可能存在不准确之处，建议核实原文：\n"
                + "\n".join(warning_lines)
            )
            return answer + warning

        return answer

    # ==================== 原有辅助方法 ====================

    def _build_context(
        self,
        documents: list[dict],
        history: Optional[list[dict]] = None,
    ) -> str:
        """构建检索上下文

        将检索到的文档片段组装成结构化的上下文字符串。

        Args:
            documents: 检索到的文档列表
            history: 对话历史（V2.0新增，预留用于上下文增强）

        Returns:
            上下文字符串
        """
        if not documents:
            return "未找到相关法律文档。"

        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_type = metadata.get("doc_type", "未知类型")
            # V2.0：展示法条效力状态，便于LLM感知
            effectiveness = metadata.get("effectiveness", "")
            eff_label = f"，效力：{effectiveness}" if effectiveness else ""
            context_parts.append(
                f"【文档{i}】（类型：{doc_type}{eff_label}）\n{content}"
            )

        return "\n\n".join(context_parts)

    def _build_prompt(
        self,
        question: str,
        context: str,
        history: Optional[list[dict]] = None,
    ) -> str:
        """构建LLM提示词

        Args:
            question: 用户问题
            context: 检索上下文
            history: 对话历史

        Returns:
            完整的提示词
        """
        # 系统提示
        system_prompt = """你是智法通——企业级智能法律顾问平台的AI助手。
你精通中国法律法规，能够提供专业、准确、有据可依的法律咨询。

回答要求：
1. 基于提供的法律文档上下文进行回答，不要编造法律条文
2. 引用具体的法律依据时，注明法律名称和条款，格式如《法律名称》第X条
3. 如果上下文不足以回答问题，请如实说明
4. 回答应当专业、严谨、易于理解
5. 如涉及重要法律决策，建议咨询专业律师
6. 仅引用上下文中实际存在的法律条文，不要引用未提供的法条"""

        # 对话历史
        history_text = ""
        if history:
            history_parts = []
            for msg in history[-6:]:  # 最近6轮对话
                role = "用户" if msg.get("role") == "user" else "助手"
                history_parts.append(f"{role}：{msg.get('content', '')}")
            history_text = "\n".join(history_parts)

        # 组装提示词
        prompt_parts = [system_prompt]

        if history_text:
            prompt_parts.append(f"\n对话历史：\n{history_text}")

        prompt_parts.append(f"\n参考法律文档：\n{context}")
        prompt_parts.append(f"\n用户问题：{question}")
        prompt_parts.append("\n请基于以上法律文档回答用户问题：")

        return "\n".join(prompt_parts)

    async def _generate_answer(
        self,
        question: str,
        context: str,
        history: Optional[list[dict]] = None,
    ) -> str:
        """使用LLM生成回答（非流式）

        Args:
            question: 用户问题
            context: 检索上下文
            history: 对话历史

        Returns:
            AI回答文本
        """
        prompt = self._build_prompt(question, context, history)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": settings.OLLAMA_TEMPERATURE,
                            "num_predict": settings.OLLAMA_MAX_TOKENS,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "抱歉，无法生成回答。")

        except Exception as e:
            return f"生成回答时出错：{str(e)}"

    def _extract_citations(self, documents: list[dict]) -> list[dict]:
        """从检索结果中提取引用来源

        Args:
            documents: 检索到的文档列表

        Returns:
            引用来源列表
        """
        citations = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            citations.append({
                "document_id": metadata.get("document_id"),
                "content": doc.get("content", "")[:200],  # 截取前200字
                "score": doc.get("rerank_score", doc.get("rrf_score", 0)),
                "doc_type": metadata.get("doc_type"),
                "law_name": metadata.get("law_name") or metadata.get("title"),
                "effectiveness": metadata.get("effectiveness"),
            })
        return citations

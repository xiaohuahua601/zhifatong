"""
智法通 - 自评估器模块

对RAG生成的回答进行自评估，判断回答的质量和可靠性。

V2.0增强：
- 评估方法从返回float置信度升级为返回结构化字典
- 采用4维度评估：法条准确性、逻辑完整性、事实一致性、实用性
- 输出具体问题列表和改进建议
- 支持低置信度重检索闭环（needs_reretrieval标志）
"""

import httpx
import json
import re
from app.config import settings


class SelfEvaluator:
    """自评估器类

    使用LLM对生成的回答进行多维度质量评估，
    输出结构化评估结果，包括4个维度的评分、综合置信度、
    具体问题列表、是否需要重新检索的标志以及改进建议。

    V2.0评估维度（参考文档6.4.4节）：
    - 法条准确性（law_accuracy）：引用的法条是否准确、是否存在编造
    - 逻辑完整性（logic_completeness）：回答的逻辑是否完整、是否遗漏要点
    - 事实一致性（factual_consistency）：回答是否与检索上下文一致、是否有幻觉
    - 实用性（practicality）：回答是否具有实际参考价值
    """

    def __init__(self):
        """初始化自评估器"""
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    async def evaluate(
        self,
        query: str,
        context: str,
        answer: str,
    ) -> dict:
        """评估回答质量（V2.0结构化评估）

        使用LLM从4个维度对回答进行评估，返回结构化评估结果。
        当置信度过低或法条准确性不足时，标记需要重新检索。

        Args:
            query: 用户问题
            context: 检索上下文
            answer: AI回答

        Returns:
            结构化评估字典，包含以下字段：
            - law_accuracy: 法条准确性评分（1-5）
            - logic_completeness: 逻辑完整性评分（1-5）
            - factual_consistency: 事实一致性评分（1-5）
            - practicality: 实用性评分（1-5）
            - confidence: 综合置信度（0.0-1.0）
            - issues: 具体问题列表
            - needs_reretrieval: 是否需要重新检索
            - improvement_suggestions: 改进建议列表
        """
        # 使用LLM进行4维度结构化评估
        raw_eval = await self._llm_evaluate(query, context, answer)

        # 计算综合置信度（加权平均，归一化到0-1）
        # 权重：法条准确性40% + 事实一致性30% + 逻辑完整性20% + 实用性10%
        # 法条准确性权重最高，因为法律咨询中法条引用的准确性至关重要
        confidence = self._calculate_confidence(
            law_accuracy=raw_eval["law_accuracy"],
            logic_completeness=raw_eval["logic_completeness"],
            factual_consistency=raw_eval["factual_consistency"],
            practicality=raw_eval["practicality"],
        )

        # 判断是否需要重新检索
        # 触发条件：综合置信度 < 0.6 或 法条准确性 < 3
        # 这两个条件意味着回答可能存在严重的法条错误或整体质量不达标
        needs_reretrieval = (confidence < 0.6) or (raw_eval["law_accuracy"] < 3)

        return {
            "law_accuracy": raw_eval["law_accuracy"],
            "logic_completeness": raw_eval["logic_completeness"],
            "factual_consistency": raw_eval["factual_consistency"],
            "practicality": raw_eval["practicality"],
            "confidence": round(confidence, 2),
            "issues": raw_eval["issues"],
            "needs_reretrieval": needs_reretrieval,
            "improvement_suggestions": raw_eval["improvement_suggestions"],
        }

    def _calculate_confidence(
        self,
        law_accuracy: int,
        logic_completeness: int,
        factual_consistency: int,
        practicality: int,
    ) -> float:
        """计算综合置信度

        将4个维度的评分（1-5）通过加权平均归一化到0-1区间。
        权重分配反映各维度在法律咨询中的重要性：
        - 法条准确性40%：法律咨询的核心，法条错误会导致严重误导
        - 事实一致性30%：避免幻觉，确保回答基于检索到的真实法律文档
        - 逻辑完整性20%：回答应当全面覆盖问题的各个要点
        - 实用性10%：回答应当对用户有实际参考价值

        Args:
            law_accuracy: 法条准确性评分（1-5）
            logic_completeness: 逻辑完整性评分（1-5）
            factual_consistency: 事实一致性评分（1-5）
            practicality: 实用性评分（1-5）

        Returns:
            综合置信度（0.0-1.0）
        """
        # 将1-5分归一化到0-1：(score - 1) / 4
        norm_law = (law_accuracy - 1) / 4
        norm_logic = (logic_completeness - 1) / 4
        norm_factual = (factual_consistency - 1) / 4
        norm_practical = (practicality - 1) / 4

        # 加权平均
        confidence = (
            0.40 * norm_law +
            0.30 * norm_factual +
            0.20 * norm_logic +
            0.10 * norm_practical
        )

        # 限制在0-1范围
        return max(0.0, min(1.0, confidence))

    async def _llm_evaluate(
        self,
        query: str,
        context: str,
        answer: str,
    ) -> dict:
        """使用LLM进行4维度评估

        调用LLM对回答进行结构化评估，返回4个维度的评分、
        具体问题列表和改进建议。

        Args:
            query: 用户问题
            context: 检索上下文
            answer: AI回答

        Returns:
            包含评分、问题列表和改进建议的字典
        """
        # 截断过长的文本，避免超出LLM上下文长度
        max_len = 1500
        truncated_answer = answer[:max_len] + "..." if len(answer) > max_len else answer
        truncated_context = context[:max_len] + "..." if len(context) > max_len else context
        truncated_query = query[:500] if len(query) > 500 else query

        prompt = f"""请对以下法律咨询AI回答进行4维度评估。严格按JSON格式返回结果，不要返回其他内容。

评估维度（每项1-5分）：
1. law_accuracy（法条准确性）：引用的法律条文是否准确、是否存在编造法条
2. logic_completeness（逻辑完整性）：回答逻辑是否完整、是否遗漏重要要点
3. factual_consistency（事实一致性）：回答是否与提供的法律文档上下文一致、是否有幻觉
4. practicality（实用性）：回答对用户是否有实际参考价值

用户问题：{truncated_query}

法律文档上下文：
{truncated_context}

AI回答：
{truncated_answer}

请返回以下JSON格式（只返回JSON，不要其他文字）：
{{
  "law_accuracy": 1到5的整数,
  "logic_completeness": 1到5的整数,
  "factual_consistency": 1到5的整数,
  "practicality": 1到5的整数,
  "issues": ["具体问题1", "具体问题2"],
  "improvement_suggestions": ["改进建议1", "改进建议2"]
}}"""

        # 默认评估结果（LLM调用失败时使用）
        default_result = {
            "law_accuracy": 3,
            "logic_completeness": 3,
            "factual_consistency": 3,
            "practicality": 3,
            "issues": [],
            "improvement_suggestions": [],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",  # 强制JSON输出
                        "options": {
                            "temperature": 0.1,  # 低温度，确保评估稳定
                            "num_predict": 500,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                result_text = data.get("response", "").strip()

                # 尝试解析JSON
                parsed = self._parse_eval_result(result_text)
                return parsed

        except Exception:
            # LLM调用失败时返回默认评估结果
            return default_result

    def _parse_eval_result(self, result_text: str) -> dict:
        """解析LLM评估结果

        从LLM返回的文本中提取JSON评估结果，
        并对字段进行校验和规范化。

        Args:
            result_text: LLM返回的文本

        Returns:
            规范化后的评估字典
        """
        default_result = {
            "law_accuracy": 3,
            "logic_completeness": 3,
            "factual_consistency": 3,
            "practicality": 3,
            "issues": [],
            "improvement_suggestions": [],
        }

        if not result_text:
            return default_result

        # 尝试直接解析JSON
        parsed = None
        try:
            parsed = json.loads(result_text)
        except json.JSONDecodeError:
            # 直接解析失败，尝试从文本中提取JSON块
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

        if not isinstance(parsed, dict):
            return default_result

        # 规范化各维度评分（限制在1-5范围）
        def clamp_score(value: int, default: int = 3) -> int:
            try:
                score = int(value)
                return max(1, min(5, score))
            except (ValueError, TypeError):
                return default

        result = {
            "law_accuracy": clamp_score(parsed.get("law_accuracy", 3)),
            "logic_completeness": clamp_score(parsed.get("logic_completeness", 3)),
            "factual_consistency": clamp_score(parsed.get("factual_consistency", 3)),
            "practicality": clamp_score(parsed.get("practicality", 3)),
        }

        # 规范化问题列表和改进建议
        issues = parsed.get("issues", [])
        if isinstance(issues, list):
            result["issues"] = [str(i) for i in issues if i]
        else:
            result["issues"] = []

        suggestions = parsed.get("improvement_suggestions", [])
        if isinstance(suggestions, list):
            result["improvement_suggestions"] = [str(s) for s in suggestions if s]
        else:
            result["improvement_suggestions"] = []

        return result

"""
智法通 - 合同模型模块

定义合同审查相关的数据库模型，包括合同、审查报告和风险条款。
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Enum, Boolean
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class ContractStatus(str, enum.Enum):
    """合同状态枚举"""
    UPLOADED = "uploaded"         # 已上传
    PARSING = "parsing"           # 解析中
    PARSED = "parsed"             # 已解析
    REVIEWING = "reviewing"       # 审查中
    REVIEWED = "reviewed"         # 已审查
    FAILED = "failed"             # 处理失败


class RiskLevel(str, enum.Enum):
    """风险等级枚举"""
    LOW = "low"                   # 低风险
    MEDIUM = "medium"             # 中风险
    HIGH = "high"                 # 高风险
    CRITICAL = "critical"         # 严重风险


class Contract(Base):
    """合同模型

    存储用户上传的合同文件信息，包括文件路径、解析状态等。
    一份合同可生成多份审查报告。
    """
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="合同ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    title = Column(String(200), nullable=False, comment="合同标题")
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    file_type = Column(String(20), nullable=True, comment="文件类型（pdf/docx/txt）")
    # 解析后的合同全文
    content = Column(Text, nullable=True, comment="合同全文内容")
    status = Column(Enum(ContractStatus), default=ContractStatus.UPLOADED, comment="合同状态")
    # 合同类型（如：劳动合同、租赁合同、买卖合同等）
    contract_type = Column(String(50), nullable=True, comment="合同类型")
    # 合同涉及的金额
    amount = Column(Float, nullable=True, comment="合同金额")
    # 合同双方
    party_a = Column(String(200), nullable=True, comment="甲方")
    party_b = Column(String(200), nullable=True, comment="乙方")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系：合同的审查报告
    reports = relationship("ReviewReport", back_populates="contract", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Contract(id={self.id}, title='{self.title}')>"


class ReviewReport(Base):
    """审查报告模型

    存储AI对合同的审查结果，包括总体评分和风险摘要。
    一份报告包含多条风险条款详情。

    V4.0新增字段（多Agent对抗式审查，参考文档4.3节）：
    - primary_risks: 主审Agent风险清单（JSON）
    - review_check: 复核Agent规则复检结果（JSON）
    - adverse_opinions: 反方Agent反对意见（JSON）
    - debate_log: 对抗辩论记录（JSON）
    - unresolved_issues: 未达成共识问题（JSON）
    - adverse_opinion_count: 反对意见数量
    - unresolved_count: 未解决问题数量
    """
    __tablename__ = "review_reports"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="报告ID")
    contract_id = Column(
        Integer,
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="合同ID"
    )
    # 总体风险评分（0-100，越高越安全）
    overall_score = Column(Float, nullable=True, comment="总体安全评分（0-100）")
    # 总体风险等级
    risk_level = Column(Enum(RiskLevel), nullable=True, comment="总体风险等级")
    # 风险条款数量
    risk_clause_count = Column(Integer, default=0, comment="风险条款数量")
    # 审查摘要
    summary = Column(Text, nullable=True, comment="审查摘要")
    # 审查建议
    suggestions = Column(Text, nullable=True, comment="改进建议（JSON格式）")
    # 完整性检查结果
    completeness = Column(Text, nullable=True, comment="完整性检查结果（JSON格式）")
    # 合规性检查结果
    compliance = Column(Text, nullable=True, comment="合规性检查结果（JSON格式）")
    # 一致性检查结果
    consistency = Column(Text, nullable=True, comment="一致性检查结果（JSON格式）")
    # 审查耗时（毫秒）
    review_duration_ms = Column(Integer, nullable=True, comment="审查耗时（毫秒）")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # ==================== V4.0新增字段：多Agent对抗式审查结果（参考文档4.3节）====================
    # 主审Agent风险清单：基于risk_clauses + compliance_issues汇总的中立专业审查结论（JSON数组）
    primary_risks = Column(Text, nullable=True, comment="主审Agent风险清单（JSON格式）")
    # 复核Agent规则复检结果：approved/disputed/missed三分类（JSON对象）
    review_check = Column(Text, nullable=True, comment="复核Agent规则复检结果（JSON格式）")
    # 反方Agent反对意见：站在合同弱势方立场质疑每一条款（JSON数组）
    adverse_opinions = Column(Text, nullable=True, comment="反方Agent反对意见（JSON格式）")
    # 对抗辩论记录：主审回应反方质疑的多轮辩论留痕（JSON数组）
    debate_log = Column(Text, nullable=True, comment="对抗辩论记录（JSON格式）")
    # 未达成共识问题列表：辩论后仍存在分歧的条款（JSON数组）
    unresolved_issues = Column(Text, nullable=True, comment="未达成共识问题（JSON格式）")
    # 反对意见数量（冗余字段，便于查询统计）
    adverse_opinion_count = Column(Integer, default=0, comment="反方Agent反对意见数量")
    # 未解决问题数量（冗余字段，便于查询统计）
    unresolved_count = Column(Integer, default=0, comment="未达成共识问题数量")

    # 关系：所属合同
    contract = relationship("Contract", back_populates="reports")
    # 关系：报告中的风险条款
    risk_clauses = relationship("RiskClause", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReviewReport(id={self.id}, score={self.overall_score})>"


class RiskClause(Base):
    """风险条款模型

    存储合同中被识别出的具体风险条款，
    包括条款内容、风险类型、风险等级和修改建议。
    """
    __tablename__ = "risk_clauses"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="风险条款ID")
    report_id = Column(
        Integer,
        ForeignKey("review_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="报告ID"
    )
    # 条款在合同中的位置序号
    clause_index = Column(Integer, nullable=True, comment="条款序号")
    # 原始条款内容
    original_text = Column(Text, nullable=False, comment="原始条款内容")
    # 风险类型（如：权利不对等、模糊条款、违法条款等）
    risk_type = Column(String(100), nullable=True, comment="风险类型")
    # 风险等级
    risk_level = Column(Enum(RiskLevel), nullable=True, comment="风险等级")
    # 风险分数（0-1，越高越危险）
    risk_score = Column(Float, nullable=True, comment="风险分数（0-1）")
    # 风险说明
    risk_description = Column(Text, nullable=True, comment="风险说明")
    # 修改建议
    suggestion = Column(Text, nullable=True, comment="修改建议")
    # 相关法律依据
    legal_basis = Column(Text, nullable=True, comment="相关法律依据")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系：所属报告
    report = relationship("ReviewReport", back_populates="risk_clauses")

    def __repr__(self):
        return f"<RiskClause(id={self.id}, risk_level='{self.risk_level}')>"

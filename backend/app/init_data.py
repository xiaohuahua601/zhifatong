"""
智法通 - 数据库种子数据初始化模块

应用首次启动时自动注入基础数据，确保新部署环境可立即登录使用。
包含：RBAC角色权限、3个内置测试账号、示例法律文档、欢迎通知。

幂等设计：所有插入均通过先查询后插入，重复启动不会产生重复数据。
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role, Permission
from app.models.knowledge import LegalDocument, DocumentStatus, DocumentSource
from app.models.notification import Notification, NotificationType
from app.models.analysis import QueryLog, CitationStat
from app.models.contract import Contract, ContractStatus, ReviewReport, RiskClause, RiskLevel
from app.utils.security import hash_password

logger = logging.getLogger(__name__)


# ==================== 内置账号配置 ====================
# 3个内置测试账号，覆盖3种核心角色，便于功能验证
# 实际生产环境应在首次登录后修改密码
BUILTIN_USERS: list[dict] = [
    {
        "username": "admin",
        "email": "admin@zhifatong.com",
        "password": "admin123",
        "phone": "13800000001",
        "is_superuser": True,
        "role_code": "admin",
        "remark": "超级管理员",
    },
    {
        "username": "lawyer",
        "email": "lawyer@zhifatong.com",
        "password": "lawyer123",
        "phone": "13800000002",
        "is_superuser": False,
        "role_code": "legal_admin",
        "remark": "法务负责人",
    },
    {
        "username": "user",
        "email": "user@zhifatong.com",
        "password": "user123456",
        "phone": "13800000003",
        "is_superuser": False,
        "role_code": "user",
        "remark": "普通用户",
    },
]


# ==================== 角色配置 ====================
BUILTIN_ROLES: list[dict] = [
    {
        "name": "超级管理员",
        "code": "admin",
        "description": "系统最高权限角色，可访问所有功能模块及系统设置",
        "is_default": False,
    },
    {
        "name": "法务负责人",
        "code": "legal_admin",
        "description": "企业法务部门负责人，可使用全部业务功能及数据分析",
        "is_default": False,
    },
    {
        "name": "普通用户",
        "code": "user",
        "description": "普通员工账号，可使用法律问答、合同审查、法规检索、个人中心",
        "is_default": True,
    },
]


# ==================== 示例法律文档（核心法条）====================
# 用于RAG检索增强生成，确保法律问答有基础知识来源
SAMPLE_LEGAL_DOCS: list[dict] = [
    {
        "title": "中华人民共和国劳动合同法（2012修正）",
        "doc_type": "法律",
        "content": """中华人民共和国劳动合同法

第一章 总则

第一条 为了完善劳动合同制度，明确劳动合同双方当事人的权利和义务，保护劳动者的合法权益，构建和发展和谐稳定的劳动关系，制定本法。

第二条 中华人民共和国境内的企业、个体经济组织、民办非企业单位等组织（以下称用人单位）与劳动者建立劳动关系，订立、履行、变更、解除或者终止劳动合同，适用本法。

第三条 订立劳动合同，应当遵循合法、公平、平等自愿、协商一致、诚实信用的原则。

第十条 建立劳动关系，应当订立书面劳动合同。已建立劳动关系，未同时订立书面劳动合同的，应当自用工之日起一个月内订立书面劳动合同。

第十九条 劳动合同期限三个月以上不满一年的，试用期不得超过一个月；劳动合同期限一年以上不满三年的，试用期不得超过二个月；三年以上固定期限和无固定期限的劳动合同，试用期不得超过六个月。

第二十条 劳动者在试用期的工资不得低于本单位相同岗位最低档工资或者劳动合同约定工资的百分之八十，并不得低于用人单位所在地的最低工资标准。

第三十六条 用人单位与劳动者协商一致，可以解除劳动合同。

第三十八条 用人单位有下列情形之一的，劳动者可以解除劳动合同：
（一）未按照劳动合同约定提供劳动保护或者劳动条件的；
（二）未及时足额支付劳动报酬的；
（三）未依法为劳动者缴纳社会保险费的；
（四）用人单位的规章制度违反法律、法规的规定，损害劳动者权益的。

第四十条 有下列情形之一的，用人单位提前三十日以书面形式通知劳动者本人或者额外支付劳动者一个月工资后，可以解除劳动合同：
（一）劳动者患病或者非因工负伤，在规定的医疗期满后不能从事原工作，也不能从事由用人单位另行安排的工作的；
（二）劳动者不能胜任工作，经过培训或者调整工作岗位，仍不能胜任工作的。

第四十六条 有下列情形之一的，用人单位应当向劳动者支付经济补偿：
（一）劳动者依照本法第三十八条规定解除劳动合同的；
（二）用人单位依照本法第三十六条规定向劳动者提出解除劳动合同并与劳动者协商一致解除劳动合同的；
（三）用人单位依照本法第四十条规定解除劳动合同的。

第四十七条 经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付。六个月以上不满一年的，按一年计算；不满六个月的，向劳动者支付半个月工资的经济补偿。

第八十二条 用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应当向劳动者每月支付二倍的工资。""",
        "summary": "劳动合同法是调整劳动关系的基础法律，规定了劳动合同的订立、履行、变更、解除、终止及经济补偿等核心制度。",
        "publish_date": datetime(2012, 12, 28),
        "tags": '["劳动法","合同","经济补偿"]',
    },
    {
        "title": "中华人民共和国民法典（2020）合同编摘录",
        "doc_type": "法律",
        "content": """中华人民共和国民法典 第三编 合同

第四百六十三条 本编调整因合同产生的民事关系。

第四百六十四条 合同是民事主体之间设立、变更、终止民事法律关系的协议。

第四百六十九条 当事人订立合同，可以采用书面形式、口头形式或者其他形式。

第四百七十条 合同的内容由当事人约定，一般包括下列条款：（一）当事人的姓名或者名称和住所；（二）标的；（三）数量；（四）质量；（五）价款或者报酬；（六）履行期限、地点和方式；（七）违约责任；（八）解决争议的方法。

第四百九十六条 格式条款是当事人为了重复使用而预先拟定，并在订立合同时未与对方协商的条款。采用格式条款订立合同的，提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务，并采取合理的方式提示对方注意免除或者减轻其责任等与对方有重大利害关系的条款。

第四百九十七条 有下列情形之一的，该格式条款无效：（一）具有本法第一编第六章第三节和本法第五百零六条规定的无效情形；（二）提供格式条款一方不合理地免除或者减轻其责任、加重对方责任、限制对方主要权利；（三）提供格式条款一方排除对方主要权利。

第五百条 当事人在订立合同过程中有下列情形之一，造成对方损失的，应当承担赔偿责任：（一）假借订立合同，恶意进行磋商；（二）故意隐瞒与订立合同有关的重要事实或者提供虚假情况；（三）有其他违背诚信原则的行为。

第五百零九条 当事人应当按照约定全面履行自己的义务。当事人应当遵循诚信原则，根据合同的性质、目的和交易习惯履行通知、协助、保密等义务。

第五百七十七条 当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。

第五百八十五条 当事人可以约定一方违约时应当根据违约情况向对方支付一定数额的违约金，也可以约定因违约产生的损失赔偿额的计算方法。约定的违约金低于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以增加；约定的违约金过分高于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以适当减少。""",
        "summary": "民法典合同编是调整合同关系的基本法律，规定了合同的订立、效力、履行、保全、变更、转让、终止及违约责任等制度。",
        "publish_date": datetime(2020, 5, 28),
        "tags": '["民法典","合同","违约责任"]',
    },
    {
        "title": "中华人民共和国消费者权益保护法（2013修正）摘录",
        "doc_type": "法律",
        "content": """中华人民共和国消费者权益保护法

第二条 消费者为生活消费需要购买、使用商品或者接受服务，其权益受本法保护。

第七条 消费者在购买、使用商品和接受服务时享有人身、财产安全不受损害的权利。

第八条 消费者享有知悉其购买、使用的商品或者接受的服务的真实情况的权利。

第九条 消费者享有自主选择商品或者服务的权利。

第十条 消费者享有公平交易的权利。

第二十四条 经营者提供的商品或者服务不符合质量要求的，消费者可以依照国家规定、当事人约定退货，或者要求经营者履行更换、修理等义务。

第二十五条 经营者采用网络、电视、电话、邮购等方式销售商品，消费者有权自收到商品之日起七日内退货，且无需说明理由。

第五十五条 经营者提供商品或者服务有欺诈行为的，应当按照消费者的要求增加赔偿其受到的损失，增加赔偿的金额为消费者购买商品的价款或者接受服务的费用的三倍；增加赔偿的金额不足五百元的，为五百元。""",
        "summary": "消费者权益保护法保护消费者在购买、使用商品和接受服务过程中的合法权益，规定了七天无理由退货、三倍赔偿等制度。",
        "publish_date": datetime(2013, 10, 25),
        "tags": '["消费者权益","三倍赔偿","七天无理由退货"]',
    },
    {
        "title": "最高人民法院关于审理民间借贷案件适用法律若干问题的规定",
        "doc_type": "司法解释",
        "content": """最高人民法院关于审理民间借贷案件适用法律若干问题的规定

第一条 本规定所称的民间借贷，是指自然人、法人和非法人组织之间进行资金融通的行为。

第二十六条 借贷双方约定的利率未超过年利率24%，出借人请求借款人按照约定的利率支付利息的，人民法院应予支持。借贷双方约定的利率超过年利率36%，超过部分的利息约定无效。

第二十九条 借贷双方对逾期利率有约定的，从其约定，但以不超过年利率24%为限。

第三十条 出借人与借款人既约定了逾期利率，又约定了违约金或者其他费用，出借人可以选择主张逾期利息、违约金或者其他费用，也可以一并主张，但总计超过年利率24%的部分，人民法院不予支持。""",
        "summary": "该司法解释明确了民间借贷的利率上限：未超24%受法律保护，超36%部分无效，24%-36%之间为自然债务。",
        "publish_date": datetime(2015, 8, 6),
        "tags": '["民间借贷","利率","司法解释"]',
    },
]


# ==================== 通知模板 ====================
def _build_welcome_notifications(user_id: int, username: str, role_name: str) -> Notification:
    """构造欢迎通知"""
    return Notification(
        user_id=user_id,
        type=NotificationType.SYSTEM,
        title="欢迎使用智法通企业级智能法律顾问平台",
        content=(
            f"尊敬的 {username}（{role_name}），欢迎您使用智法通平台！\n\n"
            "平台为您提供以下核心服务：\n"
            "• 智能法律问答：基于AI的法律咨询服务\n"
            "• 合同智能审查：上传合同自动识别风险条款\n"
            "• 法规案例检索：检索法律法规与典型案例\n\n"
            "如有疑问，请联系系统管理员。"
        ),
        is_read=False,
    )


# ==================== 主初始化函数 ====================

async def init_seed_data(db: AsyncSession) -> None:
    """执行数据库种子数据初始化（幂等）

    按以下顺序执行，每一步均先查询判断是否已存在：
    1. 创建3个内置角色
    2. 创建3个内置测试用户并绑定角色
    3. 创建示例法律文档（用于RAG检索）
    4. 为每个用户生成欢迎通知

    每步独立提交，避免最后统一commit时因历史残留数据触发唯一键冲突
    导致全部回滚。

    Args:
        db: 异步数据库会话
    """
    try:
        # ===== 步骤1：初始化角色 =====
        role_map: dict[str, Role] = {}
        for role_cfg in BUILTIN_ROLES:
            existing = await db.execute(
                select(Role).where(Role.code == role_cfg["code"])
            )
            role = existing.scalar_one_or_none()
            if role is None:
                role = Role(**role_cfg)
                db.add(role)
                await db.commit()
                await db.refresh(role)
                logger.info(f"[Seed] 创建角色: {role_cfg['code']} - {role_cfg['name']}")
            role_map[role_cfg["code"]] = role

        # ===== 步骤2：初始化内置用户 =====
        user_map: dict[str, User] = {}
        for user_cfg in BUILTIN_USERS:
            # 查询是否已存在同名用户
            existing = await db.execute(
                select(User).where(User.username == user_cfg["username"])
            )
            user = existing.scalar_one_or_none()
            if user is None:
                user = User(
                    username=user_cfg["username"],
                    email=user_cfg["email"],
                    hashed_password=hash_password(user_cfg["password"]),
                    phone=user_cfg["phone"],
                    is_active=True,
                    is_superuser=user_cfg["is_superuser"],
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                logger.info(f"[Seed] 创建用户: {user_cfg['username']} ({user_cfg['remark']})")

            # 绑定角色（避免重复绑定）
            await db.refresh(user, ["roles"])
            target_role = role_map.get(user_cfg["role_code"])
            if target_role and target_role not in user.roles:
                user.roles.append(target_role)
                await db.commit()
                logger.info(f"[Seed] 用户 {user_cfg['username']} 绑定角色 {target_role.code}")

            user_map[user_cfg["username"]] = user

        # ===== 步骤3：初始化示例法律文档 =====
        # 仅在 legal_documents 表为空时插入，避免覆盖用户已有数据
        count_result = await db.execute(
            select(LegalDocument).limit(1)
        )
        if count_result.scalar_one_or_none() is None:
            admin_user = user_map.get("admin")
            for doc_cfg in SAMPLE_LEGAL_DOCS:
                doc = LegalDocument(
                    title=doc_cfg["title"],
                    doc_type=doc_cfg["doc_type"],
                    source=DocumentSource.MANUAL,
                    content=doc_cfg["content"],
                    summary=doc_cfg["summary"],
                    status=DocumentStatus.COMPLETED,
                    indexing_progress=100,
                    chunk_count=1,
                    uploaded_by=admin_user.id if admin_user else None,
                    tags=doc_cfg.get("tags"),
                    publish_date=doc_cfg.get("publish_date"),
                    is_effective=True,
                )
                db.add(doc)
            await db.commit()
            logger.info(f"[Seed] 创建 {len(SAMPLE_LEGAL_DOCS)} 篇示例法律文档")

        # ===== 步骤4：生成欢迎通知（仅在用户无任何通知时） =====
        added_notif = 0
        for username, user in user_map.items():
            # 检查该用户是否已有通知
            notif_check = await db.execute(
                select(Notification).where(Notification.user_id == user.id).limit(1)
            )
            if notif_check.scalar_one_or_none() is None:
                role_name = next(
                    (r.name for r in user.roles),
                    "用户"
                )
                db.add(_build_welcome_notifications(user.id, username, role_name))
                added_notif += 1
        if added_notif > 0:
            await db.commit()
            logger.info(f"[Seed] 创建 {added_notif} 条欢迎通知")

        # ===== 步骤5：生成演示数据（合同+分析） =====
        # 演示合同（含全文与审查报告）独立幂等生成/修复，不受query_logs门控影响
        await _seed_demo_contracts(db, user_map)
        # 数据分析模拟数据：仅当query_logs表为空时生成，不覆盖真实业务数据
        await _seed_demo_analytics_data(db, user_map)

        logger.info("[Seed] 种子数据初始化完成 ✓")

    except Exception as e:
        # 回滚当前事务，避免脏数据
        await db.rollback()
        # 向上抛出异常，交由 main.py 生命周期中的重试机制处理：
        # - 表未就绪/连接未就绪 → 等待后重试（幂等，可安全重入）
        # - 最终仍失败 → main.py 记录错误但不阻断应用启动
        # （历史缺陷：此处曾直接吞掉异常并仅记日志，导致外层重试失效、
        #   启动日志误报"种子数据初始化完成"，多worker并发时表未就绪即静默失败）
        logger.error(f"[Seed] 种子数据初始化失败: {e}", exc_info=True)
        raise


# ==================== 数据分析模拟数据生成 ====================

# 法律分类及对应示例查询（用于生成符合业务逻辑的QueryLog）
_DEMO_CATEGORIES: list[dict] = [
    {
        "category": "劳动法",
        "queries": [
            "什么是经济补偿金？如何计算？",
            "试用期最长可以是多久？",
            "用人单位可以单方面解除劳动合同吗？",
            "未签订书面劳动合同有什么法律后果？",
            "加班工资如何计算？",
            "年休假天数怎么规定？",
            "工伤认定的流程是什么？",
        ],
    },
    {
        "category": "合同法",
        "queries": [
            "格式条款无效的情形有哪些？",
            "合同违约责任如何承担？",
            "定金和违约金可以同时主张吗？",
            "合同的必要条款包括哪些？",
            "缔约过失责任的构成要件？",
            "合同解除的法定条件是什么？",
            "违约金过高可以请求减少吗？",
        ],
    },
    {
        "category": "知识产权",
        "queries": [
            "商标侵权的认定标准是什么？",
            "专利申请需要哪些材料？",
            "著作权保护期限是多久？",
            "侵犯商业秘密的法律责任？",
            "软件著作权如何登记？",
        ],
    },
    {
        "category": "婚姻家庭",
        "queries": [
            "离婚时财产如何分割？",
            "子女抚养权怎么判？",
            "婚前财产协议有效吗？",
            "彩礼可以要求返还吗？",
            "夫妻共同债务如何认定？",
        ],
    },
    {
        "category": "公司法",
        "queries": [
            "股东出资不足承担什么责任？",
            "公司章程必须包含哪些内容？",
            "股东会决议无效的情形？",
            "有限责任公司的股权转让规则？",
            "公司清算的法定程序是什么？",
        ],
    },
    {
        "category": "侵权责任",
        "queries": [
            "人身损害赔偿包括哪些项目？",
            "网络侵权的责任如何认定？",
            "产品责任由谁承担？",
            "精神损害赔偿的标准？",
            "共同侵权的连带责任？",
        ],
    },
    {
        "category": "刑事辩护",
        "queries": [
            "自首的认定条件是什么？",
            "缓刑的适用条件有哪些？",
            "正当防卫与防卫过当的区别？",
            "取保候审需要什么条件？",
        ],
    },
]


# ==================== 演示合同全文与审查报告生成 ====================

def _build_demo_contract_text(title: str) -> str:
    """构造演示合同全文（按标题适配典型条款，含刻意风险点）

    演示合同必须携带真实感全文，否则合同审查接口会因 content 为空
    抛出"合同内容为空，请先完成解析"（历史缺陷）。

    Args:
        title: 合同标题（如"劳动合同模板审查"）

    Returns:
        合同全文文本（约600字，含2-3处典型风险条款供AI审查识别）
    """
    return (
        f"{title.replace('审查', '')}\n"
        "甲方（用工方/出让方）：上海某某科技有限公司\n"
        "乙方（受让方/承租方）：张三\n\n"
        "第一条 合同期限：本合同有效期为三年，自2026年1月1日起至2028年12月31日止。"
        "试用期为六个月，试用期内乙方工资为转正后工资的70%。\n"
        "第二条 工作内容：乙方担任运营专员岗位，甲方有权根据经营需要随时调整乙方岗位及职责，"
        "乙方应无条件服从。\n"
        "第三条 报酬与支付：甲方于每月30日前支付乙方上月工资，遇特殊情况可适当顺延，"
        "最长顺延时间不超过三个月。\n"
        "第四条 保密义务：乙方在职期间及离职后五年内不得从事与甲方业务相同或相近的工作，"
        "违反本条的，乙方应支付甲方违约金人民币五十万元。\n"
        "第五条 争议解决：因本合同引起的争议，由甲方所在地人民法院管辖，"
        "乙方放弃管辖异议权。\n"
        "第六条 合同解除：甲方可提前三日通知乙方解除本合同，无需说明理由，亦不支付经济补偿。\n"
        "第七条 其他：本合同一式两份，甲方保管正本，乙方保管副本，两份具有同等法律效力。\n"
    )


async def _seed_demo_review_report(db: AsyncSession, contract: Contract) -> None:
    """为演示合同生成完整的审查报告与风险条款（含对抗式审查结果）

    确保"查看报告"开箱即有完整数据展示（评分、三维度、风险条款、
    对抗式审查统计），避免空报告弹窗。

    Args:
        db: 异步数据库会话
        contract: 目标演示合同（须已含content）
    """
    report = ReviewReport(
        contract_id=contract.id,
        overall_score=62.5,
        risk_level=RiskLevel.MEDIUM,
        risk_clause_count=3,
        summary=(
            "该合同整体结构完整，但存在多处对乙方明显不利的条款：试用期超法定上限、"
            "竞业限制违约金过高、工资支付无明确期限约束，建议逐项修订后再行签署。"
        ),
        suggestions='["将试用期缩短至法定上限以内", "降低竞业限制违约金至合理范围", "明确工资支付的具体期限"]',
        # V6.0.4：维度分统一存数值字符串（与contract_service真实审查输出格式一致），
        # 前端parseDimScore直接数值解析展示百分比
        completeness='70.0',
        compliance='55.0',
        consistency='60.0',
        review_duration_ms=8600,
        # 多Agent对抗式审查结果（与真实工作流输出结构一致）
        primary_risks=(
            '[{"clause": "第一条", "risk": "试用期六个月超出法定上限，且试用期工资低于法定下限"},'
            '{"clause": "第四条", "risk": "竞业限制期限五年且违约金五十万元，明显偏高"}]'
        ),
        review_check='{"approved_count": 1, "disputed_count": 2, "missed_count": 0}',
        adverse_opinions=(
            '[{"clause": "第三条", "opinion": "工资最长可顺延三个月，严重侵害劳动者报酬权"},'
            '{"clause": "第六条", "opinion": "解除合同不支付经济补偿，违反《劳动合同法》第四十六条"}]'
        ),
        debate_log='[{"round": 1, "topic": "试用期长度", "resolution": "主审维持风险认定，反方质疑成立"}]',
        unresolved_issues='[{"clause": "第五条", "issue": "管辖约定剥夺乙方异议权，是否有效存在分歧"}]',
        adverse_opinion_count=2,
        unresolved_count=1,
    )
    db.add(report)
    await db.flush()  # 获取report.id以关联风险条款

    # 三条典型风险条款（内容与合同正文条款一一对应）
    clauses = [
        RiskClause(
            report_id=report.id,
            clause_index=1,
            original_text="试用期为六个月，试用期内乙方工资为转正后工资的70%。",
            risk_type="违法条款",
            risk_level=RiskLevel.HIGH,
            risk_score=0.85,
            risk_description="三年期合同法定试用期上限为二个月（劳动合同期限一年以上不满三年的，试用期不得超过二个月），六个月明显违法；试用期工资不得低于转正工资的80%。",
            suggestion="将试用期调整为不超过二个月，试用期工资提高至转正工资的80%以上。",
            legal_basis="《中华人民共和国劳动合同法》第十九条、第二十条",
        ),
        RiskClause(
            report_id=report.id,
            clause_index=2,
            original_text="乙方在职期间及离职后五年内不得从事与甲方业务相同或相近的工作，违反本条的，乙方应支付违约金五十万元。",
            risk_type="权利不对等",
            risk_level=RiskLevel.MEDIUM,
            risk_score=0.62,
            risk_description="竞业限制期限最长不得超过二年，且用人单位须在限制期内按月支付经济补偿；违约金金额过高可能被法院酌减。",
            suggestion="竞业限制期缩短至二年以内，约定按月补偿，违约金与实际损失挂钩。",
            legal_basis="《中华人民共和国劳动合同法》第二十三条、第二十四条",
        ),
        RiskClause(
            report_id=report.id,
            clause_index=3,
            original_text="甲方可提前三日通知乙方解除本合同，无需说明理由，亦不支付经济补偿。",
            risk_type="违法条款",
            risk_level=RiskLevel.CRITICAL,
            risk_score=0.92,
            risk_description="用人单位单方解除须符合法定情形并支付经济补偿，'无理由解除且不补偿'条款因违反法律强制性规定而无效。",
            suggestion="删除该条款，解除情形与补偿严格依照《劳动合同法》执行。",
            legal_basis="《中华人民共和国劳动合同法》第四十六条、第八十七条",
        ),
    ]
    db.add_all(clauses)
    await db.commit()


async def _seed_demo_analytics_data(db: AsyncSession, user_map: dict[str, User]) -> None:
    """生成数据分析模拟数据（幂等：仅当query_logs表为空时执行）

    为数据分析模块的四个子图表提供可视化数据：
    - 热点分析：按分类统计QueryLog
    - 引用统计：基于CitationStat表
    - 趋势分析：按日期聚合QueryLog
    - 用户聚类：基于QueryLog+Contract的用户特征

    生成的数据符合真实业务逻辑：
    - 过去30天分散的查询记录
    - 不同用户有不同的查询偏好和频率
    - 置信度和反馈分数呈正态分布
    - 引用统计与法律文档关联

    Args:
        db: 异步数据库会话
        user_map: 用户名到User对象的映射
    """
    # 幂等检查：仅当query_logs表为空时生成
    count_result = await db.execute(select(func.count(QueryLog.id)))
    existing_count = count_result.scalar() or 0
    if existing_count > 0:
        logger.info(f"[Seed] query_logs已有 {existing_count} 条记录，跳过模拟数据生成")
        return

    # 获取所有用户ID和文档ID
    user_ids = [u.id for u in user_map.values()]
    doc_result = await db.execute(select(LegalDocument.id, LegalDocument.title))
    docs = doc_result.all()
    if not docs or not user_ids:
        logger.info("[Seed] 无用户或文档数据，跳过模拟数据生成")
        return

    logger.info("[Seed] 开始生成数据分析模拟数据...")

    # 使用固定随机种子确保每次生成的数据分布一致
    rng = random.Random(42)

    # ===== 1. 生成QueryLog查询日志（过去30天） =====
    now = datetime.utcnow()
    query_logs: list[QueryLog] = []

    # 为每个用户定义不同的查询偏好（模拟真实用户行为差异）
    # admin: 高频查询，覆盖全部分类（高频法务用户）
    # lawyer: 中频查询，偏重合同法和公司法（合同审查为主用户）
    # user: 低频查询，偏重劳动法和婚姻家庭（法律咨询入门用户）
    user_profiles = {
        "admin": {"weight": 3.0, "categories": None},  # 全部分类
        "lawyer": {"weight": 1.5, "categories": ["合同法", "公司法", "知识产权"]},
        "user": {"weight": 0.8, "categories": ["劳动法", "婚姻家庭", "侵权责任"]},
    }

    for day_offset in range(30):
        day = now - timedelta(days=day_offset)
        # 工作日查询量更高，周末较低
        weekday_factor = 1.0 if day.weekday() < 5 else 0.4

        for username, profile in user_profiles.items():
            user = user_map.get(username)
            if not user:
                continue
            # 每天每用户的基础查询次数 = weight * weekday_factor * 随机波动
            base_count = int(profile["weight"] * weekday_factor * rng.uniform(0.6, 1.4))
            base_count = max(0, base_count)

            # 筛选该用户偏好的分类
            cats = profile["categories"]
            available_cats = _DEMO_CATEGORIES if not cats else [c for c in _DEMO_CATEGORIES if c["category"] in cats]

            for _ in range(base_count):
                cat_info = rng.choice(available_cats)
                query_text = rng.choice(cat_info["queries"])
                # 随机时间（白天为主）
                hour = rng.choices(
                    range(24), weights=[1,1,1,1,1,2,3,5,8,10,10,9,8,9,10,10,9,7,5,4,3,2,2,1]
                )[0]
                minute = rng.randint(0, 59)
                second = rng.randint(0, 59)
                log_time = day.replace(hour=hour, minute=minute, second=second, microsecond=0)

                query_logs.append(QueryLog(
                    user_id=user.id,
                    query_text=query_text,
                    category=cat_info["category"],
                    retrieved_count=rng.randint(3, 15),
                    confidence=round(rng.uniform(0.65, 0.95), 2),
                    latency_ms=rng.randint(3000, 12000),
                    feedback_score=rng.choices([1, 0, -1], weights=[55, 35, 10])[0],
                    is_streaming=rng.choices([0, 1], weights=[20, 80])[0],
                    created_at=log_time,
                ))

    if query_logs:
        db.add_all(query_logs)
        await db.commit()
        logger.info(f"[Seed] 生成 {len(query_logs)} 条QueryLog查询日志")

    # ===== 2. 生成CitationStat引用统计（过去30天，按天聚合） =====
    citation_stats: list[CitationStat] = []
    for doc_id, doc_title in docs:
        for day_offset in range(30):
            day = now - timedelta(days=day_offset)
            # 每篇文档每天被引用1-8次
            cite_count = rng.randint(1, 8) if rng.random() > 0.3 else 0
            if cite_count == 0:
                continue
            stat_date = day.replace(hour=0, minute=0, second=0, microsecond=0)
            positive = int(cite_count * rng.uniform(0.5, 0.85))
            negative = cite_count - positive
            citation_stats.append(CitationStat(
                document_id=doc_id,
                stat_date=stat_date,
                citation_count=cite_count,
                positive_feedback_count=positive,
                negative_feedback_count=negative,
                avg_confidence=round(rng.uniform(0.7, 0.95), 2),
            ))

    if citation_stats:
        db.add_all(citation_stats)
        await db.commit()
        logger.info(f"[Seed] 生成 {len(citation_stats)} 条CitationStat引用统计")

    logger.info("[Seed] 数据分析模拟数据生成完成 ✓")


async def _seed_demo_contracts(db: AsyncSession, user_map: dict[str, User]) -> None:
    """生成/修复演示合同数据（独立于query_logs门控，每次启动均执行）

    历史缺陷：旧版演示合同无content，用户点击"开始审查"触发
    "合同内容为空，请先完成解析"；已审查状态也无对应审查报告。
    本函数负责：
    1. 全新环境：生成带完整合同全文的演示合同（含审查报告+风险条款）
    2. 存量环境：为无content的旧演示合同补齐全文与报告

    幂等设计：以 file_name 前缀 demo_contract_ 作为演示数据标记。

    Args:
        db: 异步数据库会话
        user_map: 用户名到User对象的映射
    """
    rng = random.Random(7)

    # ===== 1. 生成演示合同（仅当无演示合同时） =====
    demo_count_result = await db.execute(
        select(func.count(Contract.id)).where(Contract.file_name.like("demo_contract_%"))
    )
    existing_demos = demo_count_result.scalar() or 0
    if existing_demos == 0:
        contracts: list[Contract] = []
        # admin审查5份，lawyer审查3份，user审查1份
        contract_configs = [
            (user_map.get("admin"), 5),
            (user_map.get("lawyer"), 3),
            (user_map.get("user"), 1),
        ]
        contract_titles = [
            "劳动合同模板审查", "房屋租赁合同审查", "采购合同审查",
            "技术服务协议审查", "保密协议审查", "股权转让协议审查",
            "借款合同审查", "特许经营合同审查", "合作协议审查",
        ]
        for user, count in contract_configs:
            if not user:
                continue
            for i in range(count):
                days_ago = rng.randint(1, 28)
                created = datetime.utcnow() - timedelta(days=days_ago)
                title = rng.choice(contract_titles)
                contracts.append(Contract(
                    user_id=user.id,
                    title=title,
                    file_name=f"demo_contract_{i}.pdf",
                    file_path=f"/uploads/demo_contract_{i}.pdf",
                    file_size=rng.randint(50000, 500000),
                    file_type="pdf",
                    # 演示合同携带真实感合同全文（含典型风险条款），
                    # 确保"开始审查"可直接执行，不再触发"合同内容为空"
                    content=_build_demo_contract_text(title),
                    status=rng.choice([ContractStatus.REVIEWED, ContractStatus.PARSED, ContractStatus.REVIEWED]),
                    contract_type=rng.choice(["劳动合同", "租赁合同", "采购合同", "服务合同"]),
                    created_at=created,
                ))
        if contracts:
            db.add_all(contracts)
            await db.commit()
            logger.info(f"[Seed] 生成 {len(contracts)} 条Contract合同记录（含合同全文）")

            # 为"已审查"状态的演示合同生成完整审查报告+风险条款，
            # 确保"查看报告"开箱即用（否则前端弹窗为全空数据，体验缺陷）
            report_count = 0
            for c in contracts:
                if c.status == ContractStatus.REVIEWED:
                    await _seed_demo_review_report(db, c)
                    report_count += 1
            if report_count:
                logger.info(f"[Seed] 为 {report_count} 份已审查演示合同生成审查报告")

    # ===== 2. 存量演示合同修复（历史版本种子无content导致审查失败） =====
    # 幂等：仅补齐 file_name 匹配演示标记 且 content 为空的记录
    legacy_result = await db.execute(
        select(Contract).where(
            Contract.file_name.like("demo_contract_%"),
            Contract.content.is_(None),
        )
    )
    legacy_contracts = legacy_result.scalars().all()
    for c in legacy_contracts:
        c.content = _build_demo_contract_text(c.title)
        # 已审查但无报告的存量演示合同，同时补生成报告
        if c.status == ContractStatus.REVIEWED:
            has_report = await db.execute(
                select(func.count(ReviewReport.id)).where(ReviewReport.contract_id == c.id)
            )
            if (has_report.scalar() or 0) == 0:
                await _seed_demo_review_report(db, c)
    if legacy_contracts:
        await db.commit()
        logger.info(f"[Seed] 已为 {len(legacy_contracts)} 条存量演示合同补齐合同全文/审查报告")

    # ===== 3. 演示合同报告去重（多worker并发种子保护） =====
    # 4个uvicorn worker并发执行种子逻辑时，check-then-insert存在竞态，
    # 同一演示合同可能生成多份报告。此处保留每份演示合同最新一份报告，
    # 其余连带风险条款一并删除（ON DELETE CASCADE由ORM关系级联，此处SQL显式删除）。
    # 注意：仅对演示合同去重，真实合同允许多份历史报告（重新审查场景）。
    from sqlalchemy import delete
    dup_ids_result = await db.execute(
        select(ReviewReport.contract_id)
        .join(Contract, Contract.id == ReviewReport.contract_id)
        .where(Contract.file_name.like("demo_contract_%"))
        .group_by(ReviewReport.contract_id)
        .having(func.count(ReviewReport.id) > 1)
    )
    dup_contract_ids = [row[0] for row in dup_ids_result.all() if row[0] is not None]
    if dup_contract_ids:
        for cid in dup_contract_ids:
            keep_result = await db.execute(
                select(func.max(ReviewReport.id)).where(ReviewReport.contract_id == cid)
            )
            keep_id = keep_result.scalar()
            # 先删报告的风险条款，再删旧报告（保留最新keep_id）
            await db.execute(
                delete(RiskClause).where(
                    RiskClause.report_id.in_(
                        select(ReviewReport.id).where(
                            ReviewReport.contract_id == cid,
                            ReviewReport.id != keep_id,
                        )
                    )
                )
            )
            await db.execute(
                delete(ReviewReport).where(
                    ReviewReport.contract_id == cid,
                    ReviewReport.id != keep_id,
                )
            )
        await db.commit()
        logger.info(f"[Seed] 已对 {len(dup_contract_ids)} 份演示合同审查报告去重（各保留最新一份）")


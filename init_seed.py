"""
智法通 - 数据库初始化种子数据

插入初始用户、角色、权限、法律文档、查询日志等数据，
确保所有API端点都能正常工作。
"""
import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# 添加backend目录到路径
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_dir)

# 切换到backend目录，确保.env文件能被正确加载
os.chdir(backend_dir)

from app.database import engine, async_session_factory as AsyncSessionLocal
from app.models.user import User, Role, Permission, user_role, role_permission
from app.models.knowledge import LegalDocument, DocumentChunk, DocumentStatus, DocumentSource
from app.models.analysis import QueryLog, CitationStat
from app.models.qa import Conversation, Message, MessageRole, ConversationStatus
from app.models.contract import Contract, ContractStatus
from app.utils.security import hash_password
from sqlalchemy import select, insert


async def init_seed_data():
    """初始化种子数据"""
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("  智法通 - 数据库种子数据初始化")
        print("=" * 60)

        # 1. 创建角色
        print("\n📝 创建角色...")
        roles_data = [
            {"name": "超级管理员", "code": "admin", "description": "系统超级管理员，拥有所有权限", "is_default": False},
            {"name": "律师", "code": "lawyer", "description": "法律专业人士，可使用所有法律工具", "is_default": False},
            {"name": "普通用户", "code": "user", "description": "普通注册用户，可使用基础功能", "is_default": True},
        ]
        role_map = {}
        for r in roles_data:
            role = Role(**r)
            db.add(role)
            await db.flush()
            role_map[r["code"]] = role
            print(f"  ✅ 角色: {r['name']} (ID: {role.id})")

        # 2. 创建权限
        print("\n🔑 创建权限...")
        permissions_data = [
            {"name": "用户管理", "code": "user:manage", "resource": "user", "action": "manage", "description": "管理用户"},
            {"name": "提问", "code": "qa:ask", "resource": "qa", "action": "ask", "description": "法律提问"},
            {"name": "合同上传", "code": "contract:upload", "resource": "contract", "action": "upload", "description": "上传合同"},
            {"name": "合同审查", "code": "contract:review", "resource": "contract", "action": "review", "description": "审查合同"},
            {"name": "知识库管理", "code": "knowledge:manage", "resource": "knowledge", "action": "manage", "description": "管理知识库"},
            {"name": "数据分析", "code": "analysis:view", "resource": "analysis", "action": "view", "description": "查看分析"},
        ]
        perm_map = {}
        for p in permissions_data:
            perm = Permission(**p)
            db.add(perm)
            await db.flush()
            perm_map[p["code"]] = perm

        # 给admin角色所有权限
        for perm in perm_map.values():
            await db.execute(
                insert(role_permission).values(role_id=role_map["admin"].id, permission_id=perm.id)
            )
        # 给lawyer角色部分权限
        for code in ["qa:ask", "contract:upload", "contract:review", "knowledge:manage", "analysis:view"]:
            await db.execute(
                insert(role_permission).values(role_id=role_map["lawyer"].id, permission_id=perm_map[code].id)
            )
        # 给user角色基础权限（仅个人使用功能，不含数据分析/知识库管理）
        for code in ["qa:ask", "contract:upload", "contract:review"]:
            await db.execute(
                insert(role_permission).values(role_id=role_map["user"].id, permission_id=perm_map[code].id)
            )
        print(f"  ✅ 创建 {len(permissions_data)} 个权限并分配给角色")

        # 3. 创建用户
        print("\n👤 创建用户...")
        users_data = [
            {
                "username": "admin",
                "email": "admin@zhifatong.com",
                "password": "admin123",
                "phone": "13800000001",
                "is_superuser": True,
                "role_code": "admin",
            },
            {
                "username": "lawyer",
                "email": "lawyer@zhifatong.com",
                "password": "lawyer123",
                "phone": "13800000002",
                "role_code": "lawyer",
            },
            {
                "username": "user",
                "email": "user@zhifatong.com",
                "password": "user123456",
                "phone": "13800000003",
                "role_code": "user",
            },
        ]
        user_map = {}
        for u in users_data:
            user = User(
                username=u["username"],
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                phone=u["phone"],
                is_superuser=u.get("is_superuser", False),
                is_active=True,
            )
            db.add(user)
            await db.flush()
            user_map[u["username"]] = user
            # 分配角色
            await db.execute(
                insert(user_role).values(user_id=user.id, role_id=role_map[u["role_code"]].id)
            )
            print(f"  ✅ 用户: {u['username']} (ID: {user.id}) 密码: {u['password']}")

        # 4. 创建法律文档（知识库）
        print("\n📚 创建法律文档...")
        documents_data = [
            {
                "title": "中华人民共和国民法典第一编总则",
                "doc_type": "法律",
                "content": """第一条 为了保护民事主体的合法权益，调整民事关系，维护社会和经济秩序，适应中国特色社会主义发展要求，弘扬社会主义核心价值观，根据宪法，制定本法。

第二条 民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。

第三条 民事主体的人身权利、财产权利以及其他合法权益受法律保护，任何组织或者个人不得侵犯。

第四条 民事主体在民事活动中的法律地位一律平等。

第五条 民事主体从事民事活动，应当遵循自愿原则，按照自己的意思设立、变更、终止民事法律关系。

第六条 民事主体从事民事活动，应当遵循公平原则，合理确定各方的权利和义务。

第七条 民事主体从事民事活动，应当遵循诚信原则，秉持诚实，恪守承诺。

第八条 民事主体从事民事活动，不得违反法律，不得违背公序良俗。""",
                "summary": "民法典总则编基本原则规定",
                "tags": json.dumps(["民法典", "总则", "基本原则"], ensure_ascii=False),
            },
            {
                "title": "中华人民共和国劳动合同法",
                "doc_type": "法律",
                "content": """第一条 为了完善劳动合同制度，明确劳动合同双方当事人的权利和义务，保护劳动者的合法权益，构建和发展和谐稳定的劳动关系，制定本法。

第二条 中华人民共和国境内的企业、个体经济组织、民办非企业单位等组织（以下称用人单位）与劳动者建立劳动关系，订立、履行、变更、解除或者终止劳动合同，适用本法。

第三条 订立劳动合同，应当遵循合法、公平、平等自愿、协商一致、诚实信用的原则。

第四十七条 经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付。六个月以上不满一年的，按一年计算；不满六个月的，向劳动者支付半个月工资的经济补偿。

第八十二条 用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应当向劳动者每月支付二倍的工资。""",
                "summary": "劳动合同法关于劳动合同订立、解除和经济补偿的规定",
                "tags": json.dumps(["劳动合同法", "经济补偿", "劳动法"], ensure_ascii=False),
            },
            {
                "title": "中华人民共和国合同编",
                "doc_type": "法律",
                "content": """第四百六十四条 合同是民事主体之间设立、变更、终止民事法律关系的协议。婚姻、收养、监护等有关身份关系的协议，适用有关该身份关系的法律规定；没有规定的，可以根据其性质参照适用本编规定。

第四百六十五条 依法成立的合同，受法律保护。依法成立的合同，仅对当事人具有法律约束力，但是法律另有规定的除外。

第四百六十六条 当事人对合同条款的理解有争议的，应当依据本法第一百四十二条第一款的规定，确定争议条款的含义。

第四百九十六条 格式条款是当事人为了重复使用而预先拟定，并在订立合同时未与对方协商的条款。采用格式条款订立合同的，提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务，并采取合理的方式提示对方注意免除或者减轻其责任等与对方有重大利害关系的条款，按照对方的要求，对该条款予以说明。

第四百九十七条 有下列情形之一的，该格式条款无效：（一）具有本法第一编、第三编规定的合同无效情形；（二）提供格式条款一方不合理地免除或者减轻其责任、加重对方责任、限制对方主要权利；（三）提供格式条款一方排除对方主要权利。""",
                "summary": "合同编关于合同定义、格式条款的规定",
                "tags": json.dumps(["合同法", "格式条款", "民法典"], ensure_ascii=False),
            },
            {
                "title": "中华人民共和国消费者权益保护法",
                "doc_type": "法律",
                "content": """第二条 消费者为生活消费需要购买、使用商品或者接受服务，其权益受本法保护；本法未作规定的，受其他有关法律、法规保护。

第三条 经营者为消费者提供其生产、销售的商品或者提供服务，应当遵守本法；本法未作规定的，应当遵守其他有关法律、法规。

第四条 经营者与消费者进行交易，应当遵循自愿、平等、公平、诚实信用的原则。

第二十六条 经营者在经营活动中使用格式条款的，应当以显著方式提请消费者注意商品或者服务的数量和质量、价款或者费用、履行期限和方式、安全注意事项和风险警示、售后服务、民事责任等与消费者有重大利害关系的内容，并按照消费者的要求予以说明。

经营者不得以格式条款、通知、声明、店堂告示等方式，作出排除或者限制消费者权利、减轻或者免除经营者责任、加重消费者责任等对消费者不公平、不合理的规定，不得利用格式条款并借助技术手段强制交易。

格式条款、通知、声明、店堂告示等含有前款所列内容的，其内容无效。""",
                "summary": "消费者权益保护法关于格式条款的规定",
                "tags": json.dumps(["消费者权益", "格式条款", "消费者保护"], ensure_ascii=False),
            },
            {
                "title": "房屋租赁合同示范模板",
                "doc_type": "合同模板",
                "content": """房屋租赁合同

出租方（甲方）：____________
承租方（乙方）：____________

第一条 房屋基本情况
甲方将位于____________的房屋出租给乙方使用。房屋建筑面积____平方米，房屋用途为____。

第二条 租赁期限
租赁期限为____年，自____年__月__日起至____年__月__日止。

第三条 租金及支付方式
月租金为人民币____元，乙方应于每月__日前支付当月租金。

第四条 押金
乙方应于合同签订时支付押金人民币____元，租赁期满或合同解除后，除扣除应由乙方承担的费用外，押金应于房屋交还后__日内退还乙方。

第五条 双方权利义务
甲方应保证房屋适合居住，乙方应按时支付租金并合理使用房屋。

第六条 违约责任
任何一方违反合同约定，应向守约方承担违约责任。

第七条 争议解决
本合同履行过程中发生争议，双方应协商解决；协商不成的，可向房屋所在地人民法院起诉。""",
                "summary": "房屋租赁合同标准模板，包含基本条款",
                "tags": json.dumps(["租赁合同", "房屋租赁", "模板"], ensure_ascii=False),
            },
        ]

        doc_map = {}
        for d in documents_data:
            doc = LegalDocument(
                title=d["title"],
                doc_type=d["doc_type"],
                source=DocumentSource.MANUAL,
                content=d["content"],
                summary=d["summary"],
                status=DocumentStatus.COMPLETED,
                indexing_progress=100,
                chunk_count=3,
                tags=d["tags"],
                uploaded_by=user_map["admin"].id,
                is_effective=True,
                publish_date=datetime(2021, 1, 1),
            )
            db.add(doc)
            await db.flush()
            doc_map[d["title"]] = doc

            # 创建分块
            content = d["content"]
            chunks = [content[i:i+300] for i in range(0, len(content), 300)]
            for idx, chunk_text in enumerate(chunks):
                chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk_text,
                    vector_id=f"doc_{doc.id}_chunk_{idx}",
                    token_count=len(chunk_text),
                    start_char=idx * 300,
                    end_char=idx * 300 + len(chunk_text),
                )
                db.add(chunk)
            doc.chunk_count = len(chunks)
            print(f"  ✅ 文档: {d['title']} (ID: {doc.id}, {len(chunks)}个分块)")

        # 5. 创建查询日志（用于热点分析和趋势）
        print("\n📊 创建查询日志...")
        categories = ["劳动法", "合同法", "民法典", "消费者权益", "知识产权"]
        sample_queries = [
            ("劳动合同解除后经济补偿金如何计算？", "劳动法", 0.92, 1),
            ("什么是格式条款？哪些格式条款无效？", "合同法", 0.88, 1),
            ("房屋租赁合同中承租人的权利有哪些？", "合同法", 0.85, 1),
            ("买卖合同中标的物风险何时转移？", "合同法", 0.90, 0),
            ("消费者权益保护法中的七天无理由退货", "消费者权益", 0.87, 1),
            ("民法典中关于违约责任的规定", "民法典", 0.91, 0),
            ("劳动合同法关于试用期规定", "劳动法", 0.86, 1),
            ("格式条款的效力如何认定？", "合同法", 0.89, 0),
            ("知识产权侵权的赔偿标准", "知识产权", 0.84, 0),
            ("消费者权益保护法惩罚性赔偿", "消费者权益", 0.88, 1),
            ("民法典合同编的适用范围", "民法典", 0.90, 1),
            ("劳动合同解除的法定情形", "劳动法", 0.92, 1),
            ("租赁合同中押金退还的法律规定", "合同法", 0.85, 0),
            ("格式合同与格式条款的区别", "合同法", 0.87, 1),
            ("消费者知情权的法律保护", "消费者权益", 0.86, 0),
        ]

        now = datetime.utcnow()
        for i, (query, category, confidence, feedback) in enumerate(sample_queries):
            # 分散在过去30天
            days_ago = i % 30
            created = now - timedelta(days=days_ago, hours=i % 24)
            log = QueryLog(
                user_id=user_map["admin"].id if i % 3 == 0 else user_map["user"].id,
                query_text=query,
                rewritten_query=query,
                category=category,
                sub_queries=json.dumps([query], ensure_ascii=False),
                retrieved_count=5,
                confidence=confidence,
                self_eval_score=confidence,
                is_streaming=i % 2,
                latency_ms=1500 + i * 100,
                feedback_score=feedback,
                client_ip="127.0.0.1",
                user_agent="Mozilla/5.0",
                created_at=created,
            )
            db.add(log)
        print(f"  ✅ 创建 {len(sample_queries)} 条查询日志")

        # 6. 创建引用统计
        print("\n📈 创建引用统计...")
        doc_list = list(doc_map.values())
        for i, doc in enumerate(doc_list):
            for day_offset in range(7):
                stat = CitationStat(
                    document_id=doc.id,
                    chunk_id=None,
                    stat_date=now - timedelta(days=day_offset),
                    citation_count=10 - i * 2 + day_offset,
                    positive_feedback_count=6 - i + day_offset // 2,
                    negative_feedback_count=2 - i // 2 if i < 4 else 0,
                    avg_confidence=0.85 + i * 0.02,
                )
                db.add(stat)
        print(f"  ✅ 创建 {len(doc_list) * 7} 条引用统计")

        # 7. 创建示例对话
        print("\n💬 创建示例对话...")
        conversation = Conversation(
            user_id=user_map["admin"].id,
            title="劳动合同经济补偿金咨询",
            status=ConversationStatus.ACTIVE,
            message_count=2,
        )
        db.add(conversation)
        await db.flush()

        msg1 = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="劳动合同解除后经济补偿金如何计算？",
        )
        db.add(msg1)
        await db.flush()

        msg2 = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="""根据《中华人民共和国劳动合同法》第四十七条的规定，经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付。

具体计算规则：
1. 工作满一年：支付一个月工资的经济补偿
2. 工作六个月以上不满一年：按一年计算，支付一个月工资
3. 工作不满六个月：支付半个月工资的经济补偿

月工资是指劳动者在劳动合同解除或者终止前十二个月的平均工资。

需要注意的是，劳动者月工资高于用人单位所在直辖市、设区的市级人民政府公布的本地区上年度职工月平均工资三倍的，向其支付经济补偿的标准按职工月平均工资三倍的数额支付，向其支付经济补偿的年限最高不超过十二年。""",
            citations=json.dumps([
                {"document_id": doc_map["中华人民共和国劳动合同法"].id, "title": "中华人民共和国劳动合同法", "article": "第四十七条"}
            ], ensure_ascii=False),
            confidence=0.92,
            latency_ms=2500,
            token_count=350,
        )
        db.add(msg2)
        print(f"  ✅ 创建示例对话 (ID: {conversation.id})")

        # 8. 创建示例合同
        print("\n📋 创建示例合同...")
        contract = Contract(
            user_id=user_map["admin"].id,
            title="示例房屋租赁合同",
            file_name="sample_contract.txt",
            file_path="uploads/sample_contract.txt",
            file_size=1024,
            file_type="txt",
            content="""房屋租赁合同
出租方（甲方）：张三
承租方（乙方）：李四
第一条 租赁物：甲方将位于某市某区的房屋出租给乙方使用。
第二条 租赁期限：一年，自2024年1月1日起至2024年12月31日止。
第三条 租金：月租金为人民币5000元。
第四条 甲方可以随时解除合同，无需承担任何违约责任。
第五条 本合同最终解释权归甲方所有。""",
            status=ContractStatus.REVIEWED,
            contract_type="租赁合同",
            amount=60000.0,
            party_a="张三",
            party_b="李四",
        )
        db.add(contract)
        print(f"  ✅ 创建示例合同 (ID: {contract.id})")

        # ==================== 创建通知种子数据 ====================
        from app.models.notification import Notification, NotificationType

        # 检查通知是否已存在
        existing_notif = await db.execute(select(Notification).limit(1))
        if existing_notif.scalar_one_or_none():
            print("  ℹ️  通知数据已存在，跳过创建")
        else:
            now = datetime.utcnow()
            admin_id = user_map["admin"].id
            lawyer_id = user_map["lawyer"].id
            user_id = user_map["user"].id
            notifications_data = [
                # admin的通知
                Notification(user_id=admin_id, type=NotificationType.SYSTEM, title="欢迎使用智法通平台",
                    content="您已成功登录智法通企业级智能法律顾问平台，如有问题请随时联系客服。", is_read=False, created_at=now - timedelta(hours=1)),
                Notification(user_id=admin_id, type=NotificationType.LEGAL_UPDATE, title="《民法典》司法解释更新",
                    content="最高人民法院发布最新民法典司法解释，涉及合同编若干问题的解释，建议及时学习。", is_read=False, created_at=now - timedelta(hours=3)),
                Notification(user_id=admin_id, type=NotificationType.CONTRACT, title="合同审查完成",
                    content="《技术服务协议》已完成AI智能审查，检测到3处风险条款，请及时查看。", is_read=True, created_at=now - timedelta(days=1)),
                Notification(user_id=admin_id, type=NotificationType.WARNING, title="风险预警",
                    content="系统检测到知识库中有2份文档即将过期，请及时更新。", is_read=False, created_at=now - timedelta(days=2)),
                # lawyer的通知
                Notification(user_id=lawyer_id, type=NotificationType.SYSTEM, title="新案件分配",
                    content="您有一份新的合同审查任务待处理，客户：某某科技有限公司。", is_read=False, created_at=now - timedelta(minutes=30)),
                Notification(user_id=lawyer_id, type=NotificationType.QA, title="用户咨询待回复",
                    content="有用户提交了关于劳动法方面的法律咨询，请尽快查看并回复。", is_read=False, created_at=now - timedelta(hours=2)),
                Notification(user_id=lawyer_id, type=NotificationType.LEGAL_UPDATE, title="新法规发布",
                    content="《个人信息保护法》实施细则已发布，请及时学习了解。", is_read=True, created_at=now - timedelta(days=1)),
                # user的通知
                Notification(user_id=user_id, type=NotificationType.SYSTEM, title="注册成功",
                    content="欢迎加入智法通平台！您现在可以使用智能法律问答、合同审查等功能。", is_read=False, created_at=now - timedelta(hours=2)),
                Notification(user_id=user_id, type=NotificationType.QA, title="您的咨询已回复",
                    content="您关于劳动合同的问题，律师已给出专业解答，请查看。", is_read=False, created_at=now - timedelta(hours=5)),
                Notification(user_id=user_id, type=NotificationType.CONTRACT, title="合同审查报告已生成",
                    content="您提交的合同文件审查完毕，已生成详细风险报告。", is_read=True, created_at=now - timedelta(days=1)),
            ]
            for n in notifications_data:
                db.add(n)
            print(f"  ✅ 创建 {len(notifications_data)} 条通知数据")

        # 提交所有更改
        await db.commit()
        print("\n" + "=" * 60)
        print("  ✅ 种子数据初始化完成！")
        print("=" * 60)
        print("\n登录账号：")
        print("  管理员: admin / admin123")
        print("  律师:   lawyer / lawyer123")
        print("  用户:   user / user123456")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(init_seed_data())

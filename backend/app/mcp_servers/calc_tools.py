"""
法律计算工具MCP服务器

提供法律相关的计算功能，支持：
- 经济补偿金计算（N/N+1/2N规则）
- 违约金计算
- 损害赔偿计算
- 利息计算（LPR基准）
- 诉讼时效计算
"""

from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ============================================================
# 常量配置
# ============================================================

# 2024年最新LPR利率（一年期和五年期以上）
# 实际项目中应从央行官网动态获取
LPR_ONE_YEAR = 3.10  # 一年期LPR年利率（%）
LPR_FIVE_YEAR = 3.60  # 五年期以上LPR年利率（%）

# LPR更新日期
LPR_UPDATE_DATE = "2024-10-21"

# 民间借贷利率上限：LPR四倍
PRIVATE_LENDING_RATE_CAP_MULTIPLIER = 4

# 创建FastAPI应用实例
app = FastAPI(
    title="法律计算工具MCP服务器",
    description="提供经济补偿金、违约金、损害赔偿、利息等法律计算服务",
    version="1.0.0",
)


# ============================================================
# 数据模型定义
# ============================================================

class CompensationRequest(BaseModel):
    """经济补偿金计算请求模型"""
    monthly_salary: float = Field(..., description="月工资（元），指劳动合同解除或终止前12个月的平均工资", gt=0)
    work_years: float = Field(..., description="工作年限（支持0.5表示半年）", ge=0)
    local_avg_salary: Optional[float] = Field(None, description="当地上年度职工月平均工资（元），用于判断三倍上限")
    compensation_type: str = Field(
        "N",
        description="补偿类型：N（经济补偿）、N+1（额外一个月代通知金）、2N（违法解除赔偿金）",
    )


class InterestRequest(BaseModel):
    """利息计算请求模型"""
    principal: float = Field(..., description="本金（元）", gt=0)
    start_date: str = Field(..., description="起算日期，格式YYYY-MM-DD")
    end_date: str = Field(..., description="截止日期，格式YYYY-MM-DD")
    rate_type: str = Field(
        "LPR",
        description="利率类型：LPR（贷款市场报价利率）、fixed（固定利率）、LPR_multiple（LPR倍数）",
    )
    rate_value: Optional[float] = Field(
        None,
        description="利率值：固定利率时填年利率（如5.0表示5%）；LPR_multiple时填倍数（如4表示4倍LPR）",
    )
    lpr_term: str = Field("one_year", description="LPR期限：one_year（一年期）或 five_year（五年期以上）")


class CompensationResult(BaseModel):
    """经济补偿金计算结果模型"""
    compensation_type: str = Field(..., description="补偿类型")
    monthly_salary: float = Field(..., description="计算基数月工资")
    work_years: float = Field(..., description="工作年限")
    salary_capped: bool = Field(False, description="月工资是否受三倍上限限制")
    capped_salary: Optional[float] = Field(None, description="三倍上限后的月工资")
    compensation_months: float = Field(..., description="补偿月数")
    total_compensation: float = Field(..., description="补偿总额（元）")
    calculation_detail: str = Field(..., description="计算过程说明")


class InterestResult(BaseModel):
    """利息计算结果模型"""
    principal: float = Field(..., description="本金")
    annual_rate: float = Field(..., description="年利率（%）")
    days: int = Field(..., description="计息天数")
    interest: float = Field(..., description="利息金额（元）")
    total_amount: float = Field(..., description="本息合计（元）")
    calculation_detail: str = Field(..., description="计算过程说明")


class DamageCalculationRequest(BaseModel):
    """损害赔偿计算请求模型"""
    damage_type: str = Field(
        ...,
        description="损害类型：personal_injury（人身损害）、property_damage（财产损害）、contract_breach（违约损害）",
    )
    medical_expenses: Optional[float] = Field(None, description="医疗费（元）")
    nursing_expenses: Optional[float] = Field(None, description="护理费（元）")
    lost_income: Optional[float] = Field(None, description="误工费（元）")
    other_expenses: Optional[float] = Field(None, description="其他费用（元）")
    property_value: Optional[float] = Field(None, description="财产价值（元）")
    contract_amount: Optional[float] = Field(None, description="合同金额（元）")
    expected_profit: Optional[float] = Field(None, description="可得利益损失（元）")


class DamageCalculationResult(BaseModel):
    """损害赔偿计算结果模型"""
    damage_type: str = Field(..., description="损害类型")
    items: list[dict] = Field(default_factory=list, description="赔偿项目明细")
    total_damage: float = Field(..., description="赔偿总额（元）")
    calculation_detail: str = Field(..., description="计算过程说明")


# ============================================================
# 经济补偿金计算逻辑
# ============================================================

def calculate_economic_compensation(
    monthly_salary: float,
    work_years: float,
    local_avg_salary: Optional[float] = None,
    compensation_type: str = "N",
) -> CompensationResult:
    """
    计算经济补偿金

    规则说明：
    - N：经济补偿金 = 月工资 × 工作年限
      每满一年支付一个月工资；6个月以上不满1年按1年算；不满6个月支付半个月工资
    - N+1：经济补偿金 + 代通知金（额外一个月工资）
    - 2N：违法解除赔偿金 = 经济补偿金 × 2

    月工资三倍上限：
      当月工资高于当地职工月平均工资3倍时，按3倍计算，且年限最高不超过12年

    Args:
        monthly_salary: 月工资
        work_years: 工作年限
        local_avg_salary: 当地职工月平均工资
        compensation_type: 补偿类型 N/N+1/2N

    Returns:
        补偿金计算结果
    """
    salary_capped = False
    capped_salary = monthly_salary
    max_years = work_years  # 默认不限制年限

    # 判断月工资是否超过当地平均工资3倍
    if local_avg_salary and monthly_salary > local_avg_salary * 3:
        salary_capped = True
        capped_salary = local_avg_salary * 3
        max_years = min(work_years, 12)  # 年限最高不超过12年

    # 计算补偿月数
    # 不满6个月按0.5计算，6个月以上不满1年按1计算
    integer_years = int(max_years)
    decimal_part = max_years - integer_years

    if decimal_part < 0.5 and decimal_part > 0:
        compensation_months = integer_years + 0.5
    elif decimal_part >= 0.5:
        compensation_months = integer_years + 1
    else:
        compensation_months = integer_years

    # 根据补偿类型计算总额
    base_compensation = capped_salary * compensation_months

    if compensation_type == "N":
        total = base_compensation
        detail = (
            f"经济补偿金（N）：月工资 {capped_salary:.2f}元 × 补偿月数 {compensation_months}个月 "
            f"= {total:.2f}元"
        )
    elif compensation_type == "N+1":
        total = base_compensation + capped_salary  # 额外一个月代通知金
        detail = (
            f"经济补偿金（N+1）：月工资 {capped_salary:.2f}元 × 补偿月数 {compensation_months}个月 "
            f"+ 代通知金 {capped_salary:.2f}元 = {total:.2f}元"
        )
    elif compensation_type == "2N":
        total = base_compensation * 2
        detail = (
            f"违法解除赔偿金（2N）：月工资 {capped_salary:.2f}元 × 补偿月数 {compensation_months}个月 "
            f"× 2 = {total:.2f}元"
        )
    else:
        raise ValueError(f"不支持的补偿类型：{compensation_type}")

    # 添加三倍上限说明
    if salary_capped:
        detail = (
            f"[注意] 月工资 {monthly_salary:.2f}元 超过当地平均工资3倍 "
            f"({local_avg_salary:.2f}元 × 3 = {local_avg_salary * 3:.2f}元)，"
            f"按三倍上限 {capped_salary:.2f}元 计算，年限最高不超过12年。\n"
            + detail
        )

    return CompensationResult(
        compensation_type=compensation_type,
        monthly_salary=monthly_salary,
        work_years=work_years,
        salary_capped=salary_capped,
        capped_salary=capped_salary if salary_capped else None,
        compensation_months=compensation_months,
        total_compensation=round(total, 2),
        calculation_detail=detail,
    )


# ============================================================
# 利息计算逻辑
# ============================================================

def calculate_interest_amount(
    principal: float,
    start_date: str,
    end_date: str,
    rate_type: str = "LPR",
    rate_value: Optional[float] = None,
    lpr_term: str = "one_year",
) -> InterestResult:
    """
    计算利息

    支持三种利率类型：
    - LPR：使用贷款市场报价利率
    - fixed：使用固定利率
    - LPR_multiple：使用LPR的倍数（如4倍LPR，用于民间借贷利率上限）

    计算公式：利息 = 本金 × 年利率 × 天数 / 365

    Args:
        principal: 本金
        start_date: 起算日期
        end_date: 截止日期
        rate_type: 利率类型
        rate_value: 利率值或倍数
        lpr_term: LPR期限

    Returns:
        利息计算结果
    """
    # 解析日期
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    if end <= start:
        raise ValueError("截止日期必须晚于起算日期")

    # 计算天数
    days = (end - start).days

    # 确定年利率
    if rate_type == "LPR":
        annual_rate = LPR_ONE_YEAR if lpr_term == "one_year" else LPR_FIVE_YEAR
        rate_desc = f"{'一年期' if lpr_term == 'one_year' else '五年期以上'}LPR {annual_rate}%"
    elif rate_type == "fixed":
        if rate_value is None:
            raise ValueError("固定利率类型必须提供rate_value")
        annual_rate = rate_value
        rate_desc = f"固定年利率 {annual_rate}%"
    elif rate_type == "LPR_multiple":
        if rate_value is None:
            raise ValueError("LPR倍数类型必须提供rate_value（倍数）")
        base_rate = LPR_ONE_YEAR if lpr_term == "one_year" else LPR_FIVE_YEAR
        annual_rate = base_rate * rate_value
        rate_desc = f"{rate_value}倍{'一年期' if lpr_term == 'one_year' else '五年期以上'}LPR（{base_rate}% × {rate_value} = {annual_rate}%）"
    else:
        raise ValueError(f"不支持的利率类型：{rate_type}")

    # 计算利息：本金 × 年利率 × 天数 / 365
    interest = principal * (annual_rate / 100) * days / 365
    total_amount = principal + interest

    detail = (
        f"利息计算：本金 {principal:.2f}元 × 年利率 {annual_rate}% × {days}天 / 365天 "
        f"= {interest:.2f}元\n"
        f"利率依据：{rate_desc}（LPR更新日期：{LPR_UPDATE_DATE}）\n"
        f"本息合计：{principal:.2f} + {interest:.2f} = {total_amount:.2f}元"
    )

    return InterestResult(
        principal=principal,
        annual_rate=annual_rate,
        days=days,
        interest=round(interest, 2),
        total_amount=round(total_amount, 2),
        calculation_detail=detail,
    )


# ============================================================
# 损害赔偿计算逻辑
# ============================================================

def calculate_damage(request: DamageCalculationRequest) -> DamageCalculationResult:
    """
    计算损害赔偿

    支持三种损害类型：
    - 人身损害：医疗费 + 护理费 + 误工费 + 其他费用
    - 财产损害：财产价值（按损失发生时市场价格计算）
    - 违约损害：合同金额相关损失 + 可得利益损失

    Args:
        request: 损害赔偿计算请求

    Returns:
        损害赔偿计算结果
    """
    items: list[dict] = []
    total = 0.0

    if request.damage_type == "personal_injury":
        # 人身损害赔偿
        if request.medical_expenses:
            items.append({"项目": "医疗费", "金额": request.medical_expenses})
            total += request.medical_expenses
        if request.nursing_expenses:
            items.append({"项目": "护理费", "金额": request.nursing_expenses})
            total += request.nursing_expenses
        if request.lost_income:
            items.append({"项目": "误工费", "金额": request.lost_income})
            total += request.lost_income
        if request.other_expenses:
            items.append({"项目": "其他费用", "金额": request.other_expenses})
            total += request.other_expenses

        detail = (
            f"人身损害赔偿计算（依据民法典第1179条）：\n"
            + "\n".join(f"  {item['项目']}：{item['金额']:.2f}元" for item in items)
            + f"\n赔偿总额：{total:.2f}元"
        )

    elif request.damage_type == "property_damage":
        # 财产损害赔偿
        if request.property_value:
            items.append({"项目": "财产损失", "金额": request.property_value})
            total += request.property_value

        detail = (
            f"财产损害赔偿计算（依据民法典第1184条）：\n"
            f"  财产损失（按损失发生时市场价格）：{total:.2f}元\n"
            f"赔偿总额：{total:.2f}元"
        )

    elif request.damage_type == "contract_breach":
        # 违约损害赔偿
        if request.other_expenses:
            items.append({"项目": "实际损失", "金额": request.other_expenses})
            total += request.other_expenses
        if request.expected_profit:
            items.append({"项目": "可得利益损失", "金额": request.expected_profit})
            total += request.expected_profit

        detail = (
            f"违约损害赔偿计算（依据民法典第584条）：\n"
            + "\n".join(f"  {item['项目']}：{item['金额']:.2f}元" for item in items)
            + f"\n赔偿总额：{total:.2f}元\n"
            f"注意：赔偿总额不得超过违约方订立合同时预见到或应当预见到的因违约可能造成的损失"
        )
    else:
        raise ValueError(f"不支持的损害类型：{request.damage_type}")

    return DamageCalculationResult(
        damage_type=request.damage_type,
        items=items,
        total_damage=round(total, 2),
        calculation_detail=detail,
    )


# ============================================================
# MCP工具定义（OpenAI Function Calling格式）
# ============================================================

CALCULATE_COMPENSATION_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_compensation",
        "description": "计算经济补偿金/赔偿金。支持N（经济补偿）、N+1（含代通知金）、2N（违法解除赔偿金）三种计算方式。",
        "parameters": {
            "type": "object",
            "properties": {
                "monthly_salary": {
                    "type": "number",
                    "description": "月工资（元），指劳动合同解除或终止前12个月的平均工资"
                },
                "work_years": {
                    "type": "number",
                    "description": "工作年限，支持0.5表示半年"
                },
                "local_avg_salary": {
                    "type": "number",
                    "description": "当地上年度职工月平均工资（元），用于判断三倍上限"
                },
                "compensation_type": {
                    "type": "string",
                    "description": "补偿类型：N（经济补偿）、N+1（额外一个月代通知金）、2N（违法解除赔偿金）",
                    "enum": ["N", "N+1", "2N"],
                    "default": "N"
                }
            },
            "required": ["monthly_salary", "work_years"]
        }
    }
}

CALCULATE_INTEREST_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_interest",
        "description": "计算利息。支持LPR基准利率、固定利率、LPR倍数三种利率计算方式，适用于借贷纠纷利息计算。",
        "parameters": {
            "type": "object",
            "properties": {
                "principal": {
                    "type": "number",
                    "description": "本金（元）"
                },
                "start_date": {
                    "type": "string",
                    "description": "起算日期，格式YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "截止日期，格式YYYY-MM-DD"
                },
                "rate_type": {
                    "type": "string",
                    "description": "利率类型：LPR（贷款市场报价利率）、fixed（固定利率）、LPR_multiple（LPR倍数）",
                    "enum": ["LPR", "fixed", "LPR_multiple"],
                    "default": "LPR"
                },
                "rate_value": {
                    "type": "number",
                    "description": "利率值：固定利率时填年利率（如5.0表示5%）；LPR_multiple时填倍数（如4表示4倍LPR）"
                },
                "lpr_term": {
                    "type": "string",
                    "description": "LPR期限：one_year（一年期）或 five_year（五年期以上）",
                    "enum": ["one_year", "five_year"],
                    "default": "one_year"
                }
            },
            "required": ["principal", "start_date", "end_date"]
        }
    }
}

# 工具列表
TOOLS = [CALCULATE_COMPENSATION_TOOL, CALCULATE_INTEREST_TOOL]


# ============================================================
# API路由
# ============================================================

@app.get("/tools", summary="获取工具列表")
async def get_tools():
    """返回当前MCP服务器提供的所有工具定义"""
    return {"tools": TOOLS}


@app.post("/tools/calculate_compensation", summary="计算经济补偿金")
async def calculate_compensation_api(request: CompensationRequest) -> CompensationResult:
    """
    计算经济补偿金/赔偿金工具

    支持三种计算方式：
    - N：经济补偿金（合法解除/终止时的补偿）
    - N+1：经济补偿金 + 代通知金（未提前30日通知时）
    - 2N：违法解除赔偿金（违法解除时的双倍补偿）
    """
    try:
        result = calculate_economic_compensation(
            monthly_salary=request.monthly_salary,
            work_years=request.work_years,
            local_avg_salary=request.local_avg_salary,
            compensation_type=request.compensation_type,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tools/calculate_interest", summary="计算利息")
async def calculate_interest_api(request: InterestRequest) -> InterestResult:
    """
    计算利息工具

    支持三种利率类型：
    - LPR：使用贷款市场报价利率
    - fixed：使用固定年利率
    - LPR_multiple：使用LPR的倍数（如4倍LPR用于民间借贷利率上限）
    """
    try:
        result = calculate_interest_amount(
            principal=request.principal,
            start_date=request.start_date,
            end_date=request.end_date,
            rate_type=request.rate_type,
            rate_value=request.rate_value,
            lpr_term=request.lpr_term,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tools/calculate_damage", summary="计算损害赔偿")
async def calculate_damage_api(request: DamageCalculationRequest) -> DamageCalculationResult:
    """
    计算损害赔偿工具

    支持三种损害类型：
    - 人身损害：医疗费 + 护理费 + 误工费 + 其他费用
    - 财产损害：按损失发生时市场价格计算
    - 违约损害：实际损失 + 可得利益损失
    """
    try:
        result = calculate_damage(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/lpr/current", summary="获取当前LPR利率")
async def get_current_lpr():
    """获取当前LPR利率信息"""
    return {
        "一年期LPR": f"{LPR_ONE_YEAR}%",
        "五年期以上LPR": f"{LPR_FIVE_YEAR}%",
        "更新日期": LPR_UPDATE_DATE,
        "民间借贷利率上限（4倍一年期LPR）": f"{LPR_ONE_YEAR * PRIVATE_LENDING_RATE_CAP_MULTIPLIER}%",
    }


@app.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return {
        "status": "healthy",
        "service": "calc_tools",
        "lpr_one_year": LPR_ONE_YEAR,
        "lpr_five_year": LPR_FIVE_YEAR,
    }


# ============================================================
# 直接运行入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)

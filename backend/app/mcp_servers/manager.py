"""
MCP工具管理器

统一管理所有MCP工具的注册和发现，提供：
- 工具注册：各MCP服务器启动时注册其提供的工具
- 工具发现：查询所有已注册的工具列表
- 工具调用：根据工具名称路由到对应的MCP服务器执行
- 工具Schema管理：维护所有工具的OpenAI Function Calling格式定义
"""

import os
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ============================================================
# 常量配置
# ============================================================

# 各MCP服务器的地址配置
MCP_SERVERS = {
    "law_search": {
        "name": "法律法规检索服务",
        "url": "http://localhost:8001",
        "description": "提供法律法规和司法解释的智能检索",
    },
    "case_search": {
        "name": "案例检索服务",
        "url": "http://localhost:8002",
        "description": "提供典型裁判文书的智能检索",
    },
    "contract_tools": {
        "name": "合同工具服务",
        "url": "http://localhost:8003",
        "description": "提供合同模板获取和条款合法性验证",
    },
    "calc_tools": {
        "name": "法律计算工具服务",
        "url": "http://localhost:8004",
        "description": "提供经济补偿金、利息等法律计算",
    },
    "compliance": {
        "name": "合规检查服务",
        "url": "http://localhost:8005",
        "description": "提供合同条款合规检查和法规更新通知",
    },
}

# 工具名到MCP服务器的映射（在注册时动态填充）
TOOL_SERVER_MAP: dict[str, str] = {}

# 所有工具的Schema定义（在注册时动态填充）
ALL_TOOLS: list[dict[str, Any]] = []

# 创建FastAPI应用实例
app = FastAPI(
    title="MCP工具管理器",
    description="统一管理所有MCP工具的注册、发现和调用",
    version="1.0.0",
)


# ============================================================
# 数据模型定义
# ============================================================

class ToolCallRequest(BaseModel):
    """工具调用请求模型"""
    tool_name: str = Field(..., description="工具名称，如'search_articles'、'calculate_compensation'")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具调用参数")


class ToolCallResult(BaseModel):
    """工具调用结果模型"""
    success: bool = Field(..., description="调用是否成功")
    tool_name: str = Field(..., description="工具名称")
    server: str = Field(..., description="执行工具的MCP服务器名称")
    result: Optional[Any] = Field(None, description="工具返回结果")
    error: Optional[str] = Field(None, description="错误信息（如有）")


class ServerStatus(BaseModel):
    """MCP服务器状态模型"""
    server_id: str = Field(..., description="服务器标识")
    name: str = Field(..., description="服务器名称")
    url: str = Field(..., description="服务器地址")
    description: str = Field(..., description="服务器描述")
    is_alive: bool = Field(False, description="是否在线")
    tools_count: int = Field(0, description="已注册工具数量")


class RegisterRequest(BaseModel):
    """工具注册请求模型"""
    server_id: str = Field(..., description="MCP服务器标识")
    tools: list[dict[str, Any]] = Field(..., description="工具Schema列表（OpenAI Function Calling格式）")


# ============================================================
# 工具注册逻辑
# ============================================================

def register_tools(server_id: str, tools: list[dict[str, Any]]) -> None:
    """
    注册MCP服务器的工具

    将工具Schema添加到全局工具列表，并建立工具名到服务器的映射

    Args:
        server_id: MCP服务器标识
        tools: 工具Schema列表
    """
    for tool in tools:
        func_info = tool.get("function", {})
        tool_name = func_info.get("name", "")

        if not tool_name:
            continue

        # 建立工具名到服务器的映射
        TOOL_SERVER_MAP[tool_name] = server_id

        # 添加到全局工具列表（避免重复）
        existing_names = [
            t.get("function", {}).get("name") for t in ALL_TOOLS
        ]
        if tool_name not in existing_names:
            ALL_TOOLS.append(tool)


# ============================================================
# 工具调用逻辑
# ============================================================

async def call_tool_on_server(
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    """
    向指定的MCP服务器发起工具调用

    Args:
        server_id: MCP服务器标识
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        工具返回结果
    """
    server_config = MCP_SERVERS.get(server_id)
    if not server_config:
        raise ValueError(f"未知的MCP服务器：{server_id}")

    server_url = server_config["url"]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 调用MCP服务器的工具接口
            response = await client.post(
                f"{server_url}/tools/{tool_name}",
                json=arguments,
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"工具调用失败：{response.text}",
                )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"MCP服务器 {server_id}（{server_url}）连接失败，请确认服务是否启动",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"MCP服务器 {server_id}（{server_url}）响应超时",
        )


# ============================================================
# 服务发现：从各MCP服务器拉取工具定义
# ============================================================

async def discover_server_tools(server_id: str) -> list[dict[str, Any]]:
    """
    从MCP服务器拉取其提供的工具定义

    Args:
        server_id: MCP服务器标识

    Returns:
        工具Schema列表
    """
    server_config = MCP_SERVERS.get(server_id)
    if not server_config:
        return []

    server_url = server_config["url"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{server_url}/tools")
            if response.status_code == 200:
                data = response.json()
                return data.get("tools", [])
            return []
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        return []


async def check_server_alive(server_id: str) -> bool:
    """
    检查MCP服务器是否在线

    Args:
        server_id: MCP服务器标识

    Returns:
        是否在线
    """
    server_config = MCP_SERVERS.get(server_id)
    if not server_config:
        return False

    server_url = server_config["url"]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{server_url}/health")
            return response.status_code == 200
    except (httpx.HTTPError, httpx.TimeoutException, Exception):
        return False


# ============================================================
# API路由
# ============================================================

@app.get("/tools", summary="获取所有工具列表")
async def get_all_tools():
    """
    获取所有已注册的MCP工具列表

    返回OpenAI Function Calling格式的工具定义列表，
    可直接用于大模型Function Calling调用。
    """
    return {"tools": ALL_TOOLS, "total": len(ALL_TOOLS)}


@app.get("/tools/{tool_name}", summary="获取指定工具详情")
async def get_tool_detail(tool_name: str):
    """获取指定工具的详细Schema定义"""
    for tool in ALL_TOOLS:
        if tool.get("function", {}).get("name") == tool_name:
            server_id = TOOL_SERVER_MAP.get(tool_name, "unknown")
            return {
                "tool": tool,
                "server": server_id,
                "server_info": MCP_SERVERS.get(server_id, {}),
            }
    raise HTTPException(status_code=404, detail=f"未找到工具：{tool_name}")


@app.post("/tools/call", summary="调用工具")
async def call_tool(request: ToolCallRequest) -> ToolCallResult:
    """
    统一工具调用接口

    根据工具名称自动路由到对应的MCP服务器执行调用。
    """
    # 查找工具对应的MCP服务器
    server_id = TOOL_SERVER_MAP.get(request.tool_name)
    if not server_id:
        raise HTTPException(
            status_code=404,
            detail=f"未找到工具：{request.tool_name}，请确认工具名称是否正确",
        )

    # 调用对应MCP服务器的工具
    try:
        result = await call_tool_on_server(
            server_id, request.tool_name, request.arguments
        )
        return ToolCallResult(
            success=True,
            tool_name=request.tool_name,
            server=server_id,
            result=result,
        )
    except HTTPException as e:
        return ToolCallResult(
            success=False,
            tool_name=request.tool_name,
            server=server_id,
            error=e.detail,
        )


@app.post("/register", summary="注册工具")
async def register(request: RegisterRequest):
    """
    工具注册接口

    MCP服务器启动时调用此接口注册其提供的工具。
    """
    if request.server_id not in MCP_SERVERS:
        raise HTTPException(
            status_code=400,
            detail=f"未知的MCP服务器：{request.server_id}，请先在MCP_SERVERS配置中添加",
        )

    register_tools(request.server_id, request.tools)

    return {
        "status": "ok",
        "server_id": request.server_id,
        "registered_tools": len(request.tools),
        "total_tools": len(ALL_TOOLS),
    }


@app.get("/servers", summary="获取所有MCP服务器状态")
async def get_servers_status():
    """获取所有MCP服务器的运行状态"""
    servers: list[ServerStatus] = []

    for server_id, config in MCP_SERVERS.items():
        # 检查服务器是否在线
        is_alive = await check_server_alive(server_id)

        # 统计该服务器注册的工具数量
        tools_count = sum(
            1 for s in TOOL_SERVER_MAP.values() if s == server_id
        )

        servers.append(
            ServerStatus(
                server_id=server_id,
                name=config["name"],
                url=config["url"],
                description=config["description"],
                is_alive=is_alive,
                tools_count=tools_count,
            )
        )

    return {"servers": servers, "total": len(servers)}


@app.post("/discover", summary="发现并注册所有MCP服务器的工具")
async def discover_all_tools():
    """
    自动发现并注册所有MCP服务器的工具

    遍历所有配置的MCP服务器，拉取其工具定义并注册。
    用于服务启动后初始化工具注册表。
    """
    results: dict[str, Any] = {}

    for server_id in MCP_SERVERS:
        tools = await discover_server_tools(server_id)
        if tools:
            register_tools(server_id, tools)
            results[server_id] = {
                "status": "ok",
                "tools_count": len(tools),
                "tool_names": [
                    t.get("function", {}).get("name") for t in tools
                ],
            }
        else:
            is_alive = await check_server_alive(server_id)
            results[server_id] = {
                "status": "unreachable" if not is_alive else "no_tools",
                "tools_count": 0,
                "tool_names": [],
            }

    return {
        "discovery_results": results,
        "total_registered_tools": len(ALL_TOOLS),
    }


@app.get("/schema", summary="获取OpenAI Function Calling格式的完整工具Schema")
async def get_tools_schema():
    """
    获取OpenAI Function Calling格式的完整工具Schema

    可直接用于大模型的tools参数。
    """
    return {"tools": ALL_TOOLS}


@app.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return {
        "status": "healthy",
        "service": "mcp_manager",
        "registered_tools": len(ALL_TOOLS),
        "configured_servers": len(MCP_SERVERS),
    }


# ============================================================
# 应用启动事件
# ============================================================

@app.on_event("startup")
async def startup():
    """
    服务启动时自动发现并注册所有MCP服务器的工具

    遍历所有配置的MCP服务器，尝试拉取工具定义并注册。
    如果某个服务器未启动，则跳过（后续可通过 /discover 接口重新发现）。
    """
    print("[MCP工具管理器] 正在发现并注册MCP服务器工具...")
    for server_id, config in MCP_SERVERS.items():
        tools = await discover_server_tools(server_id)
        if tools:
            register_tools(server_id, tools)
            print(f"  ✓ {config['name']}：注册 {len(tools)} 个工具")
        else:
            print(f"  ✗ {config['name']}：未响应或无工具（服务可能未启动）")
    print(f"[MCP工具管理器] 工具注册完成，共 {len(ALL_TOOLS)} 个工具")


# ============================================================
# 直接运行入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

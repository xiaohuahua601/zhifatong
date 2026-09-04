# ============================================================
# 智法通 - Windows PowerShell 启动脚本
# 说明: 检查环境、启动Docker Compose、等待服务就绪、初始化数据库
# 使用: 在PowerShell中执行 .\scripts\start.ps1
# 注意: 如遇到执行策略限制，请先执行:
#       Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# ============================================================

# 设置编码为UTF-8，确保中文正确显示
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 项目根目录
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# ============================================================
# 辅助函数
# ============================================================

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Separator {
    Write-Host "============================================================"
}

# ============================================================
# 步骤1: 环境检查
# ============================================================
function Check-Environment {
    Write-Separator
    Write-Info "正在检查运行环境..."

    # 检查Docker是否安装
    $dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerInstalled) {
        Write-Error "Docker未安装，请先安装Docker Desktop"
        Write-Info "下载地址: https://www.docker.com/products/docker-desktop"
        exit 1
    }
    Write-Success "Docker已安装: $(docker --version)"

    # 检查Docker Compose是否可用
    $script:ComposeCmd = $null
    try {
        $composeVersion = docker compose version 2>$null
        if ($LASTEXITCODE -eq 0) {
            $script:ComposeCmd = "docker compose"
            Write-Success "Docker Compose已安装: $composeVersion"
        }
    }
    catch { }

    if (-not $script:ComposeCmd) {
        $composeCmdInstalled = Get-Command docker-compose -ErrorAction SilentlyContinue
        if ($composeCmdInstalled) {
            $script:ComposeCmd = "docker-compose"
            Write-Success "Docker Compose已安装: $(docker-compose --version)"
        }
        else {
            Write-Error "Docker Compose未安装，请先安装Docker Compose"
            exit 1
        }
    }

    # 检查Docker守护进程是否运行
    try {
        docker info | Out-Null 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker not running"
        }
        Write-Success "Docker守护进程正在运行"
    }
    catch {
        Write-Error "Docker守护进程未运行，请启动Docker Desktop"
        exit 1
    }

    # 检查.env文件是否存在
    $envFile = Join-Path $ProjectDir ".env"
    if (-not (Test-Path $envFile)) {
        Write-Warning ".env文件不存在，正在从.env.example创建..."
        $exampleFile = Join-Path $ProjectDir ".env.example"
        Copy-Item $exampleFile $envFile
        Write-Success ".env文件已创建，请根据实际情况修改配置"
    }
    else {
        Write-Success ".env配置文件已存在"
    }

    # 检查Python是否安装
    $script:PythonCmd = $null
    $pythonInstalled = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonInstalled) {
        $script:PythonCmd = "python"
        Write-Success "Python已安装: $(python --version)"
    }
    else {
        $python3Installed = Get-Command python3 -ErrorAction SilentlyContinue
        if ($python3Installed) {
            $script:PythonCmd = "python3"
            Write-Success "Python已安装: $(python3 --version)"
        }
        else {
            Write-Warning "Python未安装，数据库初始化将通过Docker容器自动执行"
        }
    }

    Write-Success "环境检查完成"
}

# ============================================================
# 步骤2: 启动Docker Compose服务
# ============================================================
function Start-Services {
    Write-Separator
    Write-Info "正在启动Docker Compose服务..."

    Set-Location $ProjectDir

    # 停止已有的服务（如果存在）
    try {
        Invoke-Expression "$script:ComposeCmd down --remove-orphans" 2>$null | Out-Null
    }
    catch { }

    # 构建并启动所有服务（后台运行）
    Write-Info "正在构建和启动容器，这可能需要几分钟..."
    Invoke-Expression "$script:ComposeCmd up -d --build"

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker Compose启动失败"
        Write-Info "请检查日志: $script:ComposeCmd logs"
        exit 1
    }

    Write-Success "Docker Compose服务已启动"
}

# ============================================================
# 步骤3: 等待服务就绪
# ============================================================
function Wait-ForServices {
    Write-Separator
    Write-Info "正在等待服务就绪..."

    # 读取环境变量获取MySQL密码
    $envFile = Join-Path $ProjectDir ".env"
    $mysqlPassword = "zhifatong_root_2026"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile
        foreach ($line in $envContent) {
            if ($line -match "^MYSQL_ROOT_PASSWORD=(.+)$") {
                $mysqlPassword = $Matches[1]
                break
            }
        }
    }

    # 等待MySQL就绪（最多等待120秒）
    Write-Info "等待MySQL服务..."
    $maxWait = 120
    $waited = 0
    $mysqlReady = $false

    while ($waited -lt $maxWait) {
        try {
            $result = docker exec zhifatong-mysql mysqladmin ping -h localhost -u root -p"$mysqlPassword" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $mysqlReady = $true
                Write-Success "MySQL服务已就绪（等待了${waited}秒）"
                break
            }
        }
        catch { }

        Start-Sleep -Seconds 3
        $waited += 3
        Write-Host -NoNewline "."
    }

    if (-not $mysqlReady) {
        Write-Error "MySQL服务启动超时（${maxWait}秒）"
        Write-Info "请检查日志: docker logs zhifatong-mysql"
        exit 1
    }

    # 等待后端服务就绪（最多等待60秒）
    Write-Info "等待后端服务..."
    $waited = 0
    $maxWait = 60
    $backendReady = $false

    while ($waited -lt $maxWait) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $backendReady = $true
                Write-Success "后端服务已就绪（等待了${waited}秒）"
                break
            }
        }
        catch { }

        Start-Sleep -Seconds 3
        $waited += 3
        Write-Host -NoNewline "."
    }

    if (-not $backendReady) {
        Write-Warning "后端服务未在预期时间内就绪，但可能仍在启动中"
        Write-Info "请检查日志: docker logs zhifatong-backend"
    }

    # 等待Nginx就绪
    Write-Info "等待Nginx服务..."
    $waited = 0
    $maxWait = 30

    while ($waited -lt $maxWait) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Success "Nginx服务已就绪（等待了${waited}秒）"
                break
            }
        }
        catch { }

        Start-Sleep -Seconds 2
        $waited += 2
    }

    Write-Success "所有服务已就绪"
}

# ============================================================
# 步骤4: 初始化数据库
# ============================================================
function Initialize-Database {
    Write-Separator
    Write-Info "正在初始化数据库..."

    # 读取MySQL密码
    $envFile = Join-Path $ProjectDir ".env"
    $mysqlPassword = "zhifatong_root_2026"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile
        foreach ($line in $envContent) {
            if ($line -match "^MYSQL_ROOT_PASSWORD=(.+)$") {
                $mysqlPassword = $Matches[1]
                break
            }
        }
    }

    # 检查数据库是否已通过Docker自动初始化
    try {
        $result = docker exec zhifatong-mysql mysql -u root -p"$mysqlPassword" -e "USE zhifatong; SELECT COUNT(*) FROM users;" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "数据库已通过Docker自动初始化"
        }
        else {
            throw "Auto init failed"
        }
    }
    catch {
        Write-Warning "Docker自动初始化可能未完成，尝试手动初始化..."

        # 如果本地有Python，运行初始化脚本
        if ($script:PythonCmd) {
            Write-Info "使用Python脚本初始化数据库..."
            try {
                pip install pymysql -q 2>$null
            }
            catch { }
            try {
                $env:DB_HOST = "localhost"
                $env:DB_PORT = "3306"
                $env:DB_USER = "root"
                $env:DB_PASSWORD = $mysqlPassword
                $env:DB_NAME = "zhifatong"
                Invoke-Expression "$script:PythonCmd `"$ProjectDir\scripts\init_db.py`""
            }
            catch {
                Write-Warning "Python脚本初始化失败，尝试通过Docker执行SQL..."
                $sqlFile = Join-Path $ProjectDir "sql\init.sql"
                Get-Content $sqlFile | docker exec -i zhifatong-mysql mysql -u root -p"$mysqlPassword"
            }
        }
        else {
            # 通过Docker执行SQL
            Write-Info "通过Docker执行SQL初始化..."
            $sqlFile = Join-Path $ProjectDir "sql\init.sql"
            Get-Content $sqlFile | docker exec -i zhifatong-mysql mysql -u root -p"$mysqlPassword"
        }
    }

    Write-Success "数据库初始化完成"
}

# ============================================================
# 步骤5: 显示服务信息
# ============================================================
function Show-ServiceInfo {
    Write-Separator
    Write-Host ""
    Write-Success "智法通平台已成功启动！"
    Write-Host ""
    Write-Info "服务访问地址:"
    Write-Host "  前端界面:  http://localhost"
    Write-Host "  后端API:   http://localhost/api"
    Write-Host "  API文档:   http://localhost/api/docs"
    Write-Host "  MySQL:     localhost:3306"
    Write-Host ""
    Write-Info "默认管理员账号:"
    Write-Host "  用户名: admin"
    Write-Host "  密码:   admin123"
    Write-Host ""
    Write-Warning "请在生产环境中修改默认密码和密钥！"
    Write-Host ""
    Write-Info "常用命令:"
    Write-Host "  查看服务状态:  $script:ComposeCmd ps"
    Write-Host "  查看服务日志:  $script:ComposeCmd logs -f [服务名]"
    Write-Host "  停止所有服务:  $script:ComposeCmd down"
    Write-Host "  重启某个服务:  $script:ComposeCmd restart [服务名]"
    Write-Host ""
    Write-Separator
}

# ============================================================
# 主流程
# ============================================================
Write-Host ""
Write-Separator
Write-Host "  智法通 - 企业级智能法律顾问平台" -ForegroundColor Blue
Write-Host "  启动脚本 v1.0 (Windows PowerShell)" -ForegroundColor Blue
Write-Separator
Write-Host ""

Check-Environment
Start-Services
Wait-ForServices
Initialize-Database
Show-ServiceInfo

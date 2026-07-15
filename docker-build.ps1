# ============================================
# Docker 镜像构建脚本 (Windows PowerShell)
# ============================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LLM Graph Builder - 镜像构建脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 进入后端目录
$BackendPath = "C:\Users\25592\Desktop\llm-graph-builder-main\llm-graph-builder-main\backend"
Write-Host "步骤 1: 进入后端目录..." -ForegroundColor Yellow
Set-Location $BackendPath
Write-Host "当前目录: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# 2. 检查必要文件
Write-Host "步骤 2: 检查必要文件..." -ForegroundColor Yellow
$RequiredFiles = @("Dockerfile", "requirements.txt", "constraints.txt", "example.env")
$AllFilesExist = $true

foreach ($file in $RequiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file 存在" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file 不存在" -ForegroundColor Red
        $AllFilesExist = $false
    }
}

if (-not $AllFilesExist) {
    Write-Host "`n错误: 缺少必要文件，无法继续构建" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. 检查 .env 文件
Write-Host "步骤 3: 检查环境配置文件..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "  警告: .env 文件不存在，正在从 example.env 复制..." -ForegroundColor Yellow
    Copy-Item "example.env" ".env"
    Write-Host "  ✓ 已创建 .env 文件" -ForegroundColor Green
    Write-Host "  ⚠ 请编辑 .env 文件，配置以下必要项:" -ForegroundColor Yellow
    Write-Host "    - NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE" -ForegroundColor Cyan
    Write-Host "    - LLM_MODEL_CONFIG_* (至少配置一个模型)" -ForegroundColor Cyan
    Write-Host "    - OPENAI_API_KEY 或其他 LLM API 密钥" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "是否已完成 .env 配置? (y/n)"
    if ($continue -ne "y") {
        Write-Host "请先配置 .env 文件后再运行此脚本" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  ✓ .env 文件已存在" -ForegroundColor Green
}
Write-Host ""

# 4. 检查 Docker 是否运行
Write-Host "步骤 4: 检查 Docker 状态..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "  ✓ Docker 已安装: $dockerVersion" -ForegroundColor Green
    
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Docker 服务正在运行" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Docker 服务未运行，请启动 Docker Desktop" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ Docker 未安装或未添加到 PATH" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 5. 构建 Docker 镜像
Write-Host "步骤 5: 开始构建 Docker 镜像..." -ForegroundColor Yellow
Write-Host "  镜像名称: llm-graph-builder-backend:latest" -ForegroundColor Cyan
Write-Host "  这可能需要 10-20 分钟，请耐心等待..." -ForegroundColor Cyan
Write-Host ""

$BuildStartTime = Get-Date
docker build -t llm-graph-builder-backend:latest .

if ($LASTEXITCODE -eq 0) {
    $BuildEndTime = Get-Date
    $BuildDuration = $BuildEndTime - $BuildStartTime
    Write-Host ""
    Write-Host "  ✓ 镜像构建成功!" -ForegroundColor Green
    Write-Host "  构建耗时: $($BuildDuration.ToString('mm\:ss'))" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  ✗ 镜像构建失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 6. 查看镜像信息
Write-Host "步骤 6: 查看镜像信息..." -ForegroundColor Yellow
docker images llm-graph-builder-backend:latest
Write-Host ""

# 7. 询问是否立即运行容器
Write-Host "========================================" -ForegroundColor Cyan
$runNow = Read-Host "是否立即运行容器? (y/n)"

if ($runNow -eq "y") {
    Write-Host ""
    Write-Host "步骤 7: 启动容器..." -ForegroundColor Yellow
    
    # 停止并删除旧容器（如果存在）
    $existingContainer = docker ps -a --filter "name=llm-graph-backend" --format "{{.Names}}"
    if ($existingContainer -eq "llm-graph-backend") {
        Write-Host "  发现已存在的容器，正在删除..." -ForegroundColor Yellow
        docker stop llm-graph-backend 2>$null
        docker rm llm-graph-backend 2>$null
        Write-Host "  ✓ 旧容器已删除" -ForegroundColor Green
    }
    
    # 运行新容器
    docker run -d `
        --name llm-graph-backend `
        -p 8000:8000 `
        --env-file .env `
        --add-host=host.docker.internal:host-gateway `
        llm-graph-builder-backend:latest
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ 容器启动成功!" -ForegroundColor Green
        Write-Host ""
        Write-Host "  容器名称: llm-graph-backend" -ForegroundColor Cyan
        Write-Host "  访问地址: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host ""
        
        # 等待服务启动
        Write-Host "  等待服务启动..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # 查看容器日志
        Write-Host ""
        Write-Host "  最近的容器日志:" -ForegroundColor Yellow
        docker logs --tail 20 llm-graph-backend
        
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  常用命令:" -ForegroundColor Cyan
        Write-Host "  - 查看日志: docker logs -f llm-graph-backend" -ForegroundColor White
        Write-Host "  - 停止容器: docker stop llm-graph-backend" -ForegroundColor White
        Write-Host "  - 启动容器: docker start llm-graph-backend" -ForegroundColor White
        Write-Host "  - 删除容器: docker rm -f llm-graph-backend" -ForegroundColor White
        Write-Host "  - 进入容器: docker exec -it llm-graph-backend bash" -ForegroundColor White
        Write-Host "========================================" -ForegroundColor Cyan
    } else {
        Write-Host "  ✗ 容器启动失败" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  镜像构建完成！" -ForegroundColor Green
    Write-Host ""
    Write-Host "  手动运行容器命令:" -ForegroundColor Cyan
    Write-Host "  docker run -d ``" -ForegroundColor White
    Write-Host "    --name llm-graph-backend ``" -ForegroundColor White
    Write-Host "    -p 8000:8000 ``" -ForegroundColor White
    Write-Host "    --env-file .env ``" -ForegroundColor White
    Write-Host "    --add-host=host.docker.internal:host-gateway ``" -ForegroundColor White
    Write-Host "    llm-graph-builder-backend:latest" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✓ 所有操作完成!" -ForegroundColor Green


#!/bin/bash
# ========================================================
# 一源AI(yiyuan-ai-video)部署脚本
#
# 真实部署链路(与 docs/release-checklist.md 第 3 节一致):
#   拉取代码 → 构建并启动 backend/worker → 构建 admin/desktop 静态资源 → 重载 caddy
#
# 数据库结构:模型新增的列/表已由 backend 启动时自动追平
#   (backend/plugin/database/schema_sync.py,幂等且只增不改),
#   因此本脚本不再包含「手工补列」步骤;需要人工核查时用
#   docker compose exec backend python scripts/ensure_columns.py
# ========================================================

# 设置全局变量(与实际仓库保持一致)
PROJECT_NAME="yiyuan-ai-video"
WORK_DIR="/home/ubuntu/pro"
GIT_REPO="https://codeup.aliyun.com/638418a973a727212a3e0e32/yiyuan-ai-video.git"
# 由 caddy 托管的静态前端(构建产物同步到 devops/caddy/data/<端名>)
FRONTENDS=("admin" "desktop")

# 日志级别控制
LOG_LEVEL=${LOG_LEVEL:-INFO}

# 打印带时间戳的日志
log() {
    local message="$1"
    local level=${2:-INFO}

    # 根据日志级别决定是否输出
    case $LOG_LEVEL in
        DEBUG) ;;
        INFO) [[ $level == "DEBUG" ]] && return ;;
        WARN) [[ $level == "DEBUG" || $level == "INFO" ]] && return ;;
        ERROR) [[ $level != "ERROR" ]] && return ;;
    esac

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
}

# 检查脚本自身权限
check_permissions() {
    log "==========🔍 第一步：检查脚本权限...==========" "INFO"
    if [ ! -x "$0" ]; then
        log "⚠️ 当前脚本没有执行权限，请使用 chmod +x $0 添加执行权限" "ERROR"
        exit 1
    fi
    log "✅ 脚本已有执行权限" "INFO"
}

# 检查部署依赖(git / docker / 前端构建所需 node+npm)
check_dependencies() {
    log "==========🔍 第二步：检查系统依赖...==========" "INFO"
    local missing_deps=()

    for cmd in git docker node npm; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+=($cmd)
            log "❌ $cmd 未安装" "ERROR"
        else
            log "🎉 $cmd 已安装 - $($cmd --version 2>/dev/null || true)" "INFO"
        fi
    done

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log "❌ 缺少依赖: ${missing_deps[*]}" "ERROR"
        exit 1
    fi

    # docker compose(插件式)必须可用,否则后续步骤都会失败
    if ! docker compose version &> /dev/null; then
        log "❌ docker compose 不可用(需 Docker Compose V2 插件)" "ERROR"
        exit 1
    fi
    log "✅ 所有依赖检查通过" "INFO"
}

# 进入项目目录并校验 compose 文件
enter_project() {
    cd "${WORK_DIR}/${PROJECT_NAME}" 2>/dev/null || {
        log "❌ 无法进入项目目录：${WORK_DIR}/${PROJECT_NAME}" "ERROR"
        exit 1
    }
    if [ ! -f "docker-compose.yaml" ] && [ ! -f "docker-compose.yml" ]; then
        log "❌ 项目目录下未找到 docker-compose.yaml" "ERROR"
        exit 1
    fi
}

# 更新代码(不 down 容器,避免数据库/缓存无谓中断)
update_code() {
    log "==========🔍 第三步：更新代码...==========" "INFO"
    if [ -d "${WORK_DIR}/${PROJECT_NAME}" ]; then
        enter_project
        log "🔄 项目已存在，开始拉取更新" "INFO"
        # 不使用 --force:避免静默覆盖部署机上的本地改动/冲突,失败时明确报错交由人工处理
        git pull || { log "❌ 拉取更新失败(请检查部署机本地改动或合并冲突)" "ERROR"; exit 1; }
        git log -1 --oneline || { log "❌ 获取提交信息失败" "ERROR"; exit 1; }
        log "✅ 代码更新成功" "INFO"
    else
        log "📥 项目不存在，开始克隆代码" "INFO"
        git clone "${GIT_REPO}" || { log "❌ 项目克隆失败：${GIT_REPO}" "ERROR"; exit 1; }
        enter_project
        log "✅ 代码克隆成功" "INFO"
    fi
}

# 校验 compose 配置(改过 compose/Dockerfile 时能在部署前暴露语法问题)
validate_compose() {
    log "==========🔍 第四步：校验 compose 配置...==========" "INFO"
    enter_project
    docker compose config >/dev/null || { log "❌ docker compose 配置校验失败" "ERROR"; exit 1; }
    log "✅ compose 配置校验通过" "INFO"
}

# 构建并启动后端与 worker(数据库结构在 backend 启动时自动追平)
start_services() {
    log "==========🚀 第五步：构建并启动 backend / worker...==========" "INFO"
    enter_project
    docker compose up -d --build backend worker || { log "❌ 后端/worker 构建或启动失败" "ERROR"; exit 1; }
    docker compose ps || { log "❌ 容器状态获取失败" "ERROR"; exit 1; }
    log "✅ backend / worker 已启动" "INFO"
}

# 构建由 caddy 托管的静态前端(构建脚本会同步产物到 devops/caddy/data)
build_frontends() {
    log "==========🚀 第六步：构建前端静态资源...==========" "INFO"
    enter_project
    for app in "${FRONTENDS[@]}"; do
        if [ ! -d "${app}" ]; then
            log "⚠️ 目录不存在，跳过：${app}" "WARN"
            continue
        fi
        log "📦 安装依赖并打包：${app}" "INFO"
        (cd "${app}" && npm install && npm run build) \
            || { log "❌ ${app} 打包失败" "ERROR"; exit 1; }
        log "✅ ${app} 打包完成" "INFO"
    done
}

# 重载网关,让新的静态资源生效
reload_gateway() {
    log "==========🚀 第七步：重载 caddy...==========" "INFO"
    enter_project
    docker compose restart caddy || { log "❌ caddy 重载失败" "ERROR"; exit 1; }
    log "✅ caddy 已重载" "INFO"
}

# 部署后自检:容器状态 + 数据库结构追平日志
verify_deploy() {
    log "==========🔍 第八步：部署自检...==========" "INFO"
    enter_project
    docker compose ps || { log "❌ 容器状态获取失败" "ERROR"; exit 1; }
    # 结构追平只在「确实有缺口」时才打印日志;此处仅提示查看方式,不因无输出而判定失败
    log "ℹ️ 如需确认数据库结构追平结果：docker compose logs backend | grep 数据库结构追平" "INFO"
    log "✅ 自检完成" "INFO"
}

# 停止项目容器
stop_project() {
    log "==========⏹️ 停止项目容器...==========" "INFO"
    enter_project
    docker compose down || { log "❌ 停止容器失败" "ERROR"; exit 1; }
    log "✅ 项目容器已停止并删除" "INFO"
}

# 清理72小时前的项目旧镜像
cleanup_old_images() {
    log "==========🗑️ 第九步：清理72小时前的旧镜像...==========" "INFO"
    local before_count after_count
    before_count=$(docker images --filter "label=com.docker.compose.project=${PROJECT_NAME}" -q | wc -l)
    if [ "$before_count" -eq 0 ]; then
        log "⚠️ 没有找到项目相关镜像，跳过清理" "WARN"
        return
    fi
    docker image prune -f --filter "until=72h" --filter "label=com.docker.compose.project=${PROJECT_NAME}" >/dev/null 2>&1
    after_count=$(docker images --filter "label=com.docker.compose.project=${PROJECT_NAME}" -q | wc -l)
    log "✅ 旧镜像清理完成，清理了 $((before_count - after_count)) 个镜像" "INFO"
}

# 信号处理
handle_interrupt() {
    log "==========⚠️ 收到中断信号，正在停止部署...==========" "WARN"
    if [ -d "${WORK_DIR}/${PROJECT_NAME}" ]; then
        enter_project
        docker compose down >/dev/null 2>&1
    fi
    exit 130
}

# 主函数
main() {
    log "==========🚀 开始部署流程==========" "INFO"
    check_permissions
    check_dependencies
    update_code
    validate_compose
    start_services
    build_frontends
    reload_gateway
    verify_deploy
    cleanup_old_images
    log "==========🎉 部署完成==========" "INFO"
}

# 设置信号处理
trap handle_interrupt INT TERM

# 解析命令行参数：不带参数时默认执行完整部署流程
if [ $# -eq 0 ]; then
    main "$@"
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            LOG_LEVEL="DEBUG"
            shift
            ;;
        --work-dir)
            WORK_DIR="$2"
            shift 2
            ;;
        --stop)
            stop_project
            exit 0
            ;;
        --start)
            main
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [--debug] [--work-dir <directory>] [--stop] [--start]"
            echo "不带参数时默认执行部署流程"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

main "$@"
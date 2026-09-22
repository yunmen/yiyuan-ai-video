FROM python:3.12-slim-bullseye

LABEL author="yiyuan-ai"

# 设置时区
ENV TZ=Asia/Shanghai

# 设置容器内工作目录(与 docker-compose 的 ./worker:/home 挂载对应)
WORKDIR /home

# 复制依赖清单(构建上下文为仓库根目录)
COPY ./worker/requirements.txt .

# 安装依赖(服务器在海外,走官方源;加大超时与重试防止网络抖动)
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt -i https://pypi.org/simple

# P3 合成层:ffmpeg(字幕轨 / BGM 轨合成需要;纯 Python 方案无法替代)
# fonts-noto-cjk:**中文字体**。ffmpeg 烧字幕缺字体时**不报错**,只会渲染成豆腐块,
# 所以字体必须与 ffmpeg 一起装;代码侧还有一道保险(resolve_subtitle_font 找不到字体就跳过烧录)。
# 注意:基础镜像为 bullseye(Debian 11),若构建时 apt 源已归档(EOL)会报 404,
# 届时需把 sources.list 指向 archive.debian.org,或改用 bookworm 基础镜像。
# 构建后请在容器内执行 `python worker/scripts/probe_compose.py` 确认编码器与字体可用。
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 启动 ARQ worker
CMD ["python", "main.py", "run", "--env=prod"]

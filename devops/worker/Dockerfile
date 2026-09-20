FROM python:3.12-slim-bullseye

LABEL author="yiyuan-ai"

# 设置时区
ENV TZ=Asia/Shanghai

# 设置容器内工作目录(与 docker-compose 的 ./worker:/home 挂载对应)
WORKDIR /home

# 复制依赖清单(构建上下文为仓库根目录)
COPY ./worker/requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 启动 ARQ worker
CMD ["python", "main.py", "run", "--env=prod"]

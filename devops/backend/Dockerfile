FROM python:3.12-slim-bullseye

LABEL author="yiyuan-ai"

# 设置时区
ENV TZ=Asia/Shanghai

# 设置容器内工作目录
WORKDIR /home

# 复制依赖清单(构建上下文为仓库根目录)
COPY ./backend/requirements.txt .

# 安装依赖(服务器在海外,走官方源;加大超时与重试防止网络抖动)
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt -i https://pypi.org/simple

# 运行应用
CMD ["python", "main.py", "run", "--env=prod"]

# 暴露端口
EXPOSE 8801

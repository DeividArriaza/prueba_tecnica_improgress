FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-orchestration.txt ./
RUN pip install --no-cache-dir --default-timeout=120 --retries=5 -r requirements-orchestration.txt
COPY . .
ENTRYPOINT ["python", "-m", "orchestration.flows"]

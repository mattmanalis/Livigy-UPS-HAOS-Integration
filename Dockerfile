FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir .

CMD ["python", "-m", "livigy_ups_bridge.main", "--config", "/app/config.yaml"]

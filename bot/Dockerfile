FROM python:3.12-alpine3.20

WORKDIR /app

COPY bot/requirements.txt ./bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt

COPY shared ./shared
COPY bot ./bot

WORKDIR /app/bot
ENV PYTHONPATH=/app

USER nobody

CMD ["python", "main.py"]

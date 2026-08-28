FROM python:3.15.0b4-alpine3.24

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER nobody

CMD ["python", "main.py"]

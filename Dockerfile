FROM python:3.11-slim

COPY postgres_check.py /app/

RUN pip install psycopg2-binary tabulate requests

WORKDIR /github/workspace
ENV PYTHONPATH=/app:$PYTHONPATH

ENTRYPOINT ["python", "/app/postgres_check.py"]

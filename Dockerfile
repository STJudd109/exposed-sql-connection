FROM python:3.11-slim

WORKDIR /action

COPY postgres_check.py .

RUN pip install psycopg2-binary tabulate requests

ENTRYPOINT ["python", "postgres_check.py"]
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml requirements.txt README.md ./
COPY redcord ./redcord
RUN pip install --no-cache-dir -r requirements.txt

ENV REDCORD_BACKEND_DATABASE_URL=postgresql+psycopg://redcord:redcord@postgres:5432/redcord
EXPOSE 8088
CMD ["python", "-m", "redcord.backend.main"]

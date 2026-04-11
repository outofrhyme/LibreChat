FROM python:3.12-slim

WORKDIR /app

COPY mcp/character-notes-mcp/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp/character-notes-mcp/app.py ./
COPY Nolan ./Nolan

ENV HOST=0.0.0.0

CMD ["python", "app.py"]

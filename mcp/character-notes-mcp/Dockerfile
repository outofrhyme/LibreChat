FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./

ENV HOST=0.0.0.0
ENV PORT=8080
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HTTP_PATH=/mcp

EXPOSE 8080

CMD ["python", "app.py"]

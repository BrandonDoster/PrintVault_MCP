FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=sse
ENV MCP_PORT=8080

EXPOSE 8080

CMD ["print-vault-mcp"]

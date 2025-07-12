# Pterodactyl MCP Server Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY pterodactyl_mcp_server.py .
COPY .env.example .

# Create non-root user
RUN useradd --create-home --shell /bin/bash mcpuser && \
    chown -R mcpuser:mcpuser /app

USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; assert os.getenv('PTERODACTYL_PANEL_URL')" || exit 1

# Default command
CMD ["python", "pterodactyl_mcp_server.py"]

# Metadata
LABEL org.opencontainers.image.title="Pterodactyl MCP Server"
LABEL org.opencontainers.image.description="Model Context Protocol server for Pterodactyl Panel API"
LABEL org.opencontainers.image.source="https://github.com/defunsm/pterodactyl-mcp-server"
LABEL org.opencontainers.image.licenses="MIT"
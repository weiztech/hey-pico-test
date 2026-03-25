FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# System deps (minimal, useful for building some Python wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency metadata first for better layer caching
COPY pyproject.toml uv.lock* ./

# Install project dependencies (without installing the local project package)
RUN uv sync --frozen --no-install-project

# Copy source code
COPY . .

# Copy and permission the entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose Django dev server port
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

# Default command for container startup
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]

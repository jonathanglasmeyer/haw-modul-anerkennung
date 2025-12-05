FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application
COPY . .

# Expose port
EXPOSE 3008

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3008"]

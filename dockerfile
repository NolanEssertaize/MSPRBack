FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy dependency files
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for security
RUN adduser --disabled-password --gecos "" appuser

# Create directory for photos and fix permissions
RUN mkdir -p photos && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Expose port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Add health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/docs || exit 1

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
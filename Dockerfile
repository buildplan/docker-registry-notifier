# ---- Stage 1: The Builder ----
# We name this stage 'builder' so we can reference it later.
FROM python:3.9-slim AS builder

WORKDIR /app

# Create a virtual environment
RUN python -m venv /app/venv

# Activate the virtual environment for subsequent RUN commands
ENV PATH="/app/venv/bin:$PATH"

# Install dependencies into the virtual environment
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the builder stage
COPY app.py .


# ---- Stage 2: The Final Image ----
# Start fresh from the same slim base image
FROM python:3.9-slim

# Install curl for the HEALTHCHECK command and then clean up apt cache
RUN apt-get update && apt-get install -y curl --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/venv ./venv

# Copy the application code from the builder stage
COPY --from=builder /app/app.py .

# Change ownership of all app files to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Activate the virtual environment for the final CMD
ENV PATH="/app/venv/bin:$PATH"

# Expose the port
EXPOSE 5001

# Health check to ensure the application is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

# Define the command to run the application
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5001", "app:app"]

# ---- Stage 1: The Builder ----
FROM python:3.14-alpine@sha256:a1321512d6a287428c50dcdf2ab3857761127e03a23b1f648e9c1c0de59288f8 AS builder

WORKDIR /app

# virtual environment
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the builder stage
COPY app.py .


# ---- Stage 2: The Final Image ----
FROM python:3.14-alpine@sha256:a1321512d6a287428c50dcdf2ab3857761127e03a23b1f648e9c1c0de59288f8

# Create a non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S -G appgroup appuser

WORKDIR /app

# Copy from the builder stage
COPY --from=builder /app/venv ./venv
COPY --from=builder /app/app.py .

RUN chown -R appuser:appgroup /app
USER appuser

# Activate the virtual environment for the final CMD
ENV PATH="/app/venv/bin:$PATH"

# Expose the port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/health')" || exit 1

# Define the command to run the application
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5001", "app:app"]

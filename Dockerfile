FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY streamlit_dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY streamlit_dashboard/ .

# Expose Streamlit port
EXPOSE 3000

# Health check
HEALTHCHECK CMD curl --fail http://localhost:3000/_stcore/health || exit 1

# Run Streamlit
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=3000", "--server.address=0.0.0.0", "--server.headless=true"]

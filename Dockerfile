FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Streamlit config
RUN mkdir -p /app/.streamlit
COPY .streamlit/config.toml /app/.streamlit/config.toml

# Cloud Run uses PORT env variable
ENV PORT=8080
EXPOSE 8080

# Streamlit must bind to 0.0.0.0 and use PORT from environment
ENTRYPOINT ["sh", "-c", "streamlit run scripts/09_website.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]

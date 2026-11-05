FROM python:3.12-slim
# Compilers/runtimes used by the coding sandbox
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ default-jdk-headless nodejs \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Run as an unprivileged user
RUN useradd -m runner && chown -R runner /app
USER runner
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

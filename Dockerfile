# app/Dockerfile

FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/Boat2356/Restaurant_recommendation_system.git .

# Copy the secrets.toml into the container
COPY ./.streamlit/secrets.toml /app/.streamlit/secrets.toml

RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "web_application/1_🏠_Homepage.py", "--server.port=8501", "--server.address=0.0.0.0"]
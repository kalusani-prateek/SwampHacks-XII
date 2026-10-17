# PlanIT Control: one image serving the API, background jobs and the built React app.
#   docker compose up --build        (compose.yaml; see "Run with Docker" in README.md)
# or without Compose:
#   docker build -t planit-control .
#   docker run -p 5000:5000 --env-file backend/.env -v planit-data:/app/backend/instance -v planit-uploads:/app/backend/uploads planit-control

# Stage 1: build the frontend
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend serving the built app
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=5000
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist
EXPOSE 5000
CMD ["python", "serve.py"]

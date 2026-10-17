# PlanIT Control: one image serving the API, background jobs and the built React app.
#   docker build -t planit-control .
#   docker run -p 5000:5000 -e SECRET_KEY=... -v planit-data:/app/backend/instance planit-control
# See docs/DEPLOY.md.

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

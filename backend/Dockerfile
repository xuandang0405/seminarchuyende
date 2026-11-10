FROM node:22-alpine AS web
WORKDIR /build/apps/web-admin
COPY apps/web-admin/package*.json ./
RUN npm ci
COPY apps/web-admin/ ./
COPY shared/ /build/shared/
RUN npm run build

FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY backend/ ./
COPY deploy/demo/ ./demo/
COPY --from=web /build/apps/web-admin/dist /app/apps/web-admin/dist
RUN useradd --create-home --uid 10001 tourvoice && mkdir -p storage/audio storage/images storage/packages && chown -R tourvoice:tourvoice /app
USER tourvoice
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]

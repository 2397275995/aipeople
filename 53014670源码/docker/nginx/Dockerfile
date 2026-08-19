# ---------- 游客端 Vue ----------
FROM node:20-alpine AS web-build
WORKDIR /app
COPY web-client/package.json web-client/package-lock.json* ./
RUN npm ci --prefer-offline --no-audit || npm install --no-audit
COPY web-client/ ./
ENV VITE_API_BASE_URL=
RUN npx vite build

# ---------- 管理后台 React ----------
FROM node:20-alpine AS admin-build
WORKDIR /app
COPY admin-web/package.json admin-web/package-lock.json* ./
RUN npm ci --prefer-offline --no-audit || npm install --no-audit
COPY admin-web/ ./
ENV VITE_API_BASE_URL=
ENV VITE_BASE_PATH=/admin/
RUN npx vite build

# ---------- Nginx 静态服务 ----------
FROM nginx:1.27-alpine
COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /app/dist /usr/share/nginx/html/web
COPY --from=admin-build /app/dist /usr/share/nginx/html/admin
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/health || exit 1

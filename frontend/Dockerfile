# --- Stage 1: build ---
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package.json ./
RUN npm install --legacy-peer-deps
COPY frontend/public ./public
COPY frontend/src ./src
ENV REACT_APP_API_BASE=/api
RUN npm run build

# --- Stage 2: serve ---
FROM nginx:1.27-alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# Build frontend and serve via nginx; proxy /api

FROM node:18-alpine AS frontend-build
WORKDIR /app
COPY ./frontend/package*.json ./
RUN npm ci || npm install
COPY ./frontend .
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY ./docker/nginx/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80

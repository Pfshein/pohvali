FROM node:24-alpine AS build

WORKDIR /app
ARG VITE_TELEGRAM_MODE=telegram
ENV VITE_TELEGRAM_MODE=$VITE_TELEGRAM_MODE
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.29-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

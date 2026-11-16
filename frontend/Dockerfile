# Imagen de Nginx que corre sin root (puerto 8080)
FROM nginxinc/nginx-unprivileged:1.31-alpine

USER root
RUN apk upgrade --no-cache
USER 101

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY src/ /usr/share/nginx/html/

EXPOSE 8080

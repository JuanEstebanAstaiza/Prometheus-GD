# SGDI Frontend - Static NGINX Dockerfile
# Sin Node.js - Solo archivos HTML/CSS/JS nativos

FROM nginx:1.25-alpine

# Metadata
LABEL maintainer="SGDI Team"
LABEL description="SGDI Frontend - Native HTML/CSS/JS served by NGINX"

# Remover configuración por defecto
RUN rm /etc/nginx/conf.d/default.conf

# Copiar configuración personalizada de NGINX
COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copiar archivos estáticos del frontend
# Nota: Se copian en build time. Para desarrollo usar volumes en docker-compose
COPY . /usr/share/nginx/html

# Limpiar archivos de Docker del directorio web
RUN rm -rf /usr/share/nginx/html/docker

# Exponer puerto 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/index.html || exit 1

# Comando por defecto (ya viene en imagen base nginx:alpine)
# CMD ["nginx", "-g", "daemon off;"]

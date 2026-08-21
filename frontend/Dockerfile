FROM node:24-alpine AS build
WORKDIR /app
ARG VITE_ENTRA_TENANT_ID
ARG VITE_PORTAL_CLIENT_ID
ARG VITE_PORTAL_API_SCOPE
ENV VITE_ENTRA_TENANT_ID=$VITE_ENTRA_TENANT_ID \
    VITE_PORTAL_CLIENT_ID=$VITE_PORTAL_CLIENT_ID \
    VITE_PORTAL_API_SCOPE=$VITE_PORTAL_API_SCOPE
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080

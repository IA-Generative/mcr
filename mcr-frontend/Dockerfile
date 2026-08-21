# Build
FROM node:20.11.1@sha256:e06aae17c40c7a6b5296ca6f942a02e6737ae61bbbf3e2158624bb0f887991b5 AS install

WORKDIR /app

COPY package.json ./
COPY pnpm-lock.yaml ./

RUN corepack enable
RUN pnpm install --frozen-lockfile

# Development with hot reload
FROM install AS dev

COPY . .

EXPOSE 5173
CMD ["pnpm", "run", "dev", "--host"]

FROM install AS build

COPY . .

RUN rm -f .env

RUN pnpm run build

# Serve
FROM bitnamilegacy/nginx:1.27.4@sha256:d7437d2e3a259f34703fbfe00024ef1d0540dd0422e8250a629e0f32a719cd4b AS production

COPY --from=build /app/dist /usr/share/nginx/html

COPY docker/nginx.conf /opt/bitnami/nginx/conf/server_blocks/my_app.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

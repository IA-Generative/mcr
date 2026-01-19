# Build
FROM node:20.11.1 AS install

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
FROM bitnamilegacy/nginx:1.27.4 AS production

COPY --from=build /app/dist /usr/share/nginx/html

COPY docker/nginx.conf /opt/bitnami/nginx/conf/server_blocks/my_app.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

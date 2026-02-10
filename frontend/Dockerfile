FROM node:20-slim AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

COPY . .

# Build args become env vars at build time (set in Railway dashboard)
ARG REACT_APP_BACKEND_URL
ARG REACT_APP_API_URL
ARG REACT_APP_APP_PHASE=2
ARG REACT_APP_NAME="Elevate CRM"

ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_APP_PHASE=$REACT_APP_APP_PHASE
ENV REACT_APP_NAME=$REACT_APP_NAME

RUN npm run build

# Serve static files
FROM node:20-slim AS production

WORKDIR /app

RUN npm install -g serve

COPY --from=build /app/build ./build

ENV PORT=3000
EXPOSE ${PORT}

CMD ["serve", "-s", "build", "-l", "3000"]

FROM node:20-bookworm-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*
COPY package.json ./
RUN npm install --omit=dev
COPY src ./src
ENV NODE_ENV=production PORT=3001 WHATSAPP_SESSION_DIR=/app/data/whatsapp_sessions
RUN mkdir -p /app/data/whatsapp_sessions
EXPOSE 3001
CMD ["npm", "start"]

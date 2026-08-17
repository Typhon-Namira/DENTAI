FROM node:20-bookworm-slim
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY src ./src
ENV PORT=3001 WHATSAPP_SESSION_DIR=/app/data/whatsapp_sessions
RUN mkdir -p /app/data/whatsapp_sessions
EXPOSE 3001
CMD ["npm", "start"]

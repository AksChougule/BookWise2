FROM node:20-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY package.json package-lock.json ./

# Use a non-root user for dependency install and runtime.
RUN chown -R node:node /app
USER node
RUN npm ci

# Copy app sources after dependencies.
COPY --chown=node:node . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

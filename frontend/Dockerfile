FROM node:20-alpine

RUN apk add --no-cache bash

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm
RUN npm install -g pnpm

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build for production
RUN pnpm build

# Expose port 5173 (default Vite preview port)
EXPOSE 5173

# Serve production build
CMD ["pnpm", "preview", "--host", "0.0.0.0", "--port", "5173"]

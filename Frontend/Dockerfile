# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY Frontend/package*.json ./
RUN npm ci
# Copy app sources (contents of Frontend into /app)
COPY Frontend/ ./
# If your Vite app uses a base path, set it here or in vite.config.js
RUN npm run build

# --- runtime stage (nginx) ---
FROM nginx:alpine
# SPA fallback for client-side routing + /api proxy
COPY Frontend/nginx.conf /etc/nginx/conf.d/default.conf
# Copy Vite build output
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
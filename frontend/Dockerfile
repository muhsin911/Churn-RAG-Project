FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html ./
COPY vite.config.js tailwind.config.js ./
COPY src ./src
COPY public ./public

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
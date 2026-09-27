FROM node:20-alpine
WORKDIR /srv/web
# 严格按锁文件安装可复现依赖
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

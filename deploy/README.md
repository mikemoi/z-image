# 上服务器部署

单容器全栈(前端 dist 打进后端镜像,单端口 8000)+ 自带 PostgreSQL(首次启动自动建库)。

## 步骤

```bash
git clone https://github.com/mikemoi/z-image.git
cd z-image
cp .env.example .env
# 改掉 .env 里的 POSTGRES_PASSWORD / AUTH_TOKEN / OPENROUTER_API_KEY
docker compose up -d --build
```

访问 `http://<服务器IP>:8000`,前端口令填 `.env` 里的 `AUTH_TOKEN`。

## 几个关键点

- **建库**:`deploy/init.sql` 在 db 容器首次启动时自动执行(数据卷 `pgdata` 已存在则跳过)。用外部 PG 就手动 `psql -d zbrain -f deploy/init.sql`。
- **原图**:落宿主机 `/data/zbrain/files`,是唯一副本——**单独配定期备份**,磁盘挂=图没了。
- **反代/HTTPS**:前面挂 Nginx(1Panel)反代到 `:8000`,配好证书;`upload/delete` 别裸奔公网。
- **已有外部 PG**:删掉 compose 的 `db` 服务,把 `DATABASE_URL` 指向你的 PG。

## 更新

```bash
git pull && docker compose up -d --build
```

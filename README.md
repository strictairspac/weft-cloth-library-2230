# 纬回布库·捐布分级汇总

撤销旧贡献再累加新贡献，和 SQL 全量汇总核对仓位重量与件数。面向演示数据和本地复现，场景、操作剧本和业务边界见 [BUSINESS.md](BUSINESS.md)。

## 业务模块

- 捐赠称重
- 批次修正
- 增量汇总
- 仓位配额单

## 本地运行

```sh
cp -n .env.example .env
docker compose up -d --build --wait
```

- 工作台 `http://127.0.0.1:18300`
- FastAPI 文档 `http://127.0.0.1:19300/docs`
- PostgreSQL 16 端口 `127.0.0.1:17800`，账号 `app`，演示库 `workflow`
- `docker compose exec -T backend python -m scripts.seed_demo` 手动重跑演示数据
- `docker compose logs -f backend worker` 查看运行情况
- `docker compose down` 停容器并保留演示卷

### 演示账号

统一密码 `Demo-Walkthrough-2026`。

| 账号 | 角色 | 能执行的操作 |
|---|---|---|
| `operator` | 经办员 | 读取档案、创建实验输入、提交执行、导出结果 |
| `reviewer` | 复核员 | 读取、导出和签署结果 |
| `viewer` | 观察员 | 读取、导出已有结果 |

`SEED_DEMO=true` 启动时生成账号与一个业务样例。工作台新建档案会预填样例。可编辑表单中的数值、文本和结构化 JSON 后提交。业务说明中的原始文件是上游示例，演示数据通过表单录入。角色枚举位于后端 `src/constants/workflow.py` 与前端 `src/constants/workflow.js`。执行状态枚举也位于这两个文件，使用于队列、列表和执行详情。证据校验码是报告 JSON 按 UTF-8、键排序且省略多余空格序列化后的 SHA-256。

## 裁切组同步接口

复核员签署仓位配额单后，系统在**同一事务**内把可发单据写入同步流：签署与开放给裁切组同生同灭，重复签署返回 409 且不会重复发出。暂停发单的报告（版本冲突、库存差异）即使签署也不进入同步流。

| 接口 | 权限 | 说明 |
|---|---|---|
| `GET /api/dispatch/pull?cursor=N&limit=M` | 登录用户 | 返回位点大于 `N` 的已签可发单据（升序，上限 500 条/页），附 `next_cursor` 续拉位置与当前水位 `horizon` |
| `GET /api/dispatch/rebuild` | 登录用户 | 返回同一时点的全量已签可发单据与对应续拉位置 `cursor` |
| `POST /api/dispatch/cleanup` | 复核员 | 清理位点不超过 `upto` 的同步记录，请求体 `{"upto": N}` |

同步位点由签署事务内的计数器按提交顺序分配，因此并发签单时从 `next_cursor` 续拉不会漏单。重建返回的全量与 `cursor` 对应同一时点，重建期间新签的单据用该 `cursor` 续拉即可取回，不重不漏。清理后若 `cursor` 小于已清理水位，`pull` 返回 410，提示调用 `rebuild` 重建全量后从新位置续拉；`cursor` 超过当前水位返回 409。每条同步记录携带配额单全文、签署人、签署时间与证据校验码，裁切组可离线核对。

同步接口测试（需要可连接 127.0.0.1:17800 的 PostgreSQL 16，自动建删 `workflow_test` 库）：

```sh
cd backend && python -m pytest tests/test_dispatch.py -q
```

## 工程结构

| 服务 | 实现 |
|---|---|
| frontend | Nginx 与原生 HTML、CSS、JavaScript |
| backend | Python 3.11、FastAPI、SQLAlchemy |
| worker | Python 持久队列执行与 Redis 唤醒信号 |
| db | PostgreSQL 16，持久卷保存档案、执行、证据及审计 |
| redis | Redis 7，追加日志卷保存队列唤醒信号 |

编辑 `backend/src/services/domain.py` 可修改试算方法与业务表单说明。API 路由、数据定义和页面位于 `backend/src/routes/`、`backend/src/models/` 与 `frontend/src/pages/`。开发时更新源文件后重新构建对应服务。

`.env.example` 提供 `FRONTEND_PORT`、`BACKEND_PORT`、`DB_PORT`、`DB_PASSWORD`、`AUTH_KEY` 、`SEED_DEMO` 与 `NETWORK_SUBNET`。修改 `NETWORK_SUBNET` 可避开本机现有容器网段。所有发布的端口绑定本机回环地址。接入独立部署前需配置自己的凭据并按业务范围做独立验收。

[MIT License](LICENSE)

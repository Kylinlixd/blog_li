# IP 属地与仪表盘数据

生产路径 `/opt/blog_li`；新增迁移 `access_log.0004_ipgeocache`。

手动补全未缓存、过期或失败的 IP：

```sh
.venv/bin/python manage.py refresh_ip_geo
```

强制重新查询所有历史公网 IP：

```sh
.venv/bin/python manage.py refresh_ip_geo --all
```

命令按 IP 去重，跳过非公网地址，默认每次查询间隔 0.2 秒。查询失败保留已有成功结果并以非零状态退出；再次执行会重试失败项。360 接口需要浏览器 User-Agent 和来源 Referer，已在请求中设置。

`ops/systemd/blog-ip-geo.service` 与 `.timer` 使用生产路径和 blog 用户，每次结束十分钟后再次补全。生产已启用。

访问画像支持 `risk=low|medium|high|critical`、`network=private|public`、`region=省份或城市关键字`、`ip=地址片段或CIDR`。条件在分页前组合应用。网络 private 包括非公网地址，原始 scope 保留回环、内网等类型；生效白名单覆盖评分为低风险，过期或撤销即恢复计算。

仪表盘按上海时区今天及前六个自然日统计：文章仅计已发布内容，PV 为成功 GET 公开详情接口，UV 按 IP＋UA 去重；30 分钟无访问拆分会话，跳出率为单次阅读会话比例，属于估算。主题与热门文章使用已发布文章累计阅读量。

风险画像批量读取固定 5 次数据库查询；页面筛选不等待在线提供方，单个画像与后台刷新负责补全缓存。

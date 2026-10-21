# Agent Instructions

Decky 插件，控制 deck 上的 clash (mihomo) TUN 服务做分流加速。
插件只是遥控器；加速由独立的 `steam-clash.service` 提供，卸载 Decky 不影响加速。

## Package Manager
Use **npm**: `npm install`, `npm run build`（rollup，入口固定 `src/index.tsx`）

## File-Scoped Commands
| Task | Command |
|------|---------|
| 构建前端 | `npm run build` |
| 校验安装脚本 | `bash -n install.sh` |
| 生成 clash 配置 | `python3 tools/gen_clash_config.py <surge.conf> /tmp/clash.yaml` |
| 校验 clash 配置 | 在 deck 上：`clash -t -d /home/deck/clash-steam -f <yaml>` |
| 后端单测 | mock `decky` 模块后直接 `asyncio.run(Plugin().get_status())`，见 README「开发」 |

## Commit Attribution
AI commits MUST include:
```
Co-Authored-By: <agent name> <noreply@example.com>
```

## Key Conventions

- **`香港加速` 是硬编码契约** —— `main.py` 的 `GROUP` 常量与配置文件 `proxy-groups` 里该组名必须一致，改名要同步两处
- **`dist/index.js` 必须提交** —— Decky 直接加载产物，不做服务端构建
- **凭据绝不入库** —— `.gitignore` 拦 `*.yaml/*.yml/*.conf/.env`；只有 `config.example.yaml` 例外（含占位符）
- **改代码后必须重新构建再部署**，`install.sh` 只拷贝 `dist/`，不会自动 build
- Python 方法必须 `async`；Decky 通过 websocket 调用，**单次调用控制在 10s 内**，批量操作要 `asyncio.gather` 并发（`test_all_delay` 曾因串行 60s 触发 `PluginStopped`）
- 插件名 `SteamProxy` 会拼进 URL，不要加空格

## Fixed Paths
| 路径 | 用途 |
|---|---|
| `/home/deck/homebrew/plugins/SteamProxy` | 插件部署位置（root 所有） |
| `/home/deck/clash-steam/` | 内核 `bin/clash`、配置 `config.yaml`(600)、面板 `web/` |
| `/etc/systemd/system/steam-clash.service` | 加速服务单元 |
| `127.0.0.1:9090` | clash RESTful API（切换节点/测延迟） |

## Deploy
```bash
npm run build && sudo ./install.sh          # 配置已存在则复用
```

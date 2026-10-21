# Steam Proxy

> Steam Deck 的Decky 插件：**只代理被墙的站点**，国内流量和游戏下载 CDN 走直连。

[![Decky](https://img.shields.io/badge/Decky-3.x-blue)](https://github.com/SteamDeckHomebrew/decky-loader)

## 为什么需要它

Steam Deck 在国内的三个痛点：

| 场景 | 问题 | 本方案 |
|---|---|---|
| Steam 商店/社区 | 打不开、图片加载慢 | 走香港节点 |
| 游戏下载 | 走代理反而更慢 | **直连**国内 CDN |
| GitHub / Google | 下载插件、查资料 | 走香港节点 |

而且是**真 TUN 模式**——不只是浏览器走代理，Steam 客户端本身也能被加速。

## 特性

- 香港节点 `url-test` 自动选优（12 节点，每 5 分钟测速切换）
- 94 条分流规则：Steam / Google / GitHub / npm / PyPI / Docker / OpenAI / Claude / X / Telegram / Discord / Reddit …
- 游戏下载 CDN 与国内站点直连，下载速度不受影响
- 局域网直连，保护 SSH / Steam Link / 投屏
- 插件内操作：开关服务、切换节点、并发测延迟（0.2s）
- **插件与 clash 服务解耦**——即使卸载 Decky，加速照常运行

## 快速开始

### 前置条件

1. Steam Deck（SteamOS 3.5+，LCD/OLED 均可）
2. 已装 [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)
   （没装也行，`install.sh` 会自动装）
3. **一份可用的代理节点**（见下节）

### 节点怎么来

本仓库**不含任何节点**，你需要自备。三种方式：

**方式 A：有 Surge 配置**（最省事）

```bash
# 从 Surge 配置自动提取香港节点，生成 clash 配置
python3 tools/gen_clash_config.py ~/path/to/your-surge.conf /tmp/clash.yaml
```

**方式 B：有 clash/v2ray 订阅链接**

把订阅内容导出成 yaml（或在浏览器里打开订阅链接另存），确保里面 `proxies:` 段是标准 mihomo 格式。

**方式 C：手动填**

```bash
cp config.example.yaml /tmp/clash.yaml
# 编辑 /tmp/clash.yaml，把 proxies 段换成你自己的节点
```

> ⚠️ `proxy-groups` 里必须有一个叫 **`香港加速`** 的组，插件靠这个名字识别。

### 安装

```bash
git clone https://github.com/chenpx976/steamproxy.git
cd steamproxy
sudo ./install.sh /tmp/clash.yaml
```

脚本会依次完成：
1. 检查/安装 Decky Loader
2. 下载 mihomo 内核到 `/home/deck/clash-steam/bin/`
3. 导入分流配置（`chmod 600`）
4. 部署插件到 `~/homebrew/plugins/SteamProxy/`
5. 注册 `steam-clash.service` 开机自启，并做连通性验证

### 使用

Decky 侧栏（`...` → 电源图标）→ **Steam Proxy**

- **启用加速**：开关（直接 start/stop systemd 服务）
- **节点下拉**：12 个节点任选，自动选优兜底
- **测试所有节点延迟**：0.2 秒出结果，直接标在节点名后

## 架构

```
┌─────────────────────────────────────┐
│ Decky 插件  SteamProxy              │
│   main.py     → systemctl + REST API│
│   index.tsx   → 开关/选节点/测速    │
└──────────────┬──────────────────────┘
               │ 控制
┌──────────────▼──────────────────────┐
│ steam-clash.service (systemd 自启)  │
│   /home/deck/clash-steam/bin/clash  │
│   /home/deck/clash-steam/config.yaml│
│   TUN 接口 → 全局分流               │
└─────────────────────────────────────┘
```

插件只是"遥控器"，服务才是本体。两者可独立存在。

## 命令行管理

```bash
# 状态
systemctl status steam-clash

# 开关
sudo systemctl start|stop|restart steam-clash

# 当前节点
curl -s http://127.0.0.1:9090/proxies | jq -r '."香港加速".now'

# 手动切节点
curl -X PUT http://127.0.0.1:9090/proxies/香港加速 -d '{"name":"节点名"}'

# 网页面板（zashboard，需先放静态文件到 config 的 external-ui）
http://127.0.0.1:9090/ui
```

## 更新节点/规则

```bash
python3 tools/gen_clash_config.py ~/your-surge.conf /tmp/clash.yaml
scp /tmp/clash.yaml deck@<ip>:/tmp/
ssh deck@<ip> 'sudo cp /tmp/clash.yaml /home/deck/clash-steam/config.yaml && \
               sudo chmod 600 /home/deck/clash-steam/config.yaml && \
               sudo systemctl restart steam-clash'
```

## 开发

```bash
npm install
npm run build                     # 产出 dist/index.js
sudo ./install.sh /tmp/clash.yaml # 重新部署
```

后端 `main.py` 可脱离 Decky 单测：

```bash
sudo python3 - <<'PY'
import asyncio, sys, types, logging
fake = types.ModuleType('decky'); fake.logger = logging.getLogger('d'); sys.modules['decky'] = fake
sys.path.insert(0, '/home/deck/homebrew/plugins/SteamProxy')
import main
print(asyncio.run(main.Plugin().get_status()))
PY
```

## 卸载

```bash
sudo systemctl disable --now steam-clash
sudo rm -rf /home/deck/clash-steam ~/homebrew/plugins/SteamProxy
sudo rm -f /etc/systemd/system/steam-clash.service
sudo systemctl daemon-reload
```

## 常见问题

**Q: 装完 google 能开但国内网站变慢了？**
检查是否有别的东西在抢路由：`ip rule show | grep -v 'lookup main'`。UU 加速器等会和 TUN 冲突。

**Q: 改了 `香港加速` 这个名字就不工作了？**
插件按名字查找节点组，改名需同步改 `main.py` 里的 `GROUP`。

**Q: 节点全超时？**
先在 deck 上确认能连通节点服务器：`curl -v telnet://<server>:<port>`。

## 许可

MIT

# Steam Proxy (Decky 插件)

给 Steam Deck 做**分流加速**的 Decky 插件：只代理被墙的站点，国内流量和游戏下载 CDN 走直连。

## 特性

- **香港节点自动选优**（12 个节点，`url-test` 每 5 分钟测速切换）
- **按域名分流**：Steam 商店/社区、Google、GitHub、npm/PyPI、X/Telegram、OpenAI/Claude 等 94 条规则
- **游戏下载 CDN 直连**：`steamcontent.com`、`st.dl.*` 等不走代理，下载速度不受影响
- **局域网直连**：保护 SSH、Steam Link、投屏
- **插件内操作**：开关 / 切换节点 / 一键测延迟

## 架构

```
Decky 插件 (SteamProxy)
  ├─ main.py        控制 systemd 服务 + 调 clash REST API
  └─ src/index.tsx  开关 / 节点下拉 / 测速

steam-clash.service (systemd, 开机自启)
  └─ clash (mihomo) + TUN 模式
       └─ /home/deck/clash-steam/config.yaml
```

插件与 clash 服务解耦：即使 Decky 被卸载，加速服务仍独立运行。

## 构建

```bash
npm install
npm run build
```

## 安装到 Steam Deck

```bash
scp -r plugin.json package.json main.py dist deck@<ip>:/tmp/steamproxy-dist/
ssh deck@<ip> 'sudo rm -rf ~/homebrew/plugins/SteamProxy && \
  sudo cp -r /tmp/steamproxy-dist ~/homebrew/plugins/SteamProxy && \
  sudo chmod -R a+rX ~/homebrew/plugins/SteamProxy && \
  sudo systemctl restart plugin_loader'
```

## 刷新节点配置

节点凭据来自 Surge 配置，用生成脚本产出 clash 配置：

```bash
python3 tools/gen_clash_config.py   # 输出 /tmp/deck_clash.yaml
scp /tmp/deck_clash.yaml deck@<ip>:/tmp/
ssh deck@<ip> 'sudo cp /tmp/deck_clash.yaml /home/deck/clash-steam/config.yaml && \
  sudo chmod 600 /home/deck/clash-steam/config.yaml && \
  sudo systemctl restart steam-clash'
```

## 许可

MIT

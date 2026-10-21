#!/usr/bin/env bash
# Steam Proxy 一键安装脚本（SteamOS / Steam Deck）
# 用法: sudo ./install.sh [你的-clash-配置.yaml]
set -euo pipefail

MIHOMO_VER="v1.19.32"
HOMEBREW="/home/deck/homebrew"
PLUGIN_DIR="$HOMEBREW/plugins/SteamProxy"
BASE="/home/deck/clash-steam"
SRC="$(cd "$(dirname "$0")" && pwd)"

[ "$(id -u)" -eq 0 ] || exec sudo "$0" "$@"

say() { printf '\033[36m==>\033[0m %s\n' "$1"; }
die() { printf '\033[31m❌ %s\033[0m\n' "$1" >&2; exit 1; }

say "1/5 检查 Decky Loader"
if [ ! -x "$HOMEBREW/services/PluginLoader" ]; then
    echo "    未检测到 Decky，正在安装..."
    curl -fsSL https://github.com/SteamDeckHomebrew/decky-installer/raw/main/cli/install_release.sh | sh
else
    echo "    已安装: $(cat "$HOMEBREW/services/.loader.version" 2>/dev/null || echo '?')"
fi
touch /home/deck/.steam/steam/.cef-enable-remote-debugging

say "2/5 准备 clash 内核 (mihomo $MIHOMO_VER)"
mkdir -p "$BASE/bin" "$BASE/web"
if [ -x "$BASE/bin/clash" ]; then
    echo "    已存在: $("$BASE/bin/clash" -v 2>/dev/null | head -1)"
else
    tmp="$(mktemp -d)"
    url="https://github.com/MetaCubeX/mihomo/releases/download/$MIHOMO_VER/mihomo-linux-amd64-compatible-$MIHOMO_VER.gz"
    echo "    下载 $url"
    curl -fsSL --retry 3 -o "$tmp/mihomo.gz" "$url"
    gunzip -c "$tmp/mihomo.gz" > "$BASE/bin/clash"
    chmod +x "$BASE/bin/clash"
    rm -rf "$tmp"
    echo "    已安装: $("$BASE/bin/clash" -v 2>/dev/null | head -1)"
fi

say "3/5 检查分流配置"
if [ ! -f "$BASE/config.yaml" ]; then
    if [ -n "${1:-}" ] && [ -f "$1" ]; then
        cp "$1" "$BASE/config.yaml"
        echo "    已导入 $1"
    else
        die "缺少 $BASE/config.yaml
    请先准备配置（参考 config.example.yaml），然后重跑:
      sudo ./install.sh /path/to/your-config.yaml"
    fi
fi
chmod 600 "$BASE/config.yaml"

say "4/5 部署插件"
rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"
cp -r "$SRC/plugin.json" "$SRC/package.json" "$SRC/main.py" "$SRC/dist" "$PLUGIN_DIR/"
chown -R root:root "$PLUGIN_DIR"
chmod -R a+rX "$PLUGIN_DIR"

say "5/5 注册开机自启服务"
cat > /etc/systemd/system/steam-clash.service <<EOM
[Unit]
Description=Clash Steam Accelerator
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$BASE
ExecStart=$BASE/bin/clash -d $BASE -f $BASE/config.yaml
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOM
systemctl daemon-reload
systemctl enable steam-clash >/dev/null 2>&1
systemctl restart steam-clash
systemctl restart plugin_loader 2>/dev/null || true

sleep 8
say "验证"
if systemctl is-active --quiet steam-clash; then
    echo "    clash 服务 : 运行中"
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://www.google.com || echo 000)
    echo "    google    : HTTP $code"
    node="$(curl -s --max-time 5 http://127.0.0.1:9090/proxies 2>/dev/null \
        | jq -r 'to_entries[] | select(.value.type=="URLTest") | .value.now' 2>/dev/null \
        | head -1)"
    echo "    当前节点  : ${node:-(读取失败)}"
    echo
    echo "✅ 安装完成。打开 Decky 侧栏 → Steam Proxy"
else
    die "服务启动失败，查看日志: journalctl -u steam-clash -n 50"
fi

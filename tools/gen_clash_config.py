import re

import os
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('SURGE_CONF', '')
OUT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/deck_clash.yaml'
if not SRC or not os.path.isfile(SRC):
    sys.exit('用法: gen_clash_config.py <Surge配置.conf> [输出.yaml]')

lines = open(SRC, encoding='utf-8').read().splitlines()
start = lines.index('[Proxy]')
end = next(i for i, l in enumerate(lines) if l.strip() == '[Proxy Group]')

proxies = []
for l in lines[start + 1:end]:
    l = l.strip()
    if not l or l.startswith('#') or '=' not in l:
        continue
    name, rest = l.split('=', 1)
    name = name.strip()
    if '香港' not in name:
        continue
    parts = [p.strip() for p in rest.split(',')]
    if parts[0] != 'trojan':
        continue
    kv = {}
    for p in parts[3:]:
        if '=' in p:
            k, v = p.split('=', 1)
            kv[k.strip()] = v.strip()
    proxies.append(dict(
        name=name, server=parts[1], port=int(parts[2]),
        password=kv.get('password', ''), sni=kv.get('sni', ''),
        skip=kv.get('skip-cert-verify', 'true') == 'true',
        udp=kv.get('udp-relay', 'true') == 'true',
    ))

assert proxies, 'no HK proxies found'
proxies.sort(key=lambda p: (0 if '高级' in p['name'] else 1 if '标准' in p['name'] else 2, p['name']))

# ---------- 规则表 ----------
PROXY = '香港加速'

# 精确域名直连：Steam 靠这些判断用户位置，代理会让它误判成香港
DIRECT_EXACT = [
    'api.steampowered.com',      # 内容服务器目录 / 位置探测
]

DIRECT_ONLY = [
    # Steam 游戏下载 CDN（国内直连更快，走代理反而拖慢）
    'steamcontent.com', 'steamcdn-a.akamaihd.net', 'steamcontent.tnkjmec.com',
    'dl.steam.clngaa.com', 'st.dl.eccdnx.com', 'st.dl.bscstorage.net',
    'st.dl.pinyuncloud.com', 'dl.steam.ksyna.com', 'csgo.wmsj.cn', 'dota2.wmsj.cn',
    # Steam CM 联机服务器：走代理会干扰匹配、P2P 与下载调度
    'steamserver.net',
    # 国内站点引用广泛，走代理只会变慢
    'google-analytics.com', 'googletagmanager.com', 'cnzz.com',
]

VIA_PROXY = {
    'Steam': [
        'steampowered.com', 'steamcommunity.com', 'steamstatic.com', 'steamusercontent.com',
        'steam-chat.com', 'steamgames.com', 'steamtv.com', 'valvesoftware.com',
        'steamconnect.net', 'steamdiscussions.com', 'steamdeck.com',
        'underlords.com', 'dota2.com', 'counter-strike.net',
    ],
    'Google': [
        'google.com', 'googleapis.com', 'gstatic.com', 'googleusercontent.com',
        'googlevideo.com', 'ggpht.com', 'gvt1.com', 'gvt2.com', 'withgoogle.com',
        'google.co.jp', 'google.com.hk', 'google.com.tw', 'google.dev',
        'youtube.com', 'youtu.be', 'ytimg.com', 'youtube-nocookie.com',
        'recaptcha.net', 'android.com', 'blogger.com', 'blogspot.com',
    ],
    'GitHub': [
        'github.com', 'githubusercontent.com', 'githubassets.com', 'github.io',
        'github.dev', 'githubcopilot.com', 'githubstatus.com', 'ghcr.io',
    ],
    '开发': [
        'npmjs.org', 'npmjs.com', 'yarnpkg.com', 'pypi.org', 'pythonhosted.org',
        'rubygems.org', 'crates.io', 'docker.io', 'docker.com', 'gcr.io',
        'quay.io', 'jetbrains.com', 'gradle.org', 'maven.apache.org',
        'archlinux.org', 'huggingface.co', 'hf.co', 'stackoverflow.com',
        'stackexchange.com', 'srv.us', 'gitlab.com',
    ],
    'AI': [
        'openai.com', 'chatgpt.com', 'oaistatic.com', 'oaiusercontent.com',
        'anthropic.com', 'claude.ai', 'gemini.google.com', 'perplexity.ai',
    ],
    '社交媒体': [
        'x.com', 'twitter.com', 'twimg.com', 't.co',
        'telegram.org', 't.me', 'telegra.ph', 'tdesktop.com', 'telegram.me',
        'discord.com', 'discordapp.com', 'discord.gg', 'discordapp.net',
        'reddit.com', 'redd.it', 'redditmedia.com', 'redditstatic.com',
        'wikipedia.org', 'wikimedia.org', 'medium.com', 'quora.com',
        # 图床：Steam 商店/社区页面大量引用，国内直连不通
        'imgur.com', 'imgur.io',
    ],
}

def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

def build():
    o = []
    o += ['tun:', '  enable: true', '  stack: mixed',
          '  dns-hijack:', '    - any:53', '    - tcp://any:53',
          '  auto-route: true', '  auto-detect-interface: true',
          '  strict-route: false', '  mtu: 1500', '']
    o += ['mixed-port: 7890', 'allow-lan: false', 'bind-address: 127.0.0.1',
          'mode: rule', 'log-level: warning', 'ipv6: false',
          'unified-delay: true', 'tcp-concurrent: true',
          'find-process-mode: "off"', 'external-controller: 127.0.0.1:9090',
          'external-ui: /home/deck/homebrew/plugins/tomoon/bin/core/web/zashboard',
          'external-ui-name: zashboard', 'secret: ""', '']
    o += ['dns:', '  enable: true', '  ipv6: false', '  enhanced-mode: fake-ip',
          '  fake-ip-range: 198.18.0.1/16', '  fake-ip-filter:']
    for d in ['*.lan', '*.local', '*.localdomain', 'localhost.ptlogin2.qq.com',
              '+.stun.*.*', 'time.*.com', 'ntp.*.com', '+.ntp.org.cn',
              '+.pool.ntp.org', 'localhost.sec.qq.com', '+.market.xiaomi.com']:
        o.append(f'    - {q(d)}')
    o += ['  default-nameserver:', '    - 223.5.5.5', '    - 119.29.29.29']
    o += ['  nameserver:']
    for d in ['223.5.5.5', '119.29.29.29', 'https://dns.alidns.com/dns-query']:
        o.append(f'    - {q(d)}')
    o += ['  fallback:']
    for d in ['https://1.1.1.1/dns-query', 'https://dns.google/dns-query']:
        o.append(f'    - {q(d)}')
    o += ['  fallback-filter:', '    geoip: false', '    ipcidr:',
          '      - 240.0.0.0/4', '      - 0.0.0.0/32', '']

    o += ['rule-providers:',
          '  gfw:',
          '    type: http',
          '    behavior: domain',
          '    format: yaml',
          '    url: "https://raw.githubusercontent.com/Loyalsoldier/clash-rules/release/gfw.txt"',
          '    path: ./ruleset/gfw.yaml',
          '    interval: 86400',
          '']

    o.append('proxies:')
    for p in proxies:
        o += [f'  - name: {q(p["name"])}', '    type: trojan',
              f'    server: {p["server"]}', f'    port: {p["port"]}',
              f'    password: {q(p["password"])}']
        if p['sni']:
            o.append(f'    sni: {p["sni"]}')
        o += [f'    skip-cert-verify: {"true" if p["skip"] else "false"}',
              f'    udp: {"true" if p["udp"] else "false"}',
              '    client-fingerprint: chrome']

    o += ['', 'proxy-groups:',
          f'  - name: {q(PROXY)}', '    type: url-test',
          '    url: "https://www.gstatic.com/generate_204"',
          '    interval: 300', '    tolerance: 50', '    lazy: false',
          '    proxies:']
    for p in proxies:
        o.append(f'      - {q(p["name"])}')
    o += ['  - name: "手动选择"', '    type: select', '    proxies:',
          f'      - {q(PROXY)}']
    for p in proxies:
        o.append(f'      - {q(p["name"])}')
    o.append('      - DIRECT')

    o += ['', 'rules:']
    # 局域网优先
    for cidr in ['127.0.0.0/8', '192.168.0.0/16', '10.0.0.0/8',
                 '172.16.0.0/12', '169.254.0.0/16']:
        o.append(f'  - IP-CIDR,{cidr},DIRECT,no-resolve')
    # 精确域名直连（优先级最高）
    for d in DIRECT_EXACT:
        o.append(f'  - DOMAIN,{d},DIRECT')
    # 直连白名单
    for d in DIRECT_ONLY:
        o.append(f'  - DOMAIN-SUFFIX,{d},DIRECT')
    # 需要加速的站点
    for group, domains in VIA_PROXY.items():
        o.append(f'  # {group}')
        for d in domains:
            o.append(f'  - DOMAIN-SUFFIX,{d},{PROXY}')
    o.append(f'  # 通用被墙域名规则集（4.4k 条，自动更新）')
    o.append(f'  - RULE-SET,gfw,{PROXY}')
    o.append('  - MATCH,DIRECT')
    return '\n'.join(o) + '\n'

yaml = build()
open(OUT, 'w', encoding='utf-8').write(yaml)
total = sum(len(v) for v in VIA_PROXY.values())
print(f'生成 {OUT}  ({len(yaml)} bytes)')
print(f'香港节点 {len(proxies)} 个 | 加速域名 {total} 条 | 直连白名单 {len(DIRECT_ONLY)} 条')

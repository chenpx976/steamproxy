import asyncio
import json
import subprocess

import aiohttp
import decky

API = "http://127.0.0.1:9090"
GROUP = "香港加速"
SERVICE = "steam-clash"


async def _api(method: str, path: str, payload=None):
    """调用 clash RESTful API"""
    url = API + path
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.request(method, url, json=payload) as resp:
            text = await resp.text()
            try:
                return resp.status, json.loads(text) if text else None
            except json.JSONDecodeError:
                return resp.status, text


def _is_running() -> bool:
    try:
        out = subprocess.run(
            ["systemctl", "is-active", SERVICE],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() == "active"
    except Exception:
        return False


async def _group_info():
    """返回 (当前节点, 全部节点列表)"""
    status, data = await _api("GET", f"/proxies/{_quote(GROUP)}")
    if status != 200 or not isinstance(data, dict):
        return None, []
    return data.get("now"), data.get("all", [])


class Plugin:
    async def get_status(self):
        running = _is_running()
        node, nodes = (None, [])
        if running:
            try:
                node, nodes = await _group_info()
            except Exception as e:
                decky.logger.warning(f"clash API 不可达: {e}")
        return {
            "running": running,
            "node": node,
            "count": len(nodes),
        }

    async def get_nodes(self):
        _, nodes = await _group_info()
        return nodes

    async def set_enabled(self, enabled: bool):
        action = "start" if enabled else "stop"
        try:
            subprocess.run(
                ["systemctl", action, SERVICE],
                capture_output=True, text=True, timeout=30,
            )
        except Exception as e:
            decky.logger.error(f"systemctl {action} 失败: {e}")
            return {"ok": False, "running": _is_running()}

        if enabled:
            for _ in range(15):
                await asyncio.sleep(1)
                try:
                    status, _ = await _api("GET", "/version")
                    if status == 200:
                        break
                except Exception:
                    pass
        return {"ok": True, "running": _is_running()}

    async def set_node(self, name: str):
        status, _ = await _api(
            "PUT", f"/proxies/{_quote(GROUP)}", {"name": name}
        )
        return {"ok": status in (200, 204), "node": name if status in (200, 204) else None}

    async def test_delay(self, name: str):
        """测试单个节点延迟，失败返回 -1"""
        probe = "http://www.gstatic.com/generate_204"
        path = f"/proxies/{_quote(name)}/delay?url={_quote(probe)}&timeout=5000"
        try:
            status, data = await _api("GET", path)
            if status == 200 and isinstance(data, dict):
                return data.get("delay", -1)
        except Exception as e:
            decky.logger.warning(f"延迟测试失败 {name}: {e}")
        return -1

    async def test_all_delay(self):
        """并发测所有节点延迟，返回 {节点名: 延迟ms}（-1 表示失败）"""
        _, nodes = await _group_info()
        if not nodes:
            return {}
        results = await asyncio.gather(
            *(self.test_delay(n) for n in nodes), return_exceptions=True
        )
        return {
            name: (r if isinstance(r, int) else -1)
            for name, r in zip(nodes, results)
        }

    async def _main(self):
        decky.logger.info("Steam Proxy 后端已启动")

    async def _unload(self):
        decky.logger.info("Steam Proxy 后端已卸载")


def _quote(s: str) -> str:
    from urllib.parse import quote
    return quote(s, safe="")

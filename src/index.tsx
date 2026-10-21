// @ts-nocheck
import {
  PanelSection,
  PanelSectionRow,
  ToggleField,
  Dropdown,
  ButtonItem,
  Field,
  staticClasses,
} from "@decky/ui";
import { call } from "@decky/api";
import { useEffect, useState, useCallback } from "react";
import { FaGlobeAsia } from "react-icons/fa";

const Content = () => {
  const [running, setRunning] = useState(false);
  const [node, setNode] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState("");
  const [delays, setDelays] = useState({});

  const refresh = useCallback(async () => {
    try {
      const s = await call("get_status");
      setRunning(s.running);
      setNode(s.node);
      if (s.running) {
        setNodes(await call("get_nodes"));
      } else {
        setNodes([]);
      }
    } catch (e) {
      console.error("refresh failed", e);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  const toggle = async (on) => {
    setBusy(true);
    setHint(on ? "正在启动…" : "正在停止…");
    try {
      const r = await call("set_enabled", on);
      setRunning(r.running);
    } finally {
      setBusy(false);
      setHint("");
      refresh();
    }
  };

  const pick = async (name) => {
    if (!name || name === node) return;
    await call("set_node", name);
    setNode(name);
  };

  const testAll = async () => {
    setBusy(true);
    setHint("正在测速（约 10 秒）…");
    try {
      const d = await call("test_all_delay");
      setDelays(d || {});
    } finally {
      setBusy(false);
      setHint("");
    }
  };

  // 带延迟的节点列表
  const options = nodes.map((n) => {
    const d = delays[n];
    const suffix = d === undefined ? "" : d < 0 ? "  (超时)" : `  (${d}ms)`;
    return { label: n + suffix, data: n };
  });

  return (
    <PanelSection title="Steam 加速">
      <PanelSectionRow>
        <ToggleField
          label="启用加速"
          description={
            running
              ? `运行中 · ${nodes.length} 个节点可用`
              : "已关闭，全部流量直连"
          }
          checked={running}
          disabled={busy}
          onChange={toggle}
        />
      </PanelSectionRow>

      {running && nodes.length > 0 && (
        <PanelSectionRow>
          <Dropdown
            rgOptions={options}
            selectedOption={node}
            onChange={(o) => pick(o.data)}
          />
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          disabled={!running || busy}
          onClick={testAll}
        >
          {busy ? "处理中…" : "测试所有节点延迟"}
        </ButtonItem>
      </PanelSectionRow>

      {hint && (
        <PanelSectionRow>
          <Field label={hint} />
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <Field
          label="代理范围"
          description="Steam 商店/社区、Google、GitHub、npm/PyPI、X/Telegram 等；国内站点与游戏下载 CDN 直连"
        />
      </PanelSectionRow>
    </PanelSection>
  );
};

export default function () {
  return {
    title: <div className={staticClasses.Title}>Steam Proxy</div>,
    content: <Content />,
    icon: <FaGlobeAsia />,
    onDismount() {},
  };
}

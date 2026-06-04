import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMarketStore } from "../store";
import type { MarketIndex, SectorInfo } from "../types/api";
import { API_BASE } from "../types/api";

export default function Dashboard({ onSearch }: { onSearch: () => void }) {
  const navigate = useNavigate();
  const { indices, setIndices } = useMarketStore();
  const [sectors, setSectors] = useState<SectorInfo[]>([]);

  useEffect(() => {
    loadMarket();
    loadSectors();
    const timer = setInterval(loadMarket, 60000); // 每分钟刷新
    return () => clearInterval(timer);
  }, []);

  async function loadMarket() {
    try {
      const res = await fetch(`${API_BASE}/api/market/overview`);
      const json = await res.json();
      if (json.success) setIndices(json.data.indices);
    } catch {}
  }

  async function loadSectors() {
    try {
      const res = await fetch(`${API_BASE}/api/market/hot-sectors?top_n=12`);
      const json = await res.json();
      if (json.success) setSectors(json.data.sectors || []);
    } catch {}
  }

  const idxMap: Record<string, string> = {
    "000001": "上证指数", "399001": "深证成指", "399006": "创业板指", "000688": "科创50",
  };

  return (
    <div>
      {/* 大盘指数 */}
      <div className="card">
        <div className="card-header">
          <span>市场总览</span>
          <button className="nav-btn" onClick={loadMarket}>刷新</button>
        </div>
        <div className="card-body">
          <div className="market-grid">
            {Object.entries(indices).length === 0 ? (
              <div style={{ gridColumn: "1/-1", textAlign: "center", padding: 20, color: "var(--dm)" }}>加载中...</div>
            ) : (
              Object.entries(indices).map(([code, idx]: [string, MarketIndex]) => (
                <div key={code} className="market-card">
                  <div className="mc-name">{idxMap[code] || idx.name}</div>
                  <div className="mc-price">{idx.price.toFixed(2)}</div>
                  <div className={`mc-chg ${idx.change_pct >= 0 ? "up" : "down"}`}>
                    {idx.change_pct >= 0 ? "+" : ""}{idx.change_pct.toFixed(2)}%
                  </div>
                  <div className="mc-vol">成交 {idx.volume?.toFixed(0) ?? "--"} 亿</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="grid2">
        {/* 板块热点 */}
        <div className="card">
          <div className="card-header">板块热点 TOP12</div>
          <div className="card-body" style={{ padding: 8 }}>
            {sectors.length === 0 ? (
              <div style={{ textAlign: "center", padding: 20, color: "var(--dm)" }}>加载中...</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr><th>排名</th><th>板块</th><th>涨跌幅</th><th>资金净流入</th></tr>
                </thead>
                <tbody>
                  {sectors.map((s) => (
                    <tr key={s.code}>
                      <td style={{ color: "var(--dm)", width: 40 }}>{s.ranking}</td>
                      <td>{s.name}</td>
                      <td className={s.change_pct >= 0 ? "up" : "down"}>
                        {s.change_pct >= 0 ? "+" : ""}{s.change_pct.toFixed(2)}%
                      </td>
                      <td className={s.fund_flow_yi >= 0 ? "positive" : "text-red"}>
                        {s.fund_flow_yi.toFixed(1)}亿
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* 快速分析入口 */}
        <div>
          <div className="card">
            <div className="card-header">快速分析</div>
            <div className="card-body" style={{ textAlign: "center", padding: 24 }}>
              <div style={{ fontSize: 14, color: "var(--dm)", marginBottom: 12 }}>
                输入六位股票代码，获取七层全维度分析
              </div>
              <input
                className="nav-search"
                style={{ width: "100%", marginBottom: 10 }}
                placeholder="例如 600519 贵州茅台"
                id="quickSearch"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    const code = (e.target as HTMLInputElement).value.trim();
                    if (/^\d{6}$/.test(code)) navigate(`/stock/${code}`);
                  }
                }}
              />
              <button
                className="nav-btn primary"
                style={{ width: "100%" }}
                onClick={() => {
                  const input = document.getElementById("quickSearch") as HTMLInputElement;
                  const code = input?.value.trim();
                  if (code && /^\d{6}$/.test(code)) navigate(`/stock/${code}`);
                }}
              >
                开始分析
              </button>
            </div>
          </div>

          {/* 常用入口 */}
          <div className="card">
            <div className="card-header">常用功能</div>
            <div className="card-body">
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {[
                  { label: "持仓管理", path: "/portfolio" },
                  { label: "自选股", codes: "600519,300750,002594,600036,300308" },
                ].map((item) => (
                  <div
                    key={item.path}
                    style={{ padding: "8px 10px", borderRadius: 6, cursor: "pointer", background: "#070d18", fontSize: 12 }}
                    onClick={() => item.path && navigate(item.path)}
                  >
                    {item.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

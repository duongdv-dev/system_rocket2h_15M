import React from 'react';

export default function Navbar({ metadata, serverStatus, onToggleHistory, isHistoryOpen }) {
  const isOnline = serverStatus && serverStatus.server_status === 'online';
  const runId = metadata?.run_id || serverStatus?.active_run_id || "active_run";
  const totalRuns = serverStatus?.total_runs || 0;

  return (
    <header className="navbar">
      <div className="brand">
        <div className="brand-icon">X</div>
        <div className="brand-info">
          <h1>
            XAU/USD QUANT AI ENGINE 
            <span className="react-badge">WEB UI & HISTORY</span>
          </h1>
          <p>
            {metadata?.strategy_name || "Rocket 10h VN M15 • DCA Min = 0.5 ATR • TP Thích ứng: 0.8/0.5 ATR • Cắt Lỗ 14:00 VN"}
          </p>
        </div>
      </div>

      <div className="nav-badges">
        <span className={`badge ${isOnline ? 'badge-live' : 'badge-alert'}`}>
          {isOnline 
            ? `● WEB SERVER ONLINE` 
            : '○ MÁY CHỦ CHƯA BẬT'}
        </span>

        <span 
          className="badge" 
          onClick={onToggleHistory}
          style={{ 
            background: isHistoryOpen ? 'rgba(139, 92, 246, 0.25)' : 'rgba(139, 92, 246, 0.12)', 
            color: '#A78BFA', 
            border: '1px solid rgba(139, 92, 246, 0.3)',
            cursor: 'pointer'
          }}
          title="Bấm để bật/tắt xem lịch sử"
        >
          📜 LỊCH SỬ: {totalRuns} BẢN LƯU
        </span>

        <span className="badge badge-info" style={{ fontFamily: 'monospace' }}>
          🆔 {runId}
        </span>

        <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10B981', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
          {metadata?.compounding_rule ? `⚡ ${metadata.compounding_rule}` : (metadata?.stop_loss_rule || "CẮT LỖ: 14:00 VN")}
        </span>
      </div>
    </header>
  );
}

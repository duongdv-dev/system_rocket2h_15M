import React, { useState } from 'react';

export default function HistoryPanel({ 
  runs, 
  activeRunId, 
  onSelectRun, 
  onDeleteRun, 
  onRefreshHistory,
  isLoading 
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterPeriod, setFilterPeriod] = useState('all');

  const filteredRuns = (runs || []).filter(run => {
    const text = `${run.run_id} ${run.strategy_name} ${run.created_at} ${JSON.stringify(run.params || {})}`.toLowerCase();
    return text.includes(searchTerm.toLowerCase());
  });

  return (
    <section className="control-panel-card" style={{ marginBottom: '24px' }}>
      <div className="control-panel-header" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="panel-icon" style={{ background: 'linear-gradient(135deg, #8B5CF6, #6D28D9)' }}>📜</div>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              LỊCH SỬ CÁC LẦN CHẠY BACKTEST & HUẤN LUYỆN AI
              <span className="badge badge-info">{runs?.length || 0} BẢN LƯU</span>
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Toàn bộ dữ liệu được lưu vĩnh viễn trên Server (history/). Bạn có thể click chọn bất kỳ bản chạy nào trong quá khứ để xem lại toàn bộ biểu đồ, chỉ số và lệnh.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="🔍 Tìm theo ngày, ID hoặc tham số..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              fontSize: '12px',
              width: '240px'
            }}
          />
          <button 
            type="button" 
            className="preset-btn"
            onClick={onRefreshHistory}
            disabled={isLoading}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            🔄 Làm Mới
          </button>
        </div>
      </div>

      {(!filteredRuns || filteredRuns.length === 0) ? (
        <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>📂</div>
          <p style={{ fontSize: '14px', fontWeight: 500 }}>Chưa có bản chạy nào trong lịch sử.</p>
          <p style={{ fontSize: '12px', marginTop: '4px' }}>Hãy thiết lập tham số ở trên và nhấn <b>"🚀 Chạy Backtest / Train AI"</b> để tạo bản chạy đầu tiên!</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
          {filteredRuns.map((run, idx) => {
            const isActive = run.run_id === activeRunId;
            const p = run.params || {};
            const test = run.test_summary || {};
            const isWinPnl = (test.net_pnl || 0) >= 0;

            return (
              <div 
                key={run.run_id || idx}
                style={{
                  background: isActive ? 'rgba(59, 130, 246, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: isActive ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                  borderRadius: '12px',
                  padding: '16px',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ 
                      fontFamily: 'monospace', 
                      fontSize: '13px', 
                      fontWeight: 700, 
                      color: isActive ? 'var(--accent-blue)' : 'var(--text-primary)' 
                    }}>
                      🆔 {run.run_id}
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      🕒 {run.created_at}
                    </span>
                    {isActive && (
                      <span className="badge badge-live">
                        🟢 ĐANG XEM (ACTIVE)
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="copy-btn"
                      style={{
                        background: isActive ? 'var(--accent-blue)' : 'rgba(59, 130, 246, 0.15)',
                        color: isActive ? '#fff' : 'var(--accent-blue)',
                        border: '1px solid var(--accent-blue)',
                        padding: '6px 14px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: '12px'
                      }}
                      onClick={() => onSelectRun(run.run_id)}
                      disabled={isLoading}
                    >
                      {isActive ? '✓ Đang Xem' : '👁️ Xem Lại Bản Này'}
                    </button>

                    <button
                      type="button"
                      style={{
                        background: 'rgba(239, 68, 68, 0.1)',
                        color: 'var(--accent-red)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '12px'
                      }}
                      onClick={() => {
                        if (window.confirm(`Bạn có chắc muốn xóa bản chạy "${run.run_id}" khỏi lịch sử?`)) {
                          onDeleteRun(run.run_id);
                        }
                      }}
                      title="Xóa bản chạy này"
                      disabled={isLoading}
                    >
                      🗑️
                    </button>
                  </div>
                </div>

                {/* Tham số & Chỉ số tóm tắt */}
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', 
                  gap: '10px',
                  background: 'rgba(0, 0, 0, 0.2)',
                  padding: '12px',
                  borderRadius: '8px',
                  fontSize: '12px'
                }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>DCA MIN STEP</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                      {p.min_step_atr !== undefined ? `${p.min_step_atr} ATR` : '--'}
                    </div>
                  </div>

                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>TP LỆNH ĐƠN / DCA</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                      {p.tp_single_atr || '--'} / {p.tp_dca_atr || '--'} ATR
                    </div>
                  </div>

                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>GIỜ CẮT LỖ</div>
                    <div style={{ fontWeight: 600, color: '#F59E0B', marginTop: '2px' }}>
                      {p.hard_exit_hour !== undefined ? `${String(p.hard_exit_hour).padStart(2,'0')}:${String(p.hard_exit_minute || 0).padStart(2,'0')} VN` : '--'}
                    </div>
                  </div>

                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>TEST WINRATE</div>
                    <div style={{ fontWeight: 700, color: 'var(--accent-green)', marginTop: '2px' }}>
                      {test.win_rate !== undefined ? `${test.win_rate}%` : '--'}
                    </div>
                  </div>

                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>TEST NET PNL</div>
                    <div style={{ fontWeight: 700, color: isWinPnl ? 'var(--accent-green)' : 'var(--accent-red)', marginTop: '2px' }}>
                      {test.net_pnl !== undefined ? `$${Number(test.net_pnl).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '--'}
                    </div>
                  </div>

                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>MAX DRAWDOWN</div>
                    <div style={{ fontWeight: 700, color: 'var(--accent-red)', marginTop: '2px' }}>
                      {test.max_dd_percent !== undefined ? `${test.max_dd_percent}%` : '--'}
                    </div>
                  </div>

                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>PROFIT FACTOR</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                      {test.profit_factor || '--'}
                    </div>
                  </div>

                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>LỌC BÃO GIÁ</div>
                    <div style={{ fontWeight: 600, color: '#3B82F6', marginTop: '2px' }}>
                      {run.filtered_days_count !== undefined ? `${run.filtered_days_count} ngày` : '--'}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

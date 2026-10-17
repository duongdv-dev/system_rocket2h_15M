import React from 'react';

export default function MetricsGrid({ 
  data, 
  currentPeriod, 
  onPeriodChange, 
  currentMode, 
  onModeChange 
}) {
  if (!data) return null;

  const periodData = data[currentPeriod];
  if (!periodData) return null;

  const stats = periodData[currentMode] || periodData['ai'];
  const baselineStats = periodData['baseline'];
  const aiStats = periodData['ai'];

  const wins = Math.round(stats.total_trades * stats.win_rate / 100);
  const losses = stats.total_trades - wins;

  return (
    <>
      {/* Controls & Tab Selection */}
      <div className="tab-header">
        <div className="period-tabs">
          <button 
            type="button"
            className={`tab-btn ${currentPeriod === 'test' ? 'active' : ''}`}
            onClick={() => onPeriodChange('test')}
          >
            🎯 Test 5 Năm (2021-2025) [MÙ]
          </button>
          <button 
            type="button"
            className={`tab-btn ${currentPeriod === 'train' ? 'active' : ''}`}
            onClick={() => onPeriodChange('train')}
          >
            📚 Train 10 Năm (2011-2020)
          </button>
          <button 
            type="button"
            className={`tab-btn ${currentPeriod === 'all_time' ? 'active' : ''}`}
            onClick={() => onPeriodChange('all_time')}
          >
            🌐 Toàn Bộ 15 Năm (2011-2025)
          </button>
        </div>

        <div className="strategy-toggle-box">
          <span className="toggle-label">Chế độ xem:</span>
          <button 
            type="button"
            className={`tab-btn ${currentMode === 'ai' ? 'active' : ''}`}
            onClick={() => onModeChange('ai')}
          >
            ⚡ Có AI Lọc (Recommended)
          </button>
          <button 
            type="button"
            className={`tab-btn ${currentMode === 'baseline' ? 'active' : ''}`}
            onClick={() => onModeChange('baseline')}
          >
            ⚠️ Không AI (Gốc)
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <section className="metrics-grid">
        <div className="metric-card" style={{ '--card-accent': 'var(--accent-green)' }}>
          <div className="metric-title">Tỷ Lệ Thắng (Winrate) <span>🎯</span></div>
          <div className="metric-val text-green">{stats.win_rate}%</div>
          <div className="metric-sub">{wins} Win / {losses} Loss</div>
        </div>

        <div className="metric-card" style={{ '--card-accent': 'var(--accent-gold)' }}>
          <div className="metric-title">Lợi Nhuận Ròng <span>💰</span></div>
          <div className={`metric-val ${stats.net_pnl >= 0 ? 'text-gold' : 'text-red'}`}>
            ${stats.net_pnl?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div className="metric-sub">
            Vốn cuối: ${stats.final_balance?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>

        <div className="metric-card" style={{ '--card-accent': 'var(--accent-cyan)' }}>
          <div className="metric-title">Profit Factor <span>⚖️</span></div>
          <div className="metric-val text-cyan">
            {stats.profit_factor >= 90 ? '99.0+' : stats.profit_factor?.toFixed(2)}
          </div>
          <div className="metric-sub">Tỷ số Lãi / Lỗ ròng</div>
        </div>

        <div className="metric-card" style={{ '--card-accent': 'var(--accent-red)' }}>
          <div className="metric-title">Sụt Giảm Tối Đa (Max DD) <span>🛡️</span></div>
          <div className="metric-val text-red">{stats.max_dd_percent}%</div>
          <div className="metric-sub">
            -${(stats.max_dd_dollars ?? stats.max_dd_dollar ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>

        <div className="metric-card" style={{ '--card-accent': 'var(--accent-purple)' }}>
          <div className="metric-title">Tầng Lệnh DCA Nhồi <span>🧱</span></div>
          <div className="metric-val" style={{ color: 'var(--accent-purple)' }}>
            {stats.max_layers} Lệnh
          </div>
          <div className="metric-sub">Trung bình: {stats.avg_layers ? `${stats.avg_layers} lệnh/phiên` : 'Tối đa 1 lệnh/phiên'}</div>
        </div>

        <div className="metric-card" style={{ '--card-accent': 'var(--accent-blue)' }}>
          <div className="metric-title">Tổng Ngày Giao Dịch <span>📊</span></div>
          <div className="metric-val" style={{ color: 'var(--accent-blue)' }}>
            {stats.total_trades?.toLocaleString()}
          </div>
          <div className="metric-sub">
            {currentMode === 'ai' 
              ? `Lọc an toàn (${Math.round((stats.total_trades / (baselineStats?.total_trades || 1)) * 100)}% số ngày)`
              : '100% tất cả các ngày'}
          </div>
        </div>
      </section>

      {/* Head to Head Comparison Banner */}
      {baselineStats && aiStats && (
        <section className="comparison-banner">
          <div className="comparison-header">
            <h2>
              <span>🥊</span> 
              SO SÁNH ĐỐI ĐẦU: CHẠY THUẦN (BASELINE) VS CÓ BỘ LỌC BIẾN ĐỘNG (AI FILTER)
            </h2>
            <span className="badge badge-info">ĐÁNH GIÁ TRỰC DIỆN</span>
          </div>

          <table className="comp-table">
            <thead>
              <tr>
                <th>CHỈ SỐ ĐO LƯỜNG</th>
                <th>KHÔNG LỌC (BASELINE)</th>
                <th>CÓ BỘ LỌC (AI FILTER)</th>
                <th>MỨC ĐỘ CẢI THIỆN</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Tỷ Lệ Thắng (Winrate)</td>
                <td>{baselineStats.win_rate}%</td>
                <td style={{ color: 'var(--accent-green)', fontWeight: 700 }}>{aiStats.win_rate}%</td>
                <td>
                  <span className="badge-diff badge-better">
                    +{Math.max(0, (aiStats.win_rate - baselineStats.win_rate)).toFixed(1)}%
                  </span>
                </td>
              </tr>
              <tr>
                <td>Lợi Nhuận Ròng (Net PnL)</td>
                <td style={{ color: baselineStats.net_pnl >= 0 ? '#FFF' : 'var(--accent-red)' }}>
                  ${baselineStats.net_pnl?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </td>
                <td style={{ color: aiStats.net_pnl >= 0 ? 'var(--accent-gold)' : 'var(--accent-red)', fontWeight: 700 }}>
                  ${aiStats.net_pnl?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </td>
                <td>
                  <span className="badge-diff badge-better">
                    {aiStats.net_pnl >= baselineStats.net_pnl ? 'Tối ưu vượt trội' : 'Bảo toàn an toàn'}
                  </span>
                </td>
              </tr>
              <tr>
                <td>Sụt Giảm Tối Đa (Max Drawdown)</td>
                <td style={{ color: 'var(--accent-red)' }}>{baselineStats.max_dd_percent}%</td>
                <td style={{ color: 'var(--accent-green)', fontWeight: 700 }}>{aiStats.max_dd_percent}%</td>
                <td>
                  <span className="badge-diff badge-better">
                    Giảm rủi ro còn {aiStats.max_dd_percent}%
                  </span>
                </td>
              </tr>
              <tr>
                <td>Số Lệnh Nhồi Sâu Nhất</td>
                <td>{baselineStats.max_layers} lệnh</td>
                <td style={{ color: 'var(--accent-purple)', fontWeight: 700 }}>{aiStats.max_layers} lệnh</td>
                <td><span className="badge-diff badge-better">Khống chế an toàn</span></td>
              </tr>
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}

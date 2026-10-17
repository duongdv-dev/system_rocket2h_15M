import React, { useState, useMemo } from 'react';

export default function TrainingReportModal({ 
  isOpen, 
  onClose, 
  catalogData, 
  onApproveAndBacktest, 
  isBacktesting 
}) {
  const [selectedClusterId, setSelectedClusterId] = useState('ALL');
  const [searchDate, setSearchDate] = useState('');
  const [activeTab, setActiveTab] = useState('archetypes'); // 'archetypes' | 'days_audit'

  const metadata = catalogData?.metadata || {};
  const clusters = catalogData?.cluster_summaries || [];
  const sampleDays = catalogData?.sample_training_days || [];

  const filteredDays = useMemo(() => {
    return sampleDays.filter(d => {
      if (selectedClusterId !== 'ALL' && d.regime_id !== selectedClusterId) return false;
      if (searchDate && !d.date.includes(searchDate)) return false;
      return true;
    });
  }, [sampleDays, selectedClusterId, searchDate]);

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      background: 'rgba(5, 8, 16, 0.88)',
      backdropFilter: 'blur(14px)',
      zIndex: 99999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      animation: 'fadeIn 0.25s ease'
    }} onClick={onClose}>
      
      <div 
        style={{
          width: '100%',
          maxWidth: '1280px',
          maxHeight: '92vh',
          background: 'linear-gradient(180deg, #131B2E 0%, #0B101D 100%)',
          border: '1px solid rgba(99, 102, 241, 0.45)',
          borderRadius: '16px',
          boxShadow: '0 24px 70px rgba(0, 0, 0, 0.8), 0 0 50px rgba(99, 102, 241, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(15, 23, 42, 0.85)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '24px' }}>🔬</span>
              <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#FFF', display: 'flex', alignItems: 'center', gap: '8px' }}>
                BÁO CÁO KẾT QUẢ HUẤN LUYỆN 10 NĂM (2011–2020)
                <span className="badge" style={{ background: '#6366F1', color: '#FFF' }}>
                  PRE-BACKTEST AUDIT
                </span>
              </h2>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Kết quả quét chuyên sâu: <b>{metadata.total_training_days || 2500} ngày</b> × <b>{metadata.setups_evaluated_per_day || 1200} setups/ngày</b> = <b>{(metadata.total_simulations_executed || 3000000).toLocaleString()} lượt mô phỏng</b> ({metadata.training_elapsed_seconds || 3}s).
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              type="button"
              onClick={onApproveAndBacktest}
              disabled={isBacktesting}
              style={{
                background: isBacktesting ? '#475569' : 'linear-gradient(135deg, #10B981, #059669)',
                color: '#FFF',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '8px',
                fontWeight: 800,
                fontSize: '13px',
                cursor: isBacktesting ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)'
              }}
            >
              {isBacktesting ? '⏳ Đang Chạy Backtest...' : '✅ PHÊ DUYỆT BỘ SETUP & CHẠY BACKTEST (2021-2025)'}
            </button>

            <button 
              type="button" 
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#FFF',
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '16px'
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{
          padding: '10px 24px',
          background: 'rgba(0, 0, 0, 0.25)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap'
        }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className={`tab-btn ${activeTab === 'archetypes' ? 'active' : ''}`}
              onClick={() => setActiveTab('archetypes')}
              style={{ padding: '6px 14px', fontSize: '12px' }}
            >
              📊 Ma Trận Các Hình Thái & Bộ Setup ({clusters.length} Nhóm)
            </button>
            <button
              className={`tab-btn ${activeTab === 'days_audit' ? 'active' : ''}`}
              onClick={() => setActiveTab('days_audit')}
              style={{ padding: '6px 14px', fontSize: '12px' }}
            >
              🔍 Tra Cứu Từng Ngày (Setup Chiến Thắng Của Từng Phiên)
            </button>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            💡 Kiểm tra kỹ kết quả huấn luyện trước khi tiến hành kiểm định
          </div>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
          
          {/* TAB 1: Ma trận các hình thái */}
          {activeTab === 'archetypes' && (
            <div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))',
                gap: '16px'
              }}>
                {clusters.map((cluster) => {
                  const opt = cluster.optimal_params || {};
                  const metrics = cluster.train_metrics || {};
                  const centroid = cluster.centroid_metrics || {};

                  return (
                    <div
                      key={cluster.regime_id}
                      style={{
                        background: 'rgba(15, 23, 42, 0.75)',
                        border: `1px solid ${cluster.color ? cluster.color + '55' : 'rgba(255,255,255,0.15)'}`,
                        borderTop: `4px solid ${cluster.color || '#6366F1'}`,
                        borderRadius: '12px',
                        padding: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)'
                      }}
                    >
                      <div>
                        {/* Title Row */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '24px' }}>{cluster.icon || '🎯'}</span>
                            <span style={{ fontWeight: 800, fontSize: '14px', color: '#FFF' }}>
                              {cluster.name}
                            </span>
                          </div>
                          <span style={{
                            background: cluster.color || '#6366F1',
                            color: '#0B0F19',
                            fontSize: '10px',
                            fontWeight: 800,
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontFamily: 'var(--font-mono)'
                          }}>
                            {cluster.tag}
                          </span>
                        </div>

                        <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.45' }}>
                          {cluster.desc}
                        </p>

                        {/* Centroid Recognition Marks */}
                        <div style={{
                          background: 'rgba(0, 0, 0, 0.3)',
                          border: '1px solid rgba(255, 255, 255, 0.06)',
                          borderRadius: '8px',
                          padding: '10px',
                          marginBottom: '12px',
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr',
                          gap: '8px',
                          fontSize: '11px',
                          fontFamily: 'var(--font-mono)'
                        }}>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Mẫu 10 Năm:</span>
                            <div style={{ color: '#E2E8F0', fontWeight: 700 }}>
                              {cluster.sample_count} ngày ({cluster.sample_percent}%)
                            </div>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Biên Độ Sáng:</span>
                            <div style={{ color: '#38BDF8', fontWeight: 700 }}>
                              ${centroid.avg_morning_range} ({centroid.avg_range_to_atr}x ATR)
                            </div>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Tỷ Lệ Thân Nến:</span>
                            <div style={{ color: '#FCD34D', fontWeight: 700 }}>
                              {centroid.avg_trend_efficiency}% thân
                            </div>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>ATR14 Trung Bình:</span>
                            <div style={{ color: '#A78BFA', fontWeight: 700 }}>
                              ${centroid.avg_atr} giá
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Consensus Optimal Setup Box */}
                      <div style={{
                        background: 'rgba(15, 23, 42, 0.95)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '8px',
                        padding: '12px',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)'
                      }}>
                        <div style={{ color: cluster.color || '#818CF8', fontWeight: 700, marginBottom: '8px', fontSize: '11px', textTransform: 'uppercase' }}>
                          🏆 BỘ SETUP TỐI THƯỢNG AI MAY ĐO CHO HÌNH THÁI NÀY:
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '10px' }}>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Khoảng cách DCA:</span>
                            <div style={{ color: '#FFF', fontWeight: 700, fontSize: '12px' }}>{opt.min_step_atr} x ATR14</div>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Chốt Lời TP:</span>
                            <div style={{ color: 'var(--accent-green)', fontWeight: 700, fontSize: '12px' }}>
                              {opt.tp_single_atr} / {opt.tp_dca_atr} ATR
                            </div>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Giờ Cắt Lỗ:</span>
                            <div style={{ color: '#FCD34D', fontWeight: 700, fontSize: '12px' }}>{opt.hard_exit} VN</div>
                          </div>
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>Quản Trị Rủi Ro:</span>
                            <div style={{ color: '#A78BFA', fontWeight: 700, fontSize: '12px' }}>{opt.risk_percent}% vốn</div>
                          </div>
                        </div>

                        {/* Empirical Training Metrics */}
                        <div style={{
                          paddingTop: '8px',
                          borderTop: '1px dashed rgba(255, 255, 255, 0.12)',
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '11px'
                        }}>
                          <span>Win Rate: <b style={{ color: 'var(--accent-green)' }}>{metrics.win_rate}%</b></span>
                          <span>Profit Factor: <b style={{ color: 'var(--accent-gold)' }}>{metrics.profit_factor}</b></span>
                          <span>Max DD: <b style={{ color: '#F87171' }}>{metrics.max_dd_percent}%</b></span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 2: Tra cứu từng ngày huấn luyện */}
          {activeTab === 'days_audit' && (
            <div>
              {/* Filter Row */}
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap' }}>
                <input
                  type="text"
                  placeholder="Tra cứu ngày (YYYY-MM-DD)..."
                  value={searchDate}
                  onChange={(e) => setSearchDate(e.target.value)}
                  style={{
                    background: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid var(--border-color)',
                    color: '#FFF',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontFamily: 'var(--font-mono)'
                  }}
                />

                <div className="period-tabs">
                  <button
                    className={`tab-btn ${selectedClusterId === 'ALL' ? 'active' : ''}`}
                    onClick={() => setSelectedClusterId('ALL')}
                  >
                    Tất Cả Cụm
                  </button>
                  {clusters.map((c) => (
                    <button
                      key={c.regime_id}
                      className={`tab-btn ${selectedClusterId === c.regime_id ? 'active' : ''}`}
                      onClick={() => setSelectedClusterId(c.regime_id)}
                    >
                      {c.icon} {c.tag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Table */}
              <div className="table-wrapper" style={{ maxHeight: '55vh', overflowY: 'auto' }}>
                <table className="trade-table">
                  <thead>
                    <tr>
                      <th>NGÀY TRAIN</th>
                      <th>CHIỀU 10H</th>
                      <th>BIÊN ĐỘ SÁNG</th>
                      <th>ATR(14)</th>
                      <th>HÌNH THÁI GOM NHÓM</th>
                      <th>SETUP TOP 1 CỦA NGÀY (TRONG 1,200 SETUPS)</th>
                      <th>PNL ĐẠT ĐƯỢC</th>
                      <th>SỐ LỆNH DCA</th>
                      <th>TỶ LỆ THẮNG LƯỚI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDays.map((d) => (
                      <tr key={d.date}>
                        <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{d.date}</td>
                        <td>
                          <span className={d.direction === 'BUY' ? 'dir-buy' : 'dir-sell'}>
                            {d.direction}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>${d.m_range}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>${d.atr_val}</td>
                        <td>
                          <span style={{
                            background: 'rgba(99, 102, 241, 0.2)',
                            color: '#A5B4FC',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontFamily: 'var(--font-mono)'
                          }}>
                            {d.regime_id}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                          <span style={{ color: '#FCD34D' }}>DCA: {d.best_setup.min_step_atr}x ATR</span> • 
                          <span style={{ color: '#34D399', marginLeft: '4px' }}>TP: {d.best_setup.tp_single_atr}/{d.best_setup.tp_dca_atr}</span> • 
                          <span style={{ color: '#F87171', marginLeft: '4px' }}>Cắt: {d.best_setup.hard_exit}</span>
                        </td>
                        <td style={{
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 700,
                          color: d.best_metrics.pts_pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                        }}>
                          {d.best_metrics.pts_pnl >= 0 ? `+${d.best_metrics.pts_pnl}` : d.best_metrics.pts_pnl} pts
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          {d.best_metrics.orders_count} lệnh
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {d.stats_across_1200_setups.win_rate_percent}% thắng
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div style={{
          padding: '14px 24px',
          background: 'rgba(15, 23, 42, 0.95)',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Sau khi duyệt, thuật toán sẽ ứng dụng toàn bộ danh mục hình thái này để chạy kiểm định Backtest trên tập 5 năm (2021–2025).
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              className="preset-btn"
              onClick={onClose}
              style={{ padding: '8px 16px', fontSize: '12px' }}
            >
              Đóng Xem Lại
            </button>

            <button
              type="button"
              onClick={onApproveAndBacktest}
              disabled={isBacktesting}
              style={{
                background: 'linear-gradient(135deg, #10B981, #059669)',
                color: '#FFF',
                border: 'none',
                padding: '8px 20px',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '13px',
                cursor: isBacktesting ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {isBacktesting ? '⏳ Đang Chạy...' : '✅ PHÊ DUYỆT & CHẠY BACKTEST'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

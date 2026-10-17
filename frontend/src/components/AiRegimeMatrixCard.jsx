import React, { useMemo } from 'react';

export default function AiRegimeMatrixCard({ data, onOpenTrainingReport, onRetrain, isDeepTraining }) {
  const regimeMatrix = data?.regime_matrix;
  const comparison = data?.dynamic_ai_comparison;
  const isDynamicMode = data?.mode === 'dynamic_ai' || data?.metadata?.mode === 'dynamic_ai';

  // Trích xuất danh sách các cụm thực tế từ kết quả học máy K-Means
  const clusters = useMemo(() => {
    if (!regimeMatrix) return [];
    return Object.keys(regimeMatrix)
      .filter(key => !key.startsWith('_')) // Loại bỏ metadata phân cụm nội bộ
      .map(key => regimeMatrix[key]);
  }, [regimeMatrix]);

  return (
    <section className="section-card" style={{
      background: 'linear-gradient(180deg, rgba(30, 27, 75, 0.45) 0%, rgba(15, 23, 42, 0.75) 100%)',
      border: '1px solid rgba(129, 140, 248, 0.35)',
      boxShadow: '0 8px 32px rgba(99, 102, 241, 0.15)',
      marginBottom: '24px'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '18px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '24px' }}>🧠</span>
            <h2 style={{ fontSize: '17px', fontWeight: 800, color: '#FFF', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              HỆ THỐNG PHÂN CỤM HỌC MÁY & TỐI ƯU HÌNH THÁI TỰ ĐỘNG
              <span className="badge badge-live" style={{ background: '#6366F1', color: '#FFF' }}>
                K-MEANS CLUSTERING & AUTO-TUNER
              </span>
            </h2>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', maxWidth: '880px', lineHeight: '1.5' }}>
            <b>100% Học từ Dữ liệu Thật:</b> AI tự động chạy quét đủ các tổ hợp tham số trên từng ngày trong 10 năm huấn luyện (2011–2020), 
            sau đó dùng thuật toán phân cụm K-Means gom nhóm theo đặc tính sóng sáng thực tế, tự sinh đặc tả và may đo bộ tham số tối ưu riêng cho từng nhóm.
          </p>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '8px', flexWrap: 'wrap' }}>
            {onOpenTrainingReport && (
              <button
                type="button"
                onClick={onOpenTrainingReport}
                style={{
                  background: 'rgba(99, 102, 241, 0.2)',
                  border: '1px solid rgba(129, 140, 248, 0.4)',
                  color: '#C7D2FE',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s'
                }}
              >
                <span>🔬</span> Mở Báo Cáo Chi Tiết Huấn Luyện 10 Năm (Tra Cứu Từng Ngày)
              </button>
            )}

            {onRetrain && (
              <button
                type="button"
                onClick={onRetrain}
                disabled={isDeepTraining}
                style={{
                  background: 'rgba(168, 85, 247, 0.2)',
                  border: '1px solid rgba(168, 85, 247, 0.45)',
                  color: '#E9D5FF',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  cursor: isDeepTraining ? 'not-allowed' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s'
                }}
                title="Quét lại 1,200 setups/ngày trên 10 năm huấn luyện"
              >
                <span>{isDeepTraining ? '⏳' : '🔄'}</span> {isDeepTraining ? 'Đang Quét 3 Triệu Setups...' : 'Huấn Luyện Lại 10 Năm'}
              </button>
            )}
          </div>
        </div>

        {/* Alpha Lift Comparison Pill */}
        {comparison && (
          <div style={{
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            borderRadius: '10px',
            padding: '8px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            fontFamily: 'var(--font-mono)'
          }}>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>Tỷ Lệ Thắng Thích Ứng:</span>
              <span style={{ fontSize: '15px', fontWeight: 800, color: 'var(--accent-green)' }}>
                {comparison.dynamic_regime_ai.win_rate}% 
                {comparison.alpha_lift?.win_rate_diff > 0 && (
                  <small style={{ fontSize: '11px', color: '#34D399', marginLeft: '4px' }}>
                    (+{comparison.alpha_lift.win_rate_diff}%)
                  </small>
                )}
              </span>
            </div>
            <div style={{ width: '1px', height: '24px', background: 'rgba(255, 255, 255, 0.1)' }}></div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>Lợi Nhuận Ròng (Test):</span>
              <span style={{ fontSize: '15px', fontWeight: 800, color: 'var(--accent-gold)' }}>
                +${comparison.dynamic_regime_ai.net_pnl.toLocaleString()}
              </span>
            </div>
            <div style={{ width: '1px', height: '24px', background: 'rgba(255, 255, 255, 0.1)' }}></div>
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>Max Drawdown:</span>
              <span style={{ fontSize: '15px', fontWeight: 800, color: '#38BDF8' }}>
                {comparison.dynamic_regime_ai.max_dd_percent}%
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Hiển thị các Nhóm được AI tự động phân cụm */}
      {clusters.length > 0 ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
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
                  background: 'rgba(15, 23, 42, 0.65)',
                  border: `1px solid ${cluster.color ? cluster.color + '55' : 'rgba(255,255,255,0.15)'}`,
                  borderTop: `3px solid ${cluster.color || '#6366F1'}`,
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  transition: 'all 0.2s',
                  position: 'relative',
                  overflow: 'hidden'
                }}
              >
                {/* Top Row: Icon, Tên nhóm, Tag */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '22px' }}>{cluster.icon || '🎯'}</span>
                      <span style={{ fontWeight: 800, fontSize: '13px', color: '#FFF' }}>
                        {cluster.name}
                      </span>
                    </div>
                    <span 
                      style={{
                        background: cluster.color || '#6366F1',
                        color: '#0B0F19',
                        fontSize: '10px',
                        fontWeight: 800,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontFamily: 'var(--font-mono)'
                      }}
                    >
                      {cluster.tag || 'CỤM AI'}
                    </span>
                  </div>

                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.4' }}>
                    {cluster.desc}
                  </p>

                  {/* Centroid Characteristics Box */}
                  <div style={{
                    background: 'rgba(0, 0, 0, 0.25)',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    borderRadius: '6px',
                    padding: '8px 10px',
                    marginBottom: '12px',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '6px',
                    fontSize: '10px',
                    fontFamily: 'var(--font-mono)'
                  }}>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Mẫu Huấn Luyện:</span>
                      <div style={{ color: '#E2E8F0', fontWeight: 700 }}>
                        {cluster.train_sessions_count} ngày ({cluster.sample_percent}%)
                      </div>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Biên Độ Sáng TB:</span>
                      <div style={{ color: '#38BDF8', fontWeight: 700 }}>
                        ${centroid.avg_morning_range || '--'} ({centroid.avg_range_to_atr || '--'}x ATR)
                      </div>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Độ Định Hướng (Trend):</span>
                      <div style={{ color: '#FCD34D', fontWeight: 700 }}>
                        {centroid.avg_trend_efficiency || '--'}% thân nến
                      </div>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>ATR14 Trung Bình:</span>
                      <div style={{ color: '#A78BFA', fontWeight: 700 }}>
                        ${centroid.avg_atr || '--'} giá
                      </div>
                    </div>
                  </div>
                </div>

                {/* Optimal Parameters Box */}
                <div style={{
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '8px',
                  padding: '10px 12px',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)'
                }}>
                  <div style={{ color: cluster.color || '#818CF8', fontWeight: 700, marginBottom: '6px', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    🤖 Bộ Tham Số AI Tối Ưu Cho Nhóm Này:
                  </div>

                  {opt.action === 'SKIP_SESSION' ? (
                    <div style={{ color: '#EF4444', fontWeight: 700, padding: '4px 0' }}>
                      🛡️ KÍCH HOẠT LÁ CHẮN: NÉ VÀO LỆNH (0% RỦI RO)
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Bước DCA:</span>
                        <div style={{ color: '#FFF', fontWeight: 700 }}>{opt.min_step_atr} x ATR14</div>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Chốt Lời TP:</span>
                        <div style={{ color: 'var(--accent-green)', fontWeight: 700 }}>{opt.tp_single_atr} / {opt.tp_dca_atr} ATR</div>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Giờ Cắt Lỗ:</span>
                        <div style={{ color: '#FCD34D', fontWeight: 700 }}>{opt.hard_exit} VN</div>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Quản Trị Vốn:</span>
                        <div style={{ color: '#A78BFA', fontWeight: 700 }}>{opt.risk_percent}% rủi ro</div>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Lot AI Tự Tính:</span>
                        <div style={{ color: '#38BDF8', fontWeight: 700 }}>
                          {opt.base_lot_per_10k ? `${opt.base_lot_per_10k} lot / $10k` : 'Tự co giãn'}
                        </div>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Trần Nhồi DCA:</span>
                        <div style={{ color: '#F472B6', fontWeight: 700 }}>
                          Max {opt.max_dca_layers || 7} tầng lệnh
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Real Training Metrics */}
                  {metrics && (
                    <div style={{
                      marginTop: '8px',
                      paddingTop: '6px',
                      borderTop: '1px dashed rgba(255, 255, 255, 0.1)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '10px',
                      color: 'var(--text-muted)'
                    }}>
                      <span>Win Rate Train: <b style={{ color: 'var(--accent-green)' }}>{metrics.win_rate}%</b></span>
                      <span>Profit Factor: <b style={{ color: 'var(--accent-gold)' }}>{metrics.profit_factor}</b></span>
                      <span>Drawdown: <b style={{ color: '#F87171' }}>{metrics.max_dd_percent}%</b></span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div style={{
          padding: '24px',
          textAlign: 'center',
          background: 'rgba(15, 23, 42, 0.5)',
          borderRadius: '12px',
          border: '1px dashed rgba(99, 102, 241, 0.3)'
        }}>
          <span style={{ fontSize: '32px', display: 'block', marginBottom: '8px' }}>🤖</span>
          <h3 style={{ fontSize: '15px', color: '#FFF', fontWeight: 700 }}>
            HỆ THỐNG SẴN SÀNG HUẤN LUYỆN TỰ ĐỘNG PHÂN CỤM THEO DỮ LIỆU
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', maxWidth: '650px', margin: '6px auto 14px' }}>
            Nhấn nút <b>"⚡ HUẤN LUYỆN & CHẠY AI TỰ ĐỘNG THÍCH ỨNG"</b> ở bảng điều khiển bên dưới. 
            AI sẽ duyệt qua từng ngày trong 10 năm lịch sử (2011–2020), thử nghiệm mọi tổ hợp tham số và dùng thuật toán máy học K-Means để tự động sinh ra các nhóm hình thái thực tế.
          </p>
        </div>
      )}
    </section>
  );
}

import React, { useMemo } from 'react';

export default function DcaDistributionCard({ periodData, currentMode = 'ai' }) {
  const stats = periodData ? (periodData[currentMode] || periodData.ai) : null;
  const layerDist = stats?.layer_distribution || {};
  const trades = stats?.trades || [];

  const analysis = useMemo(() => {
    const totalTrades = trades.length || 1;

    // Phân nhóm tầng lệnh
    let singleCount = 0;       // 1 Lệnh (Chốt ngay lệnh đầu)
    let moderateCount = 0;     // 2 - 3 Lệnh (Hồi tầng trung)
    let deepCount = 0;         // 4 - 5 Lệnh (DCA sâu)
    let severeCount = 0;       // 6+ Lệnh (Bão giá mạnh)

    Object.entries(layerDist).forEach(([layerStr, count]) => {
      const layer = parseInt(layerStr, 10);
      const c = Number(count);
      if (layer === 1) singleCount += c;
      else if (layer >= 2 && layer <= 3) moderateCount += c;
      else if (layer >= 4 && layer <= 5) deepCount += c;
      else if (layer >= 6) severeCount += c;
    });

    const groups = [
      {
        id: 'single',
        label: '1 Lệnh (Chốt Lãi Tầng 1)',
        desc: 'Không cần DCA, win ngay',
        count: singleCount,
        pct: Math.round((singleCount / totalTrades) * 100) || 0,
        color: '#10B981',
        strokeColor: '#10B981'
      },
      {
        id: 'moderate',
        label: '2 – 3 Lệnh (Hồi Tầng Nhẹ)',
        desc: 'Nhồi an toàn, hồi về TP',
        count: moderateCount,
        pct: Math.round((moderateCount / totalTrades) * 100) || 0,
        color: '#06B6D4',
        strokeColor: '#06B6D4'
      },
      {
        id: 'deep',
        label: '4 – 5 Lệnh (DCA Sâu)',
        desc: 'Biến động kéo dài phiên trưa',
        count: deepCount,
        pct: Math.round((deepCount / totalTrades) * 100) || 0,
        color: '#F59E0B',
        strokeColor: '#F59E0B'
      },
      {
        id: 'severe',
        label: '6+ Lệnh (Bão Giá Cực Đại)',
        desc: 'Áp lực vốn lớn, rủi ro cao',
        count: severeCount,
        pct: Math.round((severeCount / totalTrades) * 100) || 0,
        color: '#EF4444',
        strokeColor: '#EF4444'
      }
    ];

    // Thống kê theo Lý do đóng lệnh (Exit Reason)
    let tpHits = 0;
    let hardExits = 0;
    let otherExits = 0;
    let hardExitLossTotal = 0;

    trades.forEach(t => {
      if (t.close_reason && t.close_reason.includes('TP')) {
        tpHits++;
      } else if (t.close_reason && t.close_reason.includes('Cắt lỗ')) {
        hardExits++;
        hardExitLossTotal += t.pnl_dollar;
      } else {
        otherExits++;
      }
    });

    return {
      totalTrades,
      groups,
      maxLayers: stats?.max_layers || 0,
      avgLayers: stats?.avg_layers || (totalTrades ? (Object.entries(layerDist).reduce((acc, [k, v]) => acc + k * v, 0) / totalTrades).toFixed(2) : 0),
      tpHits,
      tpPct: Math.round((tpHits / totalTrades) * 100) || 0,
      hardExits,
      hardExitPct: Math.round((hardExits / totalTrades) * 100) || 0,
      hardExitLossTotal: Math.round(hardExitLossTotal)
    };
  }, [layerDist, trades, stats]);

  // Donut SVG parameters
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  let accumulatedOffset = 0;

  return (
    <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="chart-header">
        <div>
          <div className="chart-title">
            <span>🧱</span> PHÂN PHỐI TẦNG LỆNH & LÝ DO THOÁT LỆNH
          </div>
          <div className="chart-subtitle">
            Dữ liệu thực tế: Đo lường mức độ gồng nhồi lệnh và tỷ lệ cắt lỗ 14:00
          </div>
        </div>
        <div className="badge badge-info" style={{ fontFamily: 'var(--font-mono)' }}>
          MAX: {analysis.maxLayers} LỆNH
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '170px 1fr', gap: '24px', alignItems: 'center', marginTop: '14px' }}>
        {/* Donut Chart Visual */}
        <div style={{ position: 'relative', width: '160px', height: '160px', margin: '0 auto' }}>
          <svg width="160" height="160" viewBox="0 0 160 160" style={{ transform: 'rotate(-90deg)' }}>
            {/* Background ring */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              fill="transparent"
              stroke="rgba(255, 255, 255, 0.05)"
              strokeWidth="20"
            />
            {/* Slices */}
            {analysis.groups.map((group) => {
              if (group.count === 0) return null;
              const strokeDasharray = `${(group.pct / 100) * circumference} ${circumference}`;
              const strokeDashoffset = -accumulatedOffset;
              accumulatedOffset += (group.pct / 100) * circumference;

              return (
                <circle
                  key={group.id}
                  cx="80"
                  cy="80"
                  r={radius}
                  fill="transparent"
                  stroke={group.strokeColor}
                  strokeWidth="20"
                  strokeDasharray={strokeDasharray}
                  strokeDashoffset={strokeDashoffset}
                  style={{ transition: 'stroke-dasharray 0.5s ease' }}
                />
              );
            })}
          </svg>
          {/* Donut Center Info */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none'
          }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Trung Bình
            </span>
            <span style={{ fontSize: '20px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
              {analysis.avgLayers}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>lệnh/phiên</span>
          </div>
        </div>

        {/* Group Progress Bars */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {analysis.groups.map((item) => (
            <div key={item.id} style={{ fontSize: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.color, display: 'inline-block' }}></span>
                  {item.label}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: item.color }}>
                  {item.pct}% ({item.count} phiên)
                </span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
                <div style={{ background: item.color, width: `${item.pct}%`, height: '100%', borderRadius: '4px', transition: 'width 0.4s ease' }}></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Exit Reason Summary Cards */}
      <div style={{
        marginTop: '20px',
        paddingTop: '16px',
        borderTop: '1px solid rgba(255,255,255,0.08)',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '12px'
      }}>
        <div style={{
          background: 'rgba(16, 185, 129, 0.08)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          padding: '10px 14px',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px'
        }}>
          <div style={{ fontSize: '11px', color: 'var(--accent-green)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>🎯</span> CHỐT LỜI ĐẠT TP
          </div>
          <div style={{ fontSize: '16px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
            {analysis.tpHits} phiên ({analysis.tpPct}%)
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Đạt target 0.8/0.5 ATR
          </div>
        </div>

        <div style={{
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          padding: '10px 14px',
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px'
        }}>
          <div style={{ fontSize: '11px', color: 'var(--accent-red)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>✂️</span> CẮT LỖ CƯỠNG BỨC (14:00)
          </div>
          <div style={{ fontSize: '16px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--accent-red)' }}>
            {analysis.hardExits} phiên ({analysis.hardExitPct}%)
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Tổng lỗ: ${analysis.hardExitLossTotal.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
}

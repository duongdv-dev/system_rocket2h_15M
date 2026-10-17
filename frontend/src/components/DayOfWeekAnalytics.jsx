import React, { useMemo, useState } from 'react';

const WEEKDAYS = [
  { dayIdx: 1, code: 'MON', label: 'Thứ Hai', name: 'Monday' },
  { dayIdx: 2, code: 'TUE', label: 'Thứ Ba', name: 'Tuesday' },
  { dayIdx: 3, code: 'WED', label: 'Thứ Tư', name: 'Wednesday' },
  { dayIdx: 4, code: 'THU', label: 'Thứ Năm', name: 'Thursday' },
  { dayIdx: 5, code: 'FRI', label: 'Thứ Sáu', name: 'Friday' }
];

export default function DayOfWeekAnalytics({ trades = [] }) {
  const [selectedMetric, setSelectedMetric] = useState('winrate'); // 'winrate', 'pnl', 'avg_pnl'

  const stats = useMemo(() => {
    if (!trades || trades.length === 0) return null;

    const dayMap = { 1: [], 2: [], 3: [], 4: [], 5: [] };

    trades.forEach(t => {
      if (!t.date) return;
      // Trích xuất ngày trong tuần từ YYYY-MM-DD
      const parts = t.date.split('-');
      if (parts.length === 3) {
        const d = new Date(Date.UTC(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10)));
        const day = d.getUTCDay();
        if (day >= 1 && day <= 5) {
          dayMap[day].push(t);
        }
      }
    });

    const daysData = WEEKDAYS.map(w => {
      const list = dayMap[w.dayIdx] || [];
      const total = list.length;
      const wins = list.filter(t => t.is_win).length;
      const losses = total - wins;
      const winRate = total > 0 ? Math.round((wins / total) * 1000) / 10 : 0;
      const netPnl = Math.round(list.reduce((sum, t) => sum + (t.pnl_dollar || 0), 0));
      const avgPnl = total > 0 ? Math.round(netPnl / total) : 0;
      const deepDca = list.filter(t => t.orders_count >= 4).length;
      const hardExits = list.filter(t => t.close_reason && t.close_reason.includes('Cắt lỗ')).length;

      return {
        ...w,
        total,
        wins,
        losses,
        winRate,
        netPnl,
        avgPnl,
        deepDca,
        hardExits
      };
    });

    // Xác định ngày tốt nhất & ngày rủi ro nhất
    const validDays = daysData.filter(d => d.total > 0);
    let bestDay = validDays[0];
    let worstDay = validDays[0];

    validDays.forEach(d => {
      if (d.winRate > bestDay.winRate || (d.winRate === bestDay.winRate && d.netPnl > bestDay.netPnl)) {
        bestDay = d;
      }
      if (d.hardExits > worstDay.hardExits || (d.hardExits === worstDay.hardExits && d.winRate < worstDay.winRate)) {
        worstDay = d;
      }
    });

    const maxPnl = Math.max(...daysData.map(d => Math.abs(d.netPnl)), 100);

    return {
      daysData,
      bestDay,
      worstDay,
      maxPnl
    };
  }, [trades]);

  if (!stats) return null;

  return (
    <section className="section-card" style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>📊</span>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>
              HIỆU SUẤT THEO NGÀY TRONG TUẦN (DAY-OF-WEEK QUANT BREAKDOWN)
            </h2>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Phân tích thống kê lệnh từ Thứ Hai đến Thứ Sáu để hỗ trợ AI tối ưu hóa tỷ trọng vào lệnh
          </p>
        </div>

        <div className="period-tabs">
          <button
            type="button"
            className={`tab-btn ${selectedMetric === 'winrate' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('winrate')}
          >
            🎯 Tỷ Lệ Thắng (%)
          </button>
          <button
            type="button"
            className={`tab-btn ${selectedMetric === 'pnl' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('pnl')}
          >
            💰 Tổng PnL ($)
          </button>
          <button
            type="button"
            className={`tab-btn ${selectedMetric === 'avg_pnl' ? 'active' : ''}`}
            onClick={() => setSelectedMetric('avg_pnl')}
          >
            ⚡ PnL TB / Lệnh ($)
          </button>
        </div>
      </div>

      {/* 5 Day Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '14px',
        marginBottom: '20px'
      }}>
        {stats.daysData.map(d => {
          const isBest = stats.bestDay && d.dayIdx === stats.bestDay.dayIdx;
          const isWorst = stats.worstDay && d.dayIdx === stats.worstDay.dayIdx && d.hardExits > 0;

          return (
            <div
              key={d.dayIdx}
              style={{
                background: isBest 
                  ? 'linear-gradient(180deg, rgba(16, 185, 129, 0.12) 0%, rgba(18, 24, 38, 0.85) 100%)' 
                  : isWorst 
                    ? 'linear-gradient(180deg, rgba(239, 68, 68, 0.1) 0%, rgba(18, 24, 38, 0.85) 100%)' 
                    : 'var(--bg-card)',
                border: isBest 
                  ? '1px solid rgba(16, 185, 129, 0.35)' 
                  : isWorst 
                    ? '1px solid rgba(239, 68, 68, 0.35)' 
                    : '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                position: 'relative',
                boxShadow: isBest ? '0 0 20px rgba(16, 185, 129, 0.1)' : 'none'
              }}
            >
              {/* Badge for Best / Risk */}
              {isBest && (
                <div style={{
                  position: 'absolute',
                  top: '-10px',
                  right: '12px',
                  background: 'var(--accent-green)',
                  color: '#000',
                  fontSize: '10px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '10px',
                  boxShadow: '0 2px 8px rgba(16, 185, 129, 0.4)'
                }}>
                  ⭐ HIỆU QUẢ NHẤT
                </div>
              )}
              {isWorst && !isBest && (
                <div style={{
                  position: 'absolute',
                  top: '-10px',
                  right: '12px',
                  background: 'var(--accent-red)',
                  color: '#FFF',
                  fontSize: '10px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '10px',
                  boxShadow: '0 2px 8px rgba(239, 68, 68, 0.4)'
                }}>
                  ⚠️ BIẾN ĐỘNG CAO
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div>
                  <span style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {d.label}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '6px', fontFamily: 'var(--font-mono)' }}>
                    ({d.code})
                  </span>
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                  {d.total} phiên
                </span>
              </div>

              {/* Main Metric Focus */}
              {selectedMetric === 'winrate' && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '24px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: d.winRate >= 80 ? 'var(--accent-green)' : 'var(--accent-gold)' }}>
                    {d.winRate}%
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {d.wins} Win / {d.losses} Loss
                  </div>
                </div>
              )}

              {selectedMetric === 'pnl' && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '22px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: d.netPnl >= 0 ? 'var(--accent-gold)' : 'var(--accent-red)' }}>
                    ${d.netPnl.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Tổng tích lũy cả giai đoạn
                  </div>
                </div>
              )}

              {selectedMetric === 'avg_pnl' && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '22px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: d.avgPnl >= 0 ? 'var(--accent-cyan)' : 'var(--accent-red)' }}>
                    +${d.avgPnl}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Lợi nhuận bình quân / phiên
                  </div>
                </div>
              )}

              {/* Winrate progress bar */}
              <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: '4px', height: '6px', overflow: 'hidden', marginBottom: '12px' }}>
                <div style={{
                  background: d.winRate >= 85 ? 'var(--accent-green)' : d.winRate >= 75 ? 'var(--accent-gold)' : 'var(--accent-red)',
                  width: `${d.winRate}%`,
                  height: '100%',
                  borderRadius: '4px'
                }}></div>
              </div>

              {/* Mini details list */}
              <div style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '4px', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>DCA Sâu (≥4 tầng):</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: d.deepDca > 5 ? 'var(--accent-gold)' : 'var(--text-primary)' }}>
                    {d.deepDca} lần
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Cắt lỗ 14h:</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: d.hardExits > 0 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                    {d.hardExits} lần
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* AI Quant Takeaway Banner */}
      <div style={{
        background: 'rgba(99, 102, 241, 0.08)',
        border: '1px solid rgba(99, 102, 241, 0.25)',
        borderRadius: 'var(--radius-sm)',
        padding: '12px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        flexWrap: 'wrap'
      }}>
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          background: 'rgba(99, 102, 241, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '16px'
        }}>
          💡
        </div>
        <div style={{ flex: 1, minWidth: '260px', fontSize: '12px', lineHeight: '1.5' }}>
          <b style={{ color: 'var(--text-primary)' }}>Định Hướng Feature Engineering Cho AI: </b>
          <span style={{ color: 'var(--text-secondary)' }}>
            Dữ liệu cho thấy <b>{stats.bestDay?.label}</b> đạt winrate cao nhất ({stats.bestDay?.winRate}%), 
            trong khi <b>{stats.worstDay?.label}</b> ghi nhận {stats.worstDay?.hardExits} lần cắt lỗ 14:00. 
            Mô hình AI có thể sử dụng biến <code>DayOfWeek</code> để tự động giảm 30% volume vào ngày biến động hoặc nâng cao tiêu chí Shock Filter.
          </span>
        </div>
      </div>
    </section>
  );
}

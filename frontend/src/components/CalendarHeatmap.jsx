import React, { useState, useMemo } from 'react';

const MONTH_NAMES = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'];
const FULL_MONTHS = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6', 'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'];

export default function CalendarHeatmap({ trades = [], filterAnalysis, onInspectTrade }) {
  const [viewMode, setViewMode] = useState('matrix'); // 'matrix' hoặc 'daily'
  const [selectedYear, setSelectedYear] = useState(null);
  const [hoveredDay, setHoveredDay] = useState(null);

  // Tập hợp các ngày bị lọc bởi AI
  const filteredMap = useMemo(() => {
    const map = new Map();
    if (filterAnalysis?.filtered_days) {
      filterAnalysis.filtered_days.forEach(fd => {
        map.set(fd.date, fd);
      });
    }
    return map;
  }, [filterAnalysis]);

  // Tổ chức dữ liệu theo Năm & Tháng & Ngày
  const { yearsList, yearMonthMatrix, dailyMap } = useMemo(() => {
    const matrix = {}; // { 2024: { 1: { pnl: 0, count: 0, wins: 0 }, ... } }
    const days = new Map(); // 'YYYY-MM-DD' => trade object

    trades.forEach(t => {
      if (!t.date) return;
      days.set(t.date, t);

      const parts = t.date.split('-');
      if (parts.length === 3) {
        const y = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);

        if (!matrix[y]) {
          matrix[y] = { months: {}, totalPnl: 0, totalTrades: 0, totalWins: 0 };
          for (let i = 1; i <= 12; i++) {
            matrix[y].months[i] = { pnl: 0, count: 0, wins: 0 };
          }
        }

        matrix[y].months[m].pnl += (t.pnl_dollar || 0);
        matrix[y].months[m].count += 1;
        if (t.is_win) matrix[y].months[m].wins += 1;

        matrix[y].totalPnl += (t.pnl_dollar || 0);
        matrix[y].totalTrades += 1;
        if (t.is_win) matrix[y].totalWins += 1;
      }
    });

    const sortedYears = Object.keys(matrix).map(Number).sort((a, b) => b - a);

    return {
      yearsList: sortedYears,
      yearMonthMatrix: matrix,
      dailyMap: days
    };
  }, [trades]);

  // Thiết lập năm mặc định
  const activeYear = selectedYear || (yearsList.length > 0 ? yearsList[0] : 2024);

  // Sinh danh sách các ngày trong năm được chọn cho Calendar Heatmap
  const daysInActiveYear = useMemo(() => {
    const list = [];
    const startDate = new Date(Date.UTC(activeYear, 0, 1));
    const endDate = new Date(Date.UTC(activeYear, 11, 31));

    const cur = new Date(startDate);
    while (cur <= endDate) {
      const y = cur.getUTCFullYear();
      const m = String(cur.getUTCMonth() + 1).padStart(2, '0');
      const d = String(cur.getUTCDate()).padStart(2, '0');
      const dateStr = `${y}-${m}-${d}`;
      const dayOfWeek = cur.getUTCDay(); // 0 = Chủ nhật, 6 = Thứ Bảy

      const trade = dailyMap.get(dateStr);
      const filtered = filteredMap.get(dateStr);

      list.push({
        date: dateStr,
        dayOfWeek,
        month: cur.getUTCMonth(),
        dayOfMonth: cur.getUTCDate(),
        isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
        trade,
        filtered
      });

      cur.setUTCDate(cur.getUTCDate() + 1);
    }
    return list;
  }, [activeYear, dailyMap, filteredMap]);

  if (!trades || trades.length === 0) return null;

  return (
    <section className="section-card" style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>📅</span>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>
              LỊCH NHIỆT HIỆU SUẤT & MA TRẬN PnL THÁNG/NĂM (CALENDAR HEATMAP)
            </h2>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Tổng hợp chu kỳ tăng trưởng từng tháng và từng ngày qua 15 năm kiểm định định lượng
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {viewMode === 'daily' && (
            <div className="period-tabs">
              {yearsList.map(y => (
                <button
                  key={y}
                  type="button"
                  className={`tab-btn ${activeYear === y ? 'active' : ''}`}
                  onClick={() => setSelectedYear(y)}
                  style={{ padding: '4px 10px', fontSize: '12px' }}
                >
                  {y}
                </button>
              ))}
            </div>
          )}

          <div className="period-tabs">
            <button
              type="button"
              className={`tab-btn ${viewMode === 'matrix' ? 'active' : ''}`}
              onClick={() => setViewMode('matrix')}
            >
              📊 Ma Trận Tháng/Năm
            </button>
            <button
              type="button"
              className={`tab-btn ${viewMode === 'daily' ? 'active' : ''}`}
              onClick={() => setViewMode('daily')}
            >
              🗓️ Lịch 365 Ngày ({activeYear})
            </button>
          </div>
        </div>
      </div>

      {/* VIEW 1: MA TRẬN THÁNG / NĂM (MONTHLY MATRIX) */}
      {viewMode === 'matrix' && (
        <div className="table-wrapper">
          <table className="trade-table" style={{ textAlign: 'center', fontSize: '12px' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>NĂM</th>
                {MONTH_NAMES.map(m => (
                  <th key={m} style={{ textAlign: 'center', minWidth: '60px' }}>{m}</th>
                ))}
                <th style={{ textAlign: 'right', minWidth: '90px' }}>TỔNG NĂM ($)</th>
                <th style={{ textAlign: 'center', minWidth: '70px' }}>WINRATE</th>
              </tr>
            </thead>
            <tbody>
              {yearsList.map(y => {
                const row = yearMonthMatrix[y];
                const yearWinrate = row.totalTrades > 0 ? Math.round((row.totalWins / row.totalTrades) * 100) : 0;
                const isYearPositive = row.totalPnl >= 0;

                return (
                  <tr key={y}>
                    <td style={{ textAlign: 'left', fontFamily: 'var(--font-mono)', fontWeight: 800, color: 'var(--text-primary)' }}>
                      {y}
                    </td>
                    {MONTH_NAMES.map((_, idx) => {
                      const mIdx = idx + 1;
                      const mData = row.months[mIdx];
                      const pnl = Math.round(mData.pnl);
                      const hasTrades = mData.count > 0;

                      let cellBg = 'transparent';
                      let cellColor = 'var(--text-muted)';

                      if (hasTrades) {
                        if (pnl > 0) {
                          cellBg = pnl > 1000 ? 'rgba(16, 185, 129, 0.35)' : 'rgba(16, 185, 129, 0.18)';
                          cellColor = '#34D399';
                        } else if (pnl < 0) {
                          cellBg = 'rgba(239, 68, 68, 0.25)';
                          cellColor = '#F87171';
                        } else {
                          cellBg = 'rgba(255, 255, 255, 0.03)';
                          cellColor = 'var(--text-secondary)';
                        }
                      }

                      return (
                        <td
                          key={mIdx}
                          style={{
                            background: cellBg,
                            color: cellColor,
                            fontFamily: 'var(--font-mono)',
                            fontWeight: hasTrades ? 700 : 400,
                            padding: '10px 4px',
                            border: '1px solid rgba(255, 255, 255, 0.04)'
                          }}
                          title={hasTrades ? `${y}-${mIdx}: ${mData.wins}/${mData.count} Win • PnL: $${pnl.toLocaleString()}` : 'Không có giao dịch'}
                        >
                          {hasTrades ? (pnl > 0 ? `+$${pnl}` : `$${pnl}`) : '--'}
                        </td>
                      );
                    })}
                    <td style={{
                      textAlign: 'right',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 800,
                      color: isYearPositive ? 'var(--accent-gold)' : 'var(--accent-red)',
                      fontSize: '13px'
                    }}>
                      {isYearPositive ? `+$${Math.round(row.totalPnl).toLocaleString()}` : `-$${Math.abs(Math.round(row.totalPnl)).toLocaleString()}`}
                    </td>
                    <td style={{
                      textAlign: 'center',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 700,
                      color: yearWinrate >= 80 ? 'var(--accent-green)' : 'var(--accent-gold)'
                    }}>
                      {yearWinrate}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* VIEW 2: LỊCH 365 NGÀY (DAILY HEATMAP) */}
      {viewMode === 'daily' && (
        <div>
          {/* Legend Guide */}
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>CHÚ THÍCH Ô NGÀY:</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#059669', display: 'inline-block' }}></span>
              Lãi lớn (&gt;$100)
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#10B981', display: 'inline-block' }}></span>
              Lãi vừa ($20 - $100)
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#34D399', display: 'inline-block' }}></span>
              Lãi đơn (&lt;$20)
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#EF4444', display: 'inline-block' }}></span>
              Cắt lỗ 14:00
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#8B5CF6', display: 'inline-block' }}></span>
              🛡️ AI Né bão
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'rgba(255,255,255,0.05)', display: 'inline-block' }}></span>
              Cuối tuần / Nghỉ
            </span>
          </div>

          {/* 12 Months Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px'
          }}>
            {FULL_MONTHS.map((monthName, mIdx) => {
              const monthDays = daysInActiveYear.filter(d => d.month === mIdx);

              return (
                <div
                  key={monthName}
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '12px'
                  }}
                >
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{monthName}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                      {yearMonthMatrix[activeYear]?.months[mIdx + 1]?.count || 0} phiên
                    </span>
                  </div>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(7, 1fr)',
                    gap: '4px'
                  }}>
                    {monthDays.map(d => {
                      let bgColor = 'rgba(255, 255, 255, 0.04)';
                      let borderColor = 'transparent';
                      let cursor = 'default';

                      if (d.filtered) {
                        bgColor = '#8B5CF6';
                        borderColor = 'rgba(139, 92, 246, 0.6)';
                        cursor = 'pointer';
                      } else if (d.trade) {
                        cursor = 'pointer';
                        if (d.trade.pnl_dollar < 0) {
                          bgColor = '#EF4444';
                          borderColor = 'rgba(239, 68, 68, 0.6)';
                        } else if (d.trade.pnl_dollar > 100) {
                          bgColor = '#059669';
                          borderColor = 'rgba(5, 150, 105, 0.6)';
                        } else if (d.trade.pnl_dollar >= 20) {
                          bgColor = '#10B981';
                        } else {
                          bgColor = '#34D399';
                        }
                      } else if (d.isWeekend) {
                        bgColor = 'rgba(255, 255, 255, 0.02)';
                      }

                      return (
                        <div
                          key={d.date}
                          onClick={() => (d.trade || d.filtered) && onInspectTrade && onInspectTrade(d.trade, d.filtered)}
                          onMouseEnter={() => setHoveredDay(d)}
                          onMouseLeave={() => setHoveredDay(null)}
                          style={{
                            aspectRatio: '1',
                            borderRadius: '4px',
                            background: bgColor,
                            border: `1px solid ${borderColor}`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '10px',
                            fontFamily: 'var(--font-mono)',
                            color: d.trade || d.filtered ? '#FFF' : 'var(--text-muted)',
                            fontWeight: d.trade || d.filtered ? 700 : 400,
                            cursor: cursor,
                            transition: 'transform 0.1s ease',
                            position: 'relative'
                          }}
                          title={d.trade || d.filtered ? "Bấm để mở Chart Nến M15 chi tiết phiên này" : undefined}
                        >
                          {d.dayOfMonth}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Interactive Day Inspection Card */}
          {hoveredDay && (hoveredDay.trade || hoveredDay.filtered) && (
            <div style={{
              marginTop: '16px',
              padding: '12px 18px',
              background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95))',
              border: '1px solid var(--border-highlight)',
              borderRadius: 'var(--radius-sm)',
              boxShadow: 'var(--shadow-glow)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
              animation: 'fadeIn 0.2s ease'
            }}>
              <div>
                <span style={{ fontSize: '13px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--accent-gold)' }}>
                  🗓️ Ngày: {hoveredDay.date}
                </span>
                {hoveredDay.filtered && (
                  <span className="badge badge-info" style={{ marginLeft: '10px', background: 'rgba(139, 92, 246, 0.2)', color: '#C4B5FD', border: '1px solid rgba(139, 92, 246, 0.4)' }}>
                    🛡️ AI ĐÃ NÉ BÃO: {hoveredDay.filtered.toxic_reason}
                  </span>
                )}
                {hoveredDay.trade && (
                  <span style={{ marginLeft: '10px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Lệnh: <b>{hoveredDay.trade.direction}</b> • Nhồi <b>{hoveredDay.trade.orders_count}</b> tầng • {hoveredDay.trade.close_reason}
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                {hoveredDay.trade && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontFamily: 'var(--font-mono)' }}>
                    <div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Giá vào: </span>
                      <b style={{ color: 'var(--text-primary)' }}>{hoveredDay.trade.first_entry}</b>
                    </div>
                    <div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Giá đóng: </span>
                      <b style={{ color: 'var(--text-primary)' }}>{hoveredDay.trade.close_price}</b>
                    </div>
                    <div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>PnL: </span>
                      <b style={{
                        fontSize: '15px',
                        color: hoveredDay.trade.pnl_dollar >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                      }}>
                        {hoveredDay.trade.pnl_dollar >= 0 ? `+$${hoveredDay.trade.pnl_dollar}` : `-$${Math.abs(hoveredDay.trade.pnl_dollar)}`}
                      </b>
                    </div>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => onInspectTrade && onInspectTrade(hoveredDay.trade, hoveredDay.filtered)}
                  style={{
                    background: 'linear-gradient(135deg, #3B82F6, #1D4ED8)',
                    border: 'none',
                    color: '#FFF',
                    borderRadius: '6px',
                    padding: '6px 14px',
                    fontSize: '11px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    boxShadow: '0 2px 8px rgba(59, 130, 246, 0.4)'
                  }}
                >
                  📈 Mở Chart Nến M15
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

import React from 'react';

export default function RiskDaysInspector({ filterAnalysis }) {
  if (!filterAnalysis) return null;

  const { test_total_days, test_filtered_days_count, filter_rate_percent, filtered_days } = filterAnalysis;

  return (
    <section className="section-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🛡️</span> NHẬT KÝ PHÂN TÍCH CÁC NGÀY RỦI RO BỊ BỘ LỌC AI LOẠI BỎ (RISK DAYS INSPECTOR)
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Mô phỏng đối chiếu: Xem chuyện gì đã xảy ra nếu vào lệnh ở những ngày bão giá nguy hiểm này.
          </p>
        </div>

        <div className="nav-badges">
          <span className="badge badge-info">
            TỔNG NGÀY TEST: {test_total_days}
          </span>
          <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            LỌC BỎ: {test_filtered_days_count} NGÀY ({filter_rate_percent}%)
          </span>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="trade-table">
          <thead>
            <tr>
              <th>NGÀY GIAO DỊCH</th>
              <th>LÝ DO AI NHẬN DIỆN RỦI RO</th>
              <th>ATR14</th>
              <th>BIÊN ĐỘ SÁNG</th>
              <th>SÓNG DỐC 10H</th>
              <th>NẾU VÀO LỆNH (BASELINE)</th>
              <th>THIỆT HẠI NÉ ĐƯỢC</th>
              <th>KẾT QUẢ ĐỐI CHỨNG</th>
            </tr>
          </thead>
          <tbody>
            {filtered_days && filtered_days.length > 0 ? (
              filtered_days.map((fd, idx) => {
                const isLoss = fd.baseline_pnl < 0;
                return (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{fd.date}</td>
                    <td style={{ color: '#FBBF24', maxWidth: '360px' }}>{fd.toxic_reason}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{fd.atr_val} giá</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{fd.morning_range} giá</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{fd.morning_delta} giá</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      Nhồi {fd.baseline_layers} lệnh • DD: -${Math.abs(fd.baseline_worst_dd).toLocaleString()}
                    </td>
                    <td style={{ 
                      fontFamily: 'var(--font-mono)', 
                      fontWeight: 700, 
                      color: isLoss ? 'var(--accent-green)' : 'var(--accent-red)' 
                    }}>
                      {isLoss ? `Né lỗ $${Math.abs(fd.baseline_pnl).toLocaleString('en-US', {minimumFractionDigits: 2})}` : `Bỏ lỡ +$${fd.baseline_pnl.toFixed(2)}`}
                    </td>
                    <td>
                      <span className={`badge ${isLoss ? 'badge-live' : 'badge-info'}`}>
                        {isLoss ? '🛡️ CỨU NGU THÀNH CÔNG' : 'AN TOÀN'}
                      </span>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px' }}>
                  Không có ngày nào bị lọc với cấu hình hiện tại.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

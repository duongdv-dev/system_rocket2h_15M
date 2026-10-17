import React, { useState, useMemo } from 'react';

export default function TradeLogTable({ trades, onInspectTrade }) {
  const [filterType, setFilterType] = useState('all'); // 'all', 'win', 'loss', 'deep'
  const [searchDate, setSearchDate] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const filteredTrades = useMemo(() => {
    if (!trades) return [];
    return trades.filter(t => {
      if (filterType === 'win' && !t.is_win) return false;
      if (filterType === 'loss' && t.is_win) return false;
      if (filterType === 'deep' && t.orders_count < 4) return false;
      if (searchDate && !t.date.includes(searchDate)) return false;
      return true;
    });
  }, [trades, filterType, searchDate]);

  const totalPages = Math.ceil(filteredTrades.length / pageSize) || 1;
  const pageTrades = filteredTrades.slice((page - 1) * pageSize, page * pageSize);

  return (
    <section className="section-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📜</span> NHẬT KÝ CHI TIẾT TỪNG CHU KỲ LỆNH (TRADE AUDIT LOG)
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Toàn bộ lịch sử vào lệnh, nhồi DCA, mức giá trung bình và lý do đóng lệnh. Bấm <b>"📈 Soi Nến"</b> để xem biểu đồ chi tiết từng ngày.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input 
            type="text" 
            placeholder="Tìm theo ngày (YYYY-MM)..." 
            value={searchDate} 
            onChange={(e) => { setSearchDate(e.target.value); setPage(1); }}
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              outline: 'none'
            }}
          />

          <div className="period-tabs">
            <button 
              className={`tab-btn ${filterType === 'all' ? 'active' : ''}`}
              onClick={() => { setFilterType('all'); setPage(1); }}
            >
              Tất Cả ({trades?.length || 0})
            </button>
            <button 
              className={`tab-btn ${filterType === 'win' ? 'active' : ''}`}
              onClick={() => { setFilterType('win'); setPage(1); }}
            >
              Thắng
            </button>
            <button 
              className={`tab-btn ${filterType === 'loss' ? 'active' : ''}`}
              onClick={() => { setFilterType('loss'); setPage(1); }}
            >
              Thua (Cắt 14h)
            </button>
            <button 
              className={`tab-btn ${filterType === 'deep' ? 'active' : ''}`}
              onClick={() => { setFilterType('deep'); setPage(1); }}
            >
              DCA Sâu (&ge;4)
            </button>
          </div>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="trade-table">
          <thead>
            <tr>
              <th>NGÀY VÀO (10H)</th>
              <th>HƯỚNG</th>
              <th>KHỐI LƯỢNG</th>
              <th>TẦNG NHỒI</th>
              <th>GIÁ VÀO</th>
              <th>GIÁ THOÁT</th>
              <th>LỢI NHUẬN ($)</th>
              <th>LÝ DO THOÁT LỆNH</th>
              <th>BIỂU ĐỒ</th>
            </tr>
          </thead>
          <tbody>
            {pageTrades.length > 0 ? (
              pageTrades.map((t, idx) => (
                <tr key={idx}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{t.date}</td>
                  <td>
                    <span className={t.direction === 'BUY' ? 'dir-buy' : 'dir-sell'}>
                      {t.direction}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontWeight: 700 }}>
                    {t.lot_size ? `${t.lot_size} lot` : '0.01 lot'}
                    {t.orders_count > 1 && (
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block' }}>
                        (Tổng: {(t.total_lots || (t.lot_size ? t.lot_size * t.orders_count : t.orders_count * 0.01)).toFixed(2)} lot)
                      </span>
                    )}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                    {t.orders_count} {t.orders_count > 1 ? 'lệnh' : 'đơn'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{(t.first_entry ?? t.entry_price ?? 0).toFixed(2)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{(t.close_price ?? 0).toFixed(2)}</td>
                  <td style={{ 
                    fontFamily: 'var(--font-mono)', 
                    fontWeight: 700, 
                    color: t.pnl_dollar >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' 
                  }}>
                    {t.pnl_dollar >= 0 ? `+$${t.pnl_dollar.toFixed(2)}` : `-$${Math.abs(t.pnl_dollar).toFixed(2)}`}
                  </td>
                  <td style={{ fontSize: '11px', color: t.is_win ? 'var(--text-secondary)' : '#FCA5A5' }}>
                    {t.close_reason}
                  </td>
                  <td>
                    <button
                      type="button"
                      onClick={() => onInspectTrade && onInspectTrade(t)}
                      style={{
                        background: 'rgba(59, 130, 246, 0.15)',
                        border: '1px solid rgba(59, 130, 246, 0.35)',
                        color: '#60A5FA',
                        borderRadius: '6px',
                        padding: '4px 10px',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.3)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)'}
                    >
                      📈 Soi Nến
                    </button>
                  </td>
                </tr>
              )){t.close_reason}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="9" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px' }}>
                  Không tìm thấy lệnh nào phù hợp với bộ lọc.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '14px', fontSize: '12px', color: 'var(--text-muted)' }}>
        <div>
          Hiển thị {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, filteredTrades.length)} trên tổng số {filteredTrades.length} chu kỳ
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: 'none',
              color: '#FFF',
              padding: '4px 12px',
              borderRadius: '4px',
              cursor: page <= 1 ? 'not-allowed' : 'pointer',
              opacity: page <= 1 ? 0.4 : 1
            }}
          >
            Trang Trước
          </button>
          <span style={{ fontFamily: 'var(--font-mono)', padding: '4px 8px' }}>
            {page} / {totalPages}
          </span>
          <button 
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: 'none',
              color: '#FFF',
              padding: '4px 12px',
              borderRadius: '4px',
              cursor: page >= totalPages ? 'not-allowed' : 'pointer',
              opacity: page >= totalPages ? 0.4 : 1
            }}
          >
            Trang Sau
          </button>
        </div>
      </div>
    </section>
  );
}

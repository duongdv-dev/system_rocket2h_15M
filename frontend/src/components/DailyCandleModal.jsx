import React, { useEffect, useRef, useState, useMemo } from 'react';
import { fetchDayCandles } from '../services/api';

export default function DailyCandleModal({ isOpen, onClose, trade, filteredDay }) {
  const canvasRef = useRef(null);
  const [candles, setCandles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hoveredCandle, setHoveredCandle] = useState(null);
  const [mousePos, setMousePos] = useState({ x: -1, y: -1 });

  const activeDate = trade?.date || filteredDay?.date;

  // Lắng nghe phím ESC để đóng modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Nạp danh sách nến M15 của ngày được chọn
  useEffect(() => {
    if (isOpen && activeDate) {
      setIsLoading(true);
      fetchDayCandles(activeDate)
        .then(data => {
          setCandles(data || []);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setCandles([]);
    }
  }, [isOpen, activeDate]);

  // Vẽ biểu đồ nến Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || candles.length === 0) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;

    ctx.clearRect(0, 0, width, height);

    // Padding
    const padTop = 30;
    const padBottom = 35;
    const padLeft = 20;
    const padRight = 75; // Để hiển thị trục giá bên phải

    const plotW = width - padLeft - padRight;
    const plotH = height - padTop - padBottom;

    // Tìm giá Min / Max của cả ngày
    let minPrice = Math.min(...candles.map(c => c.low));
    let maxPrice = Math.max(...candles.map(c => c.high));

    // Mở rộng thêm 5% lề trên dưới
    const priceRange = (maxPrice - minPrice) || 1;
    minPrice -= priceRange * 0.05;
    maxPrice += priceRange * 0.05;
    const totalRange = maxPrice - minPrice;

    const getY = (price) => padTop + plotH - ((price - minPrice) / totalRange) * plotH;
    const getX = (idx) => padLeft + (plotW / candles.length) * (idx + 0.5);

    // 1. Vẽ Grid ngang & Trục giá
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.lineWidth = 1;
    ctx.fillStyle = '#64748B';
    ctx.font = '11px JetBrains Mono';
    ctx.textAlign = 'left';

    const gridSteps = 6;
    for (let i = 0; i <= gridSteps; i++) {
      const y = padTop + (plotH / gridSteps) * i;
      const p = maxPrice - (totalRange / gridSteps) * i;

      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(width - padRight, y);
      ctx.stroke();

      ctx.fillText(`$${p.toFixed(2)}`, width - padRight + 8, y + 4);
    }

    // 2. Vùng đánh dấu Sóng Sáng 07h-10h VN
    let idx07h = -1;
    let idx10h = -1;
    let idx14h = -1;

    candles.forEach((c, idx) => {
      if (c.time.startsWith('07:00') || (idx07h === -1 && c.time >= '07:00')) {
        if (idx07h === -1) idx07h = idx;
      }
      if (c.time.startsWith('10:00') || (idx10h === -1 && c.time >= '10:00')) {
        if (idx10h === -1) idx10h = idx;
      }
      if (c.time.startsWith('14:00') || (idx14h === -1 && c.time >= '14:00')) {
        if (idx14h === -1) idx14h = idx;
      }
    });

    if (idx07h !== -1 && idx10h !== -1) {
      const x07 = getX(idx07h);
      const x10 = getX(idx10h);
      ctx.fillStyle = 'rgba(59, 130, 246, 0.07)';
      ctx.fillRect(x07, padTop, x10 - x07, plotH);

      // Nhãn Sóng Sáng
      ctx.fillStyle = '#60A5FA';
      ctx.font = '10px Inter';
      ctx.textAlign = 'center';
      ctx.fillText('SÓNG SÁNG 07h - 10h', (x07 + x10) / 2, padTop - 10);
    }

    // Đường gạch đỏ Cắt Lỗ Cưỡng Bức lúc 14:00
    if (idx14h !== -1) {
      const x14 = getX(idx14h);
      ctx.save();
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = 'rgba(239, 68, 68, 0.5)';
      ctx.beginPath();
      ctx.moveTo(x14, padTop);
      ctx.lineTo(x14, padTop + plotH);
      ctx.stroke();

      ctx.fillStyle = '#EF4444';
      ctx.font = '10px JetBrains Mono';
      ctx.textAlign = 'center';
      ctx.fillText('14:00 HARD EXIT', x14, padTop - 10);
      ctx.restore();
    }

    // 3. Vẽ các Cây Nến M15 (Japanese Candlesticks)
    const candleWidth = Math.max(2, (plotW / candles.length) * 0.65);

    candles.forEach((c, idx) => {
      const x = getX(idx);
      const yOpen = getY(c.open);
      const yClose = getY(c.close);
      const yHigh = getY(c.high);
      const yLow = getY(c.low);

      const isGreen = c.close >= c.open;
      const color = isGreen ? '#10B981' : '#EF4444';

      // Râu nến (Wick)
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x, yHigh);
      ctx.lineTo(x, yLow);
      ctx.stroke();

      // Thân nến (Body)
      const topBody = Math.min(yOpen, yClose);
      const bodyH = Math.max(1.5, Math.abs(yClose - yOpen));

      ctx.fillStyle = color;
      ctx.fillRect(x - candleWidth / 2, topBody, candleWidth, bodyH);

      // Nhãn trục thời gian (Mỗi 2 tiếng vẽ 1 nhãn)
      if (idx % 6 === 0 || idx === candles.length - 1) {
        ctx.fillStyle = '#64748B';
        ctx.font = '10px JetBrains Mono';
        ctx.textAlign = 'center';
        ctx.fillText(c.time, x, height - padBottom + 18);
      }
    });

    // 4. Vẽ Các Điểm Vào Lệnh (Entries), Đường Giá Trung Bình & Điểm Thoát Lệnh (Exit)
    if (trade) {
      // 4.1. Xác định nến vào lệnh đầu tiên (Lệnh 1 lúc 10:15 VN)
      let idxEntry = -1;
      if (trade.orders && trade.orders.length > 0 && trade.orders[0].timestamp) {
        let minDiff = Infinity;
        candles.forEach((c, idx) => {
          const diff = Math.abs(c.timestamp - trade.orders[0].timestamp);
          if (diff < minDiff) {
            minDiff = diff;
            idxEntry = idx;
          }
        });
      }
      if (idxEntry === -1) {
        idxEntry = candles.findIndex(c => c.time === '10:15');
      }
      if (idxEntry === -1) {
        idxEntry = candles.findIndex(c => c.time >= '10:15');
      }
      if (idxEntry === -1 && idx10h !== -1) {
        idxEntry = idx10h + 1;
      }
      if (idxEntry === -1) idxEntry = Math.floor(candles.length / 2);

      // 4.2. Xác định nến thoát lệnh (Exit)
      let exitIdx = -1;
      if (trade.close_time) {
        let minDiff = Infinity;
        candles.forEach((c, idx) => {
          const diff = Math.abs(c.timestamp - trade.close_time);
          if (diff < minDiff) {
            minDiff = diff;
            exitIdx = idx;
          }
        });
      }
      if (exitIdx === -1 && trade.bars_held && idxEntry !== -1) {
        exitIdx = Math.min(candles.length - 1, idxEntry + trade.bars_held);
      }
      if (exitIdx === -1 && idx14h !== -1) {
        exitIdx = idx14h;
      }
      if (exitIdx === -1) {
        exitIdx = Math.min(candles.length - 1, idxEntry + 4);
      }

      // Đảm bảo exitIdx >= idxEntry
      if (exitIdx < idxEntry) exitIdx = idxEntry;

      const xStart = getX(idxEntry);
      const xEnd = getX(exitIdx);
      const isProfit = trade.is_win;

      // 4.3. Tô màu vùng thời gian giao dịch (Trade Holding Period)
      ctx.fillStyle = isProfit ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)';
      ctx.fillRect(xStart - 4, padTop, Math.max(16, xEnd - xStart + 8), plotH);

      ctx.strokeStyle = isProfit ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(xStart - 4, padTop);
      ctx.lineTo(xEnd + 4, padTop);
      ctx.stroke();

      // 4.4. Vẽ Đường Giá Trung Bình (Avg Entry Line)
      const avgPrice = trade.avg_entry ?? trade.first_entry ?? trade.entry_price;
      if (avgPrice) {
        const yAvg = getY(avgPrice);
        ctx.save();
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = '#F59E0B';
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.moveTo(xStart - 4, yAvg);
        ctx.lineTo(Math.max(xEnd + 20, width - padRight), yAvg);
        ctx.stroke();

        ctx.fillStyle = '#F59E0B';
        ctx.font = 'bold 11px JetBrains Mono';
        ctx.textAlign = 'right';
        ctx.fillText(`AVG ENTRY: $${avgPrice.toFixed(2)}`, width - padRight - 8, yAvg - 5);
        ctx.restore();
      }

      // 4.5. Chuẩn bị danh sách lệnh (Hỗ trợ cả bản chạy mới và các bản lịch sử cũ)
      let ordersToDraw = [];
      if (trade.orders && trade.orders.length > 0) {
        ordersToDraw = trade.orders.map((ord, i) => {
          let cIdx = -1;
          let minDiff = Infinity;
          candles.forEach((c, idx) => {
            const diff = Math.abs(c.timestamp - ord.timestamp);
            if (diff < minDiff) {
              minDiff = diff;
              cIdx = idx;
            }
          });
          return {
            layer: ord.layer || i + 1,
            entry_price: ord.entry_price,
            candleIdx: cIdx !== -1 ? cIdx : (idxEntry + i)
          };
        });
      } else {
        // Fallback cho lịch sử cũ
        const firstPrice = trade.first_entry ?? trade.entry_price ?? trade.avg_entry;
        ordersToDraw = [{
          layer: 1,
          entry_price: firstPrice,
          candleIdx: idxEntry
        }];
      }

      // 4.6. Vẽ từng Điểm Vào Lệnh
      ordersToDraw.forEach((ord) => {
        const cIdx = Math.min(candles.length - 1, Math.max(0, ord.candleIdx));
        const xOrd = getX(cIdx);
        const yOrd = getY(ord.entry_price);

        // Vòng tròn phát sáng tại mức giá vào
        ctx.beginPath();
        ctx.arc(xOrd, yOrd, 7, 0, Math.PI * 2);
        ctx.fillStyle = trade.direction === 'BUY' ? '#3B82F6' : '#EC4899';
        ctx.fill();
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Đường gióng nét đứt từ râu nến tới điểm vào
        ctx.save();
        ctx.setLineDash([2, 2]);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(xOrd, padTop);
        ctx.lineTo(xOrd, height - padBottom);
        ctx.stroke();
        ctx.restore();

        // Hộp nhãn nổi bật
        const isBuy = trade.direction === 'BUY';
        const badgeText = ord.layer > 1 
          ? `DCA #${ord.layer}: $${ord.entry_price.toFixed(2)}` 
          : `VÀO ${trade.direction}: $${ord.entry_price.toFixed(2)}`;
        
        ctx.font = 'bold 10px JetBrains Mono';
        const textW = ctx.measureText(badgeText).width;
        const badgeY = isBuy ? yOrd + 10 : yOrd - 26;

        ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
        ctx.fillRect(xOrd - textW / 2 - 6, badgeY, textW + 12, 18);
        ctx.strokeStyle = isBuy ? '#3B82F6' : '#EC4899';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(xOrd - textW / 2 - 6, badgeY, textW + 12, 18);

        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'center';
        ctx.fillText(badgeText, xOrd, badgeY + 13);
      });

      // 4.7. Vẽ Điểm Thoát Lệnh (Exit Point)
      const closePrice = trade.close_price;
      if (closePrice) {
        const xExit = getX(exitIdx);
        const yExit = getY(closePrice);

        // Chấm tròn điểm thoát
        ctx.beginPath();
        ctx.arc(xExit, yExit, 8, 0, Math.PI * 2);
        ctx.fillStyle = trade.is_win ? '#10B981' : '#EF4444';
        ctx.fill();
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2.5;
        ctx.stroke();

        // Đường gióng dọc điểm thoát
        ctx.save();
        ctx.setLineDash([2, 2]);
        ctx.strokeStyle = trade.is_win ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(xExit, padTop);
        ctx.lineTo(xExit, height - padBottom);
        ctx.stroke();
        ctx.restore();

        // Exit Badge nổi bật
        const isCut = (trade.close_reason && trade.close_reason.includes('Cắt lỗ')) || !trade.is_win;
        const pts = Math.abs(closePrice - (avgPrice || closePrice)).toFixed(1);
        const exitLabel = isCut 
          ? `✂️ CẮT LỖ: $${closePrice.toFixed(2)} (-${pts} giá)`
          : `🎯 CHỐT TP: $${closePrice.toFixed(2)} (+${pts} giá)`;

        ctx.font = 'bold 11px JetBrains Mono';
        const eTextW = ctx.measureText(exitLabel).width;
        const eBadgeY = yExit < padTop + 40 ? yExit + 12 : yExit - 28;

        ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
        ctx.fillRect(xExit - eTextW / 2 - 8, eBadgeY, eTextW + 16, 20);
        ctx.strokeStyle = isCut ? '#EF4444' : '#10B981';
        ctx.lineWidth = 2;
        ctx.strokeRect(xExit - eTextW / 2 - 8, eBadgeY, eTextW + 16, 20);

        ctx.fillStyle = isCut ? '#F87171' : '#34D399';
        ctx.textAlign = 'center';
        ctx.fillText(exitLabel, xExit, eBadgeY + 14);
      }
    }

    // 5. Crosshair (Con trỏ chuột di chuyển)
    if (mousePos.x >= padLeft && mousePos.x <= width - padRight) {
      ctx.save();
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;

      // Đường dọc
      ctx.beginPath();
      ctx.moveTo(mousePos.x, padTop);
      ctx.lineTo(mousePos.x, height - padBottom);
      ctx.stroke();

      // Đường ngang
      if (mousePos.y >= padTop && mousePos.y <= height - padBottom) {
        ctx.beginPath();
        ctx.moveTo(padLeft, mousePos.y);
        ctx.lineTo(width - padRight, mousePos.y);
        ctx.stroke();
      }
      ctx.restore();
    }

  }, [candles, trade, mousePos]);

  // Bắt sự kiện chuột di chuyển để hiện Crosshair và Tooltip
  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas || candles.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setMousePos({ x, y });

    const padLeft = 20;
    const padRight = 75;
    const plotW = rect.width - padLeft - padRight;

    if (x >= padLeft && x <= rect.width - padRight) {
      const idx = Math.floor(((x - padLeft) / plotW) * candles.length);
      if (idx >= 0 && idx < candles.length) {
        setHoveredCandle(candles[idx]);
      }
    } else {
      setHoveredCandle(null);
    }
  };

  const handleMouseLeave = () => {
    setMousePos({ x: -1, y: -1 });
    setHoveredCandle(null);
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      background: 'rgba(5, 8, 16, 0.85)',
      backdropFilter: 'blur(12px)',
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
          maxWidth: '1200px',
          maxHeight: '90vh',
          background: 'linear-gradient(180deg, #131B2E 0%, #0B101D 100%)',
          border: '1px solid rgba(99, 102, 241, 0.4)',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.7), 0 0 40px rgba(99, 102, 241, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '20px' }}>📈</span>
              <h2 style={{ fontSize: '17px', fontWeight: 800, color: '#FFF' }}>
                BIỂU ĐỒ NẾN M15 CHI TIẾT — PHIÊN {activeDate}
              </h2>
              {trade && (
                <span className={`badge ${trade.direction === 'BUY' ? 'dir-buy' : 'dir-sell'}`} style={{ padding: '3px 8px', fontSize: '11px' }}>
                  {trade.direction}
                </span>
              )}
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {filteredDay 
                ? `🛡️ Phiên này được AI Shock Filter nhận diện rủi ro né bão: ${filteredDay.toxic_reason}`
                : `Chu kỳ ${trade?.orders_count || 1} lệnh • Thoát lệnh lúc ${trade?.close_time_str || '14:00'} • ${trade?.close_reason || '--'}`}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            {trade && (
              <div style={{
                background: trade.is_win ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                border: `1px solid ${trade.is_win ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                padding: '6px 14px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>PnL Phiên:</span>
                <span style={{
                  fontSize: '16px',
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  color: trade.is_win ? 'var(--accent-green)' : 'var(--accent-red)'
                }}>
                  {trade.pnl_dollar >= 0 ? `+$${trade.pnl_dollar.toFixed(2)}` : `-$${Math.abs(trade.pnl_dollar).toFixed(2)}`}
                </span>
              </div>
            )}

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
                fontSize: '16px',
                transition: 'all 0.2s'
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Hovered Candle Tooltip Bar */}
        <div style={{
          padding: '8px 24px',
          background: 'rgba(0, 0, 0, 0.3)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-secondary)'
        }}>
          {hoveredCandle ? (
            <>
              <span>⏰ Giờ VN: <b style={{ color: '#FFF' }}>{hoveredCandle.time}</b></span>
              <span>Open: <b style={{ color: '#38BDF8' }}>{hoveredCandle.open.toFixed(2)}</b></span>
              <span>High: <b style={{ color: '#34D399' }}>{hoveredCandle.high.toFixed(2)}</b></span>
              <span>Low: <b style={{ color: '#F87171' }}>{hoveredCandle.low.toFixed(2)}</b></span>
              <span>Close: <b style={{ color: hoveredCandle.close >= hoveredCandle.open ? '#34D399' : '#F87171' }}>{hoveredCandle.close.toFixed(2)}</b></span>
            </>
          ) : (
            <span>💡 Rê chuột lên biểu đồ để soi từng cây nến M15 • Dấu chấm là các tầng lệnh DCA</span>
          )}
        </div>

        {/* Canvas Chart Area */}
        <div style={{ position: 'relative', flex: 1, minHeight: '380px', padding: '10px' }}>
          {isLoading && (
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
              background: 'rgba(11, 16, 29, 0.8)',
              zIndex: 10
            }}>
              <div className="spinner" style={{ width: '28px', height: '28px' }}></div>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '12px' }}>
                Đang nạp dữ liệu nến M15 ngày {activeDate}...
              </span>
            </div>
          )}

          <canvas 
            ref={canvasRef} 
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{ width: '100%', height: '100%', display: 'block', cursor: 'crosshair' }}
          />
        </div>

        {/* Modal Footer Summary */}
        {trade && (
          <div style={{
            padding: '14px 24px',
            background: 'rgba(15, 23, 42, 0.8)',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '14px',
            fontSize: '12px'
          }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Giá Vào Lệnh 1 (10h):</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#FFF', fontSize: '14px' }}>
                ${(trade.first_entry ?? trade.entry_price ?? 0).toFixed(2)}
              </div>
            </div>

            <div>
              <span style={{ color: 'var(--text-muted)' }}>Giá Trung Bình Rổ (Avg):</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-gold)', fontSize: '14px' }}>
                ${(trade.avg_entry ?? 0).toFixed(2)}
              </div>
            </div>

            <div>
              <span style={{ color: 'var(--text-muted)' }}>Giá Đóng / Cắt:</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#38BDF8', fontSize: '14px' }}>
                ${(trade.close_price ?? 0).toFixed(2)}
              </div>
            </div>

            <div>
              <span style={{ color: 'var(--text-muted)' }}>Thời Gian Giữ Lệnh:</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#A78BFA', fontSize: '14px' }}>
                {trade.bars_held ? `${trade.bars_held} nến (~${Math.round(trade.bars_held * 15 / 60 * 10) / 10}h)` : '--'}
              </div>
            </div>

            <div>
              <span style={{ color: 'var(--text-muted)' }}>ATR(14) Lúc 10h:</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#FFF', fontSize: '14px' }}>
                {trade.atr_at_entry ? `${trade.atr_at_entry} giá` : '--'}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

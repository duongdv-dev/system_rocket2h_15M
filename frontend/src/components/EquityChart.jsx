import React, { useRef, useEffect, useState } from 'react';
import DcaDistributionCard from './DcaDistributionCard';

export default function EquityChart({ periodData, currentMode = 'ai' }) {
  const canvasRef = useRef(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const baselineCurve = periodData?.baseline?.equity_curve || [];
  const aiCurve = periodData?.ai?.equity_curve || [];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.parentElement.clientWidth;
    const height = canvas.height = canvas.parentElement.clientHeight;

    ctx.clearRect(0, 0, width, height);

    if (!aiCurve || aiCurve.length < 2) {
      ctx.fillStyle = '#64748B';
      ctx.font = '14px Inter';
      ctx.textAlign = 'center';
      ctx.fillText('Chưa có dữ liệu đường cong vốn', width / 2, height / 2);
      return;
    }

    // Determine scale
    const allBalances = [
      ...aiCurve.map(p => p.balance),
      ...baselineCurve.map(p => p.balance)
    ];
    const minVal = Math.min(...allBalances) * 0.98;
    const maxVal = Math.max(...allBalances) * 1.02;
    const range = (maxVal - minVal) || 1;

    const padLeft = 70;
    const padRight = 30;
    const padTop = 30;
    const padBottom = 40;
    const plotW = width - padLeft - padRight;
    const plotH = height - padTop - padBottom;

    // Draw horizontal grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    ctx.fillStyle = '#64748B';
    ctx.font = '11px JetBrains Mono';
    ctx.textAlign = 'right';

    const gridSteps = 5;
    for (let i = 0; i <= gridSteps; i++) {
      const y = padTop + (plotH / gridSteps) * i;
      const val = maxVal - (range / gridSteps) * i;
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(width - padRight, y);
      ctx.stroke();
      ctx.fillText(`$${Math.round(val).toLocaleString()}`, padLeft - 10, y + 4);
    }

    // Helper to get coordinates
    const getX = (idx, total) => padLeft + (plotW / (total - 1)) * idx;
    const getY = (val) => padTop + plotH - ((val - minVal) / range) * plotH;

    // Draw Baseline curve (grey dashed)
    if (baselineCurve.length > 1) {
      ctx.save();
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      baselineCurve.forEach((pt, i) => {
        const x = getX(i, baselineCurve.length);
        const y = getY(pt.balance);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.restore();
    }

    // Draw AI curve with glowing gradient
    const gradient = ctx.createLinearGradient(0, padTop, 0, height - padBottom);
    gradient.addColorStop(0, 'rgba(16, 185, 129, 0.35)');
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

    ctx.beginPath();
    aiCurve.forEach((pt, i) => {
      const x = getX(i, aiCurve.length);
      const y = getY(pt.balance);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    // Fill area under AI curve
    ctx.save();
    ctx.lineTo(padLeft + plotW, padTop + plotH);
    ctx.lineTo(padLeft, padTop + plotH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
    ctx.restore();

    // Stroke AI line
    ctx.strokeStyle = '#10B981';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    aiCurve.forEach((pt, i) => {
      const x = getX(i, aiCurve.length);
      const y = getY(pt.balance);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

  }, [periodData, aiCurve, baselineCurve]);

  return (
    <div className="charts-grid">
      <div className="chart-card">
        <div className="chart-header">
          <div>
            <div className="chart-title">
              <span>📈</span> ĐƯỜNG CONG TĂNG TRƯỞNG VỐN (EQUITY CURVE)
            </div>
            <div className="chart-subtitle">
              Đường xanh: Có AI Lọc biến động • Đường đứt nét xám: Chạy thuần không lọc (Baseline)
            </div>
          </div>
          <div className="badge badge-live">CO GIÃN THEO ATR(14)</div>
        </div>

        <div className="canvas-container">
          <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }}></canvas>
        </div>
      </div>

      <DcaDistributionCard periodData={periodData} currentMode={currentMode} />
    </div>
  );
}

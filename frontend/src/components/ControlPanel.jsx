import React, { useState, useEffect } from 'react';

export default function ControlPanel({ 
  onRefresh, 
  onTriggerRun, 
  onToggleHistory, 
  historyCount = 0,
  isHistoryOpen = false,
  isLoading, 
  activeParams, 
  dataStatus, 
  activeRunId 
}) {
  const [dcaStep, setDcaStep] = useState(0.5);
  const [tpSingle, setTpSingle] = useState(0.8);
  const [tpDca, setTpDca] = useState(0.5);
  const [hardExit, setHardExit] = useState("14:00");
  const [filterRatio, setFilterRatio] = useState(5.0);
  const [filterAtr, setFilterAtr] = useState(18.0);
  const [balance, setBalance] = useState(10000);
  const [lotStep, setLotStep] = useState(5000);
  const [sizingMode, setSizingMode] = useState('atr_risk');
  const [riskPercent, setRiskPercent] = useState(0.5);
  const [activePreset, setActivePreset] = useState('recommended');
  const [copied, setCopied] = useState(false);

  // Sync inputs if activeParams provided from backend metadata
  useEffect(() => {
    if (activeParams) {
      if (activeParams.min_step_atr !== undefined) setDcaStep(activeParams.min_step_atr);
      if (activeParams.tp_single_atr !== undefined) setTpSingle(activeParams.tp_single_atr);
      if (activeParams.tp_dca_atr !== undefined) setTpDca(activeParams.tp_dca_atr);
      if (activeParams.hard_exit_hour !== undefined) {
        const h = String(activeParams.hard_exit_hour).padStart(2, '0');
        const m = String(activeParams.hard_exit_minute || 0).padStart(2, '0');
        setHardExit(`${h}:${m}`);
      }
      if (activeParams.filter_ratio_range !== undefined) setFilterRatio(activeParams.filter_ratio_range);
      if (activeParams.filter_atr_max !== undefined) setFilterAtr(activeParams.filter_atr_max);
      if (activeParams.initial_balance !== undefined) setBalance(activeParams.initial_balance);
      if (activeParams.lot_step_capital !== undefined) setLotStep(activeParams.lot_step_capital);
      if (activeParams.sizing_mode !== undefined) setSizingMode(activeParams.sizing_mode);
      if (activeParams.risk_percent !== undefined) setRiskPercent(activeParams.risk_percent);
    }
  }, [activeParams]);

  const handlePreset = (preset) => {
    setActivePreset(preset);
    if (preset === 'recommended') {
      setDcaStep(0.5);
      setTpSingle(0.8);
      setTpDca(0.5);
      setHardExit("14:00");
      setFilterRatio(5.0);
      setFilterAtr(18.0);
      setSizingMode('atr_risk');
      setRiskPercent(0.5);
    } else if (preset === 'safe') {
      setDcaStep(0.6);
      setTpSingle(0.6);
      setTpDca(0.4);
      setHardExit("12:00");
      setFilterRatio(4.0);
      setFilterAtr(15.0);
      setSizingMode('atr_risk');
      setRiskPercent(0.3);
    } else if (preset === 'aggressive') {
      setDcaStep(0.5);
      setTpSingle(1.0);
      setTpDca(0.6);
      setHardExit("15:00");
      setFilterRatio(6.0);
      setFilterAtr(22.0);
      setSizingMode('atr_risk');
      setRiskPercent(1.0);
    }
  };

  // Generate exact terminal command to run engine/run_cli.py
  const cliCommand = `python3 engine/run_cli.py --min-step ${dcaStep} --tp-single ${tpSingle} --tp-dca ${tpDca} --hard-exit ${hardExit} --filter-ratio ${filterRatio} --filter-atr ${filterAtr} --balance ${balance} --sizing-mode ${sizingMode} --risk-pct ${riskPercent} --lot-cap ${lotStep}`;

  const handleCopyCommand = () => {
    navigator.clipboard.writeText(cliCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRunClick = () => {
    if (onTriggerRun) {
      onTriggerRun({
        min_step_atr: parseFloat(dcaStep),
        tp_single_atr: parseFloat(tpSingle),
        tp_dca_atr: parseFloat(tpDca),
        hard_exit: hardExit,
        filter_ratio_range: parseFloat(filterRatio),
        filter_atr_max: parseFloat(filterAtr),
        initial_balance: parseFloat(balance),
        sizing_mode: sizingMode,
        risk_percent: parseFloat(riskPercent),
        lot_step_capital: parseFloat(lotStep)
      });
    }
  };

  return (
    <section className="control-panel-card">
      <div className="control-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="panel-icon">🎛️</div>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              THIẾT LẬP THAM SỐ ĐẦU VÀO
              <span className="badge badge-live">WEB UI CONTROLLER</span>
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Nhập tham số bên dưới và nhấn nút <b>"🚀 Chạy Backtest / AI"</b>. Kết quả sẽ tự động lưu vào lịch sử Server và hiển thị trực quan.
            </p>
          </div>
        </div>

        <div className="preset-buttons">
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>MẪU NHANH:</span>
          <button 
            type="button"
            className={`preset-btn ${activePreset === 'recommended' ? 'active-preset' : ''}`}
            onClick={() => handlePreset('recommended')}
          >
            ⭐ Khuyên Dùng (0.5 DCA / TP 0.8-0.5 / 14h)
          </button>
          <button 
            type="button"
            className={`preset-btn ${activePreset === 'safe' ? 'active-preset' : ''}`}
            onClick={() => handlePreset('safe')}
          >
            🛡️ Siêu An Toàn (Cắt 12h)
          </button>
          <button 
            type="button"
            className={`preset-btn ${activePreset === 'aggressive' ? 'active-preset' : ''}`}
            onClick={() => handlePreset('aggressive')}
          >
            🔥 Tối Đa Hóa (Cắt 15h)
          </button>
        </div>
      </div>

      <div className="params-grid">
        {/* Field 1: DCA Step */}
        <div className="param-item">
          <label>Khoảng Cách Min DCA <span className="param-tip">Khoảng cách giữa các lệnh nhồi</span></label>
          <div className="input-unit">
            <input 
              type="number" 
              step="0.1" 
              min="0.1" 
              max="2.0" 
              value={dcaStep} 
              onChange={(e) => setDcaStep(e.target.value)} 
            />
            <span>x ATR14</span>
          </div>
        </div>

        {/* Field 2: TP Single */}
        <div className="param-item">
          <label>TP Lệnh Đơn <span className="param-tip">Chốt lời khi chỉ có 1 lệnh</span></label>
          <div className="input-unit">
            <input 
              type="number" 
              step="0.1" 
              min="0.2" 
              max="3.0" 
              value={tpSingle} 
              onChange={(e) => setTpSingle(e.target.value)} 
            />
            <span>x ATR14</span>
          </div>
        </div>

        {/* Field 3: TP DCA Basket */}
        <div className="param-item">
          <label>TP Rổ DCA (&ge; 2 lệnh) <span className="param-tip">Chốt lời từ giá trung bình</span></label>
          <div className="input-unit">
            <input 
              type="number" 
              step="0.1" 
              min="0.1" 
              max="2.0" 
              value={tpDca} 
              onChange={(e) => setTpDca(e.target.value)} 
            />
            <span>x ATR14</span>
          </div>
        </div>

        {/* Field 4: Hard Exit Hour */}
        <div className="param-item">
          <label>Giờ Cắt Lỗ Ép Buộc <span className="param-tip">Hết phiên Á né phiên Âu</span></label>
          <select 
            className="param-select" 
            value={hardExit} 
            onChange={(e) => setHardExit(e.target.value)}
          >
            <option value="12:00">12:00 Trưa VN (Né sớm)</option>
            <option value="13:00">13:00 Chiều VN</option>
            <option value="13:30">13:30 Chiều VN</option>
            <option value="14:00">14:00 Chiều VN (Khuyến nghị chuẩn)</option>
            <option value="14:30">14:30 Chiều VN</option>
            <option value="15:00">15:00 Chiều VN</option>
            <option value="18:00">18:00 Chiều VN</option>
          </select>
        </div>

        {/* Field 5: Volatility Morning Ratio */}
        <div className="param-item">
          <label>Lọc Sóng Sáng 07h-10h <span className="param-tip">Biên độ sáng tối đa</span></label>
          <div className="input-unit">
            <input 
              type="number" 
              step="0.5" 
              min="2.0" 
              max="10.0" 
              value={filterRatio} 
              onChange={(e) => setFilterRatio(e.target.value)} 
            />
            <span>x ATR14</span>
          </div>
        </div>

        {/* Field 6: Volatility ATR Max */}
        <div className="param-item">
          <label>Ngưỡng ATR Bão Giá <span className="param-tip">ATR14 tối đa trước 10h</span></label>
          <div className="input-unit">
            <input 
              type="number" 
              step="1.0" 
              min="5.0" 
              max="40.0" 
              value={filterAtr} 
              onChange={(e) => setFilterAtr(e.target.value)} 
            />
            <span>USD</span>
          </div>
        </div>

        {/* Field 7: Initial Balance */}
        <div className="param-item">
          <label>Vốn Khởi Điểm <span className="param-tip">Tài khoản ban đầu</span></label>
          <div className="input-unit">
            <input 
              type="number" 
              step="1000" 
              min="1000" 
              max="1000000" 
              value={balance} 
              onChange={(e) => setBalance(e.target.value)} 
            />
            <span>USD</span>
          </div>
        </div>

        {/* Field 8: Sizing Mode Selection (Cách 2 vs Cố định) */}
        <div className="param-item">
          <label>Cơ Chế Tính Lot <span className="param-tip">Phương pháp phân bổ volume</span></label>
          <select 
            className="param-select" 
            value={sizingMode} 
            onChange={(e) => setSizingMode(e.target.value)}
          >
            <option value="atr_risk">⚡ Cách 2: % Rủi Ro Theo Biến Động ATR (Khuyên Dùng)</option>
            <option value="capital">🧱 Cố Định Theo Vốn (Mỗi $5k = 0.01 lot)</option>
          </select>
        </div>

        {/* Field 9: Dynamic input based on Sizing Mode */}
        {sizingMode === 'atr_risk' ? (
          <div className="param-item">
            <label>% Rủi Ro Vốn (ATR Risk) <span className="param-tip">Co giãn theo độ lớn ATR14</span></label>
            <div className="input-unit">
              <input 
                type="number" 
                step="0.1" 
                min="0.1" 
                max="5.0" 
                value={riskPercent} 
                onChange={(e) => setRiskPercent(e.target.value)} 
              />
              <span>% Vốn</span>
            </div>
          </div>
        ) : (
          <div className="param-item">
            <label>Định Mức Vốn / 0.01 Lot <span className="param-tip">Lãi kép cổ điển</span></label>
            <div className="input-unit">
              <input 
                type="number" 
                step="1000" 
                min="1000" 
                max="50000" 
                value={lotStep} 
                onChange={(e) => setLotStep(e.target.value)} 
              />
              <span>USD</span>
            </div>
          </div>
        )}
      </div>

      {/* Terminal CLI Command Box */}
      <div style={{ background: '#060911', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '8px', padding: '12px 16px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            LỆNH CHẠY BẰNG TERMINAL / VPS (TÙY CHỌN NẾU MUỐN CHẠY CLI):
          </span>
          <button 
            type="button" 
            onClick={handleCopyCommand}
            style={{
              background: copied ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.1)',
              border: 'none',
              color: copied ? 'var(--accent-green)' : '#FFF',
              padding: '4px 10px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            {copied ? '✓ Đã Copy Lệnh!' : '📋 Copy Lệnh Chạy CLI'}
          </button>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#38BDF8', overflowX: 'auto', whiteSpace: 'nowrap', padding: '4px 0' }}>
          {cliCommand}
        </div>
      </div>

      {/* Action Bar with Primary RUN Button */}
      <div className="action-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div className="run-status">
          {activeRunId ? (
            <span style={{ color: 'var(--text-secondary)' }}>
              🟢 Đang xem bản chạy: <b style={{ color: 'var(--accent-blue)', fontFamily: 'monospace' }}>{activeRunId}</b>
            </span>
          ) : (
            <span style={{ color: 'var(--text-secondary)' }}>
              🟢 Đang xem dữ liệu kết quả từ Web Server
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button 
            type="button" 
            className="preset-btn"
            onClick={onToggleHistory}
            style={{ 
              padding: '11px 18px', 
              fontSize: '13px', 
              background: isHistoryOpen ? 'rgba(139, 92, 246, 0.3)' : 'rgba(139, 92, 246, 0.15)', 
              borderColor: '#8B5CF6', 
              color: '#C4B5FD',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            📜 Lịch Sử Chạy ({historyCount})
          </button>

          <button 
            type="button" 
            className="preset-btn"
            onClick={onRefresh}
            disabled={isLoading}
            style={{ padding: '11px 16px', fontSize: '13px' }}
            title="Đọc lại dữ liệu từ Server"
          >
            🔄 Tải Lại
          </button>

          <button 
            type="button" 
            onClick={handleRunClick}
            disabled={isLoading}
            style={{
              padding: '11px 24px',
              fontSize: '14px',
              fontWeight: 700,
              borderRadius: '8px',
              border: 'none',
              background: isLoading ? 'rgba(59, 130, 246, 0.5)' : 'linear-gradient(135deg, #2563EB, #1D4ED8)',
              color: '#FFF',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 14px rgba(37, 99, 235, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s ease'
            }}
          >
            {isLoading ? (
              <>⏳ ĐANG CHẠY MÔ PHỎNG 15 NĂM...</>
            ) : (
              <>🚀 CHẠY BACKTEST & TRAIN AI</>
            )}
          </button>
        </div>
      </div>
    </section>
  );
}

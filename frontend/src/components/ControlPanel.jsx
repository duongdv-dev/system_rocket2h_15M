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
  const [exitHour, setExitHour] = useState(14);
  const [exitMinute, setExitMinute] = useState(0);
  const [filterRatio, setFilterRatio] = useState(5.0);
  const [filterAtr, setFilterAtr] = useState(18.0);
  const [balance, setBalance] = useState(10000);
  const [lotStep, setLotStep] = useState(5000);
  const [sizingMode, setSizingMode] = useState('atr_risk');
  const [riskPercent, setRiskPercent] = useState(0.5);
  const [activePreset, setActivePreset] = useState('recommended');
  const [copied, setCopied] = useState(false);
  const [systemMode, setSystemMode] = useState('dynamic_ai');

  // Chuỗi HH:MM định dạng chuẩn
  const hardExit = `${String(Math.min(23, Math.max(0, parseInt(exitHour, 10) || 0))).padStart(2, '0')}:${String(Math.min(59, Math.max(0, parseInt(exitMinute, 10) || 0))).padStart(2, '0')}`;

  // Sync inputs if activeParams provided from backend metadata
  useEffect(() => {
    if (activeParams) {
      if (activeParams.min_step_atr !== undefined) setDcaStep(activeParams.min_step_atr);
      if (activeParams.tp_single_atr !== undefined) setTpSingle(activeParams.tp_single_atr);
      if (activeParams.tp_dca_atr !== undefined) setTpDca(activeParams.tp_dca_atr);
      if (activeParams.hard_exit_hour !== undefined) {
        setExitHour(parseInt(activeParams.hard_exit_hour, 10));
        setExitMinute(parseInt(activeParams.hard_exit_minute ?? 0, 10));
      } else if (activeParams.hard_exit && typeof activeParams.hard_exit === 'string') {
        const parts = activeParams.hard_exit.split(':');
        if (parts.length >= 2) {
          setExitHour(parseInt(parts[0], 10) || 14);
          setExitMinute(parseInt(parts[1], 10) || 0);
        }
      }
      if (activeParams.filter_ratio_range !== undefined) setFilterRatio(activeParams.filter_ratio_range);
      if (activeParams.filter_atr_max !== undefined) setFilterAtr(activeParams.filter_atr_max);
      if (activeParams.initial_balance !== undefined) setBalance(activeParams.initial_balance);
      if (activeParams.lot_step_capital !== undefined) setLotStep(activeParams.lot_step_capital);
      if (activeParams.sizing_mode !== undefined) setSizingMode(activeParams.sizing_mode);
      if (activeParams.risk_percent !== undefined) setRiskPercent(activeParams.risk_percent);
      if (activeParams.mode !== undefined) setSystemMode(activeParams.mode);
    }
  }, [activeParams]);

  const handlePreset = (preset) => {
    setActivePreset(preset);
    if (preset === 'recommended') {
      setDcaStep(0.5);
      setTpSingle(0.8);
      setTpDca(0.5);
      setExitHour(14);
      setExitMinute(0);
      setFilterRatio(5.0);
      setFilterAtr(18.0);
      setSizingMode('atr_risk');
      setRiskPercent(0.5);
    } else if (preset === 'safe') {
      setDcaStep(0.6);
      setTpSingle(0.6);
      setTpDca(0.4);
      setExitHour(12);
      setExitMinute(0);
      setFilterRatio(4.0);
      setFilterAtr(15.0);
      setSizingMode('atr_risk');
      setRiskPercent(0.3);
    } else if (preset === 'aggressive') {
      setDcaStep(0.5);
      setTpSingle(1.0);
      setTpDca(0.6);
      setExitHour(15);
      setExitMinute(0);
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
      const hNum = Math.min(23, Math.max(0, parseInt(exitHour, 10) || 0));
      const mNum = Math.min(59, Math.max(0, parseInt(exitMinute, 10) || 0));
      onTriggerRun({
        mode: systemMode,
        min_step_atr: parseFloat(dcaStep),
        tp_single_atr: parseFloat(tpSingle),
        tp_dca_atr: parseFloat(tpDca),
        hard_exit: `${String(hNum).padStart(2, '0')}:${String(mNum).padStart(2, '0')}`,
        hard_exit_hour: hNum,
        hard_exit_minute: mNum,
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
              BỘ ĐIỀU KHIỂN ĐỘNG CƠ QUANT AI
              <span className="badge badge-live" style={{ background: systemMode === 'dynamic_ai' ? '#6366F1' : '#475569', color: '#FFF' }}>
                {systemMode === 'dynamic_ai' ? '🤖 AI ADAPTIVE ACTIVE' : '⚙️ MANUAL MODE'}
              </span>
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {systemMode === 'dynamic_ai'
                ? 'Hệ thống tự động học và thích ứng tham số cho từng ngày theo hình thái sóng sáng 07h-10h VN.'
                : 'Bạn đang bật quyền can thiệp thủ công: tự do chỉnh từng tham số và nhấn nút chạy thử nghiệm.'}
            </p>
          </div>
        </div>

        {systemMode === 'manual' && (
          <div className="preset-buttons">
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>MẪU THỦ CÔNG:</span>
            <button 
              type="button"
              className={`preset-btn ${activePreset === 'recommended' ? 'active-preset' : ''}`}
              onClick={() => handlePreset('recommended')}
            >
              ⭐ Khuyên Dùng
            </button>
            <button 
              type="button"
              className={`preset-btn ${activePreset === 'safe' ? 'active-preset' : ''}`}
              onClick={() => handlePreset('safe')}
            >
              🛡️ An Toàn
            </button>
            <button 
              type="button"
              className={`preset-btn ${activePreset === 'aggressive' ? 'active-preset' : ''}`}
              onClick={() => handlePreset('aggressive')}
            >
              🔥 Tối Đa
            </button>
          </div>
        )}
      </div>

      {/* Mode Switcher Banner */}
      <div style={{
        margin: '14px 0 16px 0',
        padding: '12px 18px',
        background: systemMode === 'dynamic_ai' 
          ? 'linear-gradient(90deg, rgba(99, 102, 241, 0.18) 0%, rgba(56, 189, 248, 0.12) 100%)' 
          : 'rgba(255, 255, 255, 0.03)',
        border: `1px solid ${systemMode === 'dynamic_ai' ? 'rgba(99, 102, 241, 0.45)' : 'rgba(255, 255, 255, 0.1)'}`,
        borderRadius: '10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>{systemMode === 'dynamic_ai' ? '🤖' : '⚙️'}</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: '13px', color: '#FFF', display: 'flex', alignItems: 'center', gap: '8px' }}>
              CHẾ ĐỘ VẬN HÀNH: {systemMode === 'dynamic_ai' ? 'AI TỰ ĐỘNG THÍCH ỨNG THEO HÌNH THÁI' : 'TÙY BIẾN THỦ CÔNG'}
              <span style={{
                background: systemMode === 'dynamic_ai' ? '#10B981' : '#64748B',
                color: '#0B0F19',
                padding: '1px 6px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 800
              }}>
                {systemMode === 'dynamic_ai' ? 'KHUYÊN DÙNG' : 'OVERRIDE'}
              </span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
              {systemMode === 'dynamic_ai'
                ? '✨ Không cần nhập tay: AI sẽ tự động phân tích sóng sáng từng ngày và chọn bộ tham số (DCA, TP, Giờ Cắt) tối ưu nhất.'
                : 'Bạn đang tự nhập các giá trị cố định bên dưới để kiểm định theo ý tưởng cá nhân.'}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            onClick={() => setSystemMode('dynamic_ai')}
            style={{
              background: systemMode === 'dynamic_ai' ? 'linear-gradient(135deg, #6366F1, #4F46E5)' : 'rgba(255, 255, 255, 0.06)',
              color: '#FFF',
              border: systemMode === 'dynamic_ai' ? '1px solid #818CF8' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s',
              boxShadow: systemMode === 'dynamic_ai' ? '0 0 14px rgba(99, 102, 241, 0.4)' : 'none'
            }}
          >
            🤖 AI Tự Động Thích Ứng
          </button>
          <button
            type="button"
            onClick={() => setSystemMode('manual')}
            style={{
              background: systemMode === 'manual' ? '#475569' : 'rgba(255, 255, 255, 0.06)',
              color: systemMode === 'manual' ? '#FFF' : 'var(--text-muted)',
              border: systemMode === 'manual' ? '1px solid #64748B' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}
          >
            ⚙️ Tùy Biến Thủ Công
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

        {/* Field 4: Hard Exit Hour & Minute */}
        <div className="param-item">
          <label>Giờ Cắt Lỗ Ép Buộc <span className="param-tip">Tự do nhập Giờ & Phút (giờ VN)</span></label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="input-unit" style={{ flex: 1 }}>
              <input 
                type="number" 
                min="0" 
                max="23" 
                value={exitHour} 
                onChange={(e) => setExitHour(e.target.value)}
                placeholder="14"
                style={{ textAlign: 'center', padding: '7px 4px' }}
              />
              <span>Giờ</span>
            </div>
            <span style={{ fontWeight: 800, color: 'var(--text-muted)', fontSize: '15px' }}>:</span>
            <div className="input-unit" style={{ flex: 1 }}>
              <input 
                type="number" 
                min="0" 
                max="59" 
                value={exitMinute} 
                onChange={(e) => setExitMinute(e.target.value)}
                placeholder="00"
                style={{ textAlign: 'center', padding: '7px 4px' }}
              />
              <span>Phút</span>
            </div>
          </div>
          {/* Quick Benchmark Chips */}
          <div style={{ display: 'flex', gap: '5px', marginTop: '6px', flexWrap: 'wrap' }}>
            {['12:00', '13:00', '13:30', '14:00', '14:30', '15:00'].map((presetTime) => {
              const [h, m] = presetTime.split(':');
              const isSelected = parseInt(exitHour, 10) === parseInt(h, 10) && parseInt(exitMinute, 10) === parseInt(m, 10);
              return (
                <button
                  key={presetTime}
                  type="button"
                  onClick={() => {
                    setExitHour(parseInt(h, 10));
                    setExitMinute(parseInt(m, 10));
                  }}
                  style={{
                    background: isSelected ? 'rgba(99, 102, 241, 0.35)' : 'rgba(255, 255, 255, 0.05)',
                    border: isSelected ? '1px solid #6366F1' : '1px solid rgba(255, 255, 255, 0.1)',
                    color: isSelected ? '#A5B4FC' : 'var(--text-muted)',
                    borderRadius: '4px',
                    padding: '2px 7px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    cursor: 'pointer',
                    transition: 'all 0.15s'
                  }}
                >
                  {presetTime}
                </button>
              );
            })}
          </div>
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
              background: isLoading 
                ? 'rgba(99, 102, 241, 0.5)' 
                : (systemMode === 'dynamic_ai' ? 'linear-gradient(135deg, #6366F1, #4338CA)' : 'linear-gradient(135deg, #2563EB, #1D4ED8)'),
              color: '#FFF',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              boxShadow: systemMode === 'dynamic_ai' ? '0 4px 16px rgba(99, 102, 241, 0.5)' : '0 4px 14px rgba(37, 99, 235, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s ease'
            }}
          >
            {isLoading ? (
              <>⏳ ĐANG HUẤN LUYỆN MA TRẬN AI & MÔ PHỎNG 15 NĂM...</>
            ) : systemMode === 'dynamic_ai' ? (
              <>🧠 HUẤN LUYỆN MA TRẬN & CHẠY DYNAMIC AI</>
            ) : (
              <>🚀 CHẠY BACKTEST THAM SỐ THỦ CÔNG</>
            )}
          </button>
        </div>
      </div>
    </section>
  );
}

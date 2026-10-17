import React from 'react';

export default function AutonomousAiBar({
  balance,
  setBalance,
  onTriggerAiBacktest,
  onTriggerDeepTraining,
  onOpenTrainingReport,
  onToggleHistory,
  isDeepTraining,
  isLoading,
  hasTrainingCatalog,
  catalogCount,
  historyCount,
  isHistoryOpen,
  activeRunId,
  onRefresh
}) {
  return (
    <section className="control-panel-card" style={{
      background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 27, 75, 0.6) 100%)',
      border: '1px solid rgba(99, 102, 241, 0.4)',
      boxShadow: '0 8px 30px rgba(99, 102, 241, 0.15)',
      marginBottom: '20px',
      padding: '18px 24px'
    }}>
      {/* Header Info */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366F1, #4338CA)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '22px',
            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)'
          }}>
            🤖
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2 style={{ fontSize: '17px', fontWeight: 800, color: '#FFF', margin: 0 }}>
                100% QUANT AI AUTONOMOUS SYSTEM
              </h2>
              <span className="badge badge-live" style={{ background: '#10B981', color: '#042F2E', fontWeight: 800 }}>
                AI QUYẾT ĐỊNH MỌI THỨ
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '3px 0 0 0' }}>
              Tự động nhận diện sóng sáng, may đo khối lượng (Lot), khống chế tầng DCA, chốt lời và cắt lỗ cho từng phiên.
            </p>
          </div>
        </div>

        {/* Status Indicator */}
        <div style={{ fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
          {activeRunId ? (
            <span style={{ color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.3)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
              🟢 Đang xem bản chạy: <b style={{ color: '#38BDF8' }}>{activeRunId}</b>
            </span>
          ) : (
            <span style={{ color: '#FCD34D', background: 'rgba(251,191,36,0.1)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(251,191,36,0.3)' }}>
              ⚡ Sẵn sàng: Nhấn nút bên dưới để kích hoạt AI kiểm định
            </span>
          )}
        </div>
      </div>

      {/* Main Execution Controls */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '14px',
        paddingTop: '14px',
        borderTop: '1px solid rgba(255, 255, 255, 0.08)'
      }}>
        {/* Capital Input (Vốn ban đầu) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Vốn Ban Đầu ($):
          </label>
          <input
            type="number"
            value={balance}
            onChange={(e) => setBalance(parseFloat(e.target.value) || 10000)}
            step="1000"
            min="1000"
            style={{
              width: '130px',
              padding: '10px 12px',
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid rgba(99, 102, 241, 0.5)',
              borderRadius: '8px',
              color: '#38BDF8',
              fontWeight: 800,
              fontSize: '15px',
              fontFamily: 'var(--font-mono)'
            }}
          />
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button 
            type="button" 
            className="preset-btn"
            onClick={onToggleHistory}
            style={{ 
              padding: '11px 16px', 
              fontSize: '13px', 
              background: isHistoryOpen ? 'rgba(139, 92, 246, 0.3)' : 'rgba(139, 92, 246, 0.15)', 
              borderColor: '#8B5CF6', 
              color: '#C4B5FD',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            📜 Lịch Sử ({historyCount})
          </button>

          <button 
            type="button" 
            className="preset-btn"
            onClick={onRefresh}
            disabled={isLoading || isDeepTraining}
            style={{ padding: '11px 14px', fontSize: '13px' }}
            title="Đọc lại dữ liệu từ Server"
          >
            🔄
          </button>

          {hasTrainingCatalog && (
            <button 
              type="button" 
              onClick={onOpenTrainingReport}
              disabled={isLoading || isDeepTraining}
              style={{
                padding: '11px 16px',
                fontSize: '13px',
                fontWeight: 700,
                borderRadius: '8px',
                border: '1px solid rgba(168, 85, 247, 0.4)',
                background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(126, 34, 206, 0.35))',
                color: '#E9D5FF',
                cursor: (isLoading || isDeepTraining) ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 4px 14px rgba(168, 85, 247, 0.25)'
              }}
            >
              📊 BÁO CÁO 10 NĂM ({catalogCount} HÌNH THÁI)
            </button>
          )}

          <button 
            type="button" 
            onClick={onTriggerDeepTraining}
            disabled={isLoading || isDeepTraining}
            style={{
              padding: '11px 16px',
              fontSize: '13px',
              fontWeight: 700,
              borderRadius: '8px',
              border: '1px solid rgba(147, 51, 234, 0.5)',
              background: isDeepTraining 
                ? 'rgba(147, 51, 234, 0.3)' 
                : 'linear-gradient(135deg, rgba(147, 51, 234, 0.3), rgba(109, 40, 217, 0.4))',
              color: '#F3E8FF',
              cursor: (isLoading || isDeepTraining) ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 14px rgba(147, 51, 234, 0.2)',
              transition: 'all 0.2s ease'
            }}
            title="Quét lại 3,000,000 lượt mô phỏng trên 10 năm và tự động huấn luyện lại chính mình"
          >
            {isDeepTraining ? (
              <>⏳ ĐANG QUÉT 3 TRIỆU SETUPS...</>
            ) : (
              <>🔄 TỰ ĐỘNG HUẤN LUYỆN LẠI 10 NĂM</>
            )}
          </button>

          <button 
            type="button" 
            onClick={onTriggerAiBacktest}
            disabled={isLoading || isDeepTraining}
            style={{
              padding: '11px 26px',
              fontSize: '14px',
              fontWeight: 800,
              borderRadius: '8px',
              border: 'none',
              background: isLoading 
                ? 'rgba(99, 102, 241, 0.5)' 
                : 'linear-gradient(135deg, #10B981, #059669)',
              color: '#FFF',
              cursor: (isLoading || isDeepTraining) ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 18px rgba(16, 185, 129, 0.4)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s ease'
            }}
          >
            {isLoading ? (
              <>⏳ ĐANG CHẠY KIỂM ĐỊNH MÙ 5 NĂM...</>
            ) : (
              <>🚀 CHẠY KIỂM ĐỊNH AI TỰ TRỊ (2021-2025)</>
            )}
          </button>
        </div>
      </div>
    </section>
  );
}

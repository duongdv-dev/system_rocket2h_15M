import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ControlPanel from './components/ControlPanel';
import HistoryPanel from './components/HistoryPanel';
import MetricsGrid from './components/MetricsGrid';
import EquityChart from './components/EquityChart';
import DayOfWeekAnalytics from './components/DayOfWeekAnalytics';
import CalendarHeatmap from './components/CalendarHeatmap';
import RiskDaysInspector from './components/RiskDaysInspector';
import TradeLogTable from './components/TradeLogTable';
import DailyCandleModal from './components/DailyCandleModal';
import AiRegimeMatrixCard from './components/AiRegimeMatrixCard';
import TrainingReportModal from './components/TrainingReportModal';
import { 
  checkServerStatus, 
  fetchInitialData, 
  fetchHistory, 
  fetchRunDetail, 
  triggerBacktestRun,
  selectActiveRun,
  deleteHistoricalRun,
  fetchTrainCatalog,
  triggerDeepTraining
} from './services/api';

export default function App() {
  const [rawData, setRawData] = useState(null);
  const [currentPeriod, setCurrentPeriod] = useState('test');
  const [currentMode, setCurrentMode] = useState('ai');
  const [isLoading, setIsLoading] = useState(false);
  const [serverStatus, setServerStatus] = useState(null);
  const [historyRuns, setHistoryRuns] = useState([]);
  const [activeRunId, setActiveRunId] = useState(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);
  const [inspectTarget, setInspectTarget] = useState(null);
  const [catalogData, setCatalogData] = useState(null);
  const [isTrainingReportOpen, setIsTrainingReportOpen] = useState(false);
  const [isDeepTraining, setIsDeepTraining] = useState(false);

  const handleInspectTrade = (trade, filteredDay = null) => {
    setInspectTarget({ trade, filteredDay });
  };

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const loadDataAndHistory = async () => {
    setIsLoading(true);
    try {
      // Chỉ nạp trạng thái server, lịch sử các lần chạy và catalog huấn luyện (nếu có)
      // KHÔNG tự động nạp mặc định bất kỳ bản chạy hay setup nào khi mới vào web
      const [status, runs, catRes] = await Promise.all([
        checkServerStatus(),
        fetchHistory(),
        fetchTrainCatalog()
      ]);

      setServerStatus(status);
      setHistoryRuns(runs || []);
      if (catRes?.catalog) {
        setCatalogData(catRes.catalog);
      }
    } catch (err) {
      console.error("Lỗi nạp dữ liệu:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDataAndHistory();
  }, []);

  // Handler: Kích hoạt chạy Backtest / Train AI mới từ Web UI
  const handleTriggerRun = async (params) => {
    setIsLoading(true);
    try {
      showToast("🚀 Đang nạp 15 năm nến và chạy mô phỏng AI...");
      const res = await triggerBacktestRun(params);
      if (res && res.data) {
        setRawData(res.data);
        setActiveRunId(res.run_id);
        showToast(`✓ Chạy thành công! Đã lưu bản chạy: ${res.run_id}`);
        // Cập nhật lại lịch sử và trạng thái server
        const [status, runs] = await Promise.all([checkServerStatus(), fetchHistory()]);
        setServerStatus(status);
        setHistoryRuns(runs || []);
      }
    } catch (err) {
      alert(`Lỗi khi chạy: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handler: Kích hoạt huấn luyện sâu 10 năm (1,200 setups/ngày)
  const handleTriggerDeepTraining = async () => {
    setIsDeepTraining(true);
    try {
      showToast("🔬 Đang quét 1,200 setups x 2,500 ngày huấn luyện (3,000,000 lượt)...");
      const res = await triggerDeepTraining();
      if (res && res.catalog) {
        setCatalogData(res.catalog);
        setIsTrainingReportOpen(true);
        showToast("✓ Đã hoàn tất huấn luyện 10 năm & gom cụm thành công!");
      }
    } catch (err) {
      alert(`Lỗi huấn luyện sâu: ${err.message}`);
    } finally {
      setIsDeepTraining(false);
    }
  };

  // Handler: Phê duyệt bộ setup từ báo cáo huấn luyện và chạy backtest 2021-2025
  const handleApproveAndBacktest = async () => {
    setIsTrainingReportOpen(false);
    showToast("✅ Đã phê duyệt bộ setup! Bắt đầu chạy kiểm định Backtest (2021-2025)...");
    await handleTriggerRun({ mode: 'dynamic_ai' });
  };

  // Handler: Chọn xem lại một bản chạy lịch sử cụ thể
  const handleSelectRun = async (runId) => {
    setIsLoading(true);
    try {
      showToast(`📂 Đang tải dữ liệu bản chạy: ${runId}...`);
      const detail = await fetchRunDetail(runId);
      if (detail) {
        setRawData(detail);
        setActiveRunId(runId);
        showToast(`✓ Đã nạp thành công bản chạy: ${runId}`);
        // Đồng bộ server active
        selectActiveRun(runId).catch(() => {});
      }
    } catch (err) {
      alert(`Không thể nạp bản chạy: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handler: Xóa bản chạy khỏi lịch sử
  const handleDeleteRun = async (runId) => {
    try {
      await deleteHistoricalRun(runId);
      showToast(`🗑️ Đã xóa bản chạy: ${runId}`);
      const runs = await fetchHistory();
      setHistoryRuns(runs || []);
      const status = await checkServerStatus();
      setServerStatus(status);
    } catch (err) {
      alert(`Lỗi khi xóa: ${err.message}`);
    }
  };

  const periodData = rawData ? rawData[currentPeriod] : null;
  const currentTrades = (periodData && periodData[currentMode]) ? periodData[currentMode].trades : [];
  const filterAnalysis = rawData?.volatility_filter_analysis;

  return (
    <div className="container">
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          background: 'linear-gradient(135deg, #1E293B, #0F172A)',
          border: '1px solid #3B82F6',
          color: '#FFF',
          padding: '12px 20px',
          borderRadius: '10px',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)',
          zIndex: 9999,
          fontSize: '13px',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          animation: 'fadeIn 0.3s ease'
        }}>
          {toastMessage}
        </div>
      )}

      {/* 1. Navbar */}
      <Navbar 
        metadata={rawData?.metadata} 
        serverStatus={serverStatus} 
        onToggleHistory={() => setIsHistoryOpen(!isHistoryOpen)}
        isHistoryOpen={isHistoryOpen}
      />

      {/* 2. Control Panel with Inputs & Run Trigger */}
      <ControlPanel 
        onRefresh={loadDataAndHistory}
        onTriggerRun={handleTriggerRun}
        onTriggerDeepTraining={handleTriggerDeepTraining}
        onOpenTrainingReport={() => setIsTrainingReportOpen(true)}
        hasTrainingCatalog={!!catalogData}
        isDeepTraining={isDeepTraining}
        catalogCount={catalogData?.cluster_summaries?.length || 4}
        onToggleHistory={() => setIsHistoryOpen(!isHistoryOpen)}
        historyCount={historyRuns.length}
        isHistoryOpen={isHistoryOpen}
        isLoading={isLoading} 
        activeParams={rawData?.metadata?.active_params}
        dataStatus={serverStatus}
        activeRunId={activeRunId}
      />

      {/* 3. History Panel (Xem lại toàn bộ lịch sử các lần chạy) */}
      {isHistoryOpen && (
        <HistoryPanel 
          runs={historyRuns}
          activeRunId={activeRunId}
          onSelectRun={handleSelectRun}
          onDeleteRun={handleDeleteRun}
          onRefreshHistory={loadDataAndHistory}
          isLoading={isLoading}
        />
      )}

      {/* 3.5. AI Market Regime Matrix & Auto-Tuned Parameters */}
      <AiRegimeMatrixCard 
        data={rawData || (catalogData ? { regime_matrix: catalogData.morphology_catalog } : null)} 
        onOpenTrainingReport={catalogData ? () => setIsTrainingReportOpen(true) : handleTriggerDeepTraining} 
      />

      {/* 4. Hiển thị Kết Quả Kiểm Định (Chỉ hiện khi bạn bấm Chạy hoặc chọn từ Lịch Sử) */}
      {rawData ? (
        <>
          {/* Metrics Grid & Head-to-Head Comparison */}
          <MetricsGrid 
            data={rawData}
            currentPeriod={currentPeriod}
            onPeriodChange={setCurrentPeriod}
            currentMode={currentMode}
            onModeChange={setCurrentMode}
          />

          {/* Equity Curve & Dynamic DCA Layers Distribution */}
          <EquityChart periodData={periodData} currentMode={currentMode} />

          {/* Day-of-Week Quant Breakdown */}
          <DayOfWeekAnalytics trades={currentTrades} />

          {/* Calendar Heatmap & Monthly Return Matrix */}
          <CalendarHeatmap 
            trades={currentTrades} 
            filterAnalysis={filterAnalysis} 
            onInspectTrade={handleInspectTrade}
          />

          {/* Risk Days & Anomaly Inspector */}
          <RiskDaysInspector 
            filterAnalysis={filterAnalysis} 
            onInspectTrade={handleInspectTrade}
          />

          {/* Trade Audit Log Table */}
          <TradeLogTable 
            trades={currentTrades} 
            onInspectTrade={handleInspectTrade}
          />
        </>
      ) : (
        /* Standby State: Khi chưa kích hoạt chạy setup */
        <section className="section-card" style={{
          padding: '40px 24px',
          textAlign: 'center',
          background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.7) 0%, rgba(11, 16, 29, 0.9) 100%)',
          border: '1px dashed rgba(99, 102, 241, 0.35)',
          borderRadius: '16px',
          marginBottom: '24px'
        }}>
          <span style={{ fontSize: '42px', display: 'block', marginBottom: '12px' }}>🎯</span>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#FFF' }}>
            HỆ THỐNG ĐANG Ở CHẾ ĐỘ CHỜ (STANDBY) — ĐÃ TẮT TỰ ĐỘNG CHẠY MẶC ĐỊNH
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '680px', margin: '8px auto 20px', lineHeight: '1.6' }}>
            Hệ thống không còn tự động nạp hay chạy bất kỳ setup nào khi bạn vào Web. Bạn hoàn toàn chủ động:
            <br/>
            • Bấm <b style={{ color: '#C084FC' }}>"🔬 Huấn Luyện Sâu 10 Năm"</b> để AI quét 1,200 setups/ngày và tự động gom nhóm hình thái.
            <br/>
            • Bấm <b style={{ color: '#818CF8' }}>"🧠 Huấn Luyện Ma Trận & Chạy Dynamic AI"</b> để chạy kiểm định trực tiếp.
            <br/>
            • Hoặc mở <b style={{ color: '#38BDF8' }}>"📜 Lịch Sử Chạy"</b> để xem lại các kết quả đã lưu trước đây.
          </p>
        </section>
      )}

      {/* 10. VPS Architecture & Candle Data Storage Guide */}
      <section className="vps-box">
        <div className="vps-header">
          <h3 style={{ fontSize: '15px', fontWeight: 700 }}>
            🚀 Kiến Trúc Phân Tách 3 Thư Mục Hoàn Chỉnh
          </h3>
          <span className="badge badge-live">CLEAN ARCHITECTURE</span>
        </div>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.6' }}>
          • <b>Thư mục nến tập trung (data/):</b> Toàn bộ dữ liệu CSV 15 năm nằm gọn gàng trong <code>data/</code>.<br/>
          • <b>Thư mục Web Server & Lịch sử (server/):</b> Máy chủ trả API và lưu trữ lịch sử trong <code>server/history/</code>.<br/>
          • <b>Thư mục AI & Backtest Engine (engine/):</b> Động cơ tính toán chuyên biệt làm việc với nến trong <code>engine/</code>.<br/>
          • <b>Lệnh chạy Web Server (phục vụ Web UI & API Lịch sử 24/7):</b>
        </div>
        <div className="code-block" style={{ marginBottom: '16px' }}>
          <code>python3 server/app.py --host 0.0.0.0 --port 8080</code>
          <button 
            type="button"
            className="copy-btn" 
            onClick={() => {
              navigator.clipboard.writeText('python3 server/app.py --host 0.0.0.0 --port 8080');
              showToast('Đã copy lệnh chạy Web Server!');
            }}
          >
            Copy Lệnh Web
          </button>
        </div>

        <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.6' }}>
          • <b>Lệnh chạy Backtest / Huấn luyện độc lập bằng CLI (Nếu muốn chạy tay trên terminal):</b>
        </div>
        <div className="code-block">
          <code>python3 engine/run_cli.py --min-step 0.5 --tp-single 0.8 --tp-dca 0.5 --hard-exit 14:00</code>
          <button 
            type="button"
            className="copy-btn" 
            onClick={() => {
              navigator.clipboard.writeText('python3 engine/run_cli.py --min-step 0.5 --tp-single 0.8 --tp-dca 0.5 --hard-exit 14:00');
              showToast('Đã copy lệnh chạy AI Engine CLI!');
            }}
          >
            Copy Lệnh AI CLI
          </button>
        </div>
      </section>

      {/* 11. Daily Candlestick Inspection Modal (Soi nến M15 từng ngày) */}
      <DailyCandleModal 
        isOpen={!!inspectTarget}
        onClose={() => setInspectTarget(null)}
        trade={inspectTarget?.trade}
        filteredDay={inspectTarget?.filteredDay}
      />

      {/* 12. Pre-Backtest 10-Year Deep Training Report Modal */}
      <TrainingReportModal 
        isOpen={isTrainingReportOpen}
        onClose={() => setIsTrainingReportOpen(false)}
        catalogData={catalogData}
        onApproveAndBacktest={handleApproveAndBacktest}
        isBacktesting={isLoading}
      />
    </div>
  );
}

/**
 * API Service for Quant AI Engine & Web Server
 * Giao tiếp với web_server.py (Cổng 8080)
 */

export async function checkServerStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return { server_status: 'offline', error: err.message };
  }
}

export async function fetchInitialData() {
  try {
    const res = await fetch('/api/data');
    if (!res.ok) {
      // Fallback
      const fallback = await fetch('/web_data.json');
      if (!fallback.ok) throw new Error(`HTTP ${fallback.status}`);
      return await fallback.json();
    }
    return await res.json();
  } catch (err) {
    console.warn("Không tải được dữ liệu từ server:", err);
    return null;
  }
}

export async function fetchHistory() {
  try {
    const res = await fetch('/api/history');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.runs || [];
  } catch (err) {
    console.error("Lỗi lấy lịch sử chạy:", err);
    return [];
  }
}

export async function fetchRunDetail(runId) {
  const res = await fetch(`/api/runs/${runId}`);
  if (!res.ok) {
    throw new Error(`Không thể tải bản chạy ${runId} (${res.status})`);
  }
  return await res.json();
}

export async function triggerBacktestRun(params) {
  const res = await fetch('/api/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.message || `Lỗi máy chủ HTTP ${res.status}`);
  }

  return await res.json();
}

export async function selectActiveRun(runId) {
  const res = await fetch('/api/runs/select', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ run_id: runId }),
  });

  if (!res.ok) {
    throw new Error(`Không thể chọn bản chạy ${runId}`);
  }

  return await res.json();
}

export async function deleteHistoricalRun(runId) {
  const res = await fetch(`/api/runs/${runId}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    throw new Error(`Không thể xóa bản chạy ${runId}`);
  }

  return await res.json();
}

export async function fetchDayCandles(date) {
  try {
    const res = await fetch(`/api/candles?date=${date}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.candles || [];
  } catch (err) {
    console.error("Lỗi lấy dữ liệu nến ngày:", err);
    return [];
  }
}


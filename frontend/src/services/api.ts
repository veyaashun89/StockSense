import {
  Product,
  ReorderPlanResponse,
  ForecastResult,
  WeeklyForecastResult,
  DashboardData,
  CsvValidationResponse,
  Supplier,
  SettingsData,
  DataStatus,
  User,
  UserRole,
  AlertItem,
  PurchaseOrder,
  WholesaleCatalogItem,
  PipelineRun,
  GstLine,
  StockBatch,
  MarketSignal,
  CVScanResult,
  BarcodeDecodeResponse,
  PaymentQrResponse,
  PaymentReceipt,
  SessionInfo,
  FrameDetectionResponse,
  RecordSessionSummary,
  RecordSessionItem,
  RetailerOverviewData,
  WholesalerOverviewData,
  DealerOverviewData,
  AdminOverviewData,
  NotificationsListResponse,
  NotificationSettingsResponse,
  TopicInfoResponse,
  NotificationSetting
} from '../types';

const API_BASE = '/api';
const TOKEN_KEY = 'stocksense_token';
const USER_KEY = 'stocksense_user';

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredSession(user: User): void {
  try {
    if (user.token) {
      localStorage.setItem(TOKEN_KEY, user.token);
    }
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch (e) {
    console.error('Failed to save session to localStorage', e);
  }
}

export function clearStoredSession(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch (e) {
    console.error('Failed to clear session', e);
  }
}

export function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = getStoredToken();
  const user = getStoredUser();
  const headers = new Headers(init?.headers || {});
  
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (user?.role && !headers.has('X-User-Role')) {
    headers.set('X-User-Role', user.role);
  }
  
  return fetch(url, {
    ...init,
    headers
  });
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.error) {
        errorMsg = errJson.error;
      }
    } catch {
      // not JSON
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export const api = {
  // Auth & Session
  login: async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await handleResponse<{ user: User; message: string }>(res);
    if (data?.user) {
      setStoredSession(data.user);
    }
    return data;
  },

  logout: () => {
    clearStoredSession();
  },

  switchRole: async (role: UserRole) => {
    const res = await authFetch(`${API_BASE}/auth/switch-role`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role })
    });
    const data = await handleResponse<{ user: User; message: string }>(res);
    if (data?.user) {
      setStoredSession(data.user);
    }
    return data;
  },

  getMe: () => authFetch(`${API_BASE}/auth/me`).then(res => handleResponse<{ user: User }>(res)),

  // Health & Dashboard
  getHealth: () => fetch(`${API_BASE}/health`).then(res => handleResponse<{ status: string; timestamp: string }>(res)),

  getDashboard: () => authFetch(`${API_BASE}/dashboard`).then(res => handleResponse<DashboardData>(res)),

  // Role Scoped Overview Endpoints
  getOverview: (role?: string) => {
    const user = getStoredUser();
    const effectiveRole = (role || user?.role || 'retailer').toLowerCase();
    return authFetch(`${API_BASE}/overview/${effectiveRole}`).then(res => handleResponse<any>(res));
  },

  getRetailerOverview: () =>
    authFetch(`${API_BASE}/overview/retailer`).then(res => handleResponse<RetailerOverviewData>(res)),

  getWholesalerOverview: () =>
    authFetch(`${API_BASE}/overview/wholesaler`).then(res => handleResponse<WholesalerOverviewData>(res)),

  getDealerOverview: () =>
    authFetch(`${API_BASE}/overview/dealer`).then(res => handleResponse<DealerOverviewData>(res)),

  getAdminOverview: () =>
    authFetch(`${API_BASE}/overview/admin`).then(res => handleResponse<AdminOverviewData>(res)),

  // Products
  getProducts: (params?: {
    search?: string;
    category?: string;
    status?: string;
    sort_by?: string;
    sort_dir?: string;
    page?: number;
    per_page?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          sp.append(k, String(v));
        }
      });
    }
    return fetch(`${API_BASE}/products?${sp.toString()}`).then(res =>
      handleResponse<{
        total: number;
        page: number;
        per_page: number;
        total_pages: number;
        items: Product[];
      }>(res)
    );
  },

  getProduct: (idOrSku: string | number) =>
    fetch(`${API_BASE}/products/${idOrSku}`).then(res => handleResponse<Product>(res)),

  createProduct: (data: Partial<Product>) =>
    fetch(`${API_BASE}/products`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<Product>(res)),

  updateProduct: (id: number, data: Partial<Product>) =>
    fetch(`${API_BASE}/products/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<Product>(res)),

  deleteProduct: (id: number) =>
    fetch(`${API_BASE}/products/${id}`, {
      method: 'DELETE'
    }).then(res => handleResponse<{ status: string; message: string; sales_count: number }>(res)),

  getCategories: () => fetch(`${API_BASE}/products/categories`).then(res => handleResponse<string[]>(res)),

  getSuppliers: () => fetch(`${API_BASE}/products/suppliers`).then(res => handleResponse<Supplier[]>(res)),

  // Sales
  getSales: (params?: { sku?: string; start_date?: string; end_date?: string; page?: number; per_page?: number }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          sp.append(k, String(v));
        }
      });
    }
    return fetch(`${API_BASE}/sales?${sp.toString()}`).then(res =>
      handleResponse<{
        total: number;
        page: number;
        per_page: number;
        total_pages: number;
        items: any[];
      }>(res)
    );
  },

  validateSalesCsv: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/sales/validate`, {
      method: 'POST',
      body: formData
    }).then(res => handleResponse<CsvValidationResponse>(res));
  },

  commitSalesImport: (batchId: string, filename: string, validRecords: any[]) =>
    fetch(`${API_BASE}/sales/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ batch_id: batchId, filename, valid_records: validRecords })
    }).then(res => handleResponse<{ status: string; imported_count: number; message: string }>(res)),

  // GST Files & Mappings
  validateGstCsv: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/gst/validate`, {
      method: 'POST',
      body: formData
    }).then(res => handleResponse<CsvValidationResponse>(res));
  },

  commitGstImport: (batchId: string, filename: string, validRows: any[], updateStock: boolean = true) =>
    fetch(`${API_BASE}/gst/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ batch_id: batchId, filename, valid_rows: validRows, update_stock: updateStock })
    }).then(res => handleResponse<{ status: string; imported_count: number; outward_sales_added: number; inward_receipts_recorded: number; message: string }>(res)),

  getGstLines: (params?: { supply_type?: string; page?: number; per_page?: number }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    return fetch(`${API_BASE}/gst/lines?${sp.toString()}`).then(res =>
      handleResponse<{ total: number; page: number; per_page: number; items: GstLine[] }>(res)
    );
  },

  getGstMappings: () => fetch(`${API_BASE}/gst/mappings`).then(res => handleResponse<any[]>(res)),

  addGstMapping: (data: { hsn_code?: string; item_description?: string; mapped_sku: string }) =>
    fetch(`${API_BASE}/gst/mappings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<{ status: string; message: string }>(res)),

  // Stock Snapshots & Batches
  importStockCsv: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/stock/import`, {
      method: 'POST',
      body: formData
    }).then(res => handleResponse<{ status: string; reconciled_products: number; batches_recorded: number; message: string }>(res));
  },

  getStockBatches: (productId?: number) => {
    const sp = productId ? `?product_id=${productId}` : '';
    return fetch(`${API_BASE}/stock/batches${sp}`).then(res => handleResponse<StockBatch[]>(res));
  },

  // Market Signals
  importMarketCsv: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/market/import`, {
      method: 'POST',
      body: formData
    }).then(res => handleResponse<{ status: string; inserted_count: number; message: string }>(res));
  },

  getMarketSignals: () => fetch(`${API_BASE}/market`).then(res => handleResponse<MarketSignal[]>(res)),

  // Demand Forecast (Daily & Weekly)
  getForecast: (params?: { product_id?: number; sku?: string; horizon?: number; window?: number; method?: string }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    return fetch(`${API_BASE}/forecast?${sp.toString()}`).then(res => handleResponse<ForecastResult>(res));
  },

  getWeeklyForecast: (params?: { product_id?: number; sku?: string; horizon_weeks?: number; window?: number }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    return fetch(`${API_BASE}/forecast/weekly?${sp.toString()}`).then(res => handleResponse<WeeklyForecastResult>(res));
  },

  // Reorder Planner
  getReorderPlan: (params?: { category?: string; priority?: string; search?: string; budget?: number }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    return fetch(`${API_BASE}/reorder?${sp.toString()}`).then(res => handleResponse<ReorderPlanResponse>(res));
  },

  // Automated Alerts
  getAlerts: (params?: { status?: string; severity?: string }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    return fetch(`${API_BASE}/alerts?${sp.toString()}`).then(res =>
      handleResponse<{ total: number; open_count: number; critical_count: number; items: AlertItem[] }>(res)
    );
  },

  patchAlert: (id: number, status: 'ACKNOWLEDGED' | 'RESOLVED') =>
    fetch(`${API_BASE}/alerts/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    }).then(res => handleResponse<AlertItem>(res)),

  evaluateAlerts: () =>
    fetch(`${API_BASE}/alerts/evaluate`, { method: 'POST' }).then(res =>
      handleResponse<{ status: string; new_alerts_created: number; alerts_auto_resolved: number; message: string }>(res)
    ),

  // Purchase Orders
  getOrders: (params?: { status?: string; wholesaler_id?: number }) => {
    const sp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
      });
    }
    return authFetch(`${API_BASE}/orders?${sp.toString()}`).then(res =>
      handleResponse<{ total: number; items: PurchaseOrder[] }>(res)
    );
  },

  createOrder: (data: { items: any[]; wholesaler_id?: number; notes?: string }) =>
    authFetch(`${API_BASE}/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<PurchaseOrder>(res)),

  getOrder: (id: number) => authFetch(`${API_BASE}/orders/${id}`).then(res => handleResponse<PurchaseOrder>(res)),

  updateOrderStatus: (id: number, status: string, receivedQuantities?: Record<string, number>) =>
    authFetch(`${API_BASE}/orders/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, received_quantities: receivedQuantities })
    }).then(res => handleResponse<PurchaseOrder>(res)),

  // Wholesale Catalog & Signals
  getWholesaleCatalog: () => authFetch(`${API_BASE}/wholesale/catalog`).then(res => handleResponse<WholesaleCatalogItem[]>(res)),

  addWholesaleCatalogItem: (data: Partial<WholesaleCatalogItem>) =>
    authFetch(`${API_BASE}/wholesale/catalog`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<{ status: string; message: string }>(res)),

  getWholesaleDemandSignals: () => authFetch(`${API_BASE}/wholesale/demand-signals`).then(res => handleResponse<any[]>(res)),

  // Automated Pipeline
  getPipelineStatus: () => authFetch(`${API_BASE}/pipeline/status`).then(res => handleResponse<any>(res)),

  getPipelineRuns: (limit: number = 20) => authFetch(`${API_BASE}/pipeline/runs?limit=${limit}`).then(res => handleResponse<{ total: number; runs: PipelineRun[] }>(res)),

  runPipeline: () => authFetch(`${API_BASE}/pipeline/run`, { method: 'POST' }).then(res => handleResponse<any>(res)),

  // Admin Console
  getAdminUsers: () => authFetch(`${API_BASE}/admin/users`).then(res => handleResponse<User[]>(res)),

  createAdminUser: (data: { email: string; password: string; role: string; name: string }) =>
    authFetch(`${API_BASE}/admin/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<{ status: string; message: string }>(res)),

  updateAdminUser: (id: number, data: { active?: number; role?: string }) =>
    authFetch(`${API_BASE}/admin/users/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<User>(res)),

  getAdminSystem: () => authFetch(`${API_BASE}/admin/system`).then(res => handleResponse<any>(res)),

  // Reports
  getReportData: (reportType: string) =>
    fetch(`${API_BASE}/reports/${reportType}`).then(res => handleResponse<{ report_type: string; count: number; data: any[] }>(res)),

  getReportDownloadUrl: (reportType: string) => `${API_BASE}/reports/download/${reportType}`,

  // Settings
  getSettings: () => fetch(`${API_BASE}/settings`).then(res => handleResponse<SettingsData>(res)),

  updateSettings: (data: Partial<SettingsData>) =>
    fetch(`${API_BASE}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<{ status: string; settings: SettingsData }>(res)),

  // Data Diagnostics & Demo Seed
  getDataStatus: () => fetch(`${API_BASE}/data/status`).then(res => handleResponse<DataStatus>(res)),

  seedDemoData: () =>
    fetch(`${API_BASE}/data/seed`, {
      method: 'POST'
    }).then(res => handleResponse<{ status: string; products_count: number; sales_records_count: number; message: string }>(res)),

  resetDatabase: () =>
    fetch(`${API_BASE}/data/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true })
    }).then(res => handleResponse<{ status: string; message: string }>(res)),

  // Computer Vision Product Scanner & Payment Terminal
  recognizeProduct: (data: { image_data?: string; barcode?: string; label?: string }) =>
    fetch(`${API_BASE}/scanner/recognize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<CVScanResult>(res)),

  decodeBarcode: (data: { image?: string; image_data?: string }) =>
    fetch(`${API_BASE}/scanner/decode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<BarcodeDecodeResponse>(res)),

  quickSale: (data: { product_id: number; quantity: number }) =>
    fetch(`${API_BASE}/scanner/quick-sale`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<{ status: string; new_stock: number; total_value: number; message: string }>(res)),

  quickRestock: (data: { product_id: number; quantity: number; batch_id?: string; expiry_date?: string }) =>
    fetch(`${API_BASE}/scanner/quick-restock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<{ status: string; new_stock: number; message: string }>(res)),

  generatePaymentQr: (data: { amount: number; purpose?: string; reference_id?: string }) =>
    fetch(`${API_BASE}/payment/generate-qr`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<PaymentQrResponse>(res)),

  verifyPayment: (data: { transaction_ref: string; amount: number; payment_method?: string; utr_number?: string; cart_items?: any[]; purchase_order_id?: number }) =>
    fetch(`${API_BASE}/payment/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<PaymentReceipt>(res)),

  // Automated Record & Object Detection Pipeline
  startRecord: (operatorId?: number) =>
    fetch(`${API_BASE}/record/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operator_id: operatorId || 1 })
    }).then(res => handleResponse<{ status: string; session_id: number; session_uuid: string; state: string; message: string; privacy_notice: string }>(res)),

  stopRecord: (sessionId?: number) =>
    fetch(`${API_BASE}/record/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    }).then(res => handleResponse<{ status: string; session_id: number; state: string; summary: RecordSessionSummary; message: string }>(res)),

  getLiveRecord: () =>
    fetch(`${API_BASE}/record/live`).then(res => handleResponse<{
      status: string;
      session: SessionInfo;
      detector_ready: boolean;
      measured_fps: number;
      last_inference_ms: number;
      counters: {
        unique_people_session: number;
        unique_products_session: number;
        active_tracks_count: number;
        total_frames_processed: number;
      };
      privacy_notice: string;
    }>(res)),

  getRecordSessions: (limit?: number) =>
    fetch(`${API_BASE}/record/sessions?limit=${limit || 20}`).then(res =>
      handleResponse<{ sessions: RecordSessionItem[] }>(res)
    ),

  getRecordSessionDetail: (id: number) =>
    fetch(`${API_BASE}/record/sessions/${id}`).then(res =>
      handleResponse<{
        id: number;
        session_uuid: string;
        state: string;
        operator_id: number;
        started_at?: string;
        ended_at?: string;
        transitions: Array<{ from_state: string; to_state: string; reason: string; at: string }>;
        summary: RecordSessionSummary;
        events: any[];
      }>(res)
    ),

  sendRecordFrame: (data: { image_data?: string; blur_faces?: boolean; session_id?: number }) =>
    fetch(`${API_BASE}/record/frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(res => handleResponse<FrameDetectionResponse>(res)),

  // Session State Machine
  getSessionState: () => fetch(`${API_BASE}/session/state`).then(res => handleResponse<SessionInfo>(res)),

  transitionSession: (targetState: string, reason?: string, sessionId?: number) =>
    fetch(`${API_BASE}/session/transition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_state: targetState, reason, session_id: sessionId })
    }).then(res => handleResponse<{ session_id: number; session_uuid: string; state: string; allowed_transitions: string[]; reason?: string; timestamp: string }>(res)),

  simulateWebhookPayment: (data: { transaction_ref: string; amount: number; cart_items?: any[]; utr_number?: string }) =>
    fetch(`${API_BASE}/payment/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Demo-Simulate': 'true'
      },
      body: JSON.stringify(data)
    }).then(res => handleResponse<PaymentReceipt>(res)),

  purgeOldDetectionEvents: (olderThanDays?: number) =>
    fetch(`${API_BASE}/record/purge-old-events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ older_than_days: olderThanDays || 30 })
    }).then(res => handleResponse<{ status: string; deleted_count: number; retention_days: number; message: string }>(res)),

  // Analytics (Demo CSV vs Live Ledger)
  getDemoAnalytics: () => authFetch(`${API_BASE}/analytics/demo`).then(res => handleResponse<any>(res)),
  importDemoAnalytics: () => authFetch(`${API_BASE}/analytics/demo/import`, { method: 'POST' }).then(res => handleResponse<any>(res)),
  getLiveAnalytics: () => authFetch(`${API_BASE}/analytics/live`).then(res => handleResponse<any>(res)),

  // Push Notifications & Settings
  getNotifications: (rule?: string, status?: string, limit: number = 50, offset: number = 0) => {
    const params = new URLSearchParams();
    if (rule && rule !== 'all') params.append('rule', rule);
    if (status && status !== 'all') params.append('status', status);
    params.append('limit', String(limit));
    params.append('offset', String(offset));
    return authFetch(`${API_BASE}/notifications?${params.toString()}`).then(res =>
      handleResponse<NotificationsListResponse>(res)
    );
  },

  getNotificationSettings: (ownerId?: number) => {
    const q = ownerId ? `?owner_id=${ownerId}` : '';
    return authFetch(`${API_BASE}/notifications/settings${q}`).then(res =>
      handleResponse<NotificationSettingsResponse>(res)
    );
  },

  updateNotificationSettings: (settings: NotificationSetting[], ownerId?: number) => {
    const q = ownerId ? `?owner_id=${ownerId}` : '';
    return authFetch(`${API_BASE}/notifications/settings${q}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    }).then(res => handleResponse<{ status: string; updated_count: number; message: string }>(res));
  },

  sendTestNotification: () =>
    authFetch(`${API_BASE}/notifications/test-send`, {
      method: 'POST'
    }).then(res => handleResponse<{ status: string; notification_id?: number; message: string }>(res)),

  getTopicInfo: () =>
    authFetch(`${API_BASE}/notifications/topic-info`).then(res =>
      handleResponse<TopicInfoResponse>(res)
    )
};


export type UserRole = 'retailer' | 'wholesaler' | 'dealer' | 'admin';

export interface User {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  shop_id: number;
  shop_name?: string;
  active?: number;
  token?: string;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  category: string;
  current_stock: number;
  unit_cost: number;
  selling_price: number;
  supplier_id?: number | null;
  supplier_name?: string | null;
  lead_time_days: number;
  is_perishable: number | boolean;
  shelf_life_days?: number | null;
  min_order_qty: number;
  pack_size: number;
  safety_buffer_days: number;
  is_active?: number;
  created_at?: string;
  updated_at?: string;
}

export interface ReorderSignal {
  type: string;
  severity: "critical" | "high" | "medium" | "low";
  message: string;
}

export interface CalculationTrace {
  formula_rop: string;
  formula_target: string;
  formula_inventory_position?: string;
  formula_base_qty: string;
  coverage_days: number;
  window_days: number;
}

export interface ReorderItem {
  product_id: number;
  sku: string;
  name: string;
  category: string;
  current_stock: number;
  incoming_units?: number;
  inventory_position?: number;
  unit_cost: number;
  selling_price: number;
  supplier_name: string;
  lead_time_days: number;
  is_perishable: boolean;
  shelf_life_days?: number | null;
  min_order_qty: number;
  pack_size: number;
  safety_buffer_days: number;
  average_daily_demand: number;
  lead_time_demand: number;
  safety_stock: number;
  reorder_point: number;
  target_stock: number;
  base_quantity: number;
  uncapped_order_qty?: number;
  usable_selling_window?: number | null;
  usable_shelf_life?: number | null;
  shelf_life_cap?: number | null;
  shelf_life_capped?: boolean;
  shelf_life_note?: string | null;
  shelf_life_incompatible?: boolean;
  pack_rounding_applied: boolean;
  moq_applied: boolean;
  recommended_reorder_qty: number;
  purchase_cost: number;
  potential_revenue: number;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "HEALTHY";
  priority_score: number;
  days_until_stockout: number;
  expiry_risk: boolean;
  signals: ReorderSignal[];
  recommendation_reason: string;
  all_reasons: string[];
  calculation_trace: CalculationTrace;
  budget_capped?: boolean;
  original_qty?: number;
}

export interface ReorderSummary {
  total_products: number;
  products_requiring_reorder: number;
  critical_stockouts: number;
  high_urgency: number;
  medium_urgency: number;
  healthy_count: number;
  expiry_risk_count: number;
  capped_by_shelf_life_count?: number;
  total_reorder_value: number;
  total_reorder_units: number;
  budget_limit?: number | null;
  budget_applied?: boolean;
  allocated_cost?: number;
}

export interface ReorderPlanResponse {
  summary: ReorderSummary;
  settings: {
    historical_window_days: number;
    coverage_days: number;
    forecast_method: string;
    shelf_life_buffer_days?: number;
    safety_buffer_days?: number;
  };
  items: ReorderItem[];
}

export interface ForecastEvaluation {
  test_window_days: number;
  mae: number;
  rmse: number;
  note: string;
}

export interface ForecastResult {
  product_id: number;
  sku: string;
  product_name: string;
  category: string;
  forecast_method: string;
  window_days: number;
  horizon_days: number;
  base_avg_daily_demand?: number;
  average_daily_demand: number;
  market_adjustment?: {
    multiplier: number;
    is_adjusted: boolean;
    signal_type?: string;
    notes?: string;
  };
  total_historical_sold: number;
  active_sales_days: number;
  trend_slope: number;
  trend_direction: "increasing" | "decreasing" | "stable";
  lead_time_days: number;
  lead_time_demand: number;
  warning?: string | null;
  evaluation?: ForecastEvaluation | null;
  historical_series: Array<{ date: string; actual_sales: number }>;
  daily_forecast: Array<{ date: string; predicted_demand: number }>;
}

export interface WeeklyForecastResult {
  product_id: number;
  sku: string;
  product_name: string;
  category: string;
  forecast_granularity?: string;
  horizon_weeks: number;
  historical_weeks_count?: number;
  avg_weekly_demand: number;
  market_adjustment?: any;
  historical_weeks: Array<{ week_start: string; actual_units: number }>;
  weekly_forecast: Array<{
    week_number: number;
    week_start: string;
    predicted_units: number;
    lower_bound: number;
    upper_bound: number;
    range_label: string;
  }>;
  note: string;
}

export interface DashboardData {
  last_updated: string;
  summary: ReorderSummary;
  trend_chart: Array<{
    date: string;
    actual_sales?: number | null;
    forecast_demand?: number | null;
  }>;
  health_distribution: Array<{
    name: string;
    count: number;
    color: string;
  }>;
  top_urgent_products: ReorderItem[];
  pipeline_status?: any;
  open_alerts_count?: number;
}

export interface AlertItem {
  id: number;
  shop_id: number;
  alert_type: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "INFO";
  product_id?: number | null;
  sku?: string | null;
  title: string;
  message: string;
  explanation?: string | null;
  status: "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
  created_at: string;
  resolved_at?: string | null;
}

export interface PurchaseOrderItem {
  id: number;
  po_id: number;
  product_id: number;
  sku: string;
  product_name: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  received_quantity: number;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  order_number?: string;
  order_date?: string;
  supplier_name?: string;
  shop_id: number;
  wholesaler_id?: number | null;
  wholesaler_name?: string | null;
  status: "Draft" | "Submitted" | "Confirmed" | "Dispatched" | "Delivered" | "Rejected" | "Cancelled";
  total_amount: number;
  notes?: string | null;
  created_at: string;
  updated_at?: string;
  item_count?: number;
  total_units?: number;
  items?: PurchaseOrderItem[];
}

export interface WholesaleCatalogItem {
  id: number;
  wholesaler_id: number;
  wholesaler_name?: string;
  sku: string;
  name: string;
  category: string;
  wholesale_price: number;
  moq: number;
  pack_size: number;
  lead_time_days: number;
  shelf_life_days?: number | null;
  available_stock: number;
}

export interface PipelineRun {
  id: number;
  job_name: string;
  status: "SUCCESS" | "FAILED" | "RUNNING" | "PARTIAL_SUCCESS";
  started_at: string;
  finished_at?: string;
  rows_processed: number;
  rows_rejected: number;
  errors?: string | null;
  triggered_by: string;
}

export interface GstLine {
  id: number;
  invoice_no: string;
  invoice_date: string;
  supply_type: "outward" | "inward";
  gstin_counterparty?: string;
  hsn_code?: string;
  item_description?: string;
  sku?: string;
  quantity: number;
  taxable_value?: number;
  gst_rate?: number;
  total_value?: number;
  is_mapped: number;
}

export interface StockBatch {
  id: number;
  sku: string;
  product_name?: string;
  batch_id: string;
  quantity: number;
  expiry_date: string;
  category?: string;
  is_perishable?: boolean;
}

export interface MarketSignal {
  id: number;
  date: string;
  scope_type: string;
  scope_value: string;
  signal_type: string;
  value: number;
  notes?: string;
}

export interface CsvValidationResponse {
  batch_id: string;
  filename: string;
  total_rows: number;
  valid_count: number;
  invalid_count: number;
  duplicate_count: number;
  unmapped_count?: number;
  is_valid: boolean;
  error?: string;
  preview_valid: any[];
  all_valid: any[];
  invalid_rows: any[];
  unmapped_rows?: any[];
}

export interface Supplier {
  id: number;
  name: string;
  lead_time: number;
  min_order_qty: number;
  pack_size: number;
  contact_email?: string;
}

export interface SettingsData {
  lead_time_days: string;
  safety_buffer_days: string;
  coverage_days: string;
  historical_window_days: string;
  forecast_horizon_days: string;
  forecast_horizon_weeks?: string;
  currency: string;
  budget: string;
  forecast_method: string;
  shelf_life_buffer_days?: string;
  enable_market_adjustment?: string;
  [key: string]: string | undefined;
}

export interface DataStatus {
  database_file: string;
  database_size_kb: number;
  active_products: number;
  total_suppliers: number;
  total_sales_records: number;
  sales_date_range: {
    start: string | null;
    end: string | null;
  };
  recent_import_batches: Array<{
    id: string;
    filename: string;
    total_rows: number;
    created_at: string;
  }>;
}

export interface CVScanResult {
  matched: boolean;
  recognition_mode: string;
  confidence: number;
  confidence_percentage: string;
  bounding_box: number[];
  product?: Product;
  message?: string;
  visual_signature?: {
    detected_dominant_rgb: number[];
    edge_complexity: number;
    category_alignment: string;
  };
  top_candidates?: Array<{
    confidence: number;
    confidence_percentage: string;
    product: Product;
  }>;
}

export interface PaymentQrResponse {
  transaction_ref: string;
  amount: number;
  currency: string;
  currency_symbol: string;
  vpa: string;
  merchant_name: string;
  upi_uri: string;
  qr_svg: string;
  status: string;
  created_at: string;
}

export interface PaymentReceipt {
  status: string;
  verified: boolean;
  transaction_ref: string;
  utr_number: string;
  amount_settled: number;
  payment_method: string;
  timestamp: string;
  processed_items?: Array<{
    sku: string;
    name: string;
    quantity: number;
    new_stock: number;
  }>;
  message: string;
  purchase_order_id?: number;
}

export interface CartItem {
  product_id: number;
  sku: string;
  name: string;
  category: string;
  price: number;
  quantity: number;
  current_stock: number;
}

export type CheckoutSessionState = 'IDLE' | 'SCANNING' | 'BASKET' | 'PAYMENT_PENDING' | 'PAID' | 'RECORDING';

export interface SessionInfo {
  session_id: number;
  session_uuid: string;
  state: CheckoutSessionState;
  started_at?: string | null;
  ended_at?: string | null;
  allowed_transitions: string[];
  transitions_count: number;
}

export interface DetectionItem {
  track_id: number;
  class_name: 'person' | 'product';
  confidence: number;
  bbox: [number, number, number, number];
  raw_label?: string;
  sku?: string | null;
  sku_name?: string;
  is_new?: boolean;
}

export interface FrameDetectionResponse {
  status: string;
  frame_width: number;
  frame_height: number;
  inference_time_ms: number;
  fps: number;
  people_in_frame: number;
  unique_people_session: number;
  products_in_frame: number;
  unique_products_session: number;
  matched_skus: string[];
  detections: DetectionItem[];
  privacy_notice: string;
  annotated_frame?: string | null;
}

export interface RecordSessionSummary {
  session_id: number;
  unique_people_count: number;
  total_products_detected: number;
  matched_skus: string[];
  matched_skus_count: number;
  unmatched_items_count: number;
  total_events: number;
}

export interface RecordSessionItem {
  id: number;
  session_uuid: string;
  state: string;
  operator_id: number;
  started_at?: string | null;
  ended_at?: string | null;
  summary: RecordSessionSummary;
}

export interface OverviewAttentionItem {
  id: string | number;
  severity: 'critical' | 'high' | 'warning' | 'info';
  title: string;
  affected: string;
  message: string;
  actionLabel?: string;
}

export interface RetailerOverviewData {
  role: 'retailer';
  generated_at: string;
  kpis: {
    today_sales_paise: number;
    today_items_sold: number;
    sales_change_pct: number;
    stock_value_paise: number;
    items_to_restock: number;
    total_reorder_units: number;
  };
  attention_list: OverviewAttentionItem[];
  stock_health: {
    healthy: number;
    low: number;
    expiring: number;
    out_of_stock: number;
    total_skus: number;
  };
  trend: Array<{
    date: string;
    value: number;
    secondaryValue?: number;
  }>;
  top_urgent_products: ReorderItem[];
}

export interface WholesalerOverviewData {
  role: 'wholesaler';
  generated_at: string;
  kpis: {
    open_orders: number;
    orders_value_paise: number;
    retailers_served: number;
    stock_value_paise: number;
    catalog_skus: number;
  };
  attention_list: OverviewAttentionItem[];
  trend: Array<{
    date: string;
    value: number;
    secondaryValue?: number;
  }>;
  recent_orders: Array<{
    po_number: string;
    status: string;
    total_amount: number;
    created_at: string;
    shop_id: number;
  }>;
}

export interface DealerOverviewData {
  role: 'dealer';
  generated_at: string;
  kpis: {
    stock_supplied_month_units: number;
    open_wholesaler_orders: number;
    fill_rate_percentage: number;
    regional_stock_allocated_units: number;
  };
  attention_list: OverviewAttentionItem[];
  dealer_territory: string;
  margin_tiers: Array<{
    tier: string;
    margin: string;
    status: string;
  }>;
  trend: Array<{
    date: string;
    value: number;
    secondaryValue?: number;
  }>;
}

export interface AdminOverviewData {
  role: 'admin';
  generated_at: string;
  kpis: {
    active_users_by_role: Record<string, number>;
    total_users: number;
    transactions_today: number;
    volume_today_paise: number;
    open_alerts: number;
    pipeline_runs: number;
  };
  attention_list: OverviewAttentionItem[];
  system_health: {
    database: {
      connected: boolean;
      engine: string;
      schema_version: string;
    };
    detection_model: {
      status: string;
      model_name: string;
      measured_fps: number;
      latency_ms: number;
    };
    notifications: {
      service: string;
      status: string;
      topic: string;
      last_sent?: string;
    };
  };
  trend: Array<{
    date: string;
    value: number;
    secondaryValue?: number;
  }>;
  recent_audit_logs: Array<{
    id: number;
    action: string;
    entity: string;
    actor_id: number;
    at: string;
  }>;
}




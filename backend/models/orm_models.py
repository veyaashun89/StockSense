import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    Text, UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="retailer")  # 'retailer', 'wholesaler', 'dealer', 'admin'
    name = Column(String(255), nullable=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="SET NULL"), nullable=True, default=1)
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    inventory_items = relationship("Inventory", back_populates="owner")
    sales = relationship("Sale", back_populates="owner")

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    lead_time = Column(Integer, default=7)
    min_order_qty = Column(Integer, default=1)
    pack_size = Column(Integer, default=1)
    contact_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="SET NULL"), default=1)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    unit = Column(String(50), default="unit")
    retail_price_paise = Column(Integer, nullable=False, default=0)
    unit_cost_paise = Column(Integer, nullable=False, default=0)
    selling_price = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    gst_rate = Column(Float, default=0.0)
    current_stock = Column(Integer, default=0)  # Cached counter for quick legacy reads
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    lead_time_days = Column(Integer, default=7)
    is_perishable = Column(Integer, default=0)
    shelf_life_days = Column(Integer, nullable=True)
    min_order_qty = Column(Integer, default=1)
    pack_size = Column(Integer, default=1)
    safety_buffer_days = Column(Integer, default=3)
    barcode = Column(String(100), nullable=True, index=True)
    is_active = Column(Integer, default=1, server_default="1")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    inventory = relationship("Inventory", back_populates="product", uselist=False)
    batches = relationship("InventoryBatch", back_populates="product")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    on_hand = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, default=10)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("product_id", "owner_id", name="uq_inventory_product_owner"),
        CheckConstraint("on_hand >= 0", name="ck_inventory_on_hand_non_negative"),
    )

    product = relationship("Product", back_populates="inventory")
    owner = relationship("User", back_populates="inventory_items")

class InventoryBatch(Base):
    __tablename__ = "inventory_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(String(64), nullable=True)
    qty = Column(Integer, nullable=False, default=0)
    expiry_date = Column(String(32), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="batches")

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1, index=True)
    shop_id = Column(Integer, default=1)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    sku = Column(String(64), nullable=True)
    quantity_sold = Column(Integer, default=1)
    utr = Column(String(100), unique=True, nullable=True, index=True)
    subtotal_paise = Column(Integer, nullable=False, default=0, server_default="0")
    tax_paise = Column(Integer, nullable=False, default=0, server_default="0")
    total_paise = Column(Integer, nullable=False, default=0, server_default="0")
    payment_status = Column(String(32), default="PAID", server_default="'PAID'")  # 'PENDING', 'PAID', 'FAILED'
    source = Column(String(64), default="pos_scanner")
    import_batch_id = Column(String(64), nullable=True)
    sale_date = Column(String(32), default=lambda: datetime.date.today().isoformat())
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sale")

class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    qty = Column(Integer, nullable=False, default=1)
    unit_price_paise = Column(Integer, nullable=False, default=0)
    line_total_paise = Column(Integer, nullable=False, default=0)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_ref = Column(String(100), unique=True, nullable=False, index=True)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(32), default="pending", index=True)  # 'pending', 'verified', 'failed', 'expired'
    idempotency_key = Column(String(100), unique=True, nullable=False, index=True)
    payment_method = Column(String(32), default="UPI_QR")
    utr_number = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)

    sale = relationship("Sale", back_populates="payments")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_number = Column(String(64), unique=True, nullable=False, index=True)
    shop_id = Column(Integer, default=1, server_default="1")
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1, server_default="1")
    supplier_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    wholesaler_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), default="Submitted", index=True)  # 'Draft', 'Submitted', 'Confirmed', 'Dispatched', 'Delivered', 'Cancelled'
    total_paise = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    items = relationship("PurchaseOrderItem", back_populates="po", cascade="all, delete-orphan")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(64), nullable=True)
    product_name = Column(String(255), nullable=True)
    qty = Column(Integer, nullable=False, default=1, server_default="1")
    quantity = Column(Integer, nullable=False, default=1, server_default="1")  # alias
    unit_cost_paise = Column(Integer, nullable=False, default=0, server_default="0")
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    received_quantity = Column(Integer, default=0)

    po = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, default=1)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1)
    delta = Column(Integer, nullable=False, default=0)  # negative for deduction, positive for addition
    quantity = Column(Integer, nullable=False, default=0)  # legacy mirror of delta
    movement_type = Column(String(64), default="SALE")  # legacy mirror of reason
    balance_after = Column(Integer, nullable=False)
    reason = Column(String(64), nullable=False)  # 'INITIAL', 'SALE', 'RESTOCK', 'ADJUSTMENT', 'SPOILAGE', 'GST_INWARD', 'PO_DELIVERY'
    reference = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, default=1)
    type = Column(String(64), nullable=False, default="REORDER_POINT", server_default="'REORDER_POINT'")  # Prompt specification
    alert_type = Column(String(64), nullable=True)  # Legacy query alias
    severity = Column(String(32), default="MEDIUM", index=True)  # 'CRITICAL', 'HIGH', 'MEDIUM', 'INFO'
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    sku = Column(String(64), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    dedup_key = Column(String(255), unique=True, nullable=True, index=True)
    status = Column(String(32), default="OPEN", index=True)  # 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_uuid = Column(String(64), unique=True, nullable=False, index=True)
    state = Column(String(32), nullable=False, default="IDLE", index=True)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    transitions = relationship("StateTransition", back_populates="session", cascade="all, delete-orphan")
    detections = relationship("DetectionEvent", back_populates="session", cascade="all, delete-orphan")

class StateTransition(Base):
    __tablename__ = "state_transitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    from_state = Column(String(32), nullable=False)
    to_state = Column(String(32), nullable=False)
    reason = Column(String(255), nullable=True)
    at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ScanSession", back_populates="transitions")

class DetectionEvent(Base):
    __tablename__ = "detection_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    class_name = Column(String(32), nullable=False)  # 'person', 'product', 'unknown'
    track_id = Column(Integer, nullable=False, index=True)
    sku = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=False)
    bbox_json = Column(Text, nullable=False)

    session = relationship("ScanSession", back_populates="detections")

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    entity = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=True)
    payload_json = Column(Text, nullable=True)
    at = Column(DateTime, default=datetime.datetime.utcnow)

# Legacy support tables
class WholesaleCatalogItem(Base):
    __tablename__ = "wholesale_catalog_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wholesaler_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    wholesale_price = Column(Float, nullable=False)
    moq = Column(Integer, default=10)
    pack_size = Column(Integer, default=5)
    lead_time_days = Column(Integer, default=3)
    shelf_life_days = Column(Integer, nullable=True)
    available_stock = Column(Integer, default=500)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class GstLine(Base):
    __tablename__ = "gst_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, default=1)
    invoice_no = Column(String(64), nullable=False)
    invoice_date = Column(String(32), nullable=False)
    supply_type = Column(String(32), nullable=False)
    gstin_counterparty = Column(String(32), nullable=True)
    hsn_code = Column(String(32), nullable=True)
    item_description = Column(String(255), nullable=True)
    sku = Column(String(64), nullable=True)
    quantity = Column(Integer, default=1)
    taxable_value = Column(Float, default=0.0)
    gst_rate = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    import_batch_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class GstMapping(Base):
    __tablename__ = "gst_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, default=1)
    pattern_type = Column(String(32), default="hsn")
    pattern_value = Column(String(128), nullable=True)
    hsn_code = Column(String(32), nullable=True)
    item_description = Column(String(255), nullable=True)
    mapped_sku = Column(String(64), nullable=True)
    sku = Column(String(64), nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MarketSignal(Base):
    __tablename__ = "market_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(32), nullable=True)
    signal_date = Column(String(32), nullable=True)
    scope_type = Column(String(32), default="category")
    granularity = Column(String(32), default="category")
    scope_value = Column(String(100), nullable=True)
    target_identifier = Column(String(100), nullable=True)
    signal_type = Column(String(64), nullable=False)
    value = Column(Float, default=1.0)
    signal_value = Column(Float, default=1.0)
    notes = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    import_batch_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(100), nullable=False)
    status = Column(String(32), nullable=False)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    rows_processed = Column(Integer, default=0)
    rows_rejected = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    triggered_by = Column(String(64), default="AUTOMATED")

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)

class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(String(64), primary_key=True)
    filename = Column(String(255), nullable=True)
    batch_type = Column(String(32), default="SALES")
    total_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    invalid_rows = Column(Integer, default=0)
    status = Column(String(32), default="COMPLETED")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, default=1)
    name = Column(String(100), nullable=False)
    location_type = Column(String(32), nullable=False, default="shelf")  # 'shelf', 'bin', 'box'
    barcode = Column(String(100), unique=True, nullable=True, index=True)
    parent_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Self-referencing hierarchical relationship
    parent = relationship("Location", remote_side=[id], backref="children")
    stock_items = relationship("LocationStock", back_populates="location", cascade="all, delete-orphan")

class LocationStock(Base):
    __tablename__ = "location_stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = Column(String(64), nullable=False, index=True)
    expected_quantity = Column(Integer, nullable=False, default=0)
    actual_quantity = Column(Integer, nullable=False, default=0)
    last_counted_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="MATCH")  # 'MATCH', 'MISMATCH_SHORTAGE', 'MISMATCH_SURPLUS'

    location = relationship("Location", back_populates="stock_items")
    product = relationship("Product")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule = Column(String(64), nullable=False, index=True)  # 'low_stock', 'expiry_risk', 'payment_verified', 'count_mismatch', 'scanner_failure', 'webhook_failed'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False, default=3)  # 1 to 5
    tags = Column(String(255), nullable=True)  # e.g. "warning,package"
    event_ref = Column(String(100), nullable=False, index=True)  # Source event id
    dedup_key = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)  # 'pending', 'sent', 'failed', 'suppressed'
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), default=1, index=True)
    rule = Column(String(64), nullable=False, index=True)
    enabled = Column(Integer, default=1)  # 1 = True, 0 = False
    threshold = Column(Float, default=10.0)  # e.g. low stock units, expiry days
    quiet_hours_start = Column(String(5), default="22:00")
    quiet_hours_end = Column(String(5), default="07:00")
    min_minutes_between = Column(Integer, default=60)  # dedup window in minutes

    __table_args__ = (
        UniqueConstraint("owner_id", "rule", name="uq_owner_rule_setting"),
    )



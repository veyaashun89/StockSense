import React, { useState, useEffect } from 'react';
import { 
  ShoppingBag, 
  Clock, 
  CheckCircle2, 
  Truck, 
  PackageCheck, 
  XCircle, 
  Filter, 
  Download, 
  ChevronDown, 
  ChevronRight,
  Building2,
  Calendar,
  AlertCircle,
  QrCode
} from 'lucide-react';
import { api } from '../services/api';
import type { PurchaseOrder, UserRole, PaymentQrResponse } from '../types';

export const PurchaseOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedOrders, setExpandedOrders] = useState<Record<number, boolean>>({});
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [currentRole, setCurrentRole] = useState<UserRole>('retailer');
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const [orderRes, meData] = await Promise.all([
        api.getOrders(statusFilter !== 'all' ? { status: statusFilter } : undefined),
        api.getMe()
      ]);
      setOrders(orderRes.items || []);
      setCurrentRole(meData.user.role);
    } catch (err: any) {
      setError(err?.message || 'Failed to load purchase orders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [statusFilter]);

  const [activePayOrder, setActivePayOrder] = useState<PurchaseOrder | null>(null);
  const [poPaymentQr, setPoPaymentQr] = useState<PaymentQrResponse | null>(null);
  const [isSettlingPo, setIsSettlingPo] = useState(false);
  const [orderDetails, setOrderDetails] = useState<Record<number, PurchaseOrder>>({});

  const handlePayOrder = async (order: PurchaseOrder) => {
    setActivePayOrder(order);
    try {
      const qr = await api.generatePaymentQr({
        amount: order.total_amount,
        purpose: 'po_settlement',
        reference_id: order.po_number
      });
      setPoPaymentQr(qr);
    } catch (err: any) {
      alert(err?.message || 'Failed to generate UPI QR');
    }
  };

  const handleConfirmPoPayment = async () => {
    if (!activePayOrder || !poPaymentQr) return;
    setIsSettlingPo(true);
    try {
      await api.verifyPayment({
        transaction_ref: poPaymentQr.transaction_ref,
        amount: poPaymentQr.amount,
        payment_method: 'UPI_QR',
        purchase_order_id: activePayOrder.id
      });
      setSuccessToast(`UPI Payment settled for ${activePayOrder.po_number}!`);
      setActivePayOrder(null);
      setPoPaymentQr(null);
      await fetchOrders();
    } catch (err: any) {
      alert(err?.message || 'Payment settlement failed');
    } finally {
      setIsSettlingPo(false);
    }
  };

  const toggleExpand = async (orderId: number) => {
    const isNowExpanded = !expandedOrders[orderId];
    setExpandedOrders(prev => ({ ...prev, [orderId]: isNowExpanded }));
    
    if (isNowExpanded && !orderDetails[orderId]) {
      try {
        const details = await api.getOrder(orderId);
        setOrderDetails(prev => ({ ...prev, [orderId]: details }));
      } catch (err) {
        console.error('Failed to load order items:', err);
      }
    }
  };

  const handleUpdateStatus = async (orderId: number, newStatus: string) => {
    try {
      setActionLoading(orderId);
      await api.updateOrderStatus(orderId, newStatus);
      setSuccessToast(`Order #${orderId} status updated to ${newStatus}`);
      setTimeout(() => setSuccessToast(null), 4000);
      await fetchOrders();
    } catch (err: any) {
      alert(err?.message || 'Failed to update order status');
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Submitted':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3.5 h-3.5" /> Submitted
          </span>
        );
      case 'Confirmed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <CheckCircle2 className="w-3.5 h-3.5" /> Confirmed
          </span>
        );
      case 'Dispatched':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <Truck className="w-3.5 h-3.5" /> Dispatched
          </span>
        );
      case 'Delivered':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <PackageCheck className="w-3.5 h-3.5" /> Delivered
          </span>
        );
      case 'Cancelled':
      case 'Rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3.5 h-3.5" /> {status}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {status}
          </span>
        );
    }
  };

  const exportOrdersCsv = () => {
    if (orders.length === 0) return;
    const headers = ['Order Number', 'Date', 'Supplier', 'Items Count', 'Total Amount', 'Status', 'Notes'];
    const rows = orders.map(o => [
      o.po_number || o.order_number || `PO-${o.id}`,
      o.created_at?.slice(0, 10) || o.order_date || '',
      `"${o.wholesaler_name || o.supplier_name || 'Apex Wholesale'}"`,
      o.items?.length || o.item_count || 0,
      o.total_amount.toFixed(2),
      o.status,
      `"${o.notes || ''}"`
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `purchase_orders_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // KPI Metrics
  const totalValue = orders.reduce((sum, o) => sum + (o.total_amount || 0), 0);
  const activeOrders = orders.filter(o => ['Submitted', 'Confirmed', 'Dispatched'].includes(o.status)).length;
  const deliveredOrders = orders.filter(o => o.status === 'Delivered').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <ShoppingBag className="w-7 h-7 text-blue-600" />
            Purchase Orders
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {currentRole === 'wholesaler' 
              ? 'Fulfill and dispatch purchase orders from verified retail partners.'
              : 'Track supplier replenishments. In-transit orders count toward inventory position to prevent double-ordering.'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={exportOrdersCsv}
            disabled={orders.length === 0}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Success Toast */}
      {successToast && (
        <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium flex items-center justify-between animate-fade-in shadow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            {successToast}
          </div>
          <button onClick={() => setSuccessToast(null)} className="text-emerald-700 hover:text-emerald-900">
            &times;
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Pipeline</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-slate-900">{activeOrders}</span>
            <span className="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded-full">In Transit</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Submitted, Confirmed, or Dispatched</p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Completed Deliveries</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-emerald-600">{deliveredOrders}</span>
            <span className="text-xs text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded-full">Reconciled</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Stock received into inventory balance</p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Pipeline Value</span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-slate-900 font-mono">₹{totalValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
            <span className="text-xs text-slate-600 font-medium bg-slate-100 px-2 py-0.5 rounded-full">{orders.length} orders</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Combined purchase commitment</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-600 uppercase">Filter Status:</span>
          <div className="flex flex-wrap gap-1.5 ml-2">
            {['all', 'Submitted', 'Confirmed', 'Dispatched', 'Delivered', 'Cancelled'].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors capitalize ${
                  statusFilter === status
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200/60'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={fetchOrders}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium hover:underline"
        >
          Refresh Orders
        </button>
      </div>

      {/* Orders List */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3" />
            <p className="text-sm font-medium">Loading purchase orders...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-600">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        ) : orders.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <ShoppingBag className="w-12 h-12 mx-auto mb-3 text-slate-300" />
            <p className="text-base font-semibold text-slate-700">No purchase orders found</p>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Generate reorder plans in the Reorder Planner and click &ldquo;Create Purchase Order&rdquo; to initiate replenishments.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {orders.map((order) => {
              const isExpanded = !!expandedOrders[order.id];
              return (
                <div key={order.id} className="transition-colors hover:bg-slate-50/60">
                  {/* Order Summary Row */}
                  <div className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <button
                        onClick={() => toggleExpand(order.id)}
                        className="mt-0.5 p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                      >
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>
                      <div>
                        <div className="flex items-center gap-2.5">
                          <span className="font-mono text-sm font-bold text-slate-900">{order.po_number || order.order_number}</span>
                          {getStatusBadge(order.status)}
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 mt-1">
                          <span className="flex items-center gap-1">
                            <Building2 className="w-3.5 h-3.5 text-slate-400" />
                            {order.wholesaler_name || 'Apex Distribution'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5 text-slate-400" />
                            {order.created_at?.slice(0, 10)}
                          </span>
                          <span>{order.item_count ?? order.items?.length ?? 0} items</span>
                          {order.notes && <span className="italic text-slate-400">&ldquo;{order.notes}&rdquo;</span>}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between md:justify-end gap-4 pl-8 md:pl-0">
                      <div className="text-right">
                        <div className="font-mono text-base font-bold text-slate-900">
                          ₹{order.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-slate-400">Total Order Cost</div>
                      </div>

                      {/* Actions according to Role & Status */}
                      <div className="flex items-center gap-2">
                        {currentRole === 'wholesaler' ? (
                          <>
                            {order.status === 'Submitted' && (
                              <button
                                disabled={actionLoading === order.id}
                                onClick={() => handleUpdateStatus(order.id, 'Confirmed')}
                                className="px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors disabled:opacity-50"
                              >
                                Confirm Order
                              </button>
                            )}
                            {order.status === 'Confirmed' && (
                              <button
                                disabled={actionLoading === order.id}
                                onClick={() => handleUpdateStatus(order.id, 'Dispatched')}
                                className="px-3 py-1.5 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-700 rounded-lg shadow-xs transition-colors disabled:opacity-50"
                              >
                                Mark Dispatched
                              </button>
                            )}
                            {order.status === 'Dispatched' && (
                              <button
                                disabled={actionLoading === order.id}
                                onClick={() => handleUpdateStatus(order.id, 'Delivered')}
                                className="px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors disabled:opacity-50"
                              >
                                Confirm Delivery
                              </button>
                            )}
                          </>
                        ) : (
                          <>
                            {order.status !== 'Cancelled' && (
                              <button
                                onClick={() => handlePayOrder(order)}
                                className="px-2.5 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors flex items-center gap-1 shadow-xs"
                                title="Generate Dynamic UPI QR to settle order"
                              >
                                <QrCode className="w-3.5 h-3.5" />
                                Pay UPI
                              </button>
                            )}
                            {order.status === 'Dispatched' && (
                              <button
                                disabled={actionLoading === order.id}
                                onClick={() => handleUpdateStatus(order.id, 'Delivered')}
                                className="px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors disabled:opacity-50 flex items-center gap-1.5"
                              >
                                <PackageCheck className="w-3.5 h-3.5" />
                                Receive Stock
                              </button>
                            )}
                            {['Submitted', 'Draft'].includes(order.status) && (
                              <button
                                disabled={actionLoading === order.id}
                                onClick={() => handleUpdateStatus(order.id, 'Cancelled')}
                                className="px-2.5 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50 border border-rose-200 rounded-lg transition-colors disabled:opacity-50"
                              >
                                Cancel
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Line Items Details Sub-table */}
                  {isExpanded && (
                    <div className="bg-slate-50/80 border-t border-slate-100 px-6 py-4">
                      {(() => {
                        const items = orderDetails[order.id]?.items || order.items || [];
                        if (items.length === 0) {
                          return <div className="text-xs text-slate-500 py-2">Loading order items...</div>;
                        }
                        return (
                          <>
                            <div className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                              Order Line Items ({items.length})
                            </div>
                            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                              <table className="w-full text-xs text-left">
                                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                                  <tr>
                                    <th className="py-2 px-3">SKU</th>
                                    <th className="py-2 px-3">Product Name</th>
                                    <th className="py-2 px-3 text-right">Quantity</th>
                                    <th className="py-2 px-3 text-right">Unit Cost</th>
                                    <th className="py-2 px-3 text-right">Total Price</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 font-mono">
                                  {items.map((item, idx) => (
                                    <tr key={idx} className="hover:bg-slate-50/50">
                                      <td className="py-2 px-3 font-semibold text-blue-600">{item.sku}</td>
                                      <td className="py-2 px-3 font-sans text-slate-800">{item.product_name}</td>
                                      <td className="py-2 px-3 text-right font-bold text-slate-900">{item.quantity}</td>
                                      <td className="py-2 px-3 text-right text-slate-600">₹{item.unit_cost.toFixed(2)}</td>
                                      <td className="py-2 px-3 text-right font-bold text-slate-900">₹{item.total_cost.toFixed(2)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Dynamic UPI Payment Settlement Modal */}
      {poPaymentQr && activePayOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-sm w-full p-5 space-y-4 animate-scale-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs">
                  UPI
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900">Settle Wholesaler Order</h3>
                  <p className="text-[10px] text-slate-500 font-mono">{activePayOrder.po_number}</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setActivePayOrder(null);
                  setPoPaymentQr(null);
                }}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                &times;
              </button>
            </div>

            <div className="text-center p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div
                className="inline-block p-2 bg-white rounded-xl shadow-xs"
                dangerouslySetInnerHTML={{ __html: poPaymentQr.qr_svg }}
              />
              <div className="mt-2 text-xl font-extrabold text-slate-900 font-mono">
                ₹{poPaymentQr.amount.toFixed(2)}
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Scan with PhonePe, Google Pay, Paytm, or BHIM
              </p>
              <div className="mt-1 text-[10px] font-mono text-slate-400 bg-white px-2 py-0.5 rounded inline-block border border-slate-200">
                To: {activePayOrder.wholesaler_name || 'Apex Distribution'}
              </div>
            </div>

            <button
              onClick={handleConfirmPoPayment}
              disabled={isSettlingPo}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{isSettlingPo ? 'Settling...' : 'Confirm UPI Settlement'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

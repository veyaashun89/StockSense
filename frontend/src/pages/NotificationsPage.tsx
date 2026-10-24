import React, { useState, useEffect, useCallback } from 'react';
import {
  Bell,
  BellOff,
  Settings,
  Send,
  CheckCircle,
  AlertTriangle,
  Clock,
  ShieldAlert,
  Smartphone,
  Copy,
  Check,
  RefreshCw,
  Sliders,
  Filter,
  Info,
  ExternalLink,
  ChevronRight,
  Flame,
  Package,
  Calendar,
  CreditCard,
  Layers,
  Camera
} from 'lucide-react';
import { api } from '../services/api';
import type {
  PushNotification,
  NotificationSetting,
  NotificationRule,
  NotificationStatus,
  TopicInfoResponse
} from '../types';

interface NotificationsPageProps {
  currencySymbol?: string;
}

const RULE_METADATA: Record<NotificationRule, { label: string; desc: string; icon: any; color: string; defaultPrio: string }> = {
  low_stock: {
    label: 'Low Stock Alert',
    desc: 'Triggers priority 4 when completely out of stock (0), priority 3 below reorder point.',
    icon: Package,
    color: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
    defaultPrio: 'Priority 3 / 4'
  },
  expiry_risk: {
    label: 'Perishable Expiry Risk',
    desc: 'Triggers priority 4 when expiring today, priority 3 within shelf-life buffer window.',
    icon: Calendar,
    color: 'text-purple-500 bg-purple-500/10 border-purple-500/20',
    defaultPrio: 'Priority 3 / 4'
  },
  payment_verified: {
    label: 'Payment Verified & Settled',
    desc: 'Informational priority 2 notification upon settlement. Strict PII privacy (zero customer/financial identifiers).',
    icon: CreditCard,
    color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
    defaultPrio: 'Priority 2'
  },
  count_mismatch: {
    label: 'Storage Count Mismatch',
    desc: 'Triggers priority 4 on physical box/shelf scan discrepancies with location and unit variance.',
    icon: Layers,
    color: 'text-blue-500 bg-blue-500/10 border-blue-500/20',
    defaultPrio: 'Priority 4'
  },
  scanner_failure: {
    label: 'POS Scanner Stream Failure',
    desc: 'Triggers priority 3 only after 3 consecutive barcode/CV recognition failures in 10 minutes.',
    icon: Camera,
    color: 'text-orange-500 bg-orange-500/10 border-orange-500/20',
    defaultPrio: 'Priority 3'
  },
  webhook_failed: {
    label: 'Webhook Verification Failed',
    desc: 'Urgent priority 5 security alert. Bypasses quiet hours. Admin-only sanitized error reason category.',
    icon: ShieldAlert,
    color: 'text-red-500 bg-red-500/10 border-red-500/20',
    defaultPrio: 'Priority 5 (Max)'
  }
};

export const NotificationsPage: React.FC<NotificationsPageProps> = () => {
  const [activeTab, setActiveTab] = useState<'feed' | 'settings' | 'setup'>('feed');
  const [notifications, setNotifications] = useState<PushNotification[]>([]);
  const [settings, setSettings] = useState<NotificationSetting[]>([]);
  const [topicInfo, setTopicInfo] = useState<TopicInfoResponse | null>(null);

  // Filters & Pagination
  const [selectedRule, setSelectedRule] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [totalCount, setTotalCount] = useState<number>(0);

  // Loading & Error States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [savingSettings, setSavingSettings] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // Test send state & 60s cooldown timer
  const [testSending, setTestSending] = useState<boolean>(false);
  const [testCooldown, setTestCooldown] = useState<number>(0);
  const [testSendMsg, setTestSendMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Copied indicator
  const [copiedUrl, setCopiedUrl] = useState<boolean>(false);

  // Countdown timer effect
  useEffect(() => {
    if (testCooldown <= 0) return;
    const timer = setInterval(() => {
      setTestCooldown(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [testCooldown]);

  // Fetch notifications list
  const fetchNotifications = useCallback(async () => {
    try {
      setError(null);
      const res = await api.getNotifications(selectedRule, selectedStatus, 100, 0);
      setNotifications(res.notifications || []);
      setTotalCount(res.total || 0);
    } catch (err: any) {
      setError(err?.message || 'Failed to load notifications history.');
    }
  }, [selectedRule, selectedStatus]);

  // Fetch settings & topic info
  const fetchSettingsAndTopic = useCallback(async () => {
    try {
      const [settRes, topRes] = await Promise.all([
        api.getNotificationSettings(),
        api.getTopicInfo()
      ]);
      setSettings(settRes.settings || []);
      setTopicInfo(topRes);
    } catch (err: any) {
      console.warn('Failed to load notification settings or topic info:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    setLoading(true);
    Promise.all([fetchNotifications(), fetchSettingsAndTopic()]).finally(() => {
      setLoading(false);
    });
  }, [fetchNotifications, fetchSettingsAndTopic]);

  // Handle setting updates
  const handleToggleRule = (rule: NotificationRule) => {
    setSettings(prev =>
      prev.map(s => (s.rule === rule ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const handleUpdateThreshold = (rule: NotificationRule, val: number) => {
    setSettings(prev =>
      prev.map(s => (s.rule === rule ? { ...s, threshold: val } : s))
    );
  };

  const handleUpdateQuietHours = (rule: NotificationRule, field: 'quiet_hours_start' | 'quiet_hours_end', val: string) => {
    setSettings(prev =>
      prev.map(s => (s.rule === rule ? { ...s, [field]: val } : s))
    );
  };

  const handleUpdateMinMinutes = (rule: NotificationRule, val: number) => {
    setSettings(prev =>
      prev.map(s => (s.rule === rule ? { ...s, min_minutes_between: val } : s))
    );
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    setSaveSuccessMsg(null);
    try {
      const res = await api.updateNotificationSettings(settings);
      setSaveSuccessMsg(`Settings saved successfully! (${res.updated_count} rules updated)`);
      setTimeout(() => setSaveSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err?.message || 'Failed to update notification settings.');
    } finally {
      setSavingSettings(false);
    }
  };

  // Test notification trigger
  const handleSendTest = async () => {
    if (testCooldown > 0 || testSending) return;
    setTestSending(true);
    setTestSendMsg(null);
    try {
      const res = await api.sendTestNotification();
      setTestSendMsg({ type: 'success', text: res.message || 'Test push notification sent successfully!' });
      setTestCooldown(60); // 1 minute cooldown per specification
      fetchNotifications();
    } catch (err: any) {
      const retrySec = err?.retry_after_seconds || 60;
      setTestCooldown(retrySec);
      setTestSendMsg({
        type: 'error',
        text: err?.error || 'Rate limit reached. Please wait between test notification sends.'
      });
    } finally {
      setTestSending(false);
    }
  };

  const handleCopyBaseUrl = () => {
    if (!topicInfo?.base_url) return;
    navigator.clipboard.writeText(topicInfo.base_url);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-blue-600 text-white shadow-md shadow-blue-500/20">
              <Bell className="w-5 h-5" />
            </span>
            Push Notifications & Alerts
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time, fire-and-forget mobile push alerts powered by ntfy.sh with noise deduplication and quiet hours.
          </p>
        </div>

        {/* Global Action: Test Send Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={fetchNotifications}
            title="Refresh feed"
            className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={handleSendTest}
            disabled={testCooldown > 0 || testSending}
            className={`px-4 py-2.5 rounded-lg font-medium text-sm flex items-center gap-2 shadow-sm transition-all ${
              testCooldown > 0 || testSending
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-200 dark:border-slate-700'
                : 'bg-blue-600 hover:bg-blue-700 active:scale-95 text-white shadow-blue-500/20'
            }`}
          >
            {testSending ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            {testCooldown > 0
              ? `Cooldown (${testCooldown}s)`
              : testSending
              ? 'Sending...'
              : 'Send Test Notification'}
          </button>
        </div>
      </div>

      {/* Test Send Feedback Banner */}
      {testSendMsg && (
        <div
          className={`p-3.5 rounded-xl border flex items-center justify-between text-sm animate-in fade-in slide-in-from-top-1 duration-200 ${
            testSendMsg.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
              : 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {testSendMsg.type === 'success' ? (
              <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
            )}
            <span>{testSendMsg.text}</span>
          </div>
          <button
            onClick={() => setTestSendMsg(null)}
            className="text-xs font-semibold underline ml-4 hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs Bar */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
        <div className="flex gap-2 -mb-px">
          <button
            onClick={() => setActiveTab('feed')}
            className={`py-3 px-4 font-medium text-sm border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'feed'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <Clock className="w-4 h-4" />
            Delivery Log & Feed
            <span className="ml-1.5 px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-bold">
              {totalCount}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            className={`py-3 px-4 font-medium text-sm border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'settings'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <Sliders className="w-4 h-4" />
            Rules & Quiet Hours
          </button>

          <button
            onClick={() => setActiveTab('setup')}
            className={`py-3 px-4 font-medium text-sm border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === 'setup'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <Smartphone className="w-4 h-4" />
            Mobile App Setup
          </button>
        </div>

        {/* Masked topic pill in header */}
        {topicInfo && (
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Target Topic:</span>
            <code className="font-mono font-semibold text-slate-800 dark:text-slate-200">
              {topicInfo.masked_topic}
            </code>
          </div>
        )}
      </div>

      {/* Error state with retry */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
          <button
            onClick={fetchNotifications}
            className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* TAB 1: DELIVERY LOG FEED */}
      {activeTab === 'feed' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                <Filter className="w-3.5 h-3.5" />
                Filter Rule:
              </div>
              <select
                value={selectedRule}
                onChange={e => setSelectedRule(e.target.value)}
                className="text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Event Rules</option>
                <option value="low_stock">Low Stock Alerts</option>
                <option value="expiry_risk">Expiry Risks</option>
                <option value="payment_verified">Payment Verified</option>
                <option value="count_mismatch">Count Mismatches</option>
                <option value="scanner_failure">Scanner Failures</option>
                <option value="webhook_failed">Webhook Failures</option>
              </select>

              <div className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400 ml-2">
                Status:
              </div>
              <select
                value={selectedStatus}
                onChange={e => setSelectedStatus(e.target.value)}
                className="text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Delivery States</option>
                <option value="sent">Sent (Delivered)</option>
                <option value="pending">Pending Queue</option>
                <option value="suppressed">Suppressed (Noise Filter)</option>
                <option value="failed">Failed (Retries Exhausted)</option>
              </select>
            </div>

            <div className="text-xs text-slate-500 dark:text-slate-400">
              Showing {notifications.length} of {totalCount} events
            </div>
          </div>

          {/* Loading Skeleton */}
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map(i => (
                <div
                  key={i}
                  className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 animate-pulse space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
                    <div className="h-4 w-20 bg-slate-200 dark:bg-slate-800 rounded" />
                  </div>
                  <div className="h-5 w-2/3 bg-slate-200 dark:bg-slate-800 rounded" />
                  <div className="h-3 w-1/2 bg-slate-200 dark:bg-slate-800 rounded" />
                </div>
              ))}
            </div>
          ) : notifications.length === 0 ? (
            /* Empty State */
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-dashed border-slate-300 dark:border-slate-800 p-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
                <BellOff className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-slate-800 dark:text-slate-200">No Notifications Recorded</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                No notifications match your current filter. Real business events (sales, stock deductions, scanner timeouts) will appear here in real-time.
              </p>
              <button
                onClick={handleSendTest}
                className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                Trigger Test Event
              </button>
            </div>
          ) : (
            /* Notification Items List */
            <div className="space-y-3">
              {notifications.map(item => {
                const meta = RULE_METADATA[item.rule] || {
                  label: item.rule,
                  icon: Bell,
                  color: 'text-slate-500 bg-slate-100',
                  defaultPrio: 'Normal'
                };
                const IconComponent = meta.icon;

                return (
                  <div
                    key={item.id}
                    className="p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800/90 hover:border-slate-300 dark:hover:border-slate-700 transition-all shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="flex items-start gap-3.5">
                      <div className={`p-2.5 rounded-xl border shrink-0 ${meta.color}`}>
                        <IconComponent className="w-5 h-5" />
                      </div>

                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-sm text-slate-900 dark:text-white">
                            {item.title}
                          </span>
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                            {meta.label}
                          </span>
                          <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900">
                            Prio {item.priority}
                          </span>
                        </div>

                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                          {item.message}
                        </p>

                        <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 dark:text-slate-500 pt-0.5">
                          <span>Ref: <code className="font-mono">{item.event_ref}</code></span>
                          <span>&bull;</span>
                          <span>Created: {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                          {item.sent_at && (
                            <>
                              <span>&bull;</span>
                              <span className="text-emerald-600 dark:text-emerald-400">
                                Delivered: {new Date(item.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                              </span>
                            </>
                          )}
                          {item.last_error && (
                            <>
                              <span>&bull;</span>
                              <span className="text-amber-600 dark:text-amber-400 italic">
                                Note: {item.last_error}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div className="shrink-0 flex items-center sm:flex-col sm:items-end gap-1.5">
                      {item.status === 'sent' && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Delivered
                        </span>
                      )}

                      {item.status === 'pending' && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
                          <Clock className="w-3.5 h-3.5 animate-spin" />
                          Pending Dispatch
                        </span>
                      )}

                      {item.status === 'suppressed' && (
                        <span
                          title={item.last_error || 'Suppressed by deduplication window or quiet hours'}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 cursor-help"
                        >
                          <BellOff className="w-3.5 h-3.5 text-slate-400" />
                          Suppressed
                        </span>
                      )}

                      {item.status === 'failed' && (
                        <span
                          title={item.last_error || '3 retries failed with error'}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800 cursor-help"
                        >
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Failed ({item.attempts} attempts)
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: RULES & NOISE SETTINGS */}
      {activeTab === 'settings' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Sliders className="w-5 h-5 text-blue-600" />
                Notification Thresholds & Quiet Hours
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                Configure noise filters, quiet hour windows, and deduplication frequency per rule. Non-negotiable: Priority 5 alerts always bypass quiet hours.
              </p>
            </div>

            {saveSuccessMsg && (
              <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-sm flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{saveSuccessMsg}</span>
              </div>
            )}

            <div className="space-y-4 divide-y divide-slate-100 dark:divide-slate-800">
              {settings.map(s => {
                const meta = RULE_METADATA[s.rule] || {
                  label: s.rule,
                  desc: '',
                  icon: Bell,
                  color: 'text-slate-500 bg-slate-100',
                  defaultPrio: 'Normal'
                };
                const IconComp = meta.icon;

                return (
                  <div key={s.rule} className="pt-4 first:pt-0 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`p-2.5 rounded-xl border shrink-0 ${meta.color}`}>
                          <IconComp className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-sm text-slate-900 dark:text-white">
                              {meta.label}
                            </h3>
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                              {meta.defaultPrio}
                            </span>
                          </div>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 max-w-xl">
                            {meta.desc}
                          </p>
                        </div>
                      </div>

                      {/* Enable/Disable Toggle */}
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                          {s.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleToggleRule(s.rule)}
                          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${
                            s.enabled ? 'bg-blue-600' : 'bg-slate-200 dark:bg-slate-700'
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                              s.enabled ? 'translate-x-5' : 'translate-x-0'
                            }`}
                          />
                        </button>
                      </div>
                    </div>

                    {/* Rule Threshold Controls */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pl-0 sm:pl-12">
                      <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-xl border border-slate-200 dark:border-slate-700/60">
                        <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400">
                          Threshold Value {s.rule === 'low_stock' ? '(Units)' : s.rule === 'expiry_risk' ? '(Days)' : ''}
                        </label>
                        <input
                          type="number"
                          min="0"
                          max="1000"
                          value={s.threshold}
                          onChange={e => handleUpdateThreshold(s.rule, parseFloat(e.target.value) || 0)}
                          disabled={!s.enabled}
                          className="mt-1 w-full text-xs font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                        />
                      </div>

                      <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-xl border border-slate-200 dark:border-slate-700/60">
                        <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400">
                          Quiet Hours (Start - End)
                        </label>
                        <div className="mt-1 flex items-center gap-1.5">
                          <input
                            type="text"
                            placeholder="22:00"
                            pattern="^([01]\d|2[0-3]):([0-5]\d)$"
                            value={s.quiet_hours_start}
                            onChange={e => handleUpdateQuietHours(s.rule, 'quiet_hours_start', e.target.value)}
                            disabled={!s.enabled}
                            className="w-1/2 text-xs font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1.5 text-center focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                          />
                          <span className="text-xs text-slate-400">-</span>
                          <input
                            type="text"
                            placeholder="07:00"
                            pattern="^([01]\d|2[0-3]):([0-5]\d)$"
                            value={s.quiet_hours_end}
                            onChange={e => handleUpdateQuietHours(s.rule, 'quiet_hours_end', e.target.value)}
                            disabled={!s.enabled}
                            className="w-1/2 text-xs font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1.5 text-center focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                          />
                        </div>
                      </div>

                      <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-xl border border-slate-200 dark:border-slate-700/60">
                        <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400">
                          Min Minutes Between Repeats
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="1440"
                          value={s.min_minutes_between}
                          onChange={e => handleUpdateMinMinutes(s.rule, parseInt(e.target.value, 10) || 60)}
                          disabled={!s.enabled}
                          className="mt-1 w-full text-xs font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={handleSaveSettings}
                disabled={savingSettings}
                className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-sm font-semibold shadow-md shadow-blue-500/20 transition-all flex items-center gap-2"
              >
                {savingSettings && <RefreshCw className="w-4 h-4 animate-spin" />}
                Save Configuration
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: MOBILE APP SETUP */}
      {activeTab === 'setup' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Step 1: Install App */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-sm">
                1
              </div>
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">Install ntfy App</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                  ntfy is an open-source, zero-account mobile push client for iOS and Android. No phone numbers or signups required.
                </p>
              </div>

              <div className="space-y-2 pt-2">
                <a
                  href="https://apps.apple.com/app/ntfy/id1625396347"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors text-xs font-semibold text-slate-700 dark:text-slate-200"
                >
                  <span>Download for Apple iOS</span>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                </a>

                <a
                  href="https://play.google.com/store/apps/details?id=io.heckel.ntfy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors text-xs font-semibold text-slate-700 dark:text-slate-200"
                >
                  <span>Download for Android (Play Store)</span>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                </a>
              </div>
            </div>

            {/* Step 2: Configure Server & Topic */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-sm">
                2
              </div>
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">Subscribe to Channel</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                  Open the ntfy app, tap the <strong>+</strong> button, and connect to your instance.
                </p>
              </div>

              <div className="space-y-3 pt-1">
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Server URL
                  </label>
                  <div className="mt-1 flex items-center justify-between p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-800 dark:text-slate-200">
                    <span>{topicInfo?.base_url || 'https://ntfy.sh'}</span>
                    <button
                      onClick={handleCopyBaseUrl}
                      className="text-slate-400 hover:text-blue-600 transition-colors"
                      title="Copy server URL"
                    >
                      {copiedUrl ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Target Topic (Secret)
                  </label>
                  <div className="mt-1 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-800 dark:text-slate-200 flex items-center justify-between">
                    <span className="font-semibold text-blue-600 dark:text-blue-400">
                      {topicInfo?.masked_topic || '***8f4b'}
                    </span>
                    <span className="text-[10px] text-slate-400 italic">Masked for Secrecy</span>
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-[11px] text-blue-800 dark:text-blue-300">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <Info className="w-3.5 h-3.5 shrink-0" />
                    <span>Non-Negotiable Secrecy Rule</span>
                  </div>
                  <p className="mt-1">
                    The full topic name is stored strictly in your <code>NTFY_TOPIC</code> environment variable. Anyone who knows it can read alerts.
                  </p>
                </div>
              </div>
            </div>

            {/* Step 3: Test Verification */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-sm">
                3
              </div>
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">Verify Live Delivery</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                  Trigger an immediate test push alert to ensure notifications arrive on your phone within 5-10 seconds.
                </p>
              </div>

              <div className="pt-2">
                <button
                  onClick={handleSendTest}
                  disabled={testCooldown > 0 || testSending}
                  className={`w-full py-3 px-4 rounded-xl font-semibold text-xs flex items-center justify-center gap-2 shadow-sm transition-all ${
                    testCooldown > 0 || testSending
                      ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-200 dark:border-slate-700'
                      : 'bg-blue-600 hover:bg-blue-700 active:scale-95 text-white shadow-blue-500/20'
                  }`}
                >
                  <Send className="w-4 h-4" />
                  {testCooldown > 0
                    ? `Cooldown Active (${testCooldown}s)`
                    : testSending
                    ? 'Transmitting Alert...'
                    : 'Dispatch Live Test Push'}
                </button>

                <p className="text-[11px] text-slate-400 text-center mt-3 leading-tight">
                  Rate limited to 1 dispatch per minute to prevent accidental flood.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

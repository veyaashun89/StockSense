import React, { useState } from 'react';
import {
  Layers,
  Store,
  Truck,
  ShieldCheck,
  Building2,
  Lock,
  Mail,
  ArrowRight,
  AlertCircle,
  Eye,
  EyeOff,
  Sparkles,
  CheckCircle2
} from 'lucide-react';
import { api } from '../services/api';
import type { User, UserRole } from '../types';

interface LoginPageProps {
  onLoginSuccess: (user: User) => void;
  initialRole?: UserRole;
}

interface RolePortalConfig {
  role: UserRole;
  label: string;
  badge: string;
  icon: any;
  colorScheme: {
    accent: string;
    hover: string;
    badgeBg: string;
    badgeText: string;
    border: string;
  };
  headline: string;
  description: string;
  demoCredentials: {
    email: string;
    password: string;
  };
}

const PORTALS: RolePortalConfig[] = [
  {
    role: 'retailer',
    label: 'Retailer Portal',
    badge: 'Store Operations',
    icon: Store,
    colorScheme: {
      accent: 'bg-blue-600',
      hover: 'hover:bg-blue-700',
      badgeBg: 'bg-blue-50 dark:bg-blue-950/50',
      badgeText: 'text-blue-700 dark:text-blue-300',
      border: 'border-blue-200 dark:border-blue-800'
    },
    headline: 'Retail Store & POS Management',
    description: 'Monitor daily sales, point-of-sale scanner checkouts, automated reorder plans, and store shelf inventory.',
    demoCredentials: {
      email: 'retailer@stocksense.in',
      password: 'retailer123'
    }
  },
  {
    role: 'wholesaler',
    label: 'Wholesaler Portal',
    badge: 'Bulk Distribution',
    icon: Truck,
    colorScheme: {
      accent: 'bg-emerald-600',
      hover: 'hover:bg-emerald-700',
      badgeBg: 'bg-emerald-50 dark:bg-emerald-950/50',
      badgeText: 'text-emerald-700 dark:text-emerald-300',
      border: 'border-emerald-200 dark:border-emerald-800'
    },
    headline: 'Wholesale Supply & Order Fulfillment',
    description: 'Receive incoming purchase orders, dispatch bulk pallets, manage MOQ wholesale catalogs, and analyze demand signals.',
    demoCredentials: {
      email: 'wholesaler@stocksense.in',
      password: 'wholesaler123'
    }
  },
  {
    role: 'admin',
    label: 'Administrator Portal',
    badge: 'System Governance',
    icon: ShieldCheck,
    colorScheme: {
      accent: 'bg-rose-600',
      hover: 'hover:bg-rose-700',
      badgeBg: 'bg-rose-50 dark:bg-rose-950/50',
      badgeText: 'text-rose-700 dark:text-rose-300',
      border: 'border-rose-200 dark:border-rose-800'
    },
    headline: 'Platform Admin & Telemetry',
    description: 'Audit system health, inspect SQLite WAL integrity, monitor AI computer vision models, and govern user roles.',
    demoCredentials: {
      email: 'admin@stocksense.in',
      password: 'admin123'
    }
  },
  {
    role: 'dealer',
    label: 'Dealer Portal',
    badge: 'Regional Distribution',
    icon: Building2,
    colorScheme: {
      accent: 'bg-purple-600',
      hover: 'hover:bg-purple-700',
      badgeBg: 'bg-purple-50 dark:bg-purple-950/50',
      badgeText: 'text-purple-700 dark:text-purple-300',
      border: 'border-purple-200 dark:border-purple-800'
    },
    headline: 'Regional Dealership Command',
    description: 'Manage territory margin tiers, brand-level regional allocations, and retail dealer supply quotas.',
    demoCredentials: {
      email: 'dealer@stocksense.in',
      password: 'dealer123'
    }
  }
];

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess, initialRole = 'retailer' }) => {
  const [selectedPortal, setSelectedPortal] = useState<RolePortalConfig>(
    PORTALS.find(p => p.role === initialRole) || PORTALS[0]
  );
  const [email, setEmail] = useState<string>(selectedPortal.demoCredentials.email);
  const [password, setPassword] = useState<string>(selectedPortal.demoCredentials.password);
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handlePortalSwitch = (portal: RolePortalConfig) => {
    setSelectedPortal(portal);
    setEmail(portal.demoCredentials.email);
    setPassword(portal.demoCredentials.password);
    setError(null);
  };

  const handleUseDemo = () => {
    setEmail(selectedPortal.demoCredentials.email);
    setPassword(selectedPortal.demoCredentials.password);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide both email address and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.login(email.trim(), password);
      if (res && res.user) {
        onLoginSuccess(res.user);
      } else {
        throw new Error('Authentication failed');
      }
    } catch (err: any) {
      setError(err?.message || 'Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const CurrentIcon = selectedPortal.icon;

  return (
    <div className="min-h-screen bg-[#F7F9FC] dark:bg-[#0B0F17] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 transition-colors">
      <div className="max-w-md w-full mx-auto space-y-6">
        
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-500/30 mb-2">
            <Layers className="w-6 h-6" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            StockSense AI
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Intelligent Inventory & Automated Replenishment Platform
          </p>
        </div>

        {/* Role Portal Selection Tabs */}
        <div className="bg-white dark:bg-slate-900 p-1.5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-2 py-1">
            Select Portal Access:
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mt-1">
            {PORTALS.map((portal) => {
              const isSelected = selectedPortal.role === portal.role;
              const Icon = portal.icon;
              return (
                <button
                  key={portal.role}
                  type="button"
                  onClick={() => handlePortalSwitch(portal)}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-xs font-semibold transition-all ${
                    isSelected
                      ? `${portal.colorScheme.accent} text-white shadow-xs border-transparent font-bold scale-[1.02]`
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  <Icon className="w-4 h-4 mb-1" />
                  <span className="truncate">{portal.label.replace(' Portal', '')}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Portal Authentication Card */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl p-6 sm:p-8 space-y-5">
          
          {/* Active Portal Header */}
          <div className="flex items-start justify-between gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold border ${selectedPortal.colorScheme.badgeBg} ${selectedPortal.colorScheme.badgeText} ${selectedPortal.colorScheme.border}`}
                >
                  <CurrentIcon className="w-3.5 h-3.5" />
                  <span>{selectedPortal.badge}</span>
                </span>
              </div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mt-1.5">
                {selectedPortal.headline}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {selectedPortal.description}
              </p>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div
              role="alert"
              className="p-3.5 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-300 text-xs flex items-center gap-2.5"
            >
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600 dark:text-red-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="name@stocksense.in"
                  required
                  className="w-full pl-9 pr-3.5 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white dark:focus:bg-slate-800 transition-colors"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-9 pr-10 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white dark:focus:bg-slate-800 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* One-Click Demo Credentials Autofill */}
            <div className="flex items-center justify-between text-xs pt-1">
              <button
                type="button"
                onClick={handleUseDemo}
                className="text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 font-semibold"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Autofill Demo Credentials</span>
              </button>
              <span className="text-[11px] font-mono text-slate-400">
                {selectedPortal.demoCredentials.email}
              </span>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className={`w-full py-2.5 px-4 rounded-xl text-white text-xs sm:text-sm font-bold shadow-md flex items-center justify-center gap-2 transition-all disabled:opacity-50 active:scale-98 ${selectedPortal.colorScheme.accent} ${selectedPortal.colorScheme.hover}`}
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Sign In to {selectedPortal.label}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Security & Isolation Footnote */}
        <div className="text-center text-xs text-slate-400 dark:text-slate-500 flex items-center justify-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <span>Server-Enforced Role Scoping & Tenant Isolation</span>
        </div>
      </div>
    </div>
  );
};

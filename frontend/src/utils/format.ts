/**
 * StockSense AI Utility: Currency and Number Formatting
 * Rule 4: Money calculations stay strictly in integer paise.
 * Format figures in UI using Indian Rupee grouping (e.g. ₹1,23,456.00).
 */

export function formatRupees(paise: number, showDecimals = true): string {
  if (isNaN(paise) || paise === null || paise === undefined) {
    return '₹0.00';
  }
  const rupees = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: showDecimals ? 2 : 0,
    maximumFractionDigits: showDecimals ? 2 : 0,
  }).format(rupees);
}

export function formatIndianNumber(n: number): string {
  if (isNaN(n) || n === null || n === undefined) {
    return '0';
  }
  return new Intl.NumberFormat('en-IN').format(n);
}

export function formatRelativeTime(isoString?: string | null): string {
  if (!isoString) return 'Just now';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return 'Just now';
  }
}

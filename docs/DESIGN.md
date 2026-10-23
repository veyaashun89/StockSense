# StockSense AI — Design System & Visual Guidelines (`docs/DESIGN.md`)

## 1. Design Philosophy: The 10-Second Principle
StockSense AI is engineered for high-throughput retail shopkeepers, wholesale distributors, regional dealers, and inventory managers.
In any overview screen, the user must understand within **the first 10 seconds**:
1. **What needs attention right now?** (Critical stockouts, expiring items, pending payments, blocked orders)
2. **How is the business doing?** (Today's revenue in ₹, items moved, stock valuation, week-on-week trend)
3. **What should I do next?** (One prominent, unambiguous primary call to action per page)

---

## 2. Color Palette & Semantic Tokens

### 2.1 Neutral Foundation (Light & Dark Theme Support)
| Token | Light Mode | Dark Mode | Usage |
| :--- | :--- | :--- | :--- |
| **`bg-canvas`** | `#F8FAFC` (Slate 50) | `#0B0F17` (Deep Dark) | App background canvas |
| **`bg-surface`** | `#FFFFFF` (Pure White) | `#131B2E` (Surface Dark) | Cards, panels, drawers |
| **`bg-surface-subtle`** | `#F1F5F9` (Slate 100) | `#1E293B` (Slate 800) | Table headers, secondary blocks |
| **`border-base`** | `#E2E8F0` (Slate 200) | `#24334D` (Border Dark) | Card borders, dividers |
| **`text-primary`** | `#0F172A` (Slate 900) | `#F8FAFC` (Slate 50) | Headings, primary KPIs, bold labels |
| **`text-secondary`** | `#475569` (Slate 600) | `#94A3B8` (Slate 400) | Descriptions, captions, subtitles |
| **`text-muted`** | `#94A3B8` (Slate 400) | `#64748B` (Slate 500) | Helper text, disabled hints, timestamps |

### 2.2 Primary Brand Accent
- **Primary 600**: `#2563EB` (Actions, Primary Buttons, Active Tabs)
- **Primary 700 (Hover)**: `#1D4ED8`
- **Primary Light (Tint)**: `#EFF6FF` (Light) / `#1E3A8A33` (Dark)

### 2.3 Semantic Status System (Always Paired: Color + Icon + Text)
Never rely on color alone. Every status badge, notification, and alert MUST combine an explicit semantic color, an accessible SVG icon, and human-readable text.

| Status | Color | Light Bg / Dark Bg | Icon | Intent & Threshold |
| :--- | :--- | :--- | :--- | :--- |
| **Healthy** | `#10B981` (Emerald 500) | `#ECFDF5` / `#064E3B40` | `CheckCircle2` | Stock > Reorder Point + Safety Buffer |
| **Attention / Low** | `#F59E0B` (Amber 500) | `#FFFBEB` / `#78350F40` | `Clock` / `AlertTriangle` | Stock <= Reorder Point or Expiring < 7d |
| **Critical** | `#EF4444` (Rose 500) | `#FEF2F2` / `#7F1D1D40` | `AlertCircle` / `ShieldAlert` | Stockout (0 units), Failed Payment, Error |
| **Inactive / Neutral** | `#64748B` (Slate 500) | `#F1F5F9` / `#1E293B` | `MinusCircle` | Closed, Archived, Standby |

---

## 3. Typography & Tabular Numerals

### 3.1 Typeface Pair
- **Display & Headings**: Inter / System Sans-serif, font-weight `600` (Semi-bold) to `700` (Bold).
- **Body & Controls**: Inter / System Sans-serif, font-weight `400` (Regular) and `500` (Medium).
- **Figures & Financial Data**: **Tabular Numerals** (`font-mono tabular-nums`) to ensure vertical alignment in tables, balance strips, and KPI cards without column jitter.

### 3.2 Indian Currency Formatting Rule (Rule 4)
- Money is stored strictly in integer paise.
- Currency display MUST use Indian grouping syntax with standard Rupee symbol `₹`:
  $$\text{₹12,34,567.89} \quad \text{or} \quad \text{₹1,23,456.00}$$
- Formatted via dedicated helper: `formatCurrency(paise: number): string`.

---

## 4. Spacing, Radii & Elevation

### 4.1 Spacing Scale
- 4px baseline: `p-1` (4px), `p-2` (8px), `p-3` (12px), `p-4` (16px), `p-6` (24px), `p-8` (32px).
- Maximum viewport container: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`.
- Mobile resilience: responsive down to **360px** viewport width (`overflow-x-hidden w-full`).

### 4.2 Border Radii
- Small tags / pills: `rounded-md` (6px)
- Interactive buttons / inputs: `rounded-lg` (8px)
- Cards & modals: `rounded-xl` (12px)
- Pill badges: `rounded-full`

### 4.3 Elevation & Focus States
- Cards: `border border-slate-200 dark:border-slate-800 shadow-xs hover:shadow-sm transition-all`
- Focus States: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900`

---

## 5. Information Architecture of Overview Screens

Every role-scoped overview adheres to the strict top-to-bottom visual hierarchy:
```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. PageHeader (Title, Subtitle, Role Badge, Generated At, Refresh Btn) │
├────────────────────────────────────────────────────────────────────────┤
│ 2. AttentionList (Top urgent alerts, critical stockouts, failures)    │
├────────────────────────────────────────────────────────────────────────┤
│ 3. KPI Cards Row (Today's Sales, Units, Stock Value, Action Count)    │
├────────────────────────────────────────────────────────────────────────┤
│ 4. StockHealthBar & Business Trend Charts (with Accessible Data Table) │
├────────────────────────────────────────────────────────────────────────┤
│ 5. Detail Action Table / Recommended Queue (with 1 Primary Action)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Shared Components Catalog

1. **`PageHeader`**: Displays title, single-line intent, role badge, last-updated timestamp, and a refresh trigger.
2. **`KpiCard`**: Displays KPI title, formatted value, delta vs past period with arrow indicator & explicit text label, and sparkline.
3. **`AttentionList`**: Prioritized alert queue with severity badge, affected entity/location, and immediate "Resolve / Act" button.
4. **`StockHealthBar`**: Visual distribution bar (`Healthy`, `Low`, `Expiring`, `Out-of-Stock`) with percentage tooltips.
5. **`TrendChart`**: Recharts area/line chart with dual view: graphical curve + accessible `<button aria-label="Toggle data table">` rendering tabular data for screen readers.
6. **`EmptyState`**: Meaningful empty representation with icon, actionable headline, explanation, and primary button.
7. **`ErrorState`**: Clear diagnostic message with retry trigger.
8. **`SkeletonBlock`**: Animated pulse placeholder matching target layout dimensions (no blank spinner).

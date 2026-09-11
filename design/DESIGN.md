# Voyant — Design System & UI Specification

## 1. Brand Identity

### 1.1 Design Philosophy
Voyant embodies **"Intelligent Clarity"** — a premium observability platform where complexity dissolves into elegant simplicity. Every pixel serves purpose; every animation tells a story of data flowing through an intelligent system.

**Design Pillars:**
- **Precision**: Data-dense interfaces that never feel cluttered
- **Intelligence**: AI-aware patterns that surface insights proactively  
- **Trust**: Dark, professional aesthetic that commands confidence
- **Flow**: Seamless navigation with purposeful micro-interactions

### 1.2 Color System

#### Primary Palette
| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `--bg-void` | `#06060B` | 6, 6, 11 | Page background, deepest layer |
| `--bg-base` | `#0A0A12` | 10, 10, 18 | Card backgrounds, surfaces |
| `--bg-elevated` | `#12121E` | 18, 18, 30 | Hover states, dropdowns |
| `--bg-surface` | `#1A1A28` | 26, 26, 40 | Active states, selected items |
| `--border-subtle` | `#1E1E2E` | 30, 30, 46 | Default borders |
| `--border-default` | `#2A2A3C` | 42, 42, 60 | Emphasized borders |
| `--border-strong` | `#3A3A4F` | 58, 58, 79 | Focus rings, active borders |

#### Accent Colors
| Token | Hex | Usage |
|-------|-----|-------|
| `--accent-primary` | `#6C5CE7` | Primary actions, active states |
| `--accent-primary-light` | `#A29BFE` | Hover states, highlights |
| `--accent-primary-glow` | `rgba(108, 92, 231, 0.15)` | Ambient glow effects |
| `--accent-secondary` | `#00D2FF` | Data visualization, links |
| `--accent-tertiary` | `#FF6B9D` | Alerts, attention markers |

#### Semantic Colors
| Token | Hex | Usage |
|-------|-----|-------|
| `--status-success` | `#00E676` | Completed, healthy, online |
| `--status-warning` | `#FFB74D` | Pending, degraded, caution |
| `--status-error` | `#FF5252` | Failed, down, critical |
| `--status-info` | `#40C4FF` | Informational, running |
| `--status-neutral` | `#78909C` | Inactive, disabled, unknown |

#### Text Colors
| Token | Hex | Contrast Ratio |
|-------|-----|----------------|
| `--text-primary` | `#E8E8F0` | 15.2:1 |
| `--text-secondary` | `#9E9EB8` | 7.8:1 |
| `--text-tertiary` | `#6B6B80` | 4.6:1 |
| `--text-disabled` | `#4A4A5A` | 3.1:1 |
| `--text-inverse` | `#06060B` | — |

### 1.3 Typography

#### Font Stack
```css
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
```

#### Type Scale
| Token | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| `--text-hero` | 48px | 800 | 1.1 | -0.03em | Landing headlines |
| `--text-h1` | 32px | 700 | 1.2 | -0.02em | Page titles |
| `--text-h2` | 24px | 600 | 1.3 | -0.01em | Section headers |
| `--text-h3` | 20px | 600 | 1.4 | -0.005em | Card titles |
| `--text-h4` | 16px | 600 | 1.5 | 0 | Subsection headers |
| `--text-body` | 14px | 400 | 1.6 | 0.01em | Body text |
| `--text-body-sm` | 13px | 400 | 1.5 | 0.01em | Secondary body |
| `--text-caption` | 12px | 500 | 1.4 | 0.02em | Labels, captions |
| `--text-overline` | 11px | 600 | 1.2 | 0.08em | Overlines, badges |
| `--text-mono` | 13px | 400 | 1.6 | 0 | Code, data |

### 1.4 Spacing System
| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Tight padding, icon gaps |
| `--space-2` | 8px | Compact spacing |
| `--space-3` | 12px | Default padding |
| `--space-4` | 16px | Standard spacing |
| `--space-5` | 20px | Card padding |
| `--space-6` | 24px | Section spacing |
| `--space-8` | 32px | Large gaps |
| `--space-10` | 40px | Section breaks |
| `--space-12` | 48px | Page margins |
| `--space-16` | 64px | Major sections |

### 1.5 Border Radius
| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Badges, small buttons |
| `--radius-md` | 8px | Inputs, cards |
| `--radius-lg` | 12px | Modals, large cards |
| `--radius-xl` | 16px | Hero sections |
| `--radius-full` | 9999px | Pills, avatars |

### 1.6 Shadows & Elevation
| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | Subtle depth |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` | Cards, dropdowns |
| `--shadow-lg` | `0 8px 32px rgba(0,0,0,0.5)` | Modals, popovers |
| `--shadow-xl` | `0 16px 64px rgba(0,0,0,0.6)` | Hero elements |
| `--shadow-glow` | `0 0 40px rgba(108,92,231,0.3)` | Accent glow |
| `--shadow-glow-intense` | `0 0 80px rgba(108,92,231,0.5)` | Hover glow |

### 1.7 Glassmorphism Tokens
| Token | Value | Usage |
|-------|-------|-------|
| `--glass-bg` | `rgba(10, 10, 18, 0.7)` | Glass panels |
| `--glass-border` | `rgba(255, 255, 255, 0.06)` | Glass borders |
| `--glass-blur` | `blur(20px)` | Backdrop blur |
| `--glass-frost` | `rgba(255, 255, 255, 0.03)` | Frost overlay |

### 1.8 Animation Tokens
| Token | Value | Usage |
|-------|-------|-------|
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | Exits, dismissals |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | Transitions |
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Bouncy effects |
| `--duration-fast` | 150ms | Hover states |
| `--duration-normal` | 250ms | Standard transitions |
| `--duration-slow` | 400ms | Page transitions |
| `--duration-slower` | 600ms | Complex animations |

---

## 2. Component Library

### 2.1 Sidebar Navigation
- **Width**: 240px (expanded) / 64px (collapsed)
- **Background**: `--bg-base` with `--glass-blur`
- **Border**: 1px solid `--border-subtle` (right side)
- **Logo**: 32px height, centered in 64px header area
- **Nav Items**: 40px height, 12px horizontal padding
- **Active State**: Left 3px accent border, `--bg-surface` background
- **Hover State**: `--bg-elevated` background, 150ms transition
- **Icons**: 20px, using Heroicons or custom SVG
- **Collapse Animation**: 250ms `--ease-out`

### 2.2 Top Bar
- **Height**: 56px
- **Background**: `--bg-base` with 0.8 opacity
- **Position**: Sticky, z-index 100
- **Search**: 320px width, `--bg-elevated` background
- **User Avatar**: 32px, circular
- **Notification Badge**: 8px red dot, positioned top-right

### 2.3 Cards
- **Background**: `--bg-base`
- **Border**: 1px solid `--border-subtle`
- **Border Radius**: `--radius-lg`
- **Padding**: `--space-6`
- **Hover**: Border color → `--border-default`, subtle `--shadow-md`
- **Glass Variant**: `--glass-bg` with `--glass-blur`
- **Gradient Border**: 1px gradient from accent to transparent (animated on hover)

### 2.4 Buttons

#### Primary
- **Background**: `--accent-primary`
- **Text**: White
- **Height**: 36px (sm) / 40px (md) / 44px (lg)
- **Padding**: 0 16px
- **Border Radius**: `--radius-md`
- **Hover**: Brightness 1.1, `--shadow-glow`
- **Active**: Scale 0.98
- **Disabled**: 0.4 opacity

#### Secondary
- **Background**: transparent
- **Border**: 1px solid `--border-default`
- **Text**: `--text-primary`
- **Hover**: `--bg-elevated`, border `--border-strong`

#### Ghost
- **Background**: transparent
- **Text**: `--text-secondary`
- **Hover**: `--bg-elevated`
- **Active**: `--bg-surface`

#### Danger
- **Background**: `--status-error`
- **Hover**: Darken 10%

### 2.5 Form Elements

#### Input Fields
- **Height**: 40px
- **Background**: `--bg-elevated`
- **Border**: 1px solid `--border-subtle`
- **Border Radius**: `--radius-md`
- **Text**: `--text-body` in `--text-primary`
- **Placeholder**: `--text-tertiary`
- **Focus**: Border `--accent-primary`, `--shadow-glow`
- **Error**: Border `--status-error`, shake animation

#### Select / Dropdown
- Same styling as inputs
- **Dropdown BG**: `--bg-elevated`
- **Dropdown Shadow**: `--shadow-lg`
- **Option Hover**: `--bg-surface`
- **Selected**: Accent left border

#### Checkboxes & Toggles
- **Size**: 18px (checkbox) / 44x24px (toggle)
- **Unchecked**: `--border-default` border
- **Checked**: `--accent-primary` fill
- **Toggle Animation**: 200ms slide

### 2.6 Data Tables
- **Row Height**: 48px
- **Header**: `--bg-elevated`, 12px text, `--text-secondary`
- **Row Hover**: `--bg-elevated`
- **Selected Row**: `--accent-primary-glow` background
- **Border Bottom**: 1px `--border-subtle`
- **Zebra Striping**: Alternating `--bg-base` / `rgba(255,255,255,0.01)`
- **Sortable Header**: Cursor pointer, sort icon on hover
- **Sticky Header**: Yes, with backdrop blur

### 2.7 Badges & Status Indicators

#### Status Dots
- **Size**: 8px
- **Online/Success**: `--status-success` with pulse animation
- **Warning**: `--status-warning` with pulse
- **Error**: `--status-error` with pulse
- **Offline**: `--status-neutral` static

#### Badges
- **Height**: 22px
- **Padding**: 0 8px
- **Border Radius**: `--radius-full`
- **Font**: `--text-overline`
- **Variants**: Filled (primary, success, warning, error) / Outline

#### Progress Bars
- **Height**: 4px (default) / 8px (large)
- **Track**: `--bg-elevated`
- **Fill**: Gradient from `--accent-primary` to `--accent-secondary`
- **Animation**: Stripe pattern moving left for indeterminate

### 2.8 Modals & Dialogs
- **Overlay**: `rgba(0,0,0,0.6)` with backdrop blur
- **Container**: `--bg-base`, max-width 560px
- **Border**: 1px `--border-subtle`
- **Border Radius**: `--radius-xl`
- **Shadow**: `--shadow-xl`
- **Animation**: Scale 0.95 → 1, opacity 0 → 1, 300ms

### 2.9 Toast Notifications
- **Position**: Bottom-right, stacked
- **Width**: 380px
- **Background**: `--bg-elevated`
- **Border Left**: 3px accent color (varies by type)
- **Animation**: Slide in from right, auto-dismiss 5s
- **Progress Bar**: Thin line at bottom showing time remaining

### 2.10 Tooltips
- **Background**: `--bg-surface`
- **Text**: `--text-body-sm`
- **Border Radius**: `--radius-sm`
- **Arrow**: 6px, matching background
- **Delay**: 500ms
- **Animation**: Fade + slight scale

### 2.11 Loading States

#### Skeleton Screens
- **Background**: `--bg-elevated`
- **Shimmer**: Linear gradient animation, 1.5s infinite
- **Border Radius**: Match component radius

#### Spinners
- **Size**: 20px (sm) / 32px (md) / 48px (lg)
- **Color**: `--accent-primary`
- **Animation**: 0.8s linear infinite rotation

#### Page Transitions
- **Content**: Fade out 150ms, fade in 250ms
- **Sidebar**: Subtle highlight pulse on active item

---

## 3. Layout System

### 3.1 Page Structure
```
┌─────────────────────────────────────────────────────────────┐
│ Top Bar (56px, sticky)                                      │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ Sidebar  │  Main Content                                    │
│ (240px)  │  padding: 32px                                   │
│          │  max-width: 1400px                               │
│          │                                                  │
│          │  ┌─────────────────────────────────────────────┐ │
│          │  │ Page Header (title, subtitle, actions)      │ │
│          │  ├─────────────────────────────────────────────┤ │
│          │  │ Filters / Tabs Bar                          │ │
│          │  ├─────────────────────────────────────────────┤ │
│          │  │ Content Area                                │ │
│          │  │ (cards, tables, grids)                      │ │
│          │  └─────────────────────────────────────────────┘ │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

### 3.2 Grid System
- **Columns**: 12-column grid
- **Gap**: 24px
- **Breakpoints**:
  - `sm`: 640px (1 column)
  - `md`: 768px (2 columns)
  - `lg`: 1024px (3 columns)
  - `xl`: 1280px (4 columns)
  - `2xl`: 1536px (sidebar + content)

### 3.3 Content Max Widths
| Context | Max Width |
|---------|-----------|
| Dashboard cards | 1400px |
| Forms | 640px |
| Tables | Full width |
| Detail views | 960px |

---

## 4. Module-Specific Designs

### 4.1 Dashboard

**Layout**: 4-column KPI grid → 2-column charts → Activity feed

**KPI Cards**:
- Icon (24px) top-left
- Value (32px, bold) center
- Label (12px, muted) below
- Trend indicator (arrow + percentage) right
- Sparkline (48px height) at bottom
- Gradient border on hover

**Charts Area**:
- Jobs Timeline: Area chart with gradient fill
- System Health: Radial gauges for each service
- Recent Activity: Scrollable list with avatars

### 4.2 Job Center

**Header**: Title + "New Job" button (primary)
**Filters Bar**: Status tabs (All, Running, Queued, Failed, Completed) + Search + Type dropdown
**Table Columns**:
- Job ID (mono font, truncated)
- Type (badge)
- Source (link)
- Status (colored badge + icon)
- Progress (progress bar for running)
- Created (relative time)
- Actions (dropdown: View, Cancel, Retry)

**Job Detail Modal**:
- Header: Job ID + Status
- Tabs: Overview, Logs, Artifacts
- Timeline: Visual job execution steps
- Log Stream: Auto-scrolling terminal view

### 4.3 Data Sources

**Layout**: Card grid (3 columns)

**Source Card**:
- Source icon (type-specific: PostgreSQL, S3, API, etc.)
- Name (h3)
- Status badge (Connected, Error, Syncing)
- Last sync timestamp
- Record count
- Health indicator (green/yellow/red dot)
- Hover: Show quick actions (Sync, Edit, Delete)

**Source Detail View**:
- Connection config (read-only, masked credentials)
- Sync history table
- Data preview (sample rows)
- Schema information

### 4.4 Governance

**Layout**: Tab navigation (Policies, Contracts, Quotas)

**Policy Card**:
- Policy name (h3)
- Type badge (Access, Data, Compliance)
- Enforcement level (Strict, Warning, Audit)
- Status toggle
- Affected resources count
- Last triggered timestamp

**Contract View**:
- Version history timeline
- Diff viewer for changes
- Approval workflow status

### 4.5 Capsules

**Layout**: Filter bar + Card grid (3 columns)

**Capsule Card**:
- Icon (48px, gradient background)
- Name (h3)
- Description (2 lines, truncated)
- Version badge
- Rating (stars)
- Install count
- Category tags
- "Install" / "Manage" button

**Capsule Detail Modal**:
- Screenshot carousel
- Full description (markdown)
- Version history
- Dependencies list
- Configuration schema
- Install/uninstall actions

### 4.6 System

**Layout**: Tab navigation (General, Security, Integrations, Logs)

**Settings Cards**:
- Setting name + description
- Input field (type-appropriate: text, toggle, select, etc.)
- "Save" button (appears on change)
- Validation messages

**System Health Panel**:
- Service status grid (icons + status)
- Uptime chart
- Resource usage meters (CPU, Memory, Disk)
- Recent alerts list

---

## 5. Interaction Patterns

### 5.1 Hover Effects
- **Cards**: Subtle lift (translateY -2px), border glow
- **Buttons**: Background brighten, cursor pointer
- **Table Rows**: Background highlight
- **Links**: Underline slide in from left
- **Icons**: Scale 1.1, color shift

### 5.2 Focus States
- **All Interactive Elements**: 2px outline, `--accent-primary` color
- **Inputs**: Border color change + subtle glow
- **Keyboard Navigation**: Visible focus rings, skip links

### 5.3 Loading Patterns
- **Initial Load**: Skeleton screens matching layout
- **Action Loading**: Button spinner, disabled state
- **Data Refresh**: Subtle pulse on affected section
- **Page Transition**: Crossfade between views

### 5.4 Empty States
- **Illustration**: Abstract geometric art (matching brand)
- **Message**: Clear, actionable text
- **CTA Button**: Primary action to resolve empty state
- **Example**: "No jobs yet. Create your first job to get started."

### 5.5 Error States
- **Inline Errors**: Red border + message below field
- **Toast Errors**: Red-bordered toast with retry action
- **Page Errors**: Centered message with illustration
- **Network Errors**: Banner at top with reconnect button

---

## 6. Responsive Behavior

### 6.1 Breakpoint Adaptations

**< 768px (Mobile)**:
- Sidebar collapses to icon-only (64px)
- Cards stack vertically (1 column)
- Tables become card-based lists
- Top bar shows hamburger menu
- Font sizes reduce by 2px

**768px - 1024px (Tablet)**:
- Sidebar collapsible (overlay mode)
- Cards: 2-column grid
- Tables: Horizontal scroll
- Top bar: Compact search

**> 1024px (Desktop)**:
- Sidebar always visible
- Full grid layouts
- All features accessible

### 6.2 Touch Targets
- Minimum: 44x44px for all interactive elements
- Spacing: 8px minimum between touch targets
- Gestures: Swipe to dismiss notifications, pull to refresh

---

## 7. Accessibility

### 7.1 Color Contrast
- All text meets WCAG 2.1 AA (4.5:1 for normal text, 3:1 for large text)
- Status indicators use icons + text, not just color
- Focus states visible at 3:1 contrast

### 7.2 Keyboard Navigation
- All interactive elements focusable
- Logical tab order
- Skip navigation link
- Escape closes modals/dropdowns
- Arrow keys for menu navigation

### 7.3 Screen Readers
- Semantic HTML (nav, main, article, etc.)
- ARIA labels on icons and interactive elements
- Live regions for dynamic content (toasts, loading)
- Descriptive link text

### 7.4 Motion
- `prefers-reduced-motion` media query support
- Disable non-essential animations when preference set
- Keep functional animations (loading indicators)

---

## 8. Animation Catalog

### 8.1 Micro-interactions
| Trigger | Animation | Duration | Easing |
|---------|-----------|----------|--------|
| Button hover | Background brighten | 150ms | ease-out |
| Card hover | Lift + glow | 250ms | ease-out |
| Toggle switch | Slide + color | 200ms | spring |
| Checkbox check | Scale bounce | 250ms | spring |
| Dropdown open | Fade + slide down | 200ms | ease-out |
| Toast appear | Slide from right | 300ms | ease-out |
| Modal open | Scale + fade | 300ms | ease-out |
| Tab switch | Underline slide | 250ms | ease-in-out |

### 8.2 Ambient Animations
| Element | Animation | Duration | Purpose |
|---------|-----------|----------|---------|
| Gradient border | Rotate gradient | 3s linear | Premium feel |
| Floating orbs | Drift + scale | 20s ease-in-out | Background depth |
| Status pulse | Scale + opacity | 2s infinite | Attention |
| Skeleton shimmer | Translate gradient | 1.5s infinite | Loading feedback |
| Progress bar stripe | Translate | 1s linear | Activity indication |

### 8.3 Page Transitions
- **Route Change**: Content fades out (150ms), new content fades in (250ms)
- **Modal Open**: Backdrop fades, modal scales from 0.95
- **Sidebar Collapse**: Width animates, icons remain visible
- **Tab Switch**: Content crossfades, active tab underline slides

---

## 9. Iconography

### 9.1 Icon Library
Use **Heroicons** (outline variant for navigation, solid for status)

### 9.2 Icon Sizes
| Token | Size | Usage |
|-------|------|-------|
| `--icon-xs` | 14px | Inline with text |
| `--icon-sm` | 16px | Buttons, inputs |
| `--icon-md` | 20px | Navigation, cards |
| `--icon-lg` | 24px | Section headers |
| `--icon-xl` | 32px | Feature icons |
| `--icon-2xl` | 48px | Empty states |

### 9.3 Icon Style
- **Stroke Width**: 1.5px (outline) / 2px (solid)
- **Color**: Inherits from parent text color
- **Hover**: Scale 1.1, color shift to accent

---

## 10. Data Visualization

### 10.1 Chart Colors
| Series | Color | Usage |
|--------|-------|-------|
| Primary | `#6C5CE7` | Main metric |
| Secondary | `#00D2FF` | Comparison |
| Tertiary | `#FF6B9D` | Alerts |
| Success | `#00E676` | Positive |
| Warning | `#FFB74D` | Caution |
| Neutral | `#78909C` | Background |

### 10.2 Chart Styles
- **Background**: Transparent or `--bg-base`
- **Grid Lines**: `--border-subtle`, dashed
- **Axis Labels**: `--text-caption` in `--text-tertiary`
- **Tooltips**: Glass effect, rounded corners
- **Animations**: Draw-in on load, smooth transitions on update

### 10.3 Chart Types
| Data | Chart | Library |
|------|-------|---------|
| Time series | Area/Line | Recharts |
| Distribution | Bar/Histogram | Recharts |
| Proportion | Donut | Recharts |
| Health status | Radial gauge | Custom SVG |
| Relationships | Force graph | D3 (if needed) |

---

## 11. Responsive Grid Layouts

### 11.1 Dashboard KPIs
```
Desktop: [Card] [Card] [Card] [Card]
Tablet:  [Card] [Card]
         [Card] [Card]
Mobile:  [Card]
         [Card]
         [Card]
         [Card]
```

### 11.2 Card Grids (Sources, Capsules)
```
Desktop: [Card] [Card] [Card]
Tablet:  [Card] [Card]
         [Card]
Mobile:  [Card]
         [Card]
         [Card]
```

### 11.3 Detail Views
```
Desktop: [Sidebar 300px] [Main Content]
Tablet:  [Full width, tabs]
Mobile:  [Full width, stacked]
```

---

## 12. Implementation Notes

### 12.1 CSS Architecture
- Use CSS Custom Properties for all design tokens
- BEM naming convention for classes
- Utility classes for spacing and layout
- Component-scoped styles where possible

### 12.2 Dark Theme Implementation
- All colors defined as CSS variables
- Single dark theme (no light mode in v1)
- System preference detection for future light mode
- High contrast mode support via media query

### 12.3 Performance
- Lazy load below-fold images
- Virtual scrolling for long lists
- Debounce search/filter inputs
- Optimize animations with `will-change` and `transform`

### 12.4 Browser Support
- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+
- No IE11 support

---

## 13. File Structure

```
voyant/
├── design/
│   ├── DESIGN.md              # This document
│   └── mockups/
│       ├── index.html         # Interactive prototype
│       └── assets/
│           ├── icons/
│           ├── illustrations/
│           └── fonts/
├── apps/
│   └── admin_panel/
│       └── static/
│           ├── css/
│           │   ├── tokens.css
│           │   ├── base.css
│           │   └── components.css
│           ├── js/
│           │   ├── app.js
│           │   └── components/
│           └── images/
└── ...
```

---

## 14. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-01-15 | Complete design system overhaul |
| 1.5 | 2025-12-01 | Added capsule marketplace |
| 1.0 | 2025-10-15 | Initial design system |

---

## 15. Accessibility Checklist

### 15.1 Color Contrast
- [ ] All text meets WCAG 2.1 AA (4.5:1 for normal, 3:1 for large text)
- [ ] Status indicators use icons + text, not color alone
- [ ] Focus rings visible at 3:1 contrast ratio

### 15.2 Keyboard Navigation
- [ ] All interactive elements focusable via Tab
- [ ] Logical tab order follows visual layout
- [ ] Skip navigation link for screen readers
- [ ] Escape closes modals/dropdowns/toasts
- [ ] Arrow keys navigate within menus/tabs
- [ ] Enter/Space activates buttons and links

### 15.3 Screen Reader Support
- [ ] Semantic HTML (`<nav>`, `<main>`, `<article>`, `<section>`)
- [ ] ARIA labels on icon-only buttons
- [ ] `aria-live` regions for dynamic content (toasts, loading)
- [ ] Descriptive link text (no "click here")
- [ ] Form labels associated with inputs

### 15.4 Motion Preferences
- [ ] `prefers-reduced-motion: reduce` disables non-essential animations
- [ ] Functional animations (loading spinners) remain but simplified
- [ ] No auto-playing video or parallax effects

---

## 16. Animation Catalog (Extended)

### 16.1 Entry Animations
| Element | Animation | Duration | Easing | Trigger |
|---------|-----------|----------|--------|---------|
| Page content | Fade up 8px | 400ms | ease-out | Route change |
| Cards (staggered) | Fade up 12px | 300ms + 50ms stagger | ease-out | Page load |
| Table rows | Fade in | 200ms + 30ms stagger | ease-out | Data load |
| KPI values | Count up | 800ms | ease-out | Initial render |
| Charts | Draw in | 600ms | ease-in-out | Visible in viewport |

### 16.2 Ambient Effects
| Effect | Description | Performance |
|--------|-------------|-------------|
| Gradient border rotate | 360° hue rotation on hover | GPU-accelerated (transform) |
| Floating orbs | Slow drift with scale oscillation | Fixed position, low FPS impact |
| Status dot pulse | Opacity oscillation | CSS animation, minimal |
| Skeleton shimmer | Background-position translate | CSS animation, minimal |
| Glass blur | Backdrop filter blur(20px) | Compositor layer, isolated |

### 16.3 Interaction Feedback
| Action | Feedback | Duration |
|--------|----------|----------|
| Button click | Scale 0.98 + brightness | 100ms |
| Toggle switch | Slide + color transition | 200ms spring |
| Checkbox check | Scale bounce 0→1.2→1 | 250ms spring |
| Card hover | TranslateY -2px + border glow | 250ms ease-out |
| Input focus | Border color + box-shadow glow | 150ms ease-out |
| Toast appear | Slide from right + fade | 300ms spring |
| Toast dismiss | Slide right + fade | 200ms ease-out |
| Modal open | Scale 0.95→1 + fade | 300ms spring |
| Modal close | Scale 1→0.95 + fade | 200ms ease-out |
| Sidebar collapse | Width 240→64 + label fade | 250ms ease-out |
| Tab underline | Left + width slide | 250ms ease-in-out |

---

## 17. Responsive Behavior (Detailed)

### 17.1 Breakpoint Definitions
| Token | Min Width | Columns | Sidebar | Typical Devices |
|-------|-----------|---------|---------|-----------------|
| `xs` | 0px | 1 | Hidden (hamburger) | Small phones |
| `sm` | 640px | 1-2 | Hidden (hamburger) | Large phones |
| `md` | 768px | 2 | Overlay (64px icon-only) | Tablets portrait |
| `lg` | 1024px | 2-3 | Collapsible (64px/240px) | Tablets landscape |
| `xl` | 1280px | 3-4 | Fixed (240px) | Laptops |
| `2xl` | 1536px | 4 | Fixed (240px) | Desktops |

### 17.2 Component Adaptations

**Sidebar:**
- `< 768px`: Hidden, triggered by hamburger menu (slide-in overlay)
- `768px–1024px`: Icon-only mode (64px), tooltips on hover
- `> 1024px`: Full expanded (240px), collapsible

**Cards Grid:**
- `< 768px`: 1 column, full width
- `768px–1024px`: 2 columns
- `> 1024px`: 3 columns (sources, capsules), 4 columns (KPIs)

**Tables:**
- `< 768px`: Convert to card-based layout (stacked fields)
- `768px–1024px`: Horizontal scroll with sticky first column
- `> 1024px`: Full table

**Top Bar:**
- `< 768px`: Search collapses to icon, expands on tap
- All sizes: Notification and help icons remain visible

**Modals:**
- `< 768px`: Full-screen overlay
- `≥ 768px`: Centered with max-width 560px

### 17.3 Touch Targets
- Minimum interactive size: 44×44px on touch devices
- Minimum spacing between targets: 8px
- Swipe gestures: Pull-to-refresh on lists, swipe-to-dismiss toasts

---

## 18. Error & Empty States

### 18.1 Empty States
**Layout:** Centered column, max-width 400px
**Components:**
- Abstract geometric illustration (120px, muted accent colors)
- Headline: `--text-h3` in `--text-primary`
- Description: `--text-body` in `--text-secondary` (2 lines max)
- CTA button: Primary style

**Examples:**
| Context | Headline | Description | CTA |
|---------|----------|-------------|-----|
| No jobs | "No jobs yet" | "Create your first job to start processing data." | "Create Job" |
| No sources | "No data sources" | "Connect a data source to begin ingesting data." | "Add Source" |
| No results | "No results found" | "Try adjusting your search or filters." | "Clear Filters" |
| No capsules | "No capsules installed" | "Browse the marketplace to find useful capsules." | "Browse Capsules" |

### 18.2 Error States
**Inline Errors (Forms):**
- Border: 1px `--status-error`
- Message: `--text-caption` in `--status-error`, below field
- Icon: Warning triangle, left of message

**Toast Errors:**
- Left border: 3px `--status-error`
- Icon: X circle in `--status-error`
- Action: "Retry" button (ghost style)

**Page Errors (500/Network):**
- Centered layout with illustration
- Error code and message
- "Try Again" primary button
- "Go Home" ghost button

**Network Offline:**
- Top banner: `--status-warning` background
- Text: "You're offline. Some features may be unavailable."
- Auto-dismiss when connection restored

---

## 19. Data Visualization Standards

### 19.1 Chart.js Configuration
```javascript
// Shared tooltip config
const tooltipConfig = {
    backgroundColor: '#1A1A28',
    titleColor: '#E8E8F0',
    bodyColor: '#9E9EB8',
    borderColor: '#2A2A3C',
    borderWidth: 1,
    cornerRadius: 8,
    padding: 12,
    titleFont: { family: 'Inter', weight: '600', size: 13 },
    bodyFont: { family: 'Inter', size: 12 },
    displayColors: true,
    usePointStyle: true,
};

// Shared grid config
const gridConfig = {
    color: 'rgba(30, 30, 46, 0.5)',
    drawBorder: false,
};

// Shared tick config
const tickConfig = {
    color: '#6B6B80',
    font: { family: 'Inter', size: 11 },
};
```

### 19.2 Chart Types
| Data Pattern | Chart Type | Library | Config |
|-------------|------------|---------|--------|
| Time series | Area (gradient fill) | Chart.js | Tension 0.4, no point radius |
| Comparison | Grouped bar | Chart.js | Border radius 4px |
| Distribution | Donut | Chart.js | Cutout 70% |
| Health status | Radial gauge | Custom SVG | Animated stroke-dasharray |
| Sparkline | Mini line | Chart.js | No axes, no tooltip |

### 19.3 Color Assignments
| Series Index | Color | Usage |
|-------------|-------|-------|
| 0 | `#6C5CE7` | Primary metric |
| 1 | `#00D2FF` | Secondary metric |
| 2 | `#FF6B9D` | Tertiary/alert |
| 3 | `#00E676` | Success/positive |
| 4 | `#FFB74D` | Warning/caution |
| 5 | `#78909C` | Neutral/baseline |

---

## 20. Implementation Notes

### 20.1 CSS Architecture
- **tokens.css**: All CSS custom properties (colors, spacing, typography, shadows)
- **base.css**: Reset, global styles, layout shell, page structure
- **components.css**: Reusable component styles (buttons, cards, tables, forms)
- **pages/**: Page-specific styles (dashboard.css, jobs.css, etc.)
- Naming: BEM convention (`.block__element--modifier`)

### 20.2 JavaScript Architecture
- Vanilla JS (no framework dependency for prototype)
- Chart.js for data visualization
- Component functions: `navigate()`, `showToast()`, `openModal()`, `closeModal()`
- Data rendering: Template literals with `innerHTML`
- Event delegation for dynamic content

### 20.3 Performance Budget
| Metric | Target | Measurement |
|--------|--------|-------------|
| First Contentful Paint | < 1.5s | Lighthouse |
| Largest Contentful Paint | < 2.5s | Lighthouse |
| Cumulative Layout Shift | < 0.1 | Lighthouse |
| Total bundle size | < 200KB | Webpack |
| CSS size | < 50KB | Gzipped |
| JS size | < 100KB | Gzipped |

### 20.4 Browser Support
| Browser | Minimum Version |
|---------|-----------------|
| Chrome | 90+ |
| Firefox | 90+ |
| Safari | 14+ |
| Edge | 90+ |
| iOS Safari | 14+ |
| Chrome Android | 90+ |

No IE11 support.

---

## 21. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-01-15 | Complete design system overhaul, animation catalog, accessibility checklist |
| 1.5 | 2025-12-01 | Added capsule marketplace, governance policies |
| 1.0 | 2025-10-15 | Initial design system with dashboard and job center |

---

*This document is the single source of truth for Voyant's design system. All UI implementations must reference these specifications.*

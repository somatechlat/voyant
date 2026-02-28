# Voyant Dashboard

| Technology | Version |
|------------|---------|
| Runtime | Bun 1.3.5 |
| Framework | Lit 3 Web Components |
| Build | Vite |

## Installation

```bash
bun install
```

## Development

```bash
bun run dev
```

## Production Build

```bash
bun run build
```

---

## Components (4 Implemented)

| Component | File | Purpose |
|-----------|------|---------|
| `saas-layout` | `src/components/saas-layout.ts` | Page layout structure |
| `saas-glass-modal` | `src/components/saas-glass-modal.ts` | Glassmorphism dialog component |
| `saas-status-dot` | `src/components/saas-status-dot.ts` | Service status indicator |
| `saas-infra-card` | `src/components/saas-infra-card.ts` | Infrastructure info cards |

## Views (2 Implemented)

| View | File | Purpose |
|------|------|---------|
| `view-login` | `src/views/view-login.ts` | Authentication view |
| `view-voyant-setup` | `src/views/view-voyant-setup.ts` | Platform setup wizard |

---

## Project Structure

```
dashboard/
├── src/
│   ├── main.ts              # Application entry point
│   ├── components/          # Lit Web Components
│   │   ├── saas-layout.ts
│   │   ├── saas-glass-modal.ts
│   │   ├── saas-status-dot.ts
│   │   └── saas-infra-card.ts
│   ├── views/               # Page views
│   │   ├── view-login.ts
│   │   └── view-voyant-setup.ts
│   └── styles/
│       └── globals.css      # Global styles
├── package.json
└── README.md
```

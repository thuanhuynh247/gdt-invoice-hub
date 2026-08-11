---
name: fintech-ui-designer
description: Design, refine, and audit Webapp XML frontend interfaces according to the Wise Fintech Design System. Use when creating UI components, refactoring templates, improving typography, styling glassmorphic cards, standardizing HSL tokens, or adding interactive states.
---

# Wise Fintech UI/UX Designer

Design, audit, and elevate the Webapp XML user interface to meet the highest standards of the **Wise Fintech** design system. Build responsive, glassmorphic, and accessible interfaces that deliver an exceptional user experience.

---

## Design System Tokens & Aesthetics

### 1. Color System (HSL Tailored Tokens)
Always use HSL CSS custom properties for theme adaptability:
- **Surface Dark**: `hsl(222, 47%, 11%)` (Deep navy / Slate)
- **Card Glass**: `hsla(222, 47%, 16%, 0.65)` with `backdrop-filter: blur(16px);`
- **Border Glass**: `1px solid hsla(217, 33%, 30%, 0.4)`
- **Primary / Brand Accent**: `hsl(142, 71%, 45%)` (Emerald Green) or `hsl(217, 91%, 60%)` (Fintech Electric Blue)
- **Status Badges**:
  - Success: `hsla(142, 71%, 45%, 0.15)` text `hsl(142, 71%, 45%)`
  - Warning: `hsla(38, 92%, 50%, 0.15)` text `hsl(38, 92%, 50%)`
  - Danger: `hsla(0, 84%, 60%, 0.15)` text `hsl(0, 84%, 60%)`

### 2. Typography
- **Headings & Body UI**: `'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif`
  - Crisp line-heights (`1.2` for headings, `1.5` for body).
  - Letter spacing: `-0.02em` on titles for a modern, refined feel.
- **Data & Numbers**: `'Roboto Mono', 'JetBrains Mono', monospace`
  - Mandatory for: Invoice amounts, VAT rates, Tax IDs (MST), dates, and transaction counts.
  - Formatted with thousand separators: `1,250,000,000 VND`.

### 3. Lego Component Architecture
Every page template is built from atomic Lego components:
- **Stat Cards (Bento Grid)**: Compact cards displaying KPI value, trend pill, and contextual subtitle.
- **Filter Toolbar**: Glass container housing search input, status filter pills, date pickers, and export triggers.
- **DataTable**: Hover-highlighted rows, sticky headers, striped or glass cards, and status pill badges.
- **Modal Drill-Down**: Centered glass modal with backdrop blur for inspecting individual invoice line items and digital signatures.

---

## Implementation & Audit Checklist

1. **Visual Hierarchy & Layout**:
   - Clean spacing scale (`8px`, `16px`, `24px`, `32px`).
   - Bento grid responsive layout (`grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`).

2. **Micro-Interactions**:
   - Subtle hover transitions on cards: `transform: translateY(-2px); transition: all 0.2s ease;`
   - Smooth button active and hover states.

3. **Accessibility (A11y)**:
   - High contrast text on dark glass backgrounds.
   - Descriptive `aria-label` on icon-only buttons.
   - Semantic HTML5 structure (`<header>`, `<main>`, `<section>`, `<table>`).

4. **Template Verification**:
   - Verify template renders seamlessly across viewports (mobile, tablet, desktop).
   - Check that no broken CSS classes or inline style overrides conflict with global tokens.

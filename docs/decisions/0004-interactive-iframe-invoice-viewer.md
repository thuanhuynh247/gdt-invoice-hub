# 0004 Interactive Iframe Invoice Viewer

Date: 2026-05-22

## Status

Accepted

## Context

The user requires a premium, interactive template electronic invoice viewer modal (**F20 / US-017**). 
Typically, displaying invoice previews inside a modal interface can be done in one of three ways:
1. Re-rendering the layout dynamically on the client side via AJAX and JS template strings.
2. Generating a server-side PDF and using PDF.js or native browser plugins to view it.
3. Loading the invoice HTML via an `<iframe>` within the modal.

The printable red invoice template (`invoice_pdf.html`) uses complex, standardized CSS styling, margins, page breaks, and red border alignments optimized for paper/PDF printing. We need to prevent the document's print-specific stylesheets from bleeding into or being overridden by the parent application's Bootstrap/Supabase-styled layout.

## Decision

Embed the official red-style electronic invoice printable page (`/api/invoices/<id>/pdf-view`) inside a responsive glassmorphic modal using an `<iframe>` (`#invoiceViewerIframe`). 

The host page will:
- Display a loader overlay (`#viewerLoadingOverlay`) and keep the iframe opacity at `0` initially.
- Listen for the iframe's `onload` event to hide the loader and fade the document in smoothly.
- Provide a dedicated top control bar with metadata status badges and buttons.
- Bind the print button to `iframe.contentWindow.print()`.

## Alternatives Considered

1. **Direct modal HTML injection (AJAX)**: Rejected because print stylesheet rules (e.g. `@media print`, `@page`, custom colors, table borders) would conflict with the dark emerald dashboard theme and cause visual bleed.
2. **Server-Side PDF Generation + PDF.js**: Rejected due to high CPU rendering overhead on the Flask server and slow loading speed compared to standard browser HTML/iframe rendering.

## Consequences

### Positive:
- **Strict Stylesheet Isolation**: The invoice stylesheet remains completely encapsulated within the iframe container.
- **Unified Codebase**: The same rendering endpoint (`/api/invoices/<id>/pdf-view`) serves both the modal viewer and the fullscreen printing feature.
- **Improved UX**: Users enjoy a smooth transition without separate tab redirect fatigue, with real-time loading feedback.

### Tradeoffs:
- **HTTP Request Overhead**: Opening the modal triggers an iframe source load request, which is handled gracefully by the local caching layers and standard HTTP compression.

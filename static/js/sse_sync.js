/**
 * Server-Sent Events (SSE) listener for Real-Time GDT Synchronization
 * Milestone v3.0.0 (US-053)
 */

document.addEventListener("DOMContentLoaded", () => {
    // Only connect if the user is likely logged in
    const token = sessionStorage.getItem("jwt_token") || localStorage.getItem("jwt_token");
    if (!token && !document.getElementById("globalLogoutButton")) return;

    setupSSESyncStream();
});

function setupSSESyncStream() {
    console.log("[SSE] Initializing EventSource for GDT sync stream...");
    
    // We can't pass Bearer tokens natively via EventSource, 
    // so the backend endpoint relies on session cookies for auth.
    const evtSource = new EventSource("/api/sync/events");
    const toastContainer = document.getElementById("realtimeSyncToastContainer");
    
    if (!toastContainer) {
        console.warn("[SSE] Toast container #realtimeSyncToastContainer not found.");
    }

    evtSource.onmessage = function(event) {
        try {
            const payload = JSON.parse(event.data);
            handleSyncEvent(payload);
        } catch (e) {
            // Heartbeats or malformed JSON
        }
    };

    evtSource.onerror = function(err) {
        console.error("[SSE] Connection lost or error.", err);
        // EventSource will automatically try to reconnect.
    };
}

function handleSyncEvent(payload) {
    const { event, data, timestamp } = payload;
    console.log(`[SSE] Received event: ${event}`, data);

    switch (event) {
        case "sync_started":
            showSyncToast("Đang đồng bộ GDT...", data.message, "info", "bi-arrow-repeat spin-icon");
            break;
            
        case "sync_progress":
            // Highlight the glassmorphic sync indicator
            showSyncToast(`Đang xử lý MST: ${data.mst}`, data.company, "primary", "bi-building");
            break;
            
        case "invoice_downloaded":
            showSyncToast("Hóa đơn mới!", `Số HĐ: ${data.number}<br>${data.message}`, "success", "bi-file-earmark-check-fill");
            
            // If we are on the invoices page, reload the grid silently
            if (typeof loadLocalInvoices === "function" && document.getElementById("invoicesTableBody")) {
                // Throttle the reload so we don't hammer the DB if many invoices arrive at once
                if (window._syncReloadTimer) clearTimeout(window._syncReloadTimer);
                window._syncReloadTimer = setTimeout(() => {
                    loadLocalInvoices();
                }, 1500);
            }
            break;
            
        case "sync_finished":
            const isSuccess = data.count > 0;
            const icon = isSuccess ? "bi-check-circle-fill" : "bi-info-circle";
            const color = isSuccess ? "success" : "secondary";
            showSyncToast("Hoàn tất", data.message, color, icon);
            break;
            
        default:
            console.log(`[SSE] Unknown event type: ${event}`);
    }
}

function showSyncToast(title, message, colorClass = "primary", iconClass = "bi-info-circle") {
    const container = document.getElementById("realtimeSyncToastContainer");
    if (!container) return;
    
    // Glassmorphic styling for the toast
    const toastId = 'toast-' + Date.now() + Math.floor(Math.random() * 1000);
    const toastHtml = `
        <div id="${toastId}" class="toast glass-toast align-items-center text-bg-${colorClass} border-0 mb-2" role="alert" aria-live="assertive" aria-atomic="true" style="backdrop-filter: blur(10px); background-color: rgba(var(--bs-${colorClass}-rgb), 0.85);">
            <div class="d-flex">
                <div class="toast-body">
                    <strong><i class="bi ${iconClass} me-2"></i>${title}</strong>
                    <div class="mt-1 small">${message}</div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Add custom CSS for spin animation if it doesn't exist
    if (!document.getElementById("sse-sync-styles")) {
        const style = document.createElement("style");
        style.id = "sse-sync-styles";
        style.innerHTML = `
            .spin-icon { animation: sse-spin 2s linear infinite; }
            @keyframes sse-spin { 100% { transform: rotate(360deg); } }
            .glass-toast { box-shadow: 0 8px 32px rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.2) !important; border-radius: 8px; }
        `;
        document.head.appendChild(style);
    }
    
    container.insertAdjacentHTML("beforeend", toastHtml);
    const toastElement = document.getElementById(toastId);
    const bsToast = new bootstrap.Toast(toastElement, { delay: 5000 });
    bsToast.show();
    
    // Cleanup DOM after hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

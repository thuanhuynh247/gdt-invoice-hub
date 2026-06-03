/**
 * Client-side script for Invoice Hub Webapp.
 * Includes interactive analytics, theme switcher, and offcanvas drawers.
 */

let sessionWarningShown = false;

// 1. Alert Banner Helper
function renderAlert(message, type = "info") {
    const region = document.getElementById("appAlertRegion");
    if (!region) {
        return;
    }

    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show alert-slot shadow-sm`;
    alert.role = "alert";
    alert.innerHTML = `
        <span class="fw-medium">${message}</span>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    region.innerHTML = "";
    region.appendChild(alert);
}

// 2. Universal API Wrapper
async function apiCall(url, options = {}) {
    const redirectOn401 = options.redirectOn401 !== false;
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    if (response.status === 401 && redirectOn401) {
        window.location.href = "/login";
        return null;
    }

    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : null;

    if (!response.ok) {
        throw new Error(body?.error || "Yêu cầu thất bại.");
    }

    return body;
}

// 3. Loading Spinner Control
function setButtonLoading(button, isLoading) {
    const spinner = button.querySelector(".spinner-border");
    const label = button.querySelector(".button-label");
    if (spinner) {
        spinner.classList.toggle("d-none", !isLoading);
    }
    if (label) {
        label.textContent = isLoading ? "Đang xử lý..." : "Đăng nhập";
    }
    button.disabled = isLoading;
}

// 4. Authenticate Request
function triggerInputError(inputElement) {
    if (!inputElement) return;
    inputElement.classList.add("is-invalid");
    inputElement.addEventListener("animationend", () => {
        inputElement.classList.remove("is-invalid");
    }, { once: true });
}

async function handleLoginSubmit(event) {
    event.preventDefault();

    const button = document.getElementById("loginSubmitButton");
    setButtonLoading(button, true);

    try {
        await apiCall("/api/auth/login", {
            method: "POST",
            redirectOn401: false,
            body: JSON.stringify({
                username: document.getElementById("username").value,
                password: document.getElementById("password").value,
                captcha: document.getElementById("captcha").value,
            }),
        });
        const sessionData = await apiCall("/api/session-status", { redirectOn401: false });
        if (!sessionData || !sessionData.logged_in) {
            throw new Error("Đăng nhập thất bại.");
        }
        window.location.href = "/invoices";
    } catch (error) {
        renderAlert(error.message, "danger");
        triggerInputError(document.getElementById("username"));
        triggerInputError(document.getElementById("password"));
        triggerInputError(document.getElementById("captcha"));
        await loadAuthCaptcha();
        const capInput = document.getElementById("captcha");
        if (capInput) capInput.value = "";
    } finally {
        setButtonLoading(button, false);
    }
}

// 5. Captcha SVG Loader
async function loadAuthCaptcha() {
    const captchaBox = document.getElementById("captchaBox");
    if (!captchaBox) {
        return;
    }

    captchaBox.textContent = "Đang tải captcha...";
    try {
        const data = await apiCall("/api/auth/captcha");
        if (!data) {
            captchaBox.textContent = "Không tải được captcha";
            return;
        }
        captchaBox.innerHTML = data.image_svg;

        const captchaRow = document.getElementById("captchaRow");
        const refreshBtn = document.getElementById("refreshCaptchaButton");
        const captchaInput = document.getElementById("captcha");

        if (data.auto_solve) {
            if (captchaRow) captchaRow.classList.add("d-none");
            if (refreshBtn) refreshBtn.classList.add("d-none");
            if (captchaInput) {
                captchaInput.removeAttribute("required");
                captchaInput.value = "AUTO";
            }
            const usernameInput = document.getElementById("username");
            const passwordInput = document.getElementById("password");
            if (data.mode === "mock") {
                if (usernameInput && !usernameInput.value) {
                    usernameInput.value = "demo";
                }
                if (passwordInput && !passwordInput.value) {
                    passwordInput.value = "password";
                }
                renderAlert("Hệ thống đang chạy ở chế độ giả lập (Mock mode) với tính năng Tự động giải CAPTCHA.", "info");
            }
        } else {
            if (captchaRow) captchaRow.classList.remove("d-none");
            if (refreshBtn) refreshBtn.classList.remove("d-none");
            if (captchaInput) {
                captchaInput.setAttribute("required", "");
                if (captchaInput.value === "AUTO") {
                    captchaInput.value = "";
                }
            }
            if (data.mode === "mock") {
                if (captchaInput) {
                    captchaInput.value = "MOCK";
                }
                const usernameInput = document.getElementById("username");
                const passwordInput = document.getElementById("password");
                if (usernameInput && !usernameInput.value) {
                    usernameInput.value = "demo";
                }
                if (passwordInput && !passwordInput.value) {
                    passwordInput.value = "password";
                }
                renderAlert("Hệ thống đang chạy ở chế độ giả lập (Mock mode). Thông tin đăng nhập và captcha đã được tự động điền.", "info");
            }
        }
    } catch (_error) {
        captchaBox.textContent = "Không tải được captcha";
    }
}

// 6. Formatter & Animation helpers
function animateNumber(element, endVal, isCurrency = false) {
    let startVal = 0;
    const duration = 800; // ms
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeProgress = progress * (2 - progress); // Ease out quad
        const currentVal = Math.floor(startVal + easeProgress * (endVal - startVal));

        if (isCurrency) {
            element.textContent = currentVal.toLocaleString("vi-VN") + " ₫";
        } else {
            element.textContent = currentVal.toLocaleString("vi-VN");
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}

// 7. Render dynamic row
function buildInvoiceRow(invoice) {
    const rowClass = invoice.is_cancelled ? "invoice-row-cancelled" : "";
    const amount = Number(invoice.amount || 0).toLocaleString("vi-VN");
    const statusBadge = invoice.is_cancelled 
        ? '<span class="badge bg-danger-subtle text-danger">Đã Hủy</span>' 
        : '<span class="badge bg-success-subtle text-success">Hợp Lệ</span>';

    return `
        <tr class="${rowClass}" data-id="${invoice.id}">
            <td class="fw-bold text-primary">${invoice.id}</td>
            <td>${invoice.date}</td>
            <td class="text-end fw-semibold">${amount} ₫</td>
            <td>${statusBadge}</td>
            <td class="fw-medium">${invoice.issuer}</td>
            <td>${invoice.description || "-"}</td>
            <td class="text-center">
                <div class="d-flex justify-content-center gap-2">
                    <button class="btn btn-sm btn-outline-primary px-3" onclick="event.stopPropagation(); showInvoiceDetails('${invoice.id}')">Chi tiết</button>
                    <a class="btn btn-sm btn-outline-dark px-3" onclick="event.stopPropagation();" href="/api/invoices/${invoice.id}/download">Tải XML</a>
                </div>
            </td>
        </tr>
    `;
}

// 8. Dynamic Dashboard Renderer
// 8. Dynamic Dashboard Renderer
async function updateDashboardStats(from, to, direction) {
    try {
        const stats = await apiCall(`/api/invoices/stats?from=${from}&to=${to}&direction=${direction}`);
        if (!stats) return;

        // Animate numbers on cards
        animateNumber(document.getElementById("statSpend"), stats.total_spend, true);
        animateNumber(document.getElementById("statTax"), stats.total_tax, true);
        animateNumber(document.getElementById("statActiveCount"), stats.active_count, false);
        animateNumber(document.getElementById("statCancelledCount"), stats.cancelled_count, false);

        // Show graphs panel
        const graphsPanel = document.getElementById("analyticsGraphsPanel");
        graphsPanel.style.display = "flex";

        // Render Top 5 Vendors (Horizontal SVG Bar Chart)
        const vendorsContainer = document.getElementById("topVendorsContainer");
        if (stats.top_vendors.length === 0) {
            vendorsContainer.innerHTML = `<p class="text-secondary small my-3 text-center">Chưa có dữ liệu nhà cung cấp.</p>`;
        } else {
            const maxSpend = Math.max(...stats.top_vendors.map(v => v.spend)) || 1;
            const rowHeight = 44;
            const svgHeight = stats.top_vendors.length * rowHeight;
            let svgBars = `<svg viewBox="0 0 500 ${svgHeight}" class="chart-svg">`;
            
            stats.top_vendors.forEach((v, i) => {
                const y = i * rowHeight;
                const barWidth = Math.max((v.spend / maxSpend) * 360, 5); // Max bar width is 360px
                
                svgBars += `
                    <g class="chart-bar-group" data-name="${v.name}" data-spend="${v.spend.toLocaleString('vi-VN')} ₫" data-count="${v.count}">
                        <!-- Company Name label -->
                        <text x="10" y="${y + 16}" fill="var(--text-primary)" style="font-size: 11px; font-weight: 600; font-family: var(--font-body);">${v.name}</text>
                        <!-- Amount text -->
                        <text x="490" y="${y + 16}" fill="var(--text-secondary)" style="font-size: 11px; font-weight: 600; font-family: var(--font-body);" text-anchor="end">${v.spend.toLocaleString('vi-VN')} ₫</text>
                        <!-- Background track -->
                        <rect x="10" y="${y + 24}" width="360" height="8" rx="4" fill="var(--border-card)"></rect>
                        <!-- Animated value bar -->
                        <rect x="10" y="${y + 24}" width="0" height="8" rx="4" fill="var(--primary-accent)" class="chart-bar-rect">
                            <animate attributeName="width" from="0" to="${barWidth}" dur="0.6s" fill="freeze" />
                        </rect>
                        <!-- Number of invoices -->
                        <text x="${barWidth + 20}" y="${y + 31}" fill="var(--text-secondary)" style="font-size: 9px; font-weight: 500; font-family: var(--font-body);">(${v.count} HĐ)</text>
                    </g>
                `;
            });
            svgBars += `</svg>`;
            vendorsContainer.innerHTML = svgBars;
        }

        // Render Tax Rate Breakdown (Donut Chart + Legend)
        const taxContainer = document.getElementById("taxBreakdownContainer");
        const entries = Object.entries(stats.tax_breakdown);
        let totalTax = 0;
        entries.forEach(([_, amt]) => {
            totalTax += amt;
        });

        // HSL palettes matching Supabase style
        const colors = {
            "10%": "var(--primary-accent)",
            "8%": "#2ec4b6",
            "5%": "#3b82f6",
            "0%": "#64748b",
            "Khác": "#f59e0b"
        };

        let svgDonut = `
            <svg viewBox="0 0 200 200" class="chart-svg position-relative">
                <circle cx="100" cy="100" r="60" fill="transparent" stroke="var(--border-card)" stroke-width="16"></circle>
        `;

        let legendHtml = '<div class="chart-legend-list w-100">';
        const circumference = 2 * Math.PI * 60; // 376.991
        let currentOffset = 0;

        if (totalTax === 0) {
            svgDonut += `
                <circle cx="100" cy="100" r="60" fill="transparent" stroke="var(--border-card)" stroke-width="16"></circle>
            `;
            legendHtml += `
                <div class="chart-legend-item">
                    <span class="d-flex align-items-center">
                        <span class="chart-legend-color" style="background-color: var(--border-card);"></span>
                        <span class="fw-semibold">Không có thuế</span>
                    </span>
                    <span class="text-secondary">0 ₫ (0%)</span>
                </div>
            `;
        } else {
            entries.forEach(([rate, amt]) => {
                const percent = (amt / totalTax) * 100;
                const strokeLength = (amt / totalTax) * circumference;
                const dashArray = `${strokeLength} ${circumference}`;
                const dashOffset = -currentOffset;
                currentOffset += strokeLength;

                const color = colors[rate] || colors["Khác"];

                svgDonut += `
                    <circle cx="100" cy="100" r="60" fill="transparent" 
                            stroke="${color}" stroke-width="16" 
                            stroke-dasharray="${dashArray}" 
                            stroke-dashoffset="${dashOffset}" 
                            transform="rotate(-90 100 100)"
                            class="chart-donut-segment"
                            data-rate="${rate}"
                            data-amount="${amt.toLocaleString('vi-VN')} ₫"
                            data-percent="${percent.toFixed(1)}%">
                    </circle>
                `;

                legendHtml += `
                    <div class="chart-legend-item" data-rate="${rate}">
                        <span class="d-flex align-items-center">
                            <span class="chart-legend-color" style="background-color: ${color};"></span>
                            <span class="fw-semibold">Thuế suất ${rate}</span>
                        </span>
                        <span class="text-secondary fw-medium">${amt.toLocaleString('vi-VN')} ₫ (${percent.toFixed(1)}%)</span>
                    </div>
                `;
            });
        }

        // Center readout texts
        svgDonut += `
            <text x="100" y="96" text-anchor="middle" class="chart-center-sub" fill="var(--text-secondary)" style="font-size: 10px;">Tổng Thuế</text>
            <text x="100" y="116" text-anchor="middle" class="chart-center-val" fill="var(--text-primary)" style="font-size: 13px; font-weight: 800;">${totalTax.toLocaleString('vi-VN')} ₫</text>
            </svg>
        `;
        legendHtml += '</div>';

        taxContainer.innerHTML = `
            <div class="d-flex flex-column flex-sm-row align-items-center gap-4 py-2">
                <div style="width: 150px; height: 150px;" class="flex-shrink-0">
                    ${svgDonut}
                </div>
                <div class="flex-grow-1 w-100">
                    ${legendHtml}
                </div>
            </div>
        `;

        // Setup mouse interactivity
        setupChartInteractiveListeners();

    } catch (error) {
        console.error("Lỗi cập nhật Dashboard:", error);
    }
}

// 8.1 Setup Chart Interactivity
function setupChartInteractiveListeners() {
    const tooltip = document.getElementById("dashboardChartTooltip");
    if (!tooltip) return;

    // A. Vendor chart bars
    const groups = document.querySelectorAll(".chart-bar-group");
    groups.forEach(g => {
        g.addEventListener("mouseenter", () => {
            const name = g.getAttribute("data-name");
            const spend = g.getAttribute("data-spend");
            const count = g.getAttribute("data-count");
            
            tooltip.innerHTML = `
                <strong style="display:block;margin-bottom:3px;color:var(--text-primary);font-size:11px;">${name}</strong>
                <span style="color:var(--primary-accent);font-weight:700;">Tổng tiền: ${spend}</span><br/>
                <span style="color:var(--text-secondary);font-size:10px;">Số giao dịch: ${count} hóa đơn</span>
            `;
            tooltip.style.opacity = "1";
        });

        g.addEventListener("mousemove", (e) => {
            const panel = document.getElementById("analyticsGraphsPanel");
            const rect = panel.getBoundingClientRect();
            // Offset a bit to position top-left/top-right of pointer
            const x = e.clientX - rect.left + 15;
            const y = e.clientY - rect.top + 15;
            tooltip.style.transform = `translate(${x}px, ${y}px)`;
        });

        g.addEventListener("mouseleave", () => {
            tooltip.style.opacity = "0";
        });
    });

    // B. Tax Donut segments
    const segments = document.querySelectorAll(".chart-donut-segment");
    const centerValText = document.querySelector(".chart-center-val");
    const centerSubText = document.querySelector(".chart-center-sub");

    let originalVal = centerValText ? centerValText.textContent : "";
    let originalSub = "Tổng Thuế";

    segments.forEach(s => {
        s.addEventListener("mouseenter", () => {
            const rate = s.getAttribute("data-rate");
            const amount = s.getAttribute("data-amount");
            const percent = s.getAttribute("data-percent");

            tooltip.innerHTML = `
                <strong style="color:var(--text-primary);font-size:11px;">Thuế suất ${rate}</strong><br/>
                <span style="color:var(--primary-accent);font-weight:700;">Tiền thuế: ${amount}</span> (${percent})
            `;
            tooltip.style.opacity = "1";

            // Live center readout update
            if (centerValText && centerSubText) {
                centerSubText.textContent = `Thuế ${rate}`;
                centerValText.textContent = amount;
            }
        });

        s.addEventListener("mousemove", (e) => {
            const panel = document.getElementById("analyticsGraphsPanel");
            const rect = panel.getBoundingClientRect();
            const x = e.clientX - rect.left + 15;
            const y = e.clientY - rect.top + 15;
            tooltip.style.transform = `translate(${x}px, ${y}px)`;
        });

        s.addEventListener("mouseleave", () => {
            tooltip.style.opacity = "0";
            if (centerValText && centerSubText) {
                centerSubText.textContent = originalSub;
                centerValText.textContent = originalVal;
            }
        });
    });

    // C. Connect legend items with donut segments
    const legendItems = document.querySelectorAll(".chart-legend-item");
    legendItems.forEach(item => {
        const rate = item.getAttribute("data-rate");
        if (!rate) return;
        
        const segment = document.querySelector(`.chart-donut-segment[data-rate="${rate}"]`);
        if (!segment) return;

        item.addEventListener("mouseenter", () => {
            segment.dispatchEvent(new Event("mouseenter"));
            segment.setAttribute("stroke-width", "20");
        });

        item.addEventListener("mouseleave", () => {
            segment.dispatchEvent(new Event("mouseleave"));
            segment.setAttribute("stroke-width", "16");
        });
    });
}

// 9. Load & Slide In Details Drawer
function getCategoryStyle(category) {
    switch (category) {
        case "Văn phòng phẩm & Thiết bị văn phòng":
            return "background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.25);";
        case "Thiết bị công nghệ & Phần mềm":
            return "background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.25);";
        case "Chi phí tiếp khách & Hội nghị":
            return "background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25);";
        case "Quảng cáo, Tiếp thị & Sự kiện":
            return "background: rgba(236, 72, 153, 0.15); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.25);";
        case "Vận chuyển, Giao hàng & Logistics":
            return "background: rgba(20, 184, 166, 0.15); color: #2dd4bf; border: 1px solid rgba(20, 184, 166, 0.25);";
        case "Chi phí dịch vụ công cộng & Tiện ích":
            return "background: rgba(14, 165, 233, 0.15); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.25);";
        case "Sửa chữa, Bảo trì & Nâng cấp":
            return "background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.25);";
        default:
            return "background: rgba(107, 114, 128, 0.15); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.25);";
    }
}

async function showInvoiceDetails(invoiceId) {
    if (!invoiceId) return;

    try {
        const details = await apiCall(`/api/invoices/${invoiceId}/details`);
        if (!details) return;

        // Populate metadata
        document.getElementById("detId").textContent = details.invoice_id;
        const detPaymentMethod = document.getElementById("detPaymentMethod");
        if (detPaymentMethod) {
            detPaymentMethod.textContent = details.payment_method || "Chưa xác định";
        }
        
        // Find row to extract display fields
        const row = document.querySelector(`tr[data-id="${invoiceId}"]`);
        if (row) {
            const isLocal = row.closest("#localInvoicesTableBody") !== null;
            if (isLocal) {
                document.getElementById("detDate").textContent = row.children[1].textContent;
                const issuerEl = row.children[2].querySelector(".fw-semibold");
                document.getElementById("detIssuer").textContent = issuerEl ? issuerEl.textContent : "-";
                document.getElementById("detDesc").textContent = `Chữ ký số: ${details.warnings && details.warnings.some(w => w.includes("chưa được ký số")) ? "Chưa hợp lệ" : "Hợp lệ"}`;
                document.getElementById("detStatus").innerHTML = row.children[7].innerHTML;
            } else {
                document.getElementById("detDate").textContent = row.children[1].textContent;
                document.getElementById("detIssuer").textContent = row.children[4].textContent;
                document.getElementById("detDesc").textContent = row.children[5].textContent;
                document.getElementById("detStatus").innerHTML = row.children[3].innerHTML;
            }
        }

        // Reset AI Repair section
        const detAiRepairContent = document.getElementById("detAiRepairContent");
        const detAiRepairStatusPlaceholder = document.getElementById("detAiRepairStatusPlaceholder");
        const btnRunAiRepair = document.getElementById("btnRunAiRepair");
        
        if (detAiRepairContent) detAiRepairContent.classList.add("d-none");
        if (detAiRepairStatusPlaceholder) detAiRepairStatusPlaceholder.classList.remove("d-none");
        if (btnRunAiRepair) {
            const isLocal = row ? row.closest("#localInvoicesTableBody") !== null : false;
            btnRunAiRepair.style.display = (isLocal && window.currentUserRole !== "viewer") ? "inline-block" : "none";
        }

        // Set the active invoice ID to run classification or audit
        const btnRunAiClassification = document.getElementById("btnRunAiClassification");
        if (btnRunAiClassification) {
            btnRunAiClassification.setAttribute("data-id", invoiceId);
            btnRunAiClassification.style.display = window.currentUserRole === "viewer" ? "none" : "inline-block";
        }

        // Populate table body
        const tbody = document.getElementById("detLineItemsBody");
        if (details.line_items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-secondary py-3">Không có mặt hàng chi tiết nào.</td></tr>`;
            document.getElementById("detBeforeTax").textContent = "0 ₫";
            document.getElementById("detTotalTax").textContent = "0 ₫";
            document.getElementById("detTotalPay").textContent = "0 ₫";
        } else {
            let sumBeforeTax = 0;
            let sumTax = 0;

            tbody.innerHTML = details.line_items.map(item => {
                sumBeforeTax += item.amount_before_tax;
                sumTax += item.tax_amount;

                const catStyle = getCategoryStyle(item.expense_category || "Chưa phân loại");
                const catText = item.expense_category || "Chưa phân loại";

                return `
                    <tr>
                        <td>
                            <div class="fw-semibold">${item.item_name}</div>
                            <div class="mt-1 d-flex align-items-center gap-2">
                                <span class="badge expense-category-badge rounded-pill px-2 py-0.5" style="font-size: 0.65rem; font-weight: 500; ${catStyle}">
                                    ${catText}
                                </span>
                                ${window.currentUserRole === "viewer" ? "" : `
                                <button type="button" class="btn btn-sm btn-link p-0 text-decoration-none edit-category-btn" 
                                        data-item-id="${item.id}" 
                                        data-item-name="${item.item_name.replace(/"/g, '&quot;')}"
                                        data-category="${catText}" 
                                        style="font-size: 0.75rem; color: #10b981;">
                                    <i class="bi bi-pencil-square"></i>
                                </button>
                                `}
                            </div>
                        </td>
                        <td class="text-center">${item.quantity}</td>
                        <td class="text-end">${Number(item.unit_price).toLocaleString("vi-VN")}</td>
                        <td class="text-end fw-semibold">${Number(item.amount_before_tax).toLocaleString("vi-VN")}</td>
                        <td class="text-center badge-tax">${item.tax_rate}</td>
                        <td class="text-end">${Number(item.tax_amount).toLocaleString("vi-VN")}</td>
                    </tr>
                `;
            }).join("");

            const totalPay = sumBeforeTax + sumTax;
            document.getElementById("detBeforeTax").textContent = sumBeforeTax.toLocaleString("vi-VN") + " ₫";
            document.getElementById("detTotalTax").textContent = sumTax.toLocaleString("vi-VN") + " ₫";
            document.getElementById("detTotalPay").textContent = totalPay.toLocaleString("vi-VN") + " ₫";
        }

        // Populate Smart Audit warning logs inside drawer
        const auditBox = document.getElementById("detAuditBox");
        const auditContent = document.getElementById("detAuditContent");
        
        if (auditBox && auditContent) {
            if (details.warnings && details.warnings.length > 0) {
                auditBox.style.display = "block";
                auditContent.innerHTML = `
                    <div class="alert alert-warning d-flex flex-column gap-2 mb-0" style="background-color: rgba(245, 158, 11, 0.1); border-color: #f59e0b; color: #d97706;">
                        <div class="d-flex align-items-start gap-2">
                            <i class="bi bi-exclamation-triangle-fill mt-1 text-warning"></i>
                            <div>
                                <strong class="d-block mb-1">Phát hiện cảnh báo (${details.warnings.length})</strong>
                                <ul class="mb-0 ps-3 small text-dark">
                                    ${details.warnings.map(w => `<li>${w}</li>`).join("")}
                                </ul>
                            </div>
                        </div>
                    </div>
                `;
            } else if (details.warnings) {
                auditBox.style.display = "block";
                auditContent.innerHTML = `
                    <div class="alert alert-success d-flex align-items-start gap-2 mb-0" style="background-color: rgba(16, 185, 129, 0.1); border-color: var(--primary-accent); color: var(--primary-accent);">
                        <i class="bi bi-check-circle-fill mt-1 text-success"></i>
                        <div>
                            <strong class="d-block mb-1 text-success-emphasis">Hợp lệ</strong>
                            <span class="small text-dark">Đã vượt qua tất cả 7 bộ kiểm tra thông minh của meInvoice (Trùng lặp, lệch thuế, MST rủi ro, chữ ký số, ký số chậm, phương thức thanh toán, trạng thái hoạt động MST).</span>
                        </div>
                    </div>
                `;
            } else {
                auditBox.style.display = "none";
            }
        }

        // Populate Digital Signature Verification inside drawer
        const sigBox = document.getElementById("detSignatureBox");
        const sigContent = document.getElementById("detSignatureContent");
        
        if (sigBox && sigContent) {
            if (details.signature_details) {
                sigBox.style.display = "block";
                const sig = details.signature_details;
                
                let sigHtml = '';
                if (sig.sig_verified) {
                    sigHtml += `
                        <div class="d-flex align-items-center gap-2 mb-2 text-success fw-bold">
                            <i class="bi bi-patch-check-fill fs-5"></i>
                            <span>Chữ ký số hợp lệ</span>
                        </div>
                    `;
                } else {
                    sigHtml += `
                        <div class="d-flex align-items-center gap-2 mb-2 text-danger fw-bold">
                            <i class="bi bi-patch-exclamation-fill fs-5"></i>
                            <span>Chữ ký số không hợp lệ</span>
                        </div>
                    `;
                }

                const caBadgeHtml = sig.sig_ca_trusted !== undefined
                    ? (sig.sig_ca_trusted 
                        ? `<span class="badge bg-success-subtle text-success border border-success border-opacity-25 ms-1"><i class="bi bi-patch-check"></i> Hợp pháp</span>`
                        : `<span class="badge bg-danger-subtle text-danger border border-danger border-opacity-25 ms-1"><i class="bi bi-patch-exclamation"></i> Chưa cấp phép</span>`)
                    : '';

                const nameMatchBadgeHtml = sig.sig_name_match !== undefined
                    ? (sig.sig_name_match 
                        ? `<span class="badge bg-success-subtle text-success border border-success border-opacity-25"><i class="bi bi-person-check"></i> Khớp người bán</span>`
                        : `<span class="badge bg-danger-subtle text-danger border border-danger border-opacity-25"><i class="bi bi-person-exclamation"></i> Không khớp</span>`)
                    : `<span class="badge bg-secondary">Chưa xác minh</span>`;

                sigHtml += `
                    <div class="d-flex flex-column gap-1.5 small mt-2" style="opacity: 0.95;">
                        <div class="d-flex justify-content-between"><span class="text-secondary-accent">Đơn vị ký:</span> <span class="text-light fw-semibold text-end ms-2">${sig.sig_subject || 'Chưa rõ'}</span></div>
                        <div class="d-flex justify-content-between align-items-center"><span class="text-secondary-accent">Nhà cấp CA:</span> <div class="d-flex align-items-center">${sig.sig_issuer || 'Chưa rõ'} ${caBadgeHtml}</div></div>
                        <div class="d-flex justify-content-between"><span class="text-secondary-accent">Mã số thuế ký:</span> <span class="badge bg-secondary text-end">${sig.sig_mst || 'Chưa rõ'}</span></div>
                        <div class="d-flex justify-content-between align-items-center"><span class="text-secondary-accent">Khớp danh tính:</span> <span>${nameMatchBadgeHtml}</span></div>
                        <div class="d-flex justify-content-between"><span class="text-secondary-accent">Thời hạn CA:</span> <span class="text-light text-end ms-2">${sig.sig_valid_from} đến ${sig.sig_valid_to}</span></div>
                    </div>
                `;

                if (sig.sig_error) {
                    const alertClass = sig.sig_verified ? 'alert-warning border-warning' : 'alert-danger border-danger';
                    const textColor = sig.sig_verified ? '#f59e0b' : '#ef4444';
                    sigHtml += `
                        <div class="alert ${alertClass} p-2 mt-2 mb-0 d-flex align-items-start gap-1" style="font-size: 0.75rem; color: ${textColor}; background-color: rgba(255,255,255,0.02); border-opacity: 0.25;">
                            <i class="bi bi-info-circle-fill mt-0.5"></i>
                            <span>${sig.sig_error}</span>
                        </div>
                    `;
                }

                sigContent.innerHTML = sigHtml;
            } else {
                sigBox.style.display = "none";
            }
        }

        // Populate AI Compliance warning logs inside drawer
        const aiAuditBox = document.getElementById("detAiAuditBox");
        const aiAuditContent = document.getElementById("detAiAuditContent");
        const btnRunAiAudit = document.getElementById("btnRunAiAudit");

        // Make button/trigger only visible if the invoice exists in local db
        if (btnRunAiAudit) {
            btnRunAiAudit.style.display = isLocal ? "inline-block" : "none";
        }

        if (aiAuditBox && aiAuditContent) {
            if (details.ai_warnings && details.ai_warnings.length > 0) {
                aiAuditContent.innerHTML = `
                    <div class="alert alert-danger d-flex flex-column gap-2 mb-0 border border-danger border-opacity-25" style="background-color: rgba(239, 68, 68, 0.08); color: #f87171;">
                        <div class="d-flex align-items-start gap-2">
                            <i class="bi bi-robot mt-1 text-danger"></i>
                            <div>
                                <strong class="d-block mb-1" style="color: #f87171 !important;">Trợ lý AI phát hiện rủi ro (${details.ai_warnings.length}):</strong>
                                <ul class="mb-0 ps-3 small text-secondary">
                                    ${details.ai_warnings.map(w => `<li>${w.explanation}</li>`).join("")}
                                </ul>
                            </div>
                        </div>
                    </div>
                `;
            } else if (details.ai_audited) {
                aiAuditContent.innerHTML = `
                    <div class="alert alert-success d-flex align-items-start gap-2 mb-0 border border-success border-opacity-25" style="background-color: rgba(16, 185, 129, 0.08); color: var(--primary-accent);">
                        <i class="bi bi-robot mt-1 text-success"></i>
                        <div>
                            <strong class="d-block mb-1 text-success-emphasis">Hoàn toàn hợp lệ</strong>
                            <span class="small text-secondary">Không phát hiện rủi ro chi tiêu cá nhân hoặc đơn giá bất thường đối với bất kỳ mặt hàng nào.</span>
                        </div>
                    </div>
                `;
            } else {
                aiAuditContent.innerHTML = `
                    <div class="text-secondary small text-center py-2" id="detAiAuditStatusText">
                        Chưa chạy phân tích kiểm toán AI cho hóa đơn này.
                    </div>
                `;
            }
        }

        // Display bootstrap offcanvas
        const drawerElement = document.getElementById("invoiceDetailsDrawer");
        const bsOffcanvas = new bootstrap.Offcanvas(drawerElement);
        bsOffcanvas.show();

    } catch (error) {
        renderAlert(error.message, "danger");
    }
}

async function handleManualAiAudit() {
    const activeId = document.getElementById("detId").textContent;
    if (!activeId || activeId === "-") return;

    const btn = document.getElementById("btnRunAiAudit");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang chạy...';

    try {
        const result = await apiCall(`/api/invoices/local/${activeId}/ai-audit`, {
            method: "POST"
        });
        
        // Refresh details view
        await showInvoiceDetails(activeId);
        renderAlert(result.message || "Đã hoàn thành kiểm toán AI thành công.", "success");
    } catch (error) {
        renderAlert(`Kiểm toán AI thất bại: ${error.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}


async function handleManualAiRepair() {
    const activeId = document.getElementById("detId").textContent;
    if (!activeId || activeId === "-") return;

    const btn = document.getElementById("btnRunAiRepair");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang xử lý...';

    try {
        const res = await apiCall(`/api/ai/repair-metadata`, {
            method: "POST",
            body: JSON.stringify({ invoice_id: activeId })
        });
        
        const diffContainer = document.getElementById("detAiRepairDiffContainer");
        if (!diffContainer) return;
        diffContainer.innerHTML = "";

        const before = res.before;
        const after = res.after;
        const differences = res.differences;

        const fieldNames = {
            "seller_name": "Tên người bán",
            "buyer_name": "Tên người mua",
            "buyer_address": "Địa chỉ người mua",
            "amount_in_words": "Số tiền bằng chữ"
        };

        const applyBtn = document.getElementById("btnApplyAiRepair");

        if (!differences || differences.length === 0) {
            diffContainer.innerHTML = `
                <div class="text-success small d-flex align-items-center gap-2 py-1">
                    <i class="bi bi-check-circle-fill fs-6"></i>
                    <span>Dữ liệu hóa đơn này hiện đã hoàn thiện và tối ưu nhất!</span>
                </div>
            `;
            if (applyBtn) applyBtn.style.display = "none";
        } else {
            if (applyBtn) {
                applyBtn.style.display = "inline-block";
                applyBtn.setAttribute("data-invoice-id", activeId);
                applyBtn.setAttribute("data-suggestions", JSON.stringify(after));
                applyBtn.setAttribute("data-differences", JSON.stringify(differences));
            }

            differences.forEach(field => {
                const itemDiv = document.createElement("div");
                itemDiv.className = "mb-2 p-2 rounded border border-secondary border-opacity-10";
                itemDiv.style.background = "rgba(255, 255, 255, 0.02)";
                itemDiv.innerHTML = `
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <span class="fw-bold text-light" style="font-size: 0.8rem;">${fieldNames[field]}</span>
                        <span class="badge text-bg-warning px-2 py-0.5" style="font-size: 0.6rem; background-color: rgba(245, 158, 11, 0.15) !important; color: #fbbf24 !important; border: 1px solid rgba(245, 158, 11, 0.25);">Đề xuất</span>
                    </div>
                    <div class="text-decoration-line-through text-secondary small py-0.5" style="font-size: 0.75rem; opacity: 0.5;">${before[field] || "(trống)"}</div>
                    <div class="text-success small fw-semibold py-0.5" style="font-size: 0.75rem;"><i class="bi bi-arrow-right-short"></i> ${after[field]}</div>
                `;
                diffContainer.appendChild(itemDiv);
            });
        }

        document.getElementById("detAiRepairStatusPlaceholder")?.classList.add("d-none");
        document.getElementById("detAiRepairContent")?.classList.remove("d-none");

    } catch (error) {
        renderAlert(`Đề xuất sửa lỗi AI thất bại: ${error.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function handleCancelAiRepair() {
    document.getElementById("detAiRepairContent")?.classList.add("d-none");
    document.getElementById("detAiRepairStatusPlaceholder")?.classList.remove("d-none");
}

async function handleApplyAiRepair() {
    const applyBtn = document.getElementById("btnApplyAiRepair");
    if (!applyBtn) return;

    const invoiceId = applyBtn.getAttribute("data-invoice-id");
    const suggestions = JSON.parse(applyBtn.getAttribute("data-suggestions") || "{}");
    const differences = JSON.parse(applyBtn.getAttribute("data-differences") || "[]");

    if (!invoiceId || differences.length === 0) return;

    const originalText = applyBtn.innerHTML;
    applyBtn.disabled = true;
    applyBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

    try {
        const bodyPayload = {
            invoice_id: invoiceId,
            fields: differences
        };
        differences.forEach(field => {
            bodyPayload[field] = suggestions[field];
        });

        const res = await apiCall(`/api/ai/apply-repair`, {
            method: "POST",
            body: JSON.stringify(bodyPayload)
        });

        document.getElementById("detAiRepairContent")?.classList.add("d-none");
        document.getElementById("detAiRepairStatusPlaceholder")?.classList.remove("d-none");

        await showInvoiceDetails(invoiceId);
        if (typeof loadLocalInvoices === "function") {
            await loadLocalInvoices();
        }

        renderAlert("Đã áp dụng các tối ưu hóa dữ liệu của AI thành công!", "success");

    } catch (error) {
        renderAlert(`Áp dụng sửa lỗi AI thất bại: ${error.message}`, "danger");
    } finally {
        applyBtn.disabled = false;
        applyBtn.innerHTML = originalText;
    }
}



// 9.1 Open Premium Interactive Invoice Viewer Modal
async function openInvoiceViewer(invoiceId) {
    if (!invoiceId) return;

    const labelEl = document.getElementById("viewerModalLabel");
    const badgeEl = document.getElementById("viewerStatusBadge");
    const metaEl = document.getElementById("viewerInvoiceMetaInfo");
    const iframe = document.getElementById("invoiceViewerIframe");
    const loader = document.getElementById("viewerLoadingOverlay");

    const modalEl = document.getElementById("invoiceViewerModal");
    const viewerModal = bootstrap.Modal.getOrCreateInstance(modalEl);

    let invoiceNumber = invoiceId;
    let invoiceDate = "";
    let issuerName = "";
    let isValid = true;

    // Try to locate row metadata in the DOM
    const row = document.querySelector(`tr[data-id="${invoiceId}"]`);
    if (row) {
        const isLocal = row.closest("#localInvoicesTableBody") !== null;
        if (isLocal) {
            invoiceNumber = row.children[0].textContent.trim();
            invoiceDate = row.children[1].textContent.trim();
            const sellerEl = row.children[2].querySelector(".fw-semibold");
            issuerName = sellerEl ? sellerEl.textContent.trim() : "";
            const statusHtml = row.children[7].innerHTML;
            isValid = statusHtml.includes("Hợp lệ");
        } else {
            invoiceNumber = row.children[0].textContent.trim();
            invoiceDate = row.children[1].textContent.trim();
            const statusHtml = row.children[3].innerHTML;
            isValid = !statusHtml.includes("Đã Hủy");
            issuerName = row.children[4].textContent.trim();
        }
    } else {
        // Fallback to drawer elements if drawer is loaded with this invoice
        const detIdVal = document.getElementById("detId")?.textContent || "";
        if (detIdVal === invoiceId) {
            invoiceNumber = detIdVal;
            invoiceDate = document.getElementById("detDate")?.textContent || "";
            issuerName = document.getElementById("detIssuer")?.textContent || "";
            const statusHtml = document.getElementById("detStatus")?.innerHTML || "";
            isValid = statusHtml.includes("Hợp lệ");
        }
    }

    if (labelEl) {
        labelEl.textContent = `Hóa Đơn Số: ${invoiceNumber}`;
    }

    if (badgeEl) {
        if (isValid) {
            badgeEl.className = "badge-audit-ok";
            badgeEl.innerHTML = '<i class="bi bi-check-circle"></i> Hợp lệ';
        } else {
            badgeEl.className = "badge-audit-error";
            badgeEl.innerHTML = '<i class="bi bi-x-circle"></i> Đã Hủy';
        }
    }

    if (metaEl) {
        let metaText = `Ngày HĐ: ${invoiceDate}`;
        if (issuerName) {
            metaText += ` | Đối tác: ${issuerName}`;
        }
        metaEl.textContent = metaText;
    }

    // Bind action toolbar buttons
    const downloadXmlBtn = document.getElementById("btnViewerDownloadXml");
    const downloadPdfBtn = document.getElementById("btnViewerDownloadPdf");
    const printBtn = document.getElementById("btnViewerPrint");
    const newTabBtn = document.getElementById("btnViewerNewTab");

    if (downloadXmlBtn) {
        downloadXmlBtn.onclick = () => {
            window.location.href = `/api/invoices/${invoiceId}/download`;
        };
    }

    if (downloadPdfBtn) {
        downloadPdfBtn.onclick = () => {
            window.location.href = `/api/invoices/${invoiceId}/pdf`;
        };
    }

    if (printBtn) {
        printBtn.onclick = () => {
            if (iframe && iframe.contentWindow) {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            }
        };
    }

    if (newTabBtn) {
        newTabBtn.onclick = () => {
            window.open(`/api/invoices/${invoiceId}/pdf-view`, "_blank");
        };
    }

    const mitigationLetterBtn = document.getElementById("btnViewerMitigationLetter");
    if (mitigationLetterBtn) {
        mitigationLetterBtn.onclick = async () => {
            viewerModal.hide();

            const mitigationModalEl = document.getElementById("mitigationLetterModal");
            const mitigationModal = bootstrap.Modal.getOrCreateInstance(mitigationModalEl);
            mitigationModalEl.dataset.invoiceId = invoiceId;
            
            const loader = document.getElementById("mitigationLoadingOverlay");
            const contentPanel = document.getElementById("mitigationContentPanel");
            const textarea = document.getElementById("mitigationLetterTextarea");
            
            loader.classList.remove("d-none");
            contentPanel.classList.add("d-none");
            textarea.value = "";
            
            mitigationModal.show();
            
            try {
                const response = await fetch(`/api/invoices/local/${invoiceId}/mitigation-letter`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                if (data.status === "success") {
                    textarea.value = data.letter;
                    loader.classList.add("d-none");
                    contentPanel.classList.remove("d-none");
                } else {
                    alert(`Lỗi tạo giải trình: ${data.error || 'Không xác định'}`);
                    mitigationModal.hide();
                    viewerModal.show();
                }
            } catch (err) {
                alert(`Lỗi kết nối máy chủ: ${err.message}`);
                mitigationModal.hide();
                viewerModal.show();
            }
        };
    }

    // Set iframe src and transitions
    if (iframe) {
        iframe.classList.add("opacity-0");
        iframe.classList.remove("opacity-100");

        iframe.onload = () => {
            if (loader) {
                loader.style.opacity = "0";
                setTimeout(() => {
                    loader.classList.add("d-none");
                }, 300);
            }
            iframe.classList.remove("opacity-0");
            iframe.classList.add("opacity-100");
        };

        if (loader) {
            loader.classList.remove("d-none");
            loader.style.opacity = "1";
        }

        iframe.src = `/api/invoices/${invoiceId}/pdf-view`;
    }

    viewerModal.show();
}


async function exportMitigationLetter(invoiceId, letterText, format) {
    try {
        const response = await fetch(`/api/invoices/local/${invoiceId}/mitigation-letter/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ letter: letterText, format: format })
        });
        
        if (!response.ok) {
            const errData = await response.json();
            alert(`Lỗi xuất bản: ${errData.error || 'Không xác định'}`);
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Giai_trinh_hoa_don_${invoiceId}.${format === 'pdf' ? 'pdf' : 'doc'}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert(`Lỗi khi tải tệp xuống: ${err.message}`);
    }
}


// 10. Search Trigger
async function handleInvoiceSearch(event) {
    if (event) event.preventDefault();
    const from = document.getElementById("dateFrom").value;
    const to = document.getElementById("dateTo").value;
    const cancelledOnly = document.getElementById("cancelledOnly").checked;
    const direction = document.getElementById("invoiceDirection").value;

    try {
        const data = await apiCall(`/api/invoices?from=${from}&to=${to}&cancelled_only=${cancelledOnly}&direction=${direction}`);
        const body = document.getElementById("invoiceTableBody");
        const count = document.getElementById("resultsCount");

        count.textContent = `Tổng cộng: ${data.total_count} hóa đơn`;
        if (!data.invoices.length) {
            body.innerHTML = '<tr><td colspan="7" class="text-center text-secondary py-5"><div class="empty-state"><span class="empty-icon"><i class="bi bi-folder2-open"></i></span><p class="mb-0">Không tìm thấy hóa đơn nào trong khoảng thời gian này.</p></div></td></tr>';
            return;
        }

        body.innerHTML = data.invoices.map(buildInvoiceRow).join("");

        // Double-click row handler binding
        const rows = body.querySelectorAll("tr");
        rows.forEach(row => {
            row.addEventListener("dblclick", () => {
                const id = row.getAttribute("data-id");
                openInvoiceViewer(id);
            });
        });

        // Parallel stats dashboard update
        await updateDashboardStats(from, to, direction);

        // Auto reload partner and report data if they are active or rendered
        if (document.getElementById("partners-content").classList.contains("show")) {
            await loadPartnersData();
        } else {
            const pbody = document.getElementById("partnersTableBody");
            if (pbody) {
                loadPartnersData();
            }
        }

        if (document.getElementById("reports-content").classList.contains("show")) {
            await loadReportsData();
        } else {
            const rbody = document.getElementById("reportsTableBody");
            if (rbody) {
                loadReportsData();
            }
        }

    } catch (error) {
        renderAlert(error.message, "danger");
    }
}

// 11. Excel Export Request
function handleExportClick() {
    const from = document.getElementById("dateFrom").value;
    const to = document.getElementById("dateTo").value;
    const cancelledOnly = document.getElementById("cancelledOnly").checked;
    const direction = document.getElementById("invoiceDirection").value;

    if (!from || !to) {
        renderAlert("Bạn cần chọn từ ngày và đến ngày trước khi xuất Excel.", "warning");
        return;
    }

    window.location.href = `/api/export-excel?from=${from}&to=${to}&cancelled_only=${cancelledOnly}&direction=${direction}`;
}

// 12. Terminate session
async function handleLogoutClick() {
    await apiCall("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
}

// 13. Auto session expiration warning
async function checkSessionStatus() {
    if (window.location.pathname === "/login") {
        return;
    }
    try {
        const data = await apiCall("/api/session-status");
        if (!data || !data.logged_in) {
            return;
        }
        if (data.expires_in <= data.warning_threshold_seconds && !sessionWarningShown) {
            renderAlert("Phiên làm việc sắp hết hạn trong 1 phút.", "warning");
            sessionWarningShown = true;
        }
    } catch (_error) {
        return;
    }
}


// 14. Theme Switcher Trigger
function initializeThemeSwitcher() {
    const themeBtn = document.getElementById("themeSwitcher");
    if (!themeBtn) return;

    themeBtn.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        
        document.documentElement.setAttribute("data-theme", newTheme);
        localStorage.setItem("theme", newTheme);
    });
}

// Filter GDT invoices by partner name (issuer)
function filterInvoicesByPartnerName(partnerName) {
    // 1. Switch to Invoices tab
    const invoicesTab = document.getElementById("invoices-tab");
    if (invoicesTab) {
        bootstrap.Tab.getOrCreateInstance(invoicesTab).show();
    }

    // 2. Loop through GDT invoices rows in the table
    const rows = document.querySelectorAll("#invoiceTableBody tr");
    let visibleCount = 0;
    rows.forEach(row => {
        if (row.classList.contains("empty-state")) return;
        const issuerCell = row.children[4];
        if (issuerCell) {
            const match = issuerCell.textContent.trim().toLowerCase() === partnerName.trim().toLowerCase();
            row.style.display = match ? "" : "none";
            if (match) visibleCount++;
        }
    });

    // Update resultsCount text with a red reset link
    const resultsCount = document.getElementById("resultsCount");
    if (resultsCount) {
        resultsCount.innerHTML = `Đang lọc: ${visibleCount} hóa đơn của "${partnerName}" <button class="btn btn-sm btn-link text-decoration-none p-0 ms-2 text-danger fw-semibold align-baseline" style="font-size: 0.85em;" onclick="resetInvoiceFilter(event)">[Xóa lọc]</button>`;
    }
}

function resetInvoiceFilter(event) {
    if (event) event.preventDefault();
    const rows = document.querySelectorAll("#invoiceTableBody tr");
    rows.forEach(row => {
        row.style.display = "";
    });
    // Restore resultsCount text
    const resultsCount = document.getElementById("resultsCount");
    if (resultsCount) {
        const total = Array.from(rows).filter(r => !r.classList.contains("empty-state")).length;
        resultsCount.textContent = `Tổng cộng: ${total} hóa đơn`;
    }
}

function getMstStatusBadge(status) {
    if (!status) {
        return '<span class="badge bg-secondary-subtle text-secondary">Chưa xác định</span>';
    }
    const lower = status.toLowerCase();
    if (lower.includes("đang hoạt động")) {
        return '<span class="badge bg-success-subtle text-success d-inline-flex align-items-center gap-1"><i class="bi bi-check-circle-fill"></i> Hoạt động</span>';
    } else if (lower.includes("tạm ngừng")) {
        return '<span class="badge bg-warning-subtle text-warning d-inline-flex align-items-center gap-1"><i class="bi bi-exclamation-triangle-fill"></i> Tạm ngừng</span>';
    } else if (lower.includes("ngừng hoạt động") || lower.includes("đã đóng")) {
        return '<span class="badge bg-danger-subtle text-danger d-inline-flex align-items-center gap-1"><i class="bi bi-x-circle-fill"></i> Đã đóng MST</span>';
    } else if (lower.includes("không tồn tại")) {
        return '<span class="badge bg-danger-subtle text-danger d-inline-flex align-items-center gap-1"><i class="bi bi-question-circle-fill"></i> Không tồn tại</span>';
    } else {
        return `<span class="badge bg-secondary-subtle text-secondary">${status}</span>`;
    }
}

async function verifyMstLive(button, mst) {
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

    try {
        const result = await apiCall(`/api/partners/${mst}/status`);
        if (result && result.status) {
            const row = button.closest("tr");
            if (row) {
                const statusCell = row.querySelector(".partner-status-cell");
                if (statusCell) {
                    statusCell.innerHTML = getMstStatusBadge(result.status);
                }
            }
            renderAlert(`Đã tra cứu thành công MST ${mst}. Trạng thái: ${result.status}`, "success");
        } else {
            throw new Error("Không thể xác minh trạng thái.");
        }
    } catch (error) {
        renderAlert(`Tra cứu MST ${mst} thất bại: ${error.message}`, "danger");
    } finally {
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

// meInvoice-inspired: Load Partners dynamically
async function loadPartnersData() {
    const from = document.getElementById("dateFrom")?.value || "2026-05-01";
    const to = document.getElementById("dateTo")?.value || "2026-05-20";
    const direction = document.getElementById("invoiceDirection")?.value || "purchase";

    const tbody = document.getElementById("partnersTableBody");
    const countBadge = document.getElementById("partnersCount");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary" role="status"></div> Đang tải dữ liệu đối tác...</td></tr>';

    try {
        const data = await apiCall(`/api/partners?from=${from}&to=${to}&direction=${direction}`);
        if (!data || !data.partners || data.partners.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-secondary py-4"><i class="bi bi-folder2-open"></i> Không trích xuất được đối tác nào trong dải ngày này.</td></tr>';
            if (countBadge) countBadge.textContent = "Tổng cộng: 0 đối tác";
            return;
        }

        if (countBadge) countBadge.textContent = `Tổng cộng: ${data.partners.length} đối tác`;

        tbody.innerHTML = data.partners.map(p => {
            const statusBadge = getMstStatusBadge(p.mst_status);
            return `
                <tr>
                    <td class="fw-bold text-dark">${p.name}</td>
                    <td class="fw-semibold text-primary partner-mst-link" style="letter-spacing: 0.05em; cursor: pointer; text-decoration: underline;" onclick="filterInvoicesByPartnerName('${p.name}')">${p.mst}</td>
                    <td class="partner-status-cell">${statusBadge}</td>
                    <td>${p.address}</td>
                    <td class="text-center fw-medium">${p.transaction_count}</td>
                    <td class="text-end fw-bold text-primary-accent">${Number(p.total_spend).toLocaleString("vi-VN")} ₫</td>
                    <td class="text-center">
                        <button class="btn btn-sm btn-outline-primary px-2 py-1" onclick="verifyMstLive(this, '${p.mst}')">
                            <i class="bi bi-search"></i> Tra cứu live
                        </button>
                    </td>
                </tr>
            `;
        }).join("");
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">Lỗi: ${error.message}</td></tr>`;
    }
}


// meInvoice-inspired: Load aggregated monthly/quarterly summary by seller
async function loadPartnersSummary() {
    const periodType = document.getElementById("summaryPeriodType")?.value || "monthly";
    const year = document.getElementById("summaryYear")?.value || "2026";
    const accordion = document.getElementById("partnersSummaryAccordion");
    
    if (!accordion) return;
    
    accordion.innerHTML = `
        <div class="text-center py-5 glass-card">
            <div class="spinner-border spinner-border-sm text-primary-accent" role="status"></div>
            <p class="mb-0 mt-2 text-secondary small">Đang lập bảng kê tổng hợp đầu vào theo ${periodType === "monthly" ? "Tháng" : "Quý"}...</p>
        </div>
    `;

    try {
        const res = await apiCall(`/api/invoices/summary-by-seller?period_type=${periodType}&year=${year}`);
        if (!res || !res.success || !res.data || res.data.length === 0) {
            accordion.innerHTML = `
                <div class="text-center py-5 glass-card">
                    <div class="empty-state">
                        <span class="empty-icon"><i class="bi bi-calendar-x"></i></span>
                        <p class="mb-0 text-secondary">Không có hóa đơn đầu vào nào được ghi nhận cho kỳ này.</p>
                    </div>
                </div>
            `;
            return;
        }

        let accordionHtml = "";
        res.data.forEach((item, index) => {
            const periodId = `period_${periodType}_${index}`;
            const headerId = `heading_${periodId}`;
            const collapseId = `collapse_${periodId}`;
            const showClass = index === 0 ? "show" : "";
            const buttonCollapsedClass = index === 0 ? "" : "collapsed";

            // Aggregate totals for the period
            const totalBeforeTaxStr = Number(item.total_before_tax).toLocaleString("vi-VN") + " ₫";
            const totalTaxStr = Number(item.total_tax).toLocaleString("vi-VN") + " ₫";
            const totalAmountStr = Number(item.total_amount).toLocaleString("vi-VN") + " ₫";

            let sellersTableRows = "";
            item.sellers.forEach(s => {
                sellersTableRows += `
                    <tr>
                        <td class="fw-bold text-dark text-nowrap">${s.seller_name}</td>
                        <td class="font-monospace text-secondary text-nowrap" style="letter-spacing: 0.05em;">${s.seller_mst}</td>
                        <td class="text-center fw-medium text-nowrap">${s.invoice_count} HĐ</td>
                        <td class="text-end text-nowrap">${Number(s.total_before_tax).toLocaleString("vi-VN")} ₫</td>
                        <td class="text-end text-nowrap text-secondary">${Number(s.total_tax).toLocaleString("vi-VN")} ₫</td>
                        <td class="text-end text-nowrap fw-bold text-primary-accent">${Number(s.total_amount).toLocaleString("vi-VN")} ₫</td>
                    </tr>
                `;
            });

            accordionHtml += `
                <div class="accordion-item glass-card mb-3 overflow-hidden" style="border: 1px solid rgba(255, 255, 255, 0.08); background: rgba(30, 41, 59, 0.4); border-radius: 8px;">
                    <h2 class="accordion-header" id="${headerId}">
                        <button class="accordion-button ${buttonCollapsedClass} d-flex justify-content-between align-items-center w-100 py-3 px-4 text-white" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="${index === 0 ? 'true' : 'false'}" aria-controls="${collapseId}" style="background: transparent; border: none; box-shadow: none;">
                            <div class="d-flex flex-grow-1 align-items-center justify-content-between flex-wrap gap-2 me-3">
                                <div class="d-flex align-items-center gap-2">
                                    <span class="badge text-bg-custom py-1.5 px-3" style="font-size: 0.85rem; font-weight: 600; background: linear-gradient(135deg, var(--primary-accent), var(--secondary-accent)); color: #fff;">${item.period}</span>
                                    <span class="small text-white-50">(${item.sellers.length} người xuất HĐ)</span>
                                </div>
                                <div class="d-flex align-items-center gap-3 pe-3 text-end" style="font-size: 0.85rem;">
                                    <span class="text-white-50">Trước thuế: <strong class="text-white">${totalBeforeTaxStr}</strong></span>
                                    <span class="text-white-50">Thuế GTGT: <strong class="text-warning">${totalTaxStr}</strong></span>
                                    <span>Tổng: <strong class="text-primary-accent fw-bold">${totalAmountStr}</strong></span>
                                </div>
                            </div>
                        </button>
                    </h2>
                    <div id="${collapseId}" class="accordion-collapse collapse ${showClass}" aria-labelledby="${headerId}" data-bs-parent="#partnersSummaryAccordion">
                        <div class="accordion-body p-0 border-top" style="border-top-color: rgba(255, 255, 255, 0.08) !important;">
                            <div class="table-responsive">
                                <table class="table align-middle custom-table mb-0">
                                    <thead>
                                        <tr style="background: rgba(255, 255, 255, 0.02);">
                                            <th class="ps-4">Tên Người Xuất Hóa Đơn</th>
                                            <th>Mã Số Thuế</th>
                                            <th class="text-center">Số Lượng HĐ</th>
                                            <th class="text-end">Tiền Trước Thuế</th>
                                            <th class="text-end">Tiền Thuế GTGT</th>
                                            <th class="text-end pe-4">Tổng Cộng (₫)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${sellersTableRows}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        accordion.innerHTML = accordionHtml;

    } catch (error) {
        accordion.innerHTML = `
            <div class="alert alert-danger mx-3 my-3">
                <i class="bi bi-exclamation-triangle"></i> Lỗi lập bảng kê: ${error.message}
            </div>
        `;
    }
}


// meInvoice-inspired: Load Tax Usage reports dynamically
async function loadReportsData() {
    let from = "2026-05-01";
    let to = "2026-05-20";

    const periodSelect = document.getElementById("reportPeriod");
    if (periodSelect) {
        const val = periodSelect.value;
        if (val === "month-5") {
            from = "2026-05-01";
            to = "2026-05-20";
        } else if (val === "month-4") {
            from = "2026-04-01";
            to = "2026-04-30";
        } else if (val === "quarter-1") {
            from = "2026-01-01";
            to = "2026-03-31";
        } else if (val === "quarter-2") {
            from = "2026-04-01";
            to = "2026-05-20";
        }
    } else {
        from = document.getElementById("dateFrom")?.value || "2026-05-01";
        to = document.getElementById("dateTo")?.value || "2026-05-20";
    }

    const direction = document.getElementById("invoiceDirection")?.value || "sold"; 

    const tbody = document.getElementById("reportsTableBody");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary" role="status"></div> Đang xuất báo cáo thuế...</td></tr>';

    try {
        const data = await apiCall(`/api/reports/usage?from=${from}&to=${to}&direction=${direction}`);
        if (!data || !data.report || data.report.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-secondary py-4"><i class="bi bi-folder2-open"></i> Không có dải số hóa đơn sử dụng nào trong dải ngày này.</td></tr>';
            return;
        }

        tbody.innerHTML = data.report.map(r => {
            return `
                <tr>
                    <td class="fw-bold text-dark text-center">${r.symbol}</td>
                    <td class="text-center fw-medium">${r.start_number}</td>
                    <td class="text-center fw-medium">${r.end_number}</td>
                    <td class="text-center fw-semibold text-primary">${r.total_used}</td>
                    <td class="text-center text-success fw-semibold">${r.active_count}</td>
                    <td class="text-center text-danger fw-semibold">${r.cancelled_count}</td>
                    <td class="text-center text-secondary small">${r.cancelled_numbers}</td>
                </tr>
            `;
        }).join("");
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">Lỗi: ${error.message}</td></tr>`;
    }
}

// 15. DOM Content Loaded bootstrap
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("loginForm")?.addEventListener("submit", handleLoginSubmit);
    document.getElementById("refreshCaptchaButton")?.addEventListener("click", loadAuthCaptcha);
    document.getElementById("invoiceSearchForm")?.addEventListener("submit", handleInvoiceSearch);
    document.getElementById("exportExcelButton")?.addEventListener("click", handleExportClick);
    document.getElementById("globalLogoutButton")?.addEventListener("click", handleLogoutClick);

    // AI Mitigation Letter export listeners
    document.getElementById("btnExportMitigationDoc")?.addEventListener("click", () => {
        const modalEl = document.getElementById("mitigationLetterModal");
        const invoiceId = modalEl.dataset.invoiceId;
        const letterText = document.getElementById("mitigationLetterTextarea").value;
        if (!letterText) return alert("Nội dung giải trình trống.");
        exportMitigationLetter(invoiceId, letterText, "doc");
    });

    document.getElementById("btnExportMitigationPdf")?.addEventListener("click", () => {
        const modalEl = document.getElementById("mitigationLetterModal");
        const invoiceId = modalEl.dataset.invoiceId;
        const letterText = document.getElementById("mitigationLetterTextarea").value;
        if (!letterText) return alert("Nội dung giải trình trống.");
        exportMitigationLetter(invoiceId, letterText, "pdf");
    });

    // Tab bindings for meInvoice features
    const partnersTab = document.getElementById("partners-tab");
    partnersTab?.addEventListener("shown.bs.tab", () => {
        const viewModeSummary = document.getElementById("viewModeSummary");
        if (viewModeSummary && viewModeSummary.checked) {
            loadPartnersSummary();
        } else {
            loadPartnersData();
        }
    });

    // Toggle Partners View Modes (Cumulative vs Monthly/Quarterly Aggregated Summary)
    const viewModeAll = document.getElementById("viewModeAll");
    const viewModeSummary = document.getElementById("viewModeSummary");
    const summaryPeriodSelector = document.getElementById("summaryPeriodSelector");
    const partnersCumulativeContainer = document.getElementById("partnersCumulativeContainer");
    const partnersSummaryContainer = document.getElementById("partnersSummaryContainer");
    const btnDownloadPartnersPdf = document.getElementById("btnDownloadPartnersPdf");
    const partnersTitleText = document.getElementById("partnersTitleText");

    const togglePartnerViews = () => {
        if (viewModeAll?.checked) {
            if (partnersCumulativeContainer) partnersCumulativeContainer.style.setProperty("display", "block", "important");
            if (partnersSummaryContainer) partnersSummaryContainer.style.setProperty("display", "none", "important");
            if (summaryPeriodSelector) summaryPeriodSelector.style.setProperty("display", "none", "important");
            if (btnDownloadPartnersPdf) btnDownloadPartnersPdf.style.setProperty("display", "block", "important");
            if (partnersTitleText) partnersTitleText.textContent = "Danh Bạ Đối Tác (Mua vào / Bán ra)";
            loadPartnersData();
        } else if (viewModeSummary?.checked) {
            if (partnersCumulativeContainer) partnersCumulativeContainer.style.setProperty("display", "none", "important");
            if (partnersSummaryContainer) partnersSummaryContainer.style.setProperty("display", "block", "important");
            if (summaryPeriodSelector) summaryPeriodSelector.style.setProperty("display", "flex", "important");
            if (btnDownloadPartnersPdf) btnDownloadPartnersPdf.style.setProperty("display", "none", "important");
            if (partnersTitleText) partnersTitleText.textContent = "Bảng Kê Tổng Hợp Hóa Đơn Đầu Vào";
            loadPartnersSummary();
        }
    };

    viewModeAll?.addEventListener("change", togglePartnerViews);
    viewModeSummary?.addEventListener("change", togglePartnerViews);
    document.getElementById("summaryPeriodType")?.addEventListener("change", loadPartnersSummary);
    document.getElementById("summaryYear")?.addEventListener("change", loadPartnersSummary);


    const reportsTab = document.getElementById("reports-tab");
    reportsTab?.addEventListener("shown.bs.tab", loadReportsData);

    const reportPeriodSelect = document.getElementById("reportPeriod");
    reportPeriodSelect?.addEventListener("change", loadReportsData);

    const meinvoiceTab = document.getElementById("meinvoice-tab");
    meinvoiceTab?.addEventListener("shown.bs.tab", loadLocalInvoices);

    // Bind meInvoice Batch Downloader
    const batchForm = document.getElementById("batchDownloadForm");
    batchForm?.addEventListener("submit", handleBatchDownloadSubmit);

    // Bind meInvoice Drag and Drop Zone
    initializeDragAndDrop();

    // Bind meInvoice Search Items Button
    document.getElementById("btnSearchItems")?.addEventListener("click", handleItemSearch);
    document.getElementById("itemSearchQuery")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") handleItemSearch();
    });

    // Bind meInvoice Clear Database Button
    document.getElementById("btnClearLocalDb")?.addEventListener("click", handleClearLocalDb);

    // Bind meInvoice Adjust Submit Button
    document.getElementById("btnSubmitAdjustInvoice")?.addEventListener("click", submitInvoiceAdjustment);

    // Bind AI Expense auto-classification triggers
    document.getElementById("btnRunAiClassification")?.addEventListener("click", runAiExpenseClassification);
    document.getElementById("btnSaveCategoryChange")?.addEventListener("click", submitManualCategoryChange);

    // Bind AI Metadata Repair triggers
    document.getElementById("btnRunAiRepair")?.addEventListener("click", handleManualAiRepair);
    document.getElementById("btnCancelAiRepair")?.addEventListener("click", handleCancelAiRepair);
    document.getElementById("btnApplyAiRepair")?.addEventListener("click", handleApplyAiRepair);

    // Delegation for dynamic line item editing
    document.getElementById("detLineItemsBody")?.addEventListener("click", (e) => {
        const btn = e.target.closest(".edit-category-btn");
        if (btn) {
            const itemId = btn.getAttribute("data-item-id");
            const itemName = btn.getAttribute("data-item-name");
            const currentCat = btn.getAttribute("data-category");

            document.getElementById("editCategoryItemId").value = itemId;
            document.getElementById("editCategoryItemName").textContent = itemName;
            document.getElementById("editCategorySelector").value = currentCat === "Chưa phân loại" ? "Văn phòng phẩm & Thiết bị văn phòng" : currentCat;

            const modalEl = document.getElementById("editCategoryModal");
            if (modalEl) {
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            }
        }
    });

    // Detail print drawer button
    document.getElementById("btnViewPrintInvoice")?.addEventListener("click", () => {
        const activeId = document.getElementById("detId").textContent;
        if (activeId && activeId !== "-") {
            openInvoiceViewer(activeId);
        }
    });

    // Partner list PDF download
    document.getElementById("btnDownloadPartnersPdf")?.addEventListener("click", () => {
        const from = document.getElementById("dateFrom")?.value || "2026-05-01";
        const to = document.getElementById("dateTo")?.value || "2026-05-20";
        const direction = document.getElementById("invoiceDirection")?.value || "purchase";
        window.location.href = `/api/reports/partners/pdf?from=${from}&to=${to}&direction=${direction}`;
    });

    // BC26 print/export PDF button
    document.getElementById("btnPrintReport")?.addEventListener("click", () => {
        let from = "2026-05-01";
        let to = "2026-05-20";

        const periodSelect = document.getElementById("reportPeriod");
        if (periodSelect) {
            const val = periodSelect.value;
            if (val === "month-5") {
                from = "2026-05-01";
                to = "2026-05-20";
            } else if (val === "month-4") {
                from = "2026-04-01";
                to = "2026-04-30";
            } else if (val === "quarter-1") {
                from = "2026-01-01";
                to = "2026-03-31";
            } else if (val === "quarter-2") {
                from = "2026-04-01";
                to = "2026-05-20";
            }
        } else {
            from = document.getElementById("dateFrom")?.value || "2026-05-01";
            to = document.getElementById("dateTo")?.value || "2026-05-20";
        }

        const direction = document.getElementById("invoiceDirection")?.value || "sold"; 
        window.location.href = `/api/reports/usage/pdf?from=${from}&to=${to}&direction=${direction}`;
    });

    const fromInput = document.getElementById("dateFrom");
    const toInput = document.getElementById("dateTo");
    if (fromInput && toInput) {
        fromInput.value = "2026-05-01";
        toInput.value = "2026-05-20";
    }

    loadAuthCaptcha();
    initializeThemeSwitcher();
    initializePasswordToggle();
    initializeLocalInvoicesFilters();
    if (window.location.pathname !== "/login") {
        checkUserRoleAndEnforce().then(() => {
            loadTaxpayerProfiles();
            initializeTaxpayerProfilesEvents();
            initializeFctEvents();
            initializeVatRefundEvents();
            initRealtimeSyncSSE();
        });
    }

    const settingsTab = document.getElementById("settings-tab");
    settingsTab?.addEventListener("shown.bs.tab", () => {
        loadSettingsData();
        loadTaxpayerProfiles();
    });
    document.getElementById("btnSaveSettings")?.addEventListener("click", handleSaveSettings);
    document.getElementById("btnTestEmail")?.addEventListener("click", handleTestEmail);
    document.getElementById("settingsScheduleInterval")?.addEventListener("change", toggleWeekdayVisibility);
    document.getElementById("settingsAiProvider")?.addEventListener("change", toggleAiProviderFields);
    document.getElementById("settingsTelegramEnabled")?.addEventListener("change", toggleTelegramFields);
    document.getElementById("btnTestAudit")?.addEventListener("click", handleTestAudit);
    document.getElementById("btnRunAiAudit")?.addEventListener("click", handleManualAiAudit);
    document.getElementById("btnTriggerRealtimeSync")?.addEventListener("click", handleTriggerRealtimeSync);
    document.getElementById("btnChatAboutInvoice")?.addEventListener("click", openInvoiceChat);
    initializeSettingsPasswordToggles();


    // Bind hidden event to clean up modal iframe cache
    document.getElementById("invoiceViewerModal")?.addEventListener("hidden.bs.modal", () => {
        const iframe = document.getElementById("invoiceViewerIframe");
        if (iframe) {
            iframe.src = "about:blank";
            iframe.classList.add("opacity-0");
            iframe.classList.remove("opacity-100");
        }
    });

    // Initialize VAT declaration tab
    initVatDeclarationTab();

    window.setInterval(checkSessionStatus, 30000);

    // Auto-trigger search on load to populate dashboard statistics and list
    if (document.getElementById("invoiceSearchForm")) {
        handleInvoiceSearch();
    }

    // Initialize Offline AI Chatbot Panel (Gemma-4)
    initAiChatbot();
});


// meInvoice Intelligence Workspace logic
let localInvoicesList = [];
let currentLocalSortColumn = "date";
let currentLocalSortDirection = "desc";

function updateSortHeaders() {
    const headers = document.querySelectorAll(".sortable-header");
    headers.forEach(th => {
        const col = th.getAttribute("data-sort");
        const icon = th.querySelector("i");
        if (!icon) return;

        if (col === currentLocalSortColumn) {
            if (currentLocalSortDirection === "asc") {
                icon.className = "bi bi-arrow-up text-primary";
            } else {
                icon.className = "bi bi-arrow-down text-primary";
            }
        } else {
            icon.className = "bi bi-arrow-down-up small ms-1 text-muted";
        }
    });
}

function filterAndRenderLocalInvoices() {
    const tbody = document.getElementById("localInvoicesTableBody");
    if (!tbody) return;

    const keyword = document.getElementById("localSearchKeyword")?.value.toLowerCase().trim() || "";
    const filterStatus = document.getElementById("localFilterStatus")?.value || "all";
    const dateFrom = document.getElementById("localFilterDateFrom")?.value || "";
    const dateTo = document.getElementById("localFilterDateTo")?.value || "";

    // 1. Filter
    let filtered = localInvoicesList.filter(inv => {
        if (keyword) {
            const num = (inv.number || "").toLowerCase();
            const sellerN = (inv.seller_name || "").toLowerCase();
            const sellerM = (inv.seller_mst || "").toLowerCase();
            const buyerN = (inv.buyer_name || "").toLowerCase();
            const buyerM = (inv.buyer_mst || "").toLowerCase();
            const id = (inv.id || "").toLowerCase();
            const match = num.includes(keyword) || sellerN.includes(keyword) || sellerM.includes(keyword) || buyerN.includes(keyword) || buyerM.includes(keyword) || id.includes(keyword);
            if (!match) return false;
        }

        if (filterStatus !== "all") {
            const warnings = inv.warnings || [];
            if (filterStatus === "valid" && !inv.is_valid) return false;
            if (filterStatus === "warning" && inv.is_valid) return false;
            if (filterStatus === "duplicate") {
                const hasDup = warnings.some(w => w.includes("tồn tại") || w.includes("Trùng"));
                if (!hasDup) return false;
            }
            if (filterStatus === "tax_mismatch") {
                const hasTax = warnings.some(w => w.includes("Chênh lệch") || w.includes("thuế suất"));
                if (!hasTax) return false;
            }
            if (filterStatus === "high_risk") {
                const hasRisk = warnings.some(w => w.includes("rủi ro") || w.includes("danh mục"));
                if (!hasRisk) return false;
            }
            if (filterStatus === "no_signature") {
                const hasSig = warnings.some(w => w.includes("chưa được ký số") || w.includes("ký số"));
                if (!hasSig) return false;
            }
        }

        if (dateFrom && inv.date < dateFrom) return false;
        if (dateTo && inv.date > dateTo) return false;

        return true;
    });

    // 2. Sort
    filtered.sort((a, b) => {
        let valA = a[currentLocalSortColumn];
        let valB = b[currentLocalSortColumn];

        if (valA === undefined || valA === null) valA = "";
        if (valB === undefined || valB === null) valB = "";

        if (typeof valA === "string") {
            valA = valA.toLowerCase();
            valB = String(valB).toLowerCase();
        }

        if (valA < valB) return currentLocalSortDirection === "asc" ? -1 : 1;
        if (valA > valB) return currentLocalSortDirection === "asc" ? 1 : -1;
        return 0;
    });

    // Update sort headers UI
    updateSortHeaders();

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-secondary py-5"><div class="empty-state"><span class="empty-icon"><i class="bi bi-search"></i></span><p class="mb-0">Không tìm thấy hóa đơn nào khớp với bộ lọc.</p></div></td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(inv => {
        const auditBadge = inv.is_valid
            ? '<span class="badge-audit-ok"><i class="bi bi-check-circle"></i> Hợp lệ</span>'
            : `<span class="badge-audit-error" title="${inv.warnings.join(', ')}"><i class="bi bi-exclamation-triangle"></i> Phát hiện lỗi (${inv.warnings.length})</span>`;

        return `
            <tr data-id="${inv.id}" style="cursor: pointer;">
                <td class="fw-bold text-primary">${inv.number}</td>
                <td>${inv.date}</td>
                <td>
                    <div class="fw-semibold text-dark">${inv.seller_name}</div>
                    <div class="text-secondary small" style="letter-spacing: 0.05em;">${inv.seller_mst}</div>
                </td>
                <td>
                    <div class="fw-semibold text-dark">${inv.buyer_name}</div>
                    <div class="text-secondary small" style="letter-spacing: 0.05em;">${inv.buyer_mst}</div>
                </td>
                <td class="text-end fw-semibold">${Number(inv.amount_before_tax).toLocaleString("vi-VN")} ₫</td>
                <td class="text-end text-secondary">${Number(inv.tax_amount).toLocaleString("vi-VN")} ₫</td>
                <td class="text-end fw-bold text-primary-accent">${Number(inv.total_amount).toLocaleString("vi-VN")} ₫</td>
                <td class="text-center">${auditBadge}</td>
                <td class="text-center">
                    <div class="d-flex justify-content-center gap-1">
                        <button class="btn btn-sm btn-outline-primary px-2" onclick="event.stopPropagation(); openInvoiceViewer('${inv.id}')" title="Xem chi tiết hóa đơn"><i class="bi bi-eye"></i></button>
                        ${window.currentUserRole === "viewer" ? "" : `
                            <button class="btn btn-sm btn-outline-warning px-2" onclick="event.stopPropagation(); openAdjustModal('${inv.id}')" title="Điều chỉnh hóa đơn"><i class="bi bi-pencil-square"></i></button>
                            <button class="btn btn-sm btn-outline-danger px-2" onclick="event.stopPropagation(); deleteLocalInvoice('${inv.id}')" title="Xóa hóa đơn"><i class="bi bi-trash"></i></button>
                        `}
                    </div>
                </td>
            </tr>
        `;
    }).join("");

    // Bind row click & double click
    const rows = tbody.querySelectorAll("tr");
    rows.forEach(row => {
        row.addEventListener("click", (e) => {
            if (e.target.closest("button") || e.target.closest("a")) return;
            const id = row.getAttribute("data-id");
            showInvoiceDetails(id);
        });
        row.addEventListener("dblclick", () => {
            const id = row.getAttribute("data-id");
            openInvoiceViewer(id);
        });
    });
}

async function loadLocalInvoices() {
    const tbody = document.getElementById("localInvoicesTableBody");
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary" role="status"></div> Đang tải kho dữ liệu cục bộ...</td></tr>';

    try {
        const data = await apiCall("/api/invoices/local");
        if (!data || !data.invoices || data.invoices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-secondary py-5"><div class="empty-state"><span class="empty-icon"><i class="bi bi-lightning-charge"></i></span><p class="mb-0">Kho dữ liệu trống. Hãy kéo thả XML hoặc Tải hàng loạt theo tháng để trích xuất.</p></div></td></tr>';
            // Reset auditing counts
            const ids = ["localActiveCount", "localDuplicateCount", "localTaxMismatchCount", "localHighRiskCount"];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = "0";
            });
            localInvoicesList = [];
            renderTScoreCharts([]);
            return;
        }

        localInvoicesList = data.invoices;

        // Calculate smart auditing metrics
        let activeCount = 0;
        let duplicateCount = 0;
        let taxMismatchCount = 0;
        let highRiskCount = 0;

        localInvoicesList.forEach(inv => {
            const warnings = inv.warnings || [];
            if (warnings.length === 0) {
                activeCount++;
            } else {
                let hasDuplicate = false;
                let hasTaxMismatch = false;
                let hasHighRisk = false;

                warnings.forEach(w => {
                    if (w.includes("tồn tại") || w.includes("Trùng")) {
                        hasDuplicate = true;
                    }
                    if (w.includes("Chênh lệch") || w.includes("thuế suất")) {
                        hasTaxMismatch = true;
                    }
                    if (w.includes("rủi ro") || w.includes("danh mục")) {
                        hasHighRisk = true;
                    }
                });

                if (hasDuplicate) duplicateCount++;
                if (hasTaxMismatch) taxMismatchCount++;
                if (hasHighRisk) highRiskCount++;
            }
        });

        // Update auditing metrics in DOM
        const localActiveEl = document.getElementById("localActiveCount");
        const localDuplicateEl = document.getElementById("localDuplicateCount");
        const localTaxEl = document.getElementById("localTaxMismatchCount");
        const localHighRiskEl = document.getElementById("localHighRiskCount");

        if (localActiveEl) animateNumber(localActiveEl, activeCount, false);
        if (localDuplicateEl) animateNumber(localDuplicateEl, duplicateCount, false);
        if (localTaxEl) animateNumber(localTaxEl, taxMismatchCount, false);
        if (localHighRiskEl) animateNumber(localHighRiskEl, highRiskCount, false);

        filterAndRenderLocalInvoices();
        renderTScoreCharts(localInvoicesList);

    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger py-4">Lỗi: ${error.message}</td></tr>`;
        const ids = ["localActiveCount", "localDuplicateCount", "localTaxMismatchCount", "localHighRiskCount"];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = "-";
        });
        renderTScoreCharts([]);
    }
}

function initializeLocalInvoicesFilters() {
    // Search Inputs & Selects
    document.getElementById("localSearchKeyword")?.addEventListener("input", filterAndRenderLocalInvoices);
    document.getElementById("localFilterStatus")?.addEventListener("change", filterAndRenderLocalInvoices);
    document.getElementById("localFilterDateFrom")?.addEventListener("change", filterAndRenderLocalInvoices);
    document.getElementById("localFilterDateTo")?.addEventListener("change", filterAndRenderLocalInvoices);

    // Clear filters
    document.getElementById("btnClearLocalFilters")?.addEventListener("click", () => {
        const kw = document.getElementById("localSearchKeyword");
        if (kw) kw.value = "";
        const st = document.getElementById("localFilterStatus");
        if (st) st.value = "all";
        const df = document.getElementById("localFilterDateFrom");
        if (df) df.value = "";
        const dt = document.getElementById("localFilterDateTo");
        if (dt) dt.value = "";
        filterAndRenderLocalInvoices();
    });

    // Excel Export
    document.getElementById("btnExportLocalExcel")?.addEventListener("click", () => {
        window.location.href = "/api/invoices/local/export-excel";
    });

    // Column headers sorting
    const headers = document.querySelectorAll(".sortable-header");
    headers.forEach(th => {
        th.addEventListener("click", () => {
            const col = th.getAttribute("data-sort");
            if (currentLocalSortColumn === col) {
                currentLocalSortDirection = currentLocalSortDirection === "asc" ? "desc" : "asc";
            } else {
                currentLocalSortColumn = col;
                currentLocalSortDirection = col === "date" || col === "total_amount" || col === "amount_before_tax" || col === "tax_amount" ? "desc" : "asc";
            }
            filterAndRenderLocalInvoices();
        });
    });
}
async function handleBatchDownloadSubmit(event) {
    event.preventDefault();
    const month = document.getElementById("batchMonth").value;
    const direction = document.getElementById("batchDirection").value;
    const duplicateStrategy = document.getElementById("batchDuplicateStrategy")?.value || "overwrite";
    const btn = document.getElementById("btnBatchDownload");

    if (!month) {
        renderAlert("Vui lòng chọn tháng cần tải.", "warning");
        return;
    }

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang xử lý...';

    // Show Progress Modal
    const modalEl = document.getElementById('downloadProgressModal');
    const progressBar = document.getElementById('downloadProgressBar');
    const progressText = document.getElementById('downloadProgressText');
    const progressCounter = document.getElementById('downloadProgressCounter');
    const progressPercent = document.getElementById('downloadProgressPercent');
    const progressError = document.getElementById('downloadProgressError');
    const progressErrorMessage = document.getElementById('downloadProgressErrorMessage');
    const closeBtn = document.getElementById('btnCloseProgressModal');

    // Reset Modal elements
    progressBar.style.width = '0%';
    progressBar.setAttribute('aria-valuenow', '0');
    progressText.textContent = 'Đang khởi tạo tiến trình tải từ Tổng Cục Thuế...';
    progressCounter.textContent = '0 / 0 hóa đơn';
    progressPercent.textContent = '0%';
    progressError.classList.add('d-none');
    closeBtn.classList.add('d-none');

    const progressModal = new bootstrap.Modal(modalEl);
    progressModal.show();

    let taskId = null;
    let pollInterval = null;

    try {
        const response = await fetch("/api/invoices/batch-download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ month, direction, duplicate_strategy: duplicateStrategy })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Không thể bắt đầu tiến trình tải.");
        }

        taskId = data.task_id;

        // Start polling
        pollInterval = setInterval(async () => {
            try {
                const statusRes = await fetch(`/api/invoices/batch-download/status/${taskId}`);
                if (!statusRes.ok) {
                    throw new Error("Lỗi kết nối kiểm tra tiến trình.");
                }
                const statusData = await statusRes.json();

                // Update UI progress
                const percent = statusData.progress || 0;
                progressBar.style.width = `${percent}%`;
                progressBar.setAttribute('aria-valuenow', percent);
                progressPercent.textContent = `${percent}%`;
                progressCounter.textContent = `${statusData.completed_count} / ${statusData.total} hóa đơn`;

                const imp = statusData.imported_count || 0;
                const ovr = statusData.overwritten_count || 0;
                const skp = statusData.skipped_count || 0;
                const fail = statusData.failed_count || 0;

                if (statusData.status === "running") {
                    progressText.textContent = `Đang tải: mới ${imp}, ghi đè ${ovr}, bỏ qua ${skp}, lỗi ${fail}...`;
                } else if (statusData.status === "completed") {
                    clearInterval(pollInterval);
                    progressText.textContent = `Hoàn thành tải hóa đơn (mới: ${imp}, ghi đè: ${ovr}, bỏ qua: ${skp}, lỗi: ${fail})! Bắt đầu tải file lưu trữ...`;

                    // Trigger actual file download
                    window.location.href = `/api/invoices/batch-download/download/${taskId}`;

                    setTimeout(() => {
                        progressModal.hide();
                        renderAlert(`Tải hàng loạt tháng ${month} thành công (mới: ${imp}, ghi đè: ${ovr}, bỏ qua: ${skp}, lỗi: ${fail}) và đã tự động lưu trữ vào kho.`, "success");
                        loadLocalInvoices();
                    }, 1000);
                } else if (statusData.status === "failed") {
                    clearInterval(pollInterval);
                    throw new Error(statusData.error || "Lỗi tiến trình tải hàng loạt.");
                }
            } catch (err) {
                clearInterval(pollInterval);
                progressText.textContent = "Không thể hoàn thành.";
                progressError.classList.remove('d-none');
                progressErrorMessage.textContent = err.message;
                closeBtn.classList.remove('d-none');
            }
        }, 1000);

    } catch (error) {
        if (pollInterval) clearInterval(pollInterval);
        progressText.textContent = "Không thể hoàn thành.";
        progressError.classList.remove('d-none');
        progressErrorMessage.textContent = error.message;
        closeBtn.classList.remove('d-none');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function initializeDragAndDrop() {
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");

    if (!dropZone || !fileInput) return;

    // Click triggers file selector
    dropZone.addEventListener("click", () => fileInput.click());

    // Highlight drop zone on dragover
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    ["dragleave", "dragend"].forEach(type => {
        dropZone.addEventListener(type, () => {
            dropZone.classList.remove("dragover");
        });
    });

    dropZone.addEventListener("drop", async (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            await uploadFiles(files);
        }
    });

    fileInput.addEventListener("change", async () => {
        const files = fileInput.files;
        if (files.length > 0) {
            await uploadFiles(files);
        }
    });
}

async function uploadFiles(files) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }
    const dupSelect = document.getElementById("uploadDuplicateStrategy");
    const duplicateStrategy = dupSelect ? dupSelect.value : "overwrite";
    formData.append("duplicate_strategy", duplicateStrategy);

    renderAlert("Đang trích xuất thông tin hóa đơn và chữ ký số...", "info");

    try {
        const response = await fetch("/api/invoices/upload", {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Tải lên hóa đơn thất bại.");
        }

        const msg = `Đã nhập thành công ${result.imported_count} hóa đơn (ghi đè: ${result.overwritten_count || 0}, bỏ qua: ${result.skipped_count || 0}) vào kho lưu trữ.`;

        if (result.errors && result.errors.length > 0) {
            renderAlert(`${msg} Phát hiện một số cảnh báo:\n${result.errors.join("\n")}`, "warning");
        } else {
            renderAlert(msg, "success");
        }

        await loadLocalInvoices();
    } catch (error) {
        renderAlert(error.message, "danger");
    }
}

async function handleItemSearch() {
    const query = document.getElementById("itemSearchQuery").value.trim();
    const wrapper = document.getElementById("itemSearchResultsWrapper");
    const tbody = document.getElementById("itemSearchResultsBody");

    if (!tbody) return;

    if (!query) {
        wrapper.style.display = "none";
        return;
    }

    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary" role="status"></div> Đang tìm kiếm sản phẩm...</td></tr>';
    wrapper.style.display = "block";

    try {
        const data = await apiCall(`/api/invoices/local/items?q=${encodeURIComponent(query)}`);
        if (!data || !data.items || data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-secondary py-3">Không tìm thấy sản phẩm hoặc mặt hàng nào khớp với từ khóa tìm kiếm.</td></tr>';
            return;
        }

        tbody.innerHTML = data.items.map(item => {
            return `
                <tr>
                    <td class="fw-bold text-dark">${item.item_name}</td>
                    <td class="text-center fw-medium">${item.quantity}</td>
                    <td class="text-end">${Number(item.unit_price).toLocaleString("vi-VN")} ₫</td>
                    <td class="text-center badge-tax">${item.tax_rate}</td>
                    <td class="text-end text-secondary">${Number(item.tax_amount).toLocaleString("vi-VN")} ₫</td>
                    <td class="text-end fw-semibold text-primary-accent">${Number(item.amount_before_tax + item.tax_amount).toLocaleString("vi-VN")} ₫</td>
                    <td class="fw-medium">${item.seller_name}</td>
                    <td>
                        <a href="/api/invoices/${item.invoice_id}/pdf-view" target="_blank" class="fw-bold text-primary">${item.invoice_number}</a>
                    </td>
                </tr>
            `;
        }).join("");
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-3">Lỗi: ${error.message}</td></tr>`;
    }
}

async function handleClearLocalDb() {
    if (!confirm("Bạn có chắc chắn muốn làm sạch toàn bộ kho dữ liệu hóa đơn cục bộ? Hành động này sẽ xóa toàn bộ XML đã lưu trữ.")) {
        return;
    }

    try {
        const result = await apiCall("/api/invoices/local/clear", { method: "DELETE" });
        renderAlert(result.message, "success");
        await loadLocalInvoices();
        
        // Hide item search results
        document.getElementById("itemSearchResultsWrapper").style.display = "none";
        document.getElementById("itemSearchQuery").value = "";
    } catch (error) {
        renderAlert(error.message, "danger");
    }
}


// Password visibility toggle
function initializePasswordToggle() {
    const toggleBtn = document.getElementById("togglePassword");
    const passwordInput = document.getElementById("password");
    const toggleIcon = document.getElementById("togglePasswordIcon");

    if (!toggleBtn || !passwordInput || !toggleIcon) return;

    toggleBtn.addEventListener("click", () => {
        const isPassword = passwordInput.type === "password";
        passwordInput.type = isPassword ? "text" : "password";
        toggleIcon.className = isPassword ? "bi bi-eye-slash" : "bi bi-eye";
    });
}

// meInvoice: delete local invoice
async function deleteLocalInvoice(invoiceId) {
    if (!confirm(`Bạn có chắc chắn muốn xóa hóa đơn số ${invoiceId} khỏi kho lưu trữ cục bộ? Hành động này không thể hoàn tác.`)) {
        return;
    }
    try {
        const result = await apiCall(`/api/invoices/local/${invoiceId}`, { method: "DELETE" });
        renderAlert(result.message, "success");
        await loadLocalInvoices();
    } catch (error) {
        renderAlert(`Lỗi khi xóa hóa đơn: ${error.message}`, "danger");
    }
}

// meInvoice: open adjust invoice modal
function openAdjustModal(invoiceId) {
    const inv = localInvoicesList.find(i => i.id === invoiceId);
    if (!inv) {
        renderAlert("Không tìm thấy thông tin hóa đơn.", "warning");
        return;
    }

    document.getElementById("adjustInvoiceId").value = inv.id;
    document.getElementById("adjustDate").value = inv.date;
    
    const statusSelect = document.getElementById("adjustInvoiceStatus");
    if (statusSelect) {
        statusSelect.value = inv.invoice_status || "Gốc";
    }

    document.getElementById("adjustSellerName").value = inv.seller_name || "";
    document.getElementById("adjustSellerMst").value = inv.seller_mst || "";
    document.getElementById("adjustBuyerName").value = inv.buyer_name || "";
    document.getElementById("adjustBuyerMst").value = inv.buyer_mst || "";
    
    document.getElementById("adjustAmountBeforeTax").value = inv.amount_before_tax || 0;
    document.getElementById("adjustTaxAmount").value = inv.tax_amount || 0;
    document.getElementById("adjustTotalAmount").value = inv.total_amount || 0;
    
    document.getElementById("adjustPaymentMethod").value = inv.payment_method || "";
    document.getElementById("adjustNotes").value = inv.notes || "";

    const modalEl = document.getElementById("adjustInvoiceModal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

// meInvoice: Run AI expense classification
async function runAiExpenseClassification(e) {
    const btn = e.currentTarget;
    const invoiceId = btn.getAttribute("data-id");
    if (!invoiceId) return;

    btn.disabled = true;
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;

    showToast("Đang gửi yêu cầu phân loại chi phí AI...", "info");

    try {
        const resp = await fetch("/api/ai/classify-items", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ invoice_id: invoiceId })
        });

        const data = await resp.json();
        if (data.success) {
            showToast("Đã tự động phân loại chi phí hoàn tất!", "success");
            // Reload the details in drawer
            await showInvoiceDetails(invoiceId);
        } else {
            showToast("Không thể phân loại: " + (data.error || "Lỗi không xác định"), "error");
        }
    } catch (err) {
        showToast("Lỗi kết nối phân loại chi phí: " + err, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// meInvoice: Save manual category override change
async function submitManualCategoryChange() {
    const itemId = document.getElementById("editCategoryItemId").value;
    const selectedCat = document.getElementById("editCategorySelector").value;
    if (!itemId || !selectedCat) return;

    const btn = document.getElementById("btnSaveCategoryChange");
    btn.disabled = true;
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...`;

    try {
        const resp = await fetch("/api/ai/update-item-category", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ item_id: itemId, category: selectedCat })
        });

        const data = await resp.json();
        if (data.success) {
            showToast("Đã cập nhật danh mục chi phí!", "success");
            
            // Close modal
            const modalEl = document.getElementById("editCategoryModal");
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            // Refresh the drawer view with the active invoice
            const activeId = document.getElementById("detId").textContent;
            if (activeId && activeId !== "-") {
                await showInvoiceDetails(activeId);
            }
        } else {
            showToast("Lỗi: " + (data.error || "Lỗi không xác định"), "error");
        }
    } catch (err) {
        showToast("Lỗi kết nối cập nhật danh mục: " + err, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// meInvoice: submit invoice adjustment
async function submitInvoiceAdjustment() {
    const invoiceId = document.getElementById("adjustInvoiceId").value;
    const payload = {
        date: document.getElementById("adjustDate").value,
        invoice_status: document.getElementById("adjustInvoiceStatus").value,
        seller_name: document.getElementById("adjustSellerName").value,
        seller_mst: document.getElementById("adjustSellerMst").value,
        buyer_name: document.getElementById("adjustBuyerName").value,
        buyer_mst: document.getElementById("adjustBuyerMst").value,
        amount_before_tax: Number(document.getElementById("adjustAmountBeforeTax").value),
        tax_amount: Number(document.getElementById("adjustTaxAmount").value),
        total_amount: Number(document.getElementById("adjustTotalAmount").value),
        payment_method: document.getElementById("adjustPaymentMethod").value,
        notes: document.getElementById("adjustNotes").value
    };

    const btn = document.getElementById("btnSubmitAdjustInvoice");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';

    try {
        const result = await apiCall(`/api/invoices/local/${invoiceId}`, {
            method: "PATCH",
            body: JSON.stringify(payload)
        });

        renderAlert(result.message, "success");
        
        const modalEl = document.getElementById("adjustInvoiceModal");
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.hide();

        await loadLocalInvoices();
    } catch (error) {
        renderAlert(`Lỗi khi điều chỉnh hóa đơn: ${error.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}


// Settings and Scheduler Management (US-024)
async function loadSettingsData() {
    try {
        const settings = await apiCall("/api/settings");

        document.getElementById("settingsSmtpHost").value = settings.smtp_host || "";
        document.getElementById("settingsSmtpPort").value = settings.smtp_port || 587;
        document.getElementById("settingsSmtpUser").value = settings.smtp_user || "";
        document.getElementById("settingsSmtpPass").value = settings.smtp_pass || "";
        document.getElementById("settingsSmtpUseTls").checked = settings.smtp_use_tls !== false;

        document.getElementById("settingsScheduleEnabled").checked = !!settings.schedule_enabled;
        document.getElementById("settingsRecipientEmail").value = settings.recipient_email || "";
        document.getElementById("settingsScheduleInterval").value = settings.schedule_interval || "daily";
        document.getElementById("settingsScheduleTime").value = settings.schedule_time || "08:00";
        document.getElementById("settingsScheduleWeekday").value = settings.schedule_weekday || 0;

        document.getElementById("settingsGdtUser").value = settings.gdt_username || "";
        document.getElementById("settingsGdtPass").value = settings.gdt_password || "";

        // AI configuration fields
        document.getElementById("settingsAiEnabled").checked = !!settings.ai_enabled;
        document.getElementById("settingsAiProvider").value = settings.ai_provider || "ollama";
        document.getElementById("settingsAiModelName").value = settings.ai_model_name || "gemma-4";
        document.getElementById("settingsAiOllamaEndpoint").value = settings.ai_ollama_endpoint || "http://localhost:11434";
        document.getElementById("settingsAiApiKey").value = settings.ai_api_key || "";
        document.getElementById("settingsAiSystemPrompt").value = settings.ai_system_prompt || "";

        // Telegram & Audit Agent configuration
        const auditAgentEl = document.getElementById("settingsAuditAgentEnabled");
        if (auditAgentEl) auditAgentEl.checked = !!settings.audit_agent_enabled;
        const auditTimeEl = document.getElementById("settingsAuditAgentScheduleTime");
        if (auditTimeEl) auditTimeEl.value = settings.audit_agent_schedule_time || "23:00";
        
        const teleEnabledEl = document.getElementById("settingsTelegramEnabled");
        if (teleEnabledEl) teleEnabledEl.checked = !!settings.telegram_enabled;
        const teleTokenEl = document.getElementById("settingsTelegramBotToken");
        if (teleTokenEl) teleTokenEl.value = settings.telegram_bot_token || "";
        const teleChatEl = document.getElementById("settingsTelegramChatId");
        if (teleChatEl) teleChatEl.value = settings.telegram_chat_id || "";

        const autoDunningEl = document.getElementById("settingsAutoDunningEnabled");
        if (autoDunningEl) autoDunningEl.checked = !!settings.auto_dunning_enabled;

        const signatureFilterEl = document.getElementById("settingsSignatureFilterEnabled");
        if (signatureFilterEl) signatureFilterEl.checked = settings.signature_filter_enabled !== false;
        
        const blacklistFilterEl = document.getElementById("settingsBlacklistFilterEnabled");
        if (blacklistFilterEl) blacklistFilterEl.checked = settings.blacklist_filter_enabled !== false;

        toggleWeekdayVisibility();
        toggleAiProviderFields();
        toggleTelegramFields();
        await loadSchedulerLogs();
    } catch (error) {
        renderAlert(`Lỗi tải thiết lập: ${error.message}`, "danger");
    }
}

function toggleWeekdayVisibility() {
    const interval = document.getElementById("settingsScheduleInterval").value;
    const wrapper = document.getElementById("weekdaySelectorWrapper");
    if (wrapper) {
        wrapper.style.display = interval === "weekly" ? "block" : "none";
    }
}

function toggleAiProviderFields() {
    const provider = document.getElementById("settingsAiProvider").value;
    const keyWrapper = document.getElementById("aiApiKeyWrapper");
    const endpointWrapper = document.getElementById("aiOllamaEndpointWrapper");
    
    if (provider === "ollama") {
        if (keyWrapper) keyWrapper.style.display = "none";
        if (endpointWrapper) endpointWrapper.style.display = "block";
    } else {
        if (keyWrapper) keyWrapper.style.display = "block";
        if (endpointWrapper) endpointWrapper.style.display = "none";
    }
}

async function loadSchedulerLogs() {
    const tbody = document.getElementById("schedulerLogsTableBody");
    if (!tbody) return;

    try {
        const logs = await apiCall("/api/settings/logs");
        if (!logs || logs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-secondary py-5">
                        Chưa có nhật ký hoạt động nào được ghi nhận.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = logs.map(log => {
            const dateStr = new Date(log.time).toLocaleString("vi-VN");
            const badgeClass = log.status === "SUCCESS" ? "badge-audit-ok" : "badge-audit-fail";
            const statusText = log.status === "SUCCESS" ? "Thành công" : "Thất bại";
            return `
                <tr>
                    <td class="text-nowrap fw-medium small">${dateStr}</td>
                    <td><span class="${badgeClass}">${statusText}</span></td>
                    <td class="small text-secondary">${log.details}</td>
                </tr>
            `;
        }).join("");
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-danger py-4">Lỗi tải nhật ký: ${error.message}</td></tr>`;
    }
}

async function handleSaveSettings() {
    const btn = document.getElementById("btnSaveSettings");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';

    const payload = {
        smtp_host: document.getElementById("settingsSmtpHost").value,
        smtp_port: Number(document.getElementById("settingsSmtpPort").value),
        smtp_user: document.getElementById("settingsSmtpUser").value,
        smtp_pass: document.getElementById("settingsSmtpPass").value,
        smtp_use_tls: document.getElementById("settingsSmtpUseTls").checked,
        schedule_enabled: document.getElementById("settingsScheduleEnabled").checked,
        recipient_email: document.getElementById("settingsRecipientEmail").value,
        schedule_interval: document.getElementById("settingsScheduleInterval").value,
        schedule_time: document.getElementById("settingsScheduleTime").value,
        schedule_weekday: Number(document.getElementById("settingsScheduleWeekday").value),
        gdt_username: document.getElementById("settingsGdtUser").value,
        gdt_password: document.getElementById("settingsGdtPass").value,
        ai_enabled: document.getElementById("settingsAiEnabled").checked,
        ai_provider: document.getElementById("settingsAiProvider").value,
        ai_model_name: document.getElementById("settingsAiModelName").value,
        ai_ollama_endpoint: document.getElementById("settingsAiOllamaEndpoint").value,
        ai_api_key: document.getElementById("settingsAiApiKey").value,
        ai_system_prompt: document.getElementById("settingsAiSystemPrompt").value,
        audit_agent_enabled: document.getElementById("settingsAuditAgentEnabled") ? document.getElementById("settingsAuditAgentEnabled").checked : false,
        audit_agent_schedule_time: document.getElementById("settingsAuditAgentScheduleTime") ? document.getElementById("settingsAuditAgentScheduleTime").value : "23:00",
        telegram_enabled: document.getElementById("settingsTelegramEnabled") ? document.getElementById("settingsTelegramEnabled").checked : false,
        telegram_bot_token: document.getElementById("settingsTelegramBotToken") ? document.getElementById("settingsTelegramBotToken").value : "",
        telegram_chat_id: document.getElementById("settingsTelegramChatId") ? document.getElementById("settingsTelegramChatId").value : "",
        auto_dunning_enabled: document.getElementById("settingsAutoDunningEnabled") ? document.getElementById("settingsAutoDunningEnabled").checked : false,
        signature_filter_enabled: document.getElementById("settingsSignatureFilterEnabled") ? document.getElementById("settingsSignatureFilterEnabled").checked : true,
        blacklist_filter_enabled: document.getElementById("settingsBlacklistFilterEnabled") ? document.getElementById("settingsBlacklistFilterEnabled").checked : true
    };

    try {
        const result = await apiCall("/api/settings", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        renderAlert(result.message, "success");
        await loadSettingsData(); // Refresh UI and logs
    } catch (error) {
        renderAlert(`Lỗi lưu thiết lập: ${error.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}


async function handleTestEmail() {
    const btn = document.getElementById("btnTestEmail");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang gửi...';

    const payload = {
        smtp_host: document.getElementById("settingsSmtpHost").value,
        smtp_port: Number(document.getElementById("settingsSmtpPort").value),
        smtp_user: document.getElementById("settingsSmtpUser").value,
        smtp_pass: document.getElementById("settingsSmtpPass").value,
        smtp_use_tls: document.getElementById("settingsSmtpUseTls").checked,
        recipient_email: document.getElementById("settingsRecipientEmail").value
    };

    try {
        const result = await apiCall("/api/settings/test-email", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        renderAlert(result.message, "success");
    } catch (error) {
        renderAlert(`Lỗi gửi email thử nghiệm: ${error.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function initializeSettingsPasswordToggles() {
    const bindToggle = (btnId, inputId) => {
        const btn = document.getElementById(btnId);
        const input = document.getElementById(inputId);
        if (!btn || !input) return;

        btn.addEventListener("click", () => {
            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            const icon = btn.querySelector("i");
            if (icon) {
                icon.className = isPassword ? "bi bi-eye-slash" : "bi bi-eye";
            }
        });
    };
    bindToggle("toggleSmtpPass", "settingsSmtpPass");
    bindToggle("toggleGdtPass", "settingsGdtPass");
    bindToggle("toggleAiApiKey", "settingsAiApiKey");
    bindToggle("toggleTelegramBotToken", "settingsTelegramBotToken");
}

function toggleTelegramFields() {
    const checkbox = document.getElementById("settingsTelegramEnabled");
    if (!checkbox) return;
    const enabled = checkbox.checked;
    const botTokenWrapper = document.getElementById("telegramBotTokenWrapper");
    const chatIdWrapper = document.getElementById("telegramChatIdWrapper");
    
    if (botTokenWrapper) botTokenWrapper.style.display = enabled ? "block" : "none";
    if (chatIdWrapper) chatIdWrapper.style.display = enabled ? "block" : "none";
}

async function handleTestAudit() {
    const btn = document.getElementById("btnTestAudit");
    if (!btn) return;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang chạy kiểm toán...';

    try {
        const result = await apiCall("/api/settings/test-audit", {
            method: "POST"
        });
        renderAlert(result.message || "Đã kích hoạt quét kiểm toán thành công.", "success");
        await loadLocalInvoices();
        await loadSchedulerLogs();
    } catch (error) {
        renderAlert(`Lỗi chạy kiểm toán: ${error.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function renderTScoreCharts(invoices) {
    const donutContainer = document.getElementById("tscoreDistributionContainer");
    const barContainer = document.getElementById("tscoreBarChartContainer");
    if (!donutContainer || !barContainer) return;

    if (!invoices || invoices.length === 0) {
        donutContainer.innerHTML = `
            <div class="text-center text-secondary py-5 w-100">
                <i class="bi bi-pie-chart fs-1 mb-2 opacity-50"></i>
                <p class="small mb-0">Chưa có dữ liệu tuân thủ.</p>
            </div>
        `;
        barContainer.innerHTML = `
            <div class="text-center text-secondary py-5 w-100">
                <i class="bi bi-bar-chart-line fs-1 mb-2 opacity-50"></i>
                <p class="small mb-0">Chưa có dữ liệu phân phối điểm.</p>
            </div>
        `;
        return;
    }

    // 1. Calculate T-Rating distribution
    const ratingCounts = { "A++": 0, "A": 0, "B": 0, "C": 0 };
    invoices.forEach(inv => {
        const rating = inv.t_rating || "A++";
        if (ratingCounts[rating] !== undefined) {
            ratingCounts[rating]++;
        } else {
            const score = inv.t_score !== undefined ? inv.t_score : 100;
            if (score === 100) ratingCounts["A++"]++;
            else if (score >= 80) ratingCounts["A"]++;
            else if (score >= 50) ratingCounts["B"]++;
            else ratingCounts["C"]++;
        }
    });

    const total = invoices.length;

    // 2. Generate SVG Donut Chart
    const ratingColors = {
        "A++": "#10b981", // Emerald
        "A": "#0ea5e9",  // Sky Blue
        "B": "#f59e0b",  // Amber
        "C": "#f43f5e"   // Rose
    };
    const ratingLabels = {
        "A++": "A++ (Xuất sắc - 100đ)",
        "A": "A (Tốt - từ 80đ)",
        "B": "B (Trung bình - từ 50đ)",
        "C": "C (Rủi ro cao - dưới 50đ)"
    };

    const slices = [];
    Object.keys(ratingCounts).forEach(rating => {
        const count = ratingCounts[rating];
        const percentage = total > 0 ? (count / total) * 100 : 0;
        slices.push({ rating, count, percentage, color: ratingColors[rating] });
    });

    const r = 35;
    const cx = 60;
    const cy = 60;
    const circumference = 2 * Math.PI * r;
    let strokeOffset = 0;
    let svgSlicesHtml = "";

    slices.forEach(slice => {
        if (slice.count === 0) return;
        const strokeLength = (slice.percentage / 100) * circumference;
        svgSlicesHtml += `
            <circle cx="${cx}" cy="${cy}" r="${r}"
                    fill="transparent"
                    stroke="${slice.color}"
                    stroke-width="12"
                    stroke-dasharray="${strokeLength} ${circumference}"
                    stroke-dashoffset="${-strokeOffset}"
                    transform="rotate(-90 ${cx} ${cy})"
                    class="chart-donut-segment"
                    data-rating="${slice.rating}"
                    data-percentage="${slice.percentage.toFixed(1)}%"
                    data-count="${slice.count}">
            </circle>
        `;
        strokeOffset += strokeLength;
    });

    if (strokeOffset === 0) {
        svgSlicesHtml = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="transparent" stroke="#4b5563" stroke-width="12"></circle>`;
    }

    const donutSvg = `
        <div class="d-flex align-items-center justify-content-center flex-wrap gap-4 w-100">
            <div class="position-relative" style="width: 140px; height: 140px;">
                <svg viewBox="0 0 120 120" width="140" height="140" class="chart-svg">
                    <circle cx="${cx}" cy="${cy}" r="${r}" fill="transparent" stroke="rgba(255,255,255,0.05)" stroke-width="12"></circle>
                    ${svgSlicesHtml}
                </svg>
                <div class="position-absolute top-50 start-50 translate-middle text-center">
                    <span class="fs-4 fw-bold text-white">${total}</span>
                    <div style="font-size: 0.65rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em;">Hóa Đơn</div>
                </div>
            </div>
            <div class="flex-grow-1" style="min-width: 200px;">
                <div class="d-flex flex-column gap-2">
                    ${slices.map(slice => `
                        <div class="d-flex align-items-center justify-content-between text-white" style="font-size: 0.85rem;">
                            <div class="d-flex align-items-center gap-2">
                                <span class="d-inline-block rounded-circle" style="width: 10px; height: 10px; background-color: ${slice.color};"></span>
                                <span class="fw-medium text-secondary-accent" style="color: var(--text-secondary);">${ratingLabels[slice.rating]}</span>
                            </div>
                            <div class="fw-bold d-flex gap-2">
                                <span>${slice.count}</span>
                                <span class="text-secondary" style="font-size: 0.75rem; width: 40px; text-align: right;">(${slice.percentage.toFixed(1)}%)</span>
                            </div>
                        </div>
                    `).join("")}
                </div>
            </div>
        </div>
    `;
    donutContainer.innerHTML = donutSvg;

    // 3. Generate SVG Bar Chart for T-Score ranges
    const ranges = [
        { label: "<50 (Nguy cơ)", min: 0, max: 49, color: "#f43f5e", count: 0 },
        { label: "50-69 (Cảnh báo)", min: 50, max: 69, color: "#f59e0b", count: 0 },
        { label: "70-89 (Khá)", min: 70, max: 89, color: "#3b82f6", count: 0 },
        { label: "90-99 (Tốt)", min: 90, max: 99, color: "#0ea5e9", count: 0 },
        { label: "100 (Xuất sắc)", min: 100, max: 100, color: "#10b981", count: 0 }
    ];

    invoices.forEach(inv => {
        const score = inv.t_score !== undefined ? inv.t_score : 100;
        for (let r of ranges) {
            if (score >= r.min && score <= r.max) {
                r.count++;
                break;
            }
        }
    });

    const maxCount = Math.max(...ranges.map(r => r.count), 1);
    const barWidth = 40;
    const barGap = 24;
    const chartHeight = 120;
    const chartWidth = ranges.length * (barWidth + barGap) + barGap;

    const svgBars = ranges.map((r, idx) => {
        const height = (r.count / maxCount) * chartHeight;
        const x = barGap + idx * (barWidth + barGap);
        const y = chartHeight - height;
        return `
            <g class="bar-group" data-label="${r.label}" data-count="${r.count}">
                <rect x="${x}" y="0" width="${barWidth}" height="${chartHeight}" fill="rgba(255,255,255,0.02)" rx="4"></rect>
                <rect x="${x}" y="${y}" width="${barWidth}" height="${height}" fill="${r.color}" rx="4" class="chart-bar-rect" style="transform-origin: ${x + barWidth/2}px ${chartHeight}px; animation: barGrow 1s ease-out forwards;"></rect>
                <text x="${x + barWidth/2}" y="${y - 6}" text-anchor="middle" fill="#ffffff" font-size="10" font-weight="bold">${r.count}</text>
            </g>
        `;
    }).join("");

    const svgBarChart = `
        <div class="d-flex flex-column align-items-center w-100">
            <svg viewBox="0 0 ${chartWidth} ${chartHeight + 35}" width="100%" height="155" class="chart-svg">
                <g>
                    ${svgBars}
                </g>
                ${ranges.map((r, idx) => {
                    const x = barGap + idx * (barWidth + barGap) + barWidth / 2;
                    return `<text x="${x}" y="${chartHeight + 18}" text-anchor="middle" fill="#9ca3af" font-size="9" font-weight="medium">${r.label.split(" ")[0]}</text>
                            <text x="${x}" y="${chartHeight + 28}" text-anchor="middle" fill="#4b5563" font-size="8">${r.label.split(" ")[1] || ""}</text>`;
                }).join("")}
            </svg>
        </div>
    `;
    barContainer.innerHTML = svgBarChart;
}


// =========================================================================
// AI Chatbot RAG Panel Controllers & Formatting Renderers
// =========================================================================
let currentChatSessionId = null;

function initAiChatbot() {
    const btnToggle = document.getElementById("btnToggleAiChat");
    const btnClose = document.getElementById("btnCloseAiChat");
    const chatCard = document.getElementById("aiChatCard");
    const chatForm = document.getElementById("aiChatForm");
    const messageInput = document.getElementById("aiChatMessageInput");
    const sessionSelect = document.getElementById("chatSessionSelect");
    const btnNewSession = document.getElementById("btnNewChatSession");
    const btnDeleteSession = document.getElementById("btnDeleteChatSession");

    if (!btnToggle || !chatCard) return;

    // Toggle Chat visibility
    btnToggle.addEventListener("click", () => {
        chatCard.classList.toggle("d-none");
        if (!chatCard.classList.contains("d-none")) {
            loadChatSessions();
            messageInput.focus();
        }
    });

    btnClose.addEventListener("click", () => {
        chatCard.classList.add("d-none");
    });

    // Handle session select change
    sessionSelect.addEventListener("change", (e) => {
        const val = e.target.value;
        if (val) {
            selectChatSession(val);
        } else {
            currentChatSessionId = null;
            clearChatMessagesView();
        }
    });

    // New Session
    btnNewSession.addEventListener("click", async () => {
        try {
            btnNewSession.disabled = true;
            const res = await apiCall("/api/ai/chat/sessions", {
                method: "POST",
                body: JSON.stringify({ title: "Cuộc trò chuyện mới" })
            });
            if (res && res.session) {
                await loadChatSessions();
                sessionSelect.value = res.session.id;
                selectChatSession(res.session.id);
            }
        } catch (error) {
            renderAlert(`Không thể tạo phiên chat mới: ${error.message}`, "danger");
        } finally {
            btnNewSession.disabled = false;
        }
    });

    // Delete Session
    btnDeleteSession.addEventListener("click", async () => {
        if (!currentChatSessionId) {
            renderAlert("Vui lòng chọn một phiên hội thoại để xóa.", "warning");
            return;
        }
        if (!confirm("Bạn có chắc muốn xóa vĩnh viễn phiên hội thoại này?")) {
            return;
        }

        try {
            btnDeleteSession.disabled = true;
            await apiCall(`/api/ai/chat/sessions/${currentChatSessionId}`, {
                method: "DELETE"
            });
            renderAlert("Đã xóa phiên hội thoại thành công.", "success");
            currentChatSessionId = null;
            await loadChatSessions();
            clearChatMessagesView();
        } catch (error) {
            renderAlert(`Không thể xóa phiên chat: ${error.message}`, "danger");
        } finally {
            btnDeleteSession.disabled = false;
        }
    });

    // Suggestion chips
    document.querySelectorAll(".chat-suggestion").forEach(chip => {
        chip.addEventListener("click", (e) => {
            e.preventDefault();
            const msg = chip.getAttribute("data-msg");
            if (msg) {
                messageInput.value = msg;
                chatForm.dispatchEvent(new Event("submit"));
            }
        });
    });

    // Form Submit
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = messageInput.value.trim();
        if (!text) return;

        // Clear input
        messageInput.value = "";

        // If no active session, automatically create one first
        if (!currentChatSessionId) {
            try {
                const res = await apiCall("/api/ai/chat/sessions", {
                    method: "POST",
                    body: JSON.stringify({ title: text.substring(0, 30) })
                });
                if (res && res.session) {
                    await loadChatSessions();
                    sessionSelect.value = res.session.id;
                    currentChatSessionId = res.session.id;
                }
            } catch (error) {
                renderAlert(`Tự động khởi tạo phiên thất bại: ${error.message}`, "danger");
                return;
            }
        }

        // Add user message to view
        appendChatMessage("user", text);

        // Show typing indicator
        showChatTypingIndicator();

        try {
            const res = await apiCall(`/api/ai/chat/sessions/${currentChatSessionId}/message`, {
                method: "POST",
                body: JSON.stringify({ message: text })
            });

            removeChatTypingIndicator();

            if (res && res.reply) {
                appendChatMessage("assistant", res.reply);
            } else {
                appendChatMessage("assistant", "Lỗi: Không nhận được phản hồi từ mô hình AI.");
            }
        } catch (error) {
            removeChatTypingIndicator();
            appendChatMessage("assistant", `Lỗi kết nối: ${error.message}`);
        }
    });
}

/**
 * Open (or resume) an AI chat session linked to the currently-viewed invoice.
 * Called from the "Hỏi AI" button inside the invoice details drawer.
 * Flow: check existing sessions for one linked to this invoice_id → select it,
 *       or create a brand new session with invoice_id → open the chatbot panel.
 */
async function openInvoiceChat() {
    const invoiceId = document.getElementById("detId")?.textContent?.trim();
    if (!invoiceId || invoiceId === "-") {
        renderAlert("Vui lòng mở chi tiết hóa đơn trước khi hỏi Trợ lý AI.", "warning");
        return;
    }

    const chatCard = document.getElementById("aiChatCard");
    const sessionSelect = document.getElementById("chatSessionSelect");
    const btn = document.getElementById("btnChatAboutInvoice");
    if (!chatCard || !sessionSelect) return;

    // Disable button during processing
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang mở...'; }

    try {
        // 1. Fetch all sessions and look for one already linked to this invoice
        const rawData = await apiCall("/api/ai/chat/sessions");
        const sessions = (rawData && rawData.sessions) ? rawData.sessions : (Array.isArray(rawData) ? rawData : []);
        const existing = sessions.find(s => s.invoice_id === invoiceId);

        if (existing) {
            // Resume existing session
            currentChatSessionId = existing.id;
            await loadChatSessions();
            sessionSelect.value = existing.id;
            await selectChatSession(existing.id);
        } else {
            // Create new session linked to this invoice
            const res = await apiCall("/api/ai/chat/sessions", {
                method: "POST",
                body: JSON.stringify({ invoice_id: invoiceId })
            });
            if (res && res.session) {
                currentChatSessionId = res.session.id;
                await loadChatSessions();
                sessionSelect.value = res.session.id;
                await selectChatSession(res.session.id);
            }
        }

        // 2. Show the chatbot panel and close the drawer
        chatCard.classList.remove("d-none");
        const drawerEl = document.getElementById("invoiceDetailsDrawer");
        if (drawerEl) {
            const bsOffcanvas = bootstrap.Offcanvas.getInstance(drawerEl);
            if (bsOffcanvas) bsOffcanvas.hide();
        }

        // 3. Focus input
        document.getElementById("aiChatMessageInput")?.focus();
    } catch (error) {
        renderAlert(`Không thể mở phiên chat AI: ${error.message}`, "danger");
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-chat-dots-fill" aria-hidden="true"></i> Hỏi AI'; }
    }
}

async function loadChatSessions() {
    const sessionSelect = document.getElementById("chatSessionSelect");
    if (!sessionSelect) return;

    try {
        const rawData = await apiCall("/api/ai/chat/sessions");
        const sessions = (rawData && rawData.sessions) ? rawData.sessions : (Array.isArray(rawData) ? rawData : []);
        if (sessions) {
            if (sessions.length === 0) {
                sessionSelect.innerHTML = '<option value="">-- Chưa có phiên chat nào --</option>';
                currentChatSessionId = null;
                clearChatMessagesView();
                return;
            }

            sessionSelect.innerHTML = sessions.map(s => {
                const dateStr = new Date(s.updated_at).toLocaleString("vi-VN", { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
                const invoicePrefix = s.invoice_id ? "🧾 " : "";
                return `<option value="${s.id}">${invoicePrefix}${s.title} (${dateStr})</option>`;
            }).join("");

            // Keep selection or pick first
            if (currentChatSessionId && sessions.some(s => s.id === currentChatSessionId)) {
                sessionSelect.value = currentChatSessionId;
            } else {
                currentChatSessionId = sessions[0].id;
                sessionSelect.value = currentChatSessionId;
                selectChatSession(currentChatSessionId);
            }
        }
    } catch (error) {
        sessionSelect.innerHTML = '<option value="">-- Lỗi tải danh sách --</option>';
        console.error("Error loading chat sessions:", error);
    }
}

async function selectChatSession(sessionId) {
    currentChatSessionId = sessionId;
    const messagesContainer = document.getElementById("aiChatMessages");
    const emptyState = document.getElementById("aiChatEmptyState");
    if (!messagesContainer) return;

    messagesContainer.innerHTML = '<div class="text-center py-4 text-secondary small"><div class="spinner-border spinner-border-sm" role="status"></div> Đang tải cuộc hội thoại...</div>';
    emptyState.classList.add("d-none");

    try {
        const rawData = await apiCall("/api/ai/chat/sessions");
        const sessions = (rawData && rawData.sessions) ? rawData.sessions : (Array.isArray(rawData) ? rawData : []);
        const session = sessions.find(s => s.id === sessionId);
        if (session) {
            // Update invoice badge indicator
            updateChatInvoiceBadge(session.invoice_id);

            messagesContainer.innerHTML = "";
            if (session.messages && session.messages.length > 0) {
                session.messages.forEach(msg => {
                    appendChatMessage(msg.role, msg.content, false);
                });
                scrollChatToBottom();
            } else {
                emptyState.classList.remove("d-none");
            }
        }
    } catch (error) {
        messagesContainer.innerHTML = `<div class="text-danger small py-3 text-center">Lỗi tải tin nhắn: ${error.message}</div>`;
    }
}

/**
 * Show or hide the invoice-linked badge in the chat panel header.
 * @param {string|null} invoiceId - The linked invoice ID, or null/undefined.
 */
function updateChatInvoiceBadge(invoiceId) {
    const badge = document.getElementById("chatInvoiceBadge");
    const badgeText = document.getElementById("chatInvoiceBadgeText");
    if (!badge || !badgeText) return;
    if (invoiceId) {
        // Extract short display: show last segment (number) or truncate
        const shortId = invoiceId.length > 20 ? "..." + invoiceId.slice(-15) : invoiceId;
        badgeText.textContent = shortId;
        badge.classList.remove("d-none");
    } else {
        badge.classList.add("d-none");
        badgeText.textContent = "";
    }
}

function clearChatMessagesView() {
    const messagesContainer = document.getElementById("aiChatMessages");
    const emptyState = document.getElementById("aiChatEmptyState");
    if (messagesContainer) messagesContainer.innerHTML = "";
    if (emptyState) emptyState.classList.remove("d-none");
}

function appendChatMessage(role, content, scroll = true) {
    const messagesContainer = document.getElementById("aiChatMessages");
    const emptyState = document.getElementById("aiChatEmptyState");
    if (!messagesContainer) return;

    if (emptyState) emptyState.classList.add("d-none");

    const msgBubble = document.createElement("div");
    msgBubble.className = `chat-msg-bubble chat-msg-${role}`;
    
    if (role === "assistant") {
        msgBubble.innerHTML = formatMarkdown(content);
    } else {
        msgBubble.textContent = content;
    }

    const timeStr = new Date().toLocaleTimeString("vi-VN", { hour: '2-digit', minute: '2-digit' });
    const meta = document.createElement("span");
    meta.className = "chat-msg-meta";
    meta.textContent = timeStr;
    msgBubble.appendChild(meta);

    messagesContainer.appendChild(msgBubble);

    if (scroll) {
        scrollChatToBottom();
    }
}

function showChatTypingIndicator() {
    const messagesContainer = document.getElementById("aiChatMessages");
    if (!messagesContainer) return;

    if (document.getElementById("aiChatTypingIndicator")) return;

    const loader = document.createElement("div");
    loader.id = "aiChatTypingIndicator";
    loader.className = "typing-dots";
    loader.innerHTML = "<span></span><span></span><span></span>";
    messagesContainer.appendChild(loader);
    scrollChatToBottom();
}

function removeChatTypingIndicator() {
    const loader = document.getElementById("aiChatTypingIndicator");
    if (loader) loader.remove();
}

function scrollChatToBottom() {
    const chatBody = document.getElementById("aiChatBody");
    if (chatBody) {
        setTimeout(() => {
            chatBody.scrollTop = chatBody.scrollHeight;
        }, 50);
    }
}

function escapeHtml(string) {
    return String(string).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function renderMarkdownTable(lines) {
    if (lines.length < 2) return lines.join("\n");
    
    const headers = lines[0].split("|").map(h => h.trim()).filter((h, idx, arr) => idx > 0 && idx < arr.length - 1);
    const rows = [];
    for (let i = 2; i < lines.length; i++) {
        const rowCells = lines[i].split("|").map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
        if (rowCells.length > 0) {
            rows.push(rowCells);
        }
    }
    
    let html = '<div class="table-responsive my-2"><table class="table table-sm table-bordered text-white border-secondary small" style="background: rgba(255,255,255,0.03);">';
    html += '<thead style="background: rgba(255,255,255,0.08);">';
    html += '<tr>' + headers.map(h => `<th class="fw-bold border-secondary text-primary">${h}</th>`).join("") + '</tr>';
    html += '</thead><tbody>';
    html += rows.map(r => '<tr>' + r.map(c => `<td class="border-secondary text-white-50">${c}</td>`).join("") + '</tr>').join("");
    html += '</tbody></table></div>';
    return html;
}

function highlightSql(code) {
    let highlighted = escapeHtml(code);
    
    // Comments
    highlighted = highlighted.replace(/(--.*)/g, '<span class="chat-sql-comment">$1</span>');
    highlighted = highlighted.replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="chat-sql-comment">$1</span>');
    
    // Strings (single quotes)
    highlighted = highlighted.replace(/('(?:''|[^'])*')/g, '<span class="chat-sql-string">$1</span>');
    
    // SQL Keywords
    const keywords = [
        "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "ON", "GROUP BY", "ORDER BY",
        "HAVING", "LIMIT", "AND", "OR", "IN", "NOT", "NULL", "AS", "IS", "LIKE", "COUNT", "SUM",
        "AVG", "MIN", "MAX", "WITH", "UNION", "ALL", "CASE", "WHEN", "THEN", "ELSE", "END"
    ];
    keywords.forEach(kw => {
        const regex = new RegExp(`\\b(${kw})\\b`, 'gi');
        highlighted = highlighted.replace(regex, (match) => {
            return `<span class="chat-sql-keyword">${match.toUpperCase()}</span>`;
        });
    });
    
    // Numbers
    highlighted = highlighted.replace(/\b(\d+)\b/g, '<span class="chat-sql-number">$1</span>');
    
    return highlighted;
}

function formatMarkdown(text) {
    if (!text) return "";
    
    let escaped = escapeHtml(text);
    
    // Code blocks with syntax highlighting
    escaped = escaped.replace(/```(?:sql)?([\s\S]*?)```/g, (match, code) => {
        const cleanCode = code.trim();
        const isSql = /select\s|from\s|where\s|join\s|group\sby\s/i.test(cleanCode) || match.startsWith("```sql");
        if (isSql) {
            // Unescape the HTML-escaped code block for highlightSql to process safely
            const rawCode = cleanCode.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#039;/g, "'");
            return `<pre class="bg-dark p-2 rounded small border border-secondary" style="overflow-x: auto;"><code class="chat-sql-code">${highlightSql(rawCode)}</code></pre>`;
        }
        return `<pre class="bg-dark text-light p-2 rounded small border border-secondary" style="overflow-x: auto;"><code>${cleanCode}</code></pre>`;
    });

    // Law Citations formatting
    // 1. Nghị định
    escaped = escaped.replace(/(Nghị\s+định\s+\d+\/\d+\/NĐ-CP)/gi, '<span class="law-badge"><i class="bi bi-file-earmark-ruled" aria-hidden="true"></i> $1</span>');
    // 2. Thông tư
    escaped = escaped.replace(/(Thông\s+tư\s+\d+\/\d+\/TT-BTC)/gi, '<span class="law-badge"><i class="bi bi-file-earmark-ruled" aria-hidden="true"></i> $1</span>');
    // 3. Luật số ... /QH... hoặc Luật Thuế...
    escaped = escaped.replace(/(Luật\s+số\s+\d+\/\d+\/QH\d+|Luật\s+Thuế\s+GTGT\s+\d+\/\d+\/QH\d+|Luật\s+Thuế\s+GTGT|Luật\s+Thuế\s+TNDN|Luật\s+Quản\s+lý\s+thuế)/gi, '<span class="law-badge"><i class="bi bi-file-earmark-ruled" aria-hidden="true"></i> $1</span>');
    // 4. Điều ... Khoản ...
    escaped = escaped.replace(/(Điều\s+\d+(?:\s+Khoản\s+\d+)?)/gi, '<span class="law-badge"><i class="bi bi-bookmark-fill" aria-hidden="true"></i> $1</span>');
    
    // Markdown tables parsing
    const lines = escaped.split("\n");
    let insideTable = false;
    let tableLines = [];
    let resultHtml = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith("|") && line.endsWith("|")) {
            if (!insideTable) {
                insideTable = true;
            }
            tableLines.push(line);
        } else {
            if (insideTable) {
                resultHtml.push(renderMarkdownTable(tableLines));
                insideTable = false;
                tableLines = [];
            }
            resultHtml.push(line);
        }
    }
    if (insideTable) {
        resultHtml.push(renderMarkdownTable(tableLines));
    }
    
    let formatted = resultHtml.join("\n");
    
    // Bold text (**word**)
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    
    // Inline code (`word`)
    formatted = formatted.replace(/`(.*?)`/g, '<code class="bg-dark text-warning p-1 rounded font-monospace" style="font-size: 0.85em;">$1</code>');
    
    // Bullet list items (- item)
    formatted = formatted.replace(/^\s*-\s+(.*?)$/gm, "<li>$1</li>");
    formatted = formatted.replace(/(<li>.*?<\/li>)+/gs, '<ul class="ps-3 mb-2">$1</ul>');
    
    // Paragraph divisions
    const paragraphs = formatted.split(/\n{2,}/);
    formatted = paragraphs.map(p => {
        p = p.trim();
        if (!p) return "";
        if (p.startsWith("<ul") || p.startsWith("<ol") || p.startsWith("<pre") || p.startsWith("<table") || p.startsWith("<div") || p.startsWith("<span")) {
            return p;
        }
        return `<p class="mb-2">${p.replace(/\n/g, "<br>")}</p>`;
    }).join("");
    
    return formatted;
}


// =========================================================================
// VAT Declaration & Tax Optimizer (US-033)
// =========================================================================
let vatDataStore = null;

function populateVatPeriodOptions() {
    const periodType = document.getElementById("vatPeriodType").value;
    const periodValSelect = document.getElementById("vatPeriodValue");
    const label = document.getElementById("vatPeriodValueLabel");
    if (!periodValSelect) return;

    if (periodType === "monthly") {
        label.textContent = "Tháng Kê Khai";
        periodValSelect.innerHTML = Array.from({ length: 12 }, (_, i) => {
            const m = String(i + 1).padStart(2, "0");
            return `<option value="${m}">Tháng ${m}</option>`;
        }).join("");
        // Default to last month
        const now = new Date();
        let lastMonth = now.getMonth(); // getMonth is 0-indexed, so this is previous month
        if (lastMonth === 0) lastMonth = 12;
        periodValSelect.value = String(lastMonth).padStart(2, "0");
    } else {
        label.textContent = "Quý Kê Khai";
        periodValSelect.innerHTML = `
            <option value="1">Quý 1 (T1, T2, T3)</option>
            <option value="2">Quý 2 (T4, T5, T6)</option>
            <option value="3">Quý 3 (T7, T8, T9)</option>
            <option value="4">Quý 4 (T10, T11, T12)</option>
        `;
        // Default to last quarter
        const now = new Date();
        const currentQ = Math.floor(now.getMonth() / 3) + 1;
        let lastQ = currentQ - 1;
        if (lastQ === 0) lastQ = 4;
        periodValSelect.value = String(lastQ);
    }
}

function initVatDeclarationTab() {
    const tabEl = document.getElementById("tax-return-tab");
    const typeSelect = document.getElementById("vatPeriodType");
    const form = document.getElementById("vatDeclarationForm");
    const printBtn = document.getElementById("btnPrintVatDeclaration");
    const input21 = document.getElementById("indicator21");

    if (!tabEl) return;

    // Populate default dropdown options
    populateVatPeriodOptions();
    
    // Set default year
    const yearInput = document.getElementById("vatYear");
    if (yearInput) {
        yearInput.value = new Date().getFullYear();
    }

    // Tab change or tab shown listener
    tabEl.addEventListener("shown.bs.tab", () => {
        if (!vatDataStore) {
            loadVatDeclaration();
        }
    });

    typeSelect?.addEventListener("change", () => {
        populateVatPeriodOptions();
    });

    form?.addEventListener("submit", (e) => {
        e.preventDefault();
        loadVatDeclaration();
    });

    input21?.addEventListener("input", () => {
        recalculateVatDeclaration();
    });

    printBtn?.addEventListener("click", () => {
        window.print();
    });
}

function formatVatCurrency(value) {
    if (value === null || value === undefined) return "0 ₫";
    return Math.round(value).toLocaleString("vi-VN") + " ₫";
}

async function loadVatDeclaration() {
    const btn = document.getElementById("btnLoadVatData");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang tải...';

    const pType = document.getElementById("vatPeriodType").value;
    const pValue = document.getElementById("vatPeriodValue").value;
    const year = document.getElementById("vatYear").value;

    try {
        const data = await apiCall(`/api/reports/vat-declaration?period_type=${pType}&period_value=${pValue}&year=${year}`);
        vatDataStore = data;

        // Reset disputed list in UI
        const disputedList = document.getElementById("vatDisputedList");
        const disputedCount = document.getElementById("vatDisputedCount");
        
        if (data.disputed_invoices && data.disputed_invoices.length > 0) {
            disputedCount.textContent = data.disputed_invoices.length;
            disputedCount.className = "badge bg-danger fw-bold px-2 py-1";
            
            disputedList.innerHTML = data.disputed_invoices.map(inv => {
                const dateStr = new Date(inv.date).toLocaleDateString("vi-VN");
                return `
                    <div class="glass-card p-3 border border-secondary border-opacity-10 disputed-invoice-card animate__animated animate__fadeIn">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h6 class="fw-bold mb-0 text-white" style="font-size: 0.85rem;">${inv.seller_name}</h6>
                                <span class="text-secondary small">MST: ${inv.seller_mst}</span>
                            </div>
                            <div class="form-check form-switch p-0 m-0">
                                <input class="form-check-input disputed-toggle m-0" type="checkbox" role="switch" data-invoice-id="${inv.id}" data-tax-amount="${inv.tax_amount}" style="cursor: pointer; width: 40px; height: 20px;">
                            </div>
                        </div>
                        <div class="d-flex justify-content-between mb-2" style="font-size: 0.75rem;">
                            <span class="text-secondary">HĐ Số: <strong class="text-light">${inv.number}</strong> (${dateStr})</span>
                            <span class="text-secondary">Tiền thuế: <strong class="text-warning">${formatVatCurrency(inv.tax_amount)}</strong></span>
                        </div>
                        <div class="p-2 rounded bg-danger bg-opacity-10 border border-danger border-opacity-10 small text-danger" style="font-size: 0.75rem;">
                            <i class="bi bi-shield-exclamation"></i> ${inv.warning}
                        </div>
                    </div>
                `;
            }).join("");

            // Attach change listeners to disputed toggles
            document.querySelectorAll(".disputed-toggle").forEach(toggle => {
                toggle.addEventListener("change", () => {
                    recalculateVatDeclaration();
                });
            });

        } else {
            disputedCount.textContent = "0";
            disputedCount.className = "badge bg-success fw-bold px-2 py-1";
            disputedList.innerHTML = `
                <div class="text-center text-secondary py-5">
                    <i class="bi bi-emoji-smile fs-1 text-success mb-2"></i>
                    <p class="small mb-0">Tuyệt vời! Không phát hiện hóa đơn đầu vào nào có rủi ro pháp lý cao trong kỳ này.</p>
                </div>
            `;
        }

        recalculateVatDeclaration();

    } catch (error) {
        renderAlert(`Lỗi tải dữ liệu kê khai thuế: ${error.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function recalculateVatDeclaration() {
    if (!vatDataStore) return;

    const outputs = vatDataStore.outputs;
    const inputs = vatDataStore.inputs;
    
    // Sum user override toggles
    let addedDeductibleVat = 0;
    let allowedCount = 0;
    const toggles = document.querySelectorAll(".disputed-toggle");
    
    toggles.forEach(toggle => {
        if (toggle.checked) {
            addedDeductibleVat += Number(toggle.getAttribute("data-tax-amount"));
            allowedCount++;
        }
    });

    const indicator21 = Number(document.getElementById("indicator21").value) || 0;
    const calculatedDeductible = inputs.deductible_vat + addedDeductibleVat;

    // 1. Render Group A: Purchases
    document.getElementById("indicator22").textContent = formatVatCurrency(inputs.total_vat);
    document.getElementById("indicator23").textContent = formatVatCurrency(inputs.total_value);
    document.getElementById("indicator24").textContent = formatVatCurrency(inputs.total_vat);
    document.getElementById("indicator25").textContent = formatVatCurrency(calculatedDeductible);

    // 2. Render Group B: Sales (Outputs)
    document.getElementById("indicator26").textContent = formatVatCurrency(outputs.tax_exempt_val);
    document.getElementById("indicator29").textContent = formatVatCurrency(outputs.tax_0_val);
    document.getElementById("indicator30").textContent = formatVatCurrency(outputs.tax_5_val);
    document.getElementById("indicator31").textContent = formatVatCurrency(outputs.tax_5_vat);
    document.getElementById("indicator32").textContent = formatVatCurrency(outputs.tax_8_val + outputs.tax_10_val);
    document.getElementById("indicator33").textContent = formatVatCurrency(outputs.tax_8_vat + outputs.tax_10_vat);
    
    document.getElementById("indicator35").textContent = formatVatCurrency(outputs.total_val);
    document.getElementById("indicator36").textContent = formatVatCurrency(outputs.total_vat);

    // 3. Render Group C: Payables & Carried Forward
    // Payable = Output VAT - Deductible Input VAT - Carried Forward [21]
    const vatPayable = outputs.total_vat - calculatedDeductible - indicator21;
    
    const indicator40 = document.getElementById("indicator40");
    const indicator43 = document.getElementById("indicator43");

    if (vatPayable > 0) {
        indicator40.textContent = formatVatCurrency(vatPayable);
        indicator43.textContent = "0 ₫";
        indicator40.className = "text-end fw-bold text-danger";
        indicator43.className = "text-end fw-bold text-secondary";
    } else {
        indicator40.textContent = "0 ₫";
        indicator43.textContent = formatVatCurrency(Math.abs(vatPayable));
        indicator40.className = "text-end fw-bold text-secondary";
        indicator43.className = "text-end fw-bold text-success";
    }

    // Update Recommendations box
    const recBox = document.getElementById("vatRecommendationBox");
    const recText = document.getElementById("vatRecommendationText");

    if (toggles.length > 0) {
        if (allowedCount > 0) {
            recBox.className = "mt-4 p-3 rounded border border-warning border-opacity-20";
            recBox.querySelector("h6").className = "fw-bold small text-warning mb-1 d-flex align-items-center gap-2";
            recBox.querySelector("h6").innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> CẢNH BÁO TUÂN THỦ TỪ TRỢ LÝ AI';
            recText.innerHTML = `Bạn đang chủ động ghi đè để khấu trừ <strong>${allowedCount}</strong> hóa đơn rủi ro cao (tổng cộng <strong>${formatVatCurrency(addedDeductibleVat)}</strong> tiền thuế). Hãy đảm bảo doanh nghiệp có đầy đủ chứng từ chuyển khoản qua ngân hàng và hồ sơ giải trình chi tiết để tránh bị phạt truy thu thuế khi thanh tra.`;
        } else {
            recBox.className = "mt-4 p-3 rounded border border-success border-opacity-20";
            recBox.querySelector("h6").className = "fw-bold small text-success mb-1 d-flex align-items-center gap-2";
            recBox.querySelector("h6").innerHTML = '<i class="bi bi-shield-fill-check"></i> AN TOÀN TUÂN THỦ TỪ TRỢ LÝ AI';
            recText.innerHTML = `AI đã loại trừ thành công <strong>${toggles.length}</strong> hóa đơn rủi ro cao khỏi Chỉ tiêu [25] để bảo vệ doanh nghiệp. Các hóa đơn còn lại của bạn hoàn toàn hợp lệ và an toàn tuyệt đối.`;
        }
    } else {
        recBox.className = "mt-4 p-3 rounded border border-success border-opacity-20";
        recBox.querySelector("h6").className = "fw-bold small text-success mb-1 d-flex align-items-center gap-2";
        recBox.querySelector("h6").innerHTML = '<i class="bi bi-shield-fill-check"></i> AN TOÀN TUÂN THỦ TỪ TRỢ LÝ AI';
        recText.innerHTML = "Dữ liệu tuân thủ thuế an toàn tuyệt đối. Hãy chuẩn bị các chứng từ thanh toán không dùng tiền mặt (Ủy nhiệm chi) cho các hóa đơn mua vào hợp lệ để hoàn tất hồ sơ quyết toán.";
    }
}

// =============================================================================
// Analytics Pro – Supplier Price Trends & VAT Forecast
// =============================================================================

const CHART_COLORS = [
  'hsl(160 64% 45%)', 'hsl(200 80% 55%)', 'hsl(280 65% 60%)',
  'hsl(32 95% 55%)',  'hsl(0 72% 60%)',   'hsl(48 95% 50%)',
];

function fmtPrice(v) {
  if (!v && v !== 0) return '—';
  return new Intl.NumberFormat('vi-VN').format(v) + ' ₫';
}

// ── Autocomplete ──────────────────────────────────────────────────────────────
let _topItems = [];

async function _ensureTopItems() {
  if (_topItems.length) return;
  try {
    const r = await fetch('/api/analytics/top-items');
    const d = await r.json();
    if (d.success) _topItems = d.items.map(i => i.name);
  } catch (_) {}
}

document.addEventListener('DOMContentLoaded', () => {
  const inp = document.getElementById('priceItemInput');
  const sug = document.getElementById('priceItemSuggestions');
  if (!inp) return;

  inp.addEventListener('focus', _ensureTopItems);
  inp.addEventListener('input', () => {
    const q = inp.value.toLowerCase().trim();
    sug.innerHTML = '';
    if (!q) { sug.style.display = 'none'; return; }
    const hits = _topItems.filter(n => n.toLowerCase().includes(q)).slice(0, 8);
    if (!hits.length) { sug.style.display = 'none'; return; }
    hits.forEach(name => {
      const li = document.createElement('li');
      li.textContent = name;
      li.className = 'px-3 py-2';
      li.style.cssText = 'cursor:pointer;font-size:.85rem;border-bottom:1px solid hsl(var(--border))';
      li.onmouseenter = () => li.style.background = 'hsl(var(--surface-2))';
      li.onmouseleave = () => li.style.background = '';
      li.onclick = () => { inp.value = name; sug.style.display = 'none'; };
      sug.appendChild(li);
    });
    sug.style.display = 'block';
  });
  document.addEventListener('click', e => {
    if (!inp.contains(e.target) && !sug.contains(e.target)) sug.style.display = 'none';
  });
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); loadPriceTrends(); } });
});

// ── Price Trends ──────────────────────────────────────────────────────────────
async function loadPriceTrends() {
  const item = (document.getElementById('priceItemInput')?.value || '').trim();
  const year = document.getElementById('priceYearFilter')?.value || '';
  if (!item) { alert('Vui lòng nhập tên mặt hàng.'); return; }

  const btn = document.getElementById('btnLoadPriceTrends');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Đang tải...'; }

  try {
    const params = new URLSearchParams({ item_name: item });
    if (year) params.set('year', year);
    const r = await fetch('/api/analytics/supplier-price-trends?' + params);
    const d = await r.json();
    if (!d.success) throw new Error(d.error || 'Lỗi API');
    _renderPriceTrends(d);
  } catch (e) {
    alert('Lỗi: ' + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-search"></i> Phân tích'; }
  }
}

function _renderPriceTrends(d) {
  const wrap = document.getElementById('priceTrendsChartWrap');
  const empty = document.getElementById('priceTrendsEmpty');

  if (!d.series?.length) {
    wrap.style.display = 'none';
    empty.style.display = 'block';
    empty.querySelector('p').textContent = 'Không tìm thấy dữ liệu cho mặt hàng này.';
    return;
  }

  empty.style.display = 'none';
  wrap.style.display = 'block';

  // Summary cards
  const cards = document.getElementById('priceSummaryCards');
  cards.innerHTML = [
    { label: 'Số NCC', value: d.series.length, icon: 'bi-building' },
    { label: 'Giá TB toàn thị trường', value: fmtPrice(d.avg_global), icon: 'bi-currency-exchange' },
    { label: 'Cảnh báo bất thường', value: d.anomalies.length, icon: 'bi-exclamation-triangle', warn: d.anomalies.length > 0 },
  ].map(c => `
    <div class="col-md-4">
      <div class="stat-card glass-card" style="${c.warn ? 'border-left:3px solid hsl(38 95% 55%)' : ''}">
        <div class="stat-icon"><i class="bi ${c.icon}"></i></div>
        <div class="stat-content">
          <p class="stat-label">${c.label}</p>
          <h3 class="stat-value" style="font-size:1.1rem;${c.warn ? 'color:hsl(38 95% 55%)' : ''}">${c.value}</h3>
        </div>
      </div>
    </div>`).join('');

  // SVG Line Chart
  _drawPriceLineSvg(d);

  // Supplier table
  const tbody = document.getElementById('supplierCompareBody');
  tbody.innerHTML = d.series.map((s, i) => {
    const color = CHART_COLORS[i % CHART_COLORS.length];
    const isAnomaly = d.anomalies.some(a => a.seller_mst === s.seller_mst);
    return `<tr>
      <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:6px"></span>${s.seller_name}</td>
      <td class="text-muted" style="font-size:.8rem">${s.seller_mst}</td>
      <td class="text-end">${s.purchase_count}</td>
      <td class="text-end fw-semibold">${fmtPrice(s.avg_price)}</td>
      <td class="text-end text-success">${fmtPrice(s.min_price)}</td>
      <td class="text-end text-danger">${fmtPrice(s.max_price)}</td>
      <td class="text-center">${isAnomaly
        ? '<span class="badge" style="background:hsl(38 95% 55%);font-size:.75rem">Bất thường</span>'
        : '<span class="badge bg-success" style="font-size:.75rem">Bình thường</span>'}</td>
    </tr>`;
  }).join('');

  // Anomalies
  const anomWrap = document.getElementById('priceAnomaliesWrap');
  const anomList = document.getElementById('priceAnomaliesList');
  if (d.anomalies.length) {
    anomWrap.style.display = 'block';
    anomList.innerHTML = d.anomalies.map(a => `
      <div class="d-flex align-items-center gap-3 py-2" style="border-bottom:1px solid hsl(var(--border))">
        <i class="bi bi-arrow-up-circle-fill" style="color:hsl(0 72% 60%)"></i>
        <span style="font-size:.85rem">
          <strong>${a.seller_name}</strong> — Tháng ${a.month}:
          <strong>${fmtPrice(a.price)}</strong>
          <span class="text-danger">(+${a.pct_above}% so với TB ${fmtPrice(a.avg_global)})</span>
        </span>
      </div>`).join('');
  } else {
    anomWrap.style.display = 'none';
  }
}

function _drawPriceLineSvg(d) {
  const svg = document.getElementById('priceTrendsSvg');
  const legend = document.getElementById('priceTrendsLegend');
  if (!svg) return;

  const W = svg.clientWidth || 700, H = 280;
  const pad = { top: 20, right: 20, bottom: 50, left: 80 };
  const cW = W - pad.left - pad.right;
  const cH = H - pad.top - pad.bottom;
  const months = d.months;
  const n = months.length;
  if (!n) { svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="gray">Không có dữ liệu</text>'; return; }

  const allPrices = d.series.flatMap(s => s.prices.filter(p => p !== null));
  const maxP = Math.max(...allPrices) * 1.1 || 1;

  const xPos = i => pad.left + (n === 1 ? cW / 2 : i * cW / (n - 1));
  const yPos = v => pad.top + cH - (v / maxP) * cH;

  let html = '';

  // Grid lines
  [0, 0.25, 0.5, 0.75, 1].forEach(t => {
    const y = pad.top + cH * (1 - t);
    const val = Math.round(maxP * t);
    html += `<line x1="${pad.left}" y1="${y}" x2="${W - pad.right}" y2="${y}" stroke="hsl(var(--border))" stroke-width="1" stroke-dasharray="4"/>`;
    html += `<text x="${pad.left - 6}" y="${y + 4}" text-anchor="end" fill="hsl(var(--text-muted))" font-size="11">${new Intl.NumberFormat('vi-VN', {notation:'compact'}).format(val)}</text>`;
  });

  // X labels
  months.forEach((m, i) => {
    html += `<text x="${xPos(i)}" y="${H - 8}" text-anchor="middle" fill="hsl(var(--text-muted))" font-size="11">${m.slice(5)}</text>`;
  });

  // Series lines + dots
  d.series.forEach((s, si) => {
    const color = CHART_COLORS[si % CHART_COLORS.length];
    let pathD = '';
    const points = s.prices.map((p, i) => p !== null ? { x: xPos(i), y: yPos(p) } : null);
    points.forEach((pt, i) => {
      if (!pt) return;
      if (pathD === '') pathD = `M${pt.x},${pt.y}`;
      else {
        const prev = points.slice(0, i).reverse().find(Boolean);
        if (prev) pathD += ` C${(prev.x + pt.x) / 2},${prev.y} ${(prev.x + pt.x) / 2},${pt.y} ${pt.x},${pt.y}`;
        else pathD += ` L${pt.x},${pt.y}`;
      }
    });
    if (pathD) html += `<path d="${pathD}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/>`;
    points.forEach(pt => {
      if (pt) html += `<circle cx="${pt.x}" cy="${pt.y}" r="4" fill="${color}" stroke="hsl(var(--surface))" stroke-width="1.5"/>`;
    });
  });

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = html;

  // Legend
  legend.innerHTML = d.series.map((s, i) =>
    `<span class="d-flex align-items-center gap-1" style="font-size:.8rem">
      <span style="width:20px;height:3px;background:${CHART_COLORS[i % CHART_COLORS.length]};border-radius:2px"></span>
      ${s.seller_name}
    </span>`).join('');
}

// ── VAT Forecast ──────────────────────────────────────────────────────────────
async function loadVatForecast() {
  const year = document.getElementById('vatForecastYear')?.value || new Date().getFullYear();
  const empty = document.getElementById('vatForecastEmpty');
  if (empty) empty.style.display = 'block';

  try {
    const r = await fetch('/api/analytics/vat-forecast?year=' + year);
    const d = await r.json();
    if (!d.success) throw new Error(d.error || 'Lỗi API');
    _renderVatForecast(d);
  } catch (e) {
    if (empty) { empty.style.display = 'block'; empty.querySelector('p').textContent = 'Lỗi tải dữ liệu: ' + e.message; }
  }
}

function _renderVatForecast(d) {
  const empty = document.getElementById('vatForecastEmpty');
  if (empty) empty.style.display = 'none';

  // Summary cards
  const s = d.summary;
  document.getElementById('vatSummaryCards').innerHTML = [
    { label: 'Tổng thuế đầu ra', value: fmtPrice(s.total_output_vat), icon: 'bi-arrow-up-circle', color: 'hsl(160 64% 40%)' },
    { label: 'Tổng thuế đầu vào KT', value: fmtPrice(s.total_input_vat), icon: 'bi-arrow-down-circle', color: 'hsl(200 80% 50%)' },
    { label: 'Số thuế phải nộp', value: fmtPrice(s.total_net_vat), icon: 'bi-cash-stack', color: s.total_net_vat > 0 ? 'hsl(0 72% 55%)' : 'hsl(160 64% 40%)' },
    { label: 'Tháng có dữ liệu', value: s.months_with_data + ' tháng', icon: 'bi-calendar-check' },
  ].map(c => `
    <div class="col-sm-6 col-lg-3">
      <div class="stat-card glass-card">
        <div class="stat-icon"><i class="bi ${c.icon}" style="${c.color ? 'color:' + c.color : ''}"></i></div>
        <div class="stat-content">
          <p class="stat-label">${c.label}</p>
          <h3 class="stat-value" style="font-size:1rem;${c.color ? 'color:' + c.color : ''}">${c.value}</h3>
        </div>
      </div>
    </div>`).join('');

  // Warning
  const warnEl = document.getElementById('vatForecastWarning');
  const warnMsg = document.getElementById('vatForecastWarningMsg');
  const hasWarn = d.forecast?.some(f => f.warning);
  if (warnEl) {
    if (hasWarn) {
      const wm = d.forecast.find(f => f.warning);
      warnEl.style.display = 'flex';
      warnEl.style.cssText += ';background:hsl(38 95% 55% / .15);border:1px solid hsl(38 95% 55% / .4);color:hsl(38 95% 55%);border-radius:12px;padding:12px 16px';
      if (warnMsg) warnMsg.textContent = `Cảnh báo: Thuế GTGT dự báo tháng ${wm.month} tăng >30% so với kỳ trước (${fmtPrice(wm.net_vat_forecast)}). Hãy chuẩn bị nguồn tiền nộp thuế.`;
    } else {
      warnEl.style.display = 'none';
    }
  }

  // Chart
  document.getElementById('vatChartWrap').style.display = 'block';
  _drawVatBarSvg(d);

  // Monthly detail table
  document.getElementById('vatDetailWrap').style.display = 'block';
  const tbody = document.getElementById('vatDetailBody');
  const forecastMonths = new Set((d.forecast || []).map(f => f.month));
  const forecastMap = Object.fromEntries((d.forecast || []).map(f => [f.month, f]));

  const actualRows = d.actual.map(a => `<tr style="${!a.has_data ? 'opacity:.4' : ''}">
    <td class="fw-semibold">${a.month}</td>
    <td class="text-end text-success">${a.has_data ? fmtPrice(a.output_vat) : '—'}</td>
    <td class="text-end" style="color:hsl(200 80% 55%)">${a.has_data ? fmtPrice(a.input_vat) : '—'}</td>
    <td class="text-end fw-bold" style="color:${a.net_vat > 0 ? 'hsl(0 72% 55%)' : 'hsl(160 64% 45%)'}">${a.has_data ? fmtPrice(a.net_vat) : '—'}</td>
    <td class="text-center"><span class="badge bg-secondary" style="font-size:.72rem">Thực tế</span></td>
  </tr>`).join('');

  const forecastRows = (d.forecast || []).map(f => `<tr style="background:hsl(32 95% 55% / .08)">
    <td class="fw-semibold">${f.month} <i class="bi bi-stars" style="color:hsl(32 95% 55%);font-size:.75rem"></i></td>
    <td class="text-end text-muted">—</td>
    <td class="text-end text-muted">—</td>
    <td class="text-end fw-bold" style="color:hsl(32 95% 55%)">${fmtPrice(f.net_vat_forecast)}</td>
    <td class="text-center"><span class="badge" style="background:hsl(32 95% 55%);font-size:.72rem">${f.warning ? '⚠ Tăng mạnh' : 'Dự báo'}</span></td>
  </tr>`).join('');

  tbody.innerHTML = actualRows + forecastRows;
}

function _drawVatBarSvg(d) {
  const svg = document.getElementById('vatForecastSvg');
  if (!svg) return;
  const W = svg.clientWidth || 700, H = 280;
  const pad = { top: 20, right: 20, bottom: 50, left: 80 };
  const cW = W - pad.left - pad.right, cH = H - pad.top - pad.bottom;

  const allData = [
    ...d.actual.filter(a => a.has_data).map(a => ({ month: a.month, val: a.net_vat, forecast: false })),
    ...(d.forecast || []).map(f => ({ month: f.month, val: f.net_vat_forecast, forecast: true, warn: f.warning })),
  ];

  if (!allData.length) { svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="gray">Chưa có dữ liệu</text>'; return; }

  const maxV = Math.max(...allData.map(a => Math.abs(a.val))) * 1.15 || 1;
  const barW = Math.max(8, cW / allData.length * 0.6);
  const xPos = i => pad.left + (i + 0.5) * cW / allData.length;
  const zeroY = pad.top + cH * (maxV / (maxV * 2 || 1));
  const yPos = v => pad.top + cH / 2 - (v / maxV) * (cH / 2);

  let html = '';
  // Zero line
  html += `<line x1="${pad.left}" y1="${pad.top + cH / 2}" x2="${W - pad.right}" y2="${pad.top + cH / 2}" stroke="hsl(var(--border))" stroke-width="1.5"/>`;

  // Grid
  [0.5, 1].forEach(t => {
    const y1 = pad.top + cH / 2 - (t * cH / 2);
    const y2 = pad.top + cH / 2 + (t * cH / 2);
    const val = Math.round(maxV * t);
    [y1, y2].forEach(y => {
      html += `<line x1="${pad.left}" y1="${y}" x2="${W - pad.right}" y2="${y}" stroke="hsl(var(--border))" stroke-width="1" stroke-dasharray="3"/>`;
    });
    html += `<text x="${pad.left - 6}" y="${y1 + 4}" text-anchor="end" fill="hsl(var(--text-muted))" font-size="10">${new Intl.NumberFormat('vi-VN',{notation:'compact'}).format(val)}</text>`;
    html += `<text x="${pad.left - 6}" y="${y2 + 4}" text-anchor="end" fill="hsl(var(--text-muted))" font-size="10">-${new Intl.NumberFormat('vi-VN',{notation:'compact'}).format(val)}</text>`;
  });

  allData.forEach((item, i) => {
    const x = xPos(i);
    const isPos = item.val >= 0;
    const barTop = isPos ? yPos(item.val) : pad.top + cH / 2;
    const barH = Math.abs(yPos(item.val) - (pad.top + cH / 2));
    const color = item.forecast ? 'hsl(32 95% 55%)' : (isPos ? 'hsl(160 64% 40%)' : 'hsl(200 80% 55%)');
    html += `<rect x="${x - barW / 2}" y="${barTop}" width="${barW}" height="${Math.max(2, barH)}" rx="3" fill="${color}" opacity="${item.forecast ? 0.75 : 0.9}"/>`;
    html += `<text x="${x}" y="${H - 8}" text-anchor="middle" fill="hsl(var(--text-muted))" font-size="10">${item.month.slice(5)}</text>`;
    if (item.warn) html += `<text x="${x}" y="${barTop - 4}" text-anchor="middle" font-size="12">⚠</text>`;
  });

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = html;
}


// ── Multi-MST Profile Management ──────────────────────────────────────────────
async function loadTaxpayerProfiles() {
    const selector = document.getElementById("globalTaxpayerSelector");
    const tbody = document.getElementById("taxpayerProfilesTableBody");
    
    try {
        const profiles = await apiCall("/api/profiles");
        
        // 1. Populate global navbar selector
        if (selector) {
            selector.innerHTML = '<option value="all">-- Tất cả doanh nghiệp --</option>';
            profiles.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.mst;
                opt.textContent = `[${p.mst}] ${p.company_name}`;
                if (window.activeTaxpayerMst === p.mst) {
                    opt.selected = true;
                }
                selector.appendChild(opt);
            });
            // Ensure synchronization with template state
            if (window.activeTaxpayerMst) {
                selector.value = window.activeTaxpayerMst;
            }
        }
        
        // 2. Populate table in Settings if it exists
        if (tbody) {
            if (profiles.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-secondary py-4">Chưa có mã số thuế nào được cấu hình.</td></tr>';
                return;
            }
            
            tbody.innerHTML = profiles.map(p => {
                const statusBadge = p.mst === window.activeTaxpayerMst
                    ? '<span class="badge bg-primary text-white d-inline-flex align-items-center gap-1"><i class="bi bi-star-fill"></i> Đang chọn</span>'
                    : (p.is_active 
                        ? '<span class="badge bg-success-subtle text-success d-inline-flex align-items-center gap-1"><i class="bi bi-check-circle-fill"></i> Hoạt động</span>' 
                        : '<span class="badge bg-secondary-subtle text-secondary">Tạm dừng</span>');
                
                return `
                    <tr data-mst="${p.mst}">
                        <td class="fw-bold text-dark font-monospace">${p.mst}</td>
                        <td class="fw-medium">${p.company_name}</td>
                        <td class="text-secondary small">${p.gdt_username}</td>
                        <td>${statusBadge}</td>
                        <td>
                            ${window.currentUserRole === "viewer" ? "" : `
                            <div class="d-flex gap-1">
                                <button class="btn btn-sm btn-outline-warning px-2 btn-edit-profile" title="Sửa cấu hình"><i class="bi bi-pencil-square"></i></button>
                                <button class="btn btn-sm btn-outline-danger px-2 btn-delete-profile" title="Xóa cấu hình"><i class="bi bi-trash"></i></button>
                            </div>
                            `}
                        </td>
                    </tr>
                `;
            }).join("");

            // Bind edit/delete buttons
            tbody.querySelectorAll("tr").forEach(row => {
                const mst = row.getAttribute("data-mst");
                const profile = profiles.find(p => p.mst === mst);
                
                row.querySelector(".btn-edit-profile")?.addEventListener("click", () => {
                    document.getElementById("profileMst").value = profile.mst;
                    document.getElementById("profileMst").readOnly = true;
                    document.getElementById("profileCompanyName").value = profile.company_name;
                    document.getElementById("profileGdtUser").value = profile.gdt_username;
                    document.getElementById("profileGdtPass").value = ""; 
                    document.getElementById("profileGdtPass").placeholder = "Nhập mật khẩu mới nếu muốn thay đổi...";
                    document.getElementById("profileGdtPass").required = false;
                    document.getElementById("profileFormTitle").textContent = "Cập nhật doanh nghiệp: " + profile.mst;
                });

                row.querySelector(".btn-delete-profile")?.addEventListener("click", () => {
                    if (confirm(`Bạn có chắc chắn muốn xóa doanh nghiệp MST ${profile.mst} (${profile.company_name}) và TẤT CẢ hóa đơn liên quan không? Hành động này không thể hoàn tác.`)) {
                        handleDeleteProfile(profile.mst);
                    }
                });
            });
        }
    } catch (error) {
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Lỗi tải hồ sơ: ${error.message}</td></tr>`;
        }
    }
}

async function handleDeleteProfile(mst) {
    try {
        const res = await apiCall(`/api/profiles/${mst}`, { method: "DELETE" });
        renderAlert(res.message || `Đã xóa doanh nghiệp MST ${mst}`, "success");
        if (window.activeTaxpayerMst === mst) {
            await handleSwitchTaxpayerProfile("all");
        } else {
            await loadTaxpayerProfiles();
        }
    } catch (error) {
        renderAlert("Lỗi xóa hồ sơ: " + error.message, "danger");
    }
}

async function handleSwitchTaxpayerProfile(mst) {
    try {
        const res = await apiCall("/api/profiles/switch", {
            method: "POST",
            body: JSON.stringify({ mst: mst })
        });
        if (res.success) {
            window.activeTaxpayerMst = res.active_taxpayer_mst || "";
            const selector = document.getElementById("globalTaxpayerSelector");
            if (selector) selector.value = mst;
            
            // Reload all lists and dashboards
            handleInvoiceSearch();
            loadLocalInvoices();
            
            // If settings page is active, reload profiles table
            if (document.getElementById("settings-content") && document.getElementById("settings-content").classList.contains("show")) {
                loadTaxpayerProfiles();
            }
            
            // If VAT Refund page is active, reload
            if (document.getElementById("vat-refund-content") && document.getElementById("vat-refund-content").classList.contains("show")) {
                loadVATRefundData();
            }
            renderAlert(`Đã chuyển sang doanh nghiệp: ${mst === "all" ? "Tất cả" : mst}`, "success");
        }
    } catch (error) {
        renderAlert("Lỗi chuyển đổi doanh nghiệp: " + error.message, "danger");
    }
}

function initializeTaxpayerProfilesEvents() {
    // 1. Selector switch on navbar
    document.getElementById("globalTaxpayerSelector")?.addEventListener("change", (e) => {
        handleSwitchTaxpayerProfile(e.target.value);
    });

    // 2. Add/Edit Form submission
    const form = document.getElementById("taxpayerProfileForm");
    form?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const mst = document.getElementById("profileMst").value;
        const companyName = document.getElementById("profileCompanyName").value;
        const gdtUser = document.getElementById("profileGdtUser").value;
        const gdtPass = document.getElementById("profileGdtPass").value;

        const payload = {
            mst: mst,
            company_name: companyName,
            gdt_username: gdtUser
        };
        if (gdtPass) {
            payload.gdt_password = gdtPass;
        }

        try {
            await apiCall("/api/profiles", {
                method: "POST",
                body: JSON.stringify(payload)
            });
            renderAlert("Lưu cấu hình doanh nghiệp thành công!", "success");
            resetProfileForm();
            await loadTaxpayerProfiles();
        } catch (error) {
            renderAlert("Lỗi lưu cấu hình: " + error.message, "danger");
        }
    });

    // 3. Reset form button
    document.getElementById("btnResetProfileForm")?.addEventListener("click", resetProfileForm);
    
    // 4. Toggle password visibility in form
    document.getElementById("toggleProfileGdtPass")?.addEventListener("click", () => {
        const input = document.getElementById("profileGdtPass");
        const icon = document.querySelector("#toggleProfileGdtPass i");
        if (input && icon) {
            if (input.type === "password") {
                input.type = "text";
                icon.className = "bi bi-eye-slash";
            } else {
                input.type = "password";
                icon.className = "bi bi-eye";
            }
        }
    });
}

function resetProfileForm() {
    const form = document.getElementById("taxpayerProfileForm");
    if (form) form.reset();
    const mstInput = document.getElementById("profileMst");
    if (mstInput) {
        mstInput.readOnly = false;
        mstInput.required = true;
    }
    const passInput = document.getElementById("profileGdtPass");
    if (passInput) {
        passInput.placeholder = "Nhập mật khẩu...";
        passInput.required = true;
    }
    const title = document.getElementById("profileFormTitle");
    if (title) title.textContent = "Thêm doanh nghiệp mới";
}

async function checkUserRoleAndEnforce() {
    try {
        const data = await apiCall("/api/session-status", { redirectOn401: false });
        if (data && data.logged_in) {
            window.currentUserRole = data.role || "viewer";
            applyRolePermissions(window.currentUserRole);
        } else {
            window.currentUserRole = "viewer";
            applyRolePermissions("viewer");
        }
    } catch (e) {
        console.error("Error loading session status for role enforcement:", e);
        window.currentUserRole = "viewer";
        applyRolePermissions("viewer");
    }
}

function applyRolePermissions(role) {
    if (role === "admin") {
        return;
    }

    if (role === "auditor") {
        // Mask settings edit for auditor
        const saveBtn = document.getElementById("btnSaveSettings");
        if (saveBtn) saveBtn.style.display = "none";
        
        const testEmailBtn = document.getElementById("btnTestEmail");
        if (testEmailBtn) testEmailBtn.style.display = "none";
        
        const testAuditBtn = document.getElementById("btnTestAudit");
        if (testAuditBtn) testAuditBtn.style.display = "none";
        
        const settingsForm1 = document.getElementById("smtpSettingsForm");
        if (settingsForm1) {
            const inputs = settingsForm1.querySelectorAll("input, select, textarea");
            inputs.forEach(el => el.disabled = true);
        }
        const settingsForm2 = document.getElementById("schedulerSettingsForm");
        if (settingsForm2) {
            const inputs = settingsForm2.querySelectorAll("input, select, textarea");
            inputs.forEach(el => el.disabled = true);
        }
        const settingsForm3 = document.getElementById("aiSettingsForm");
        if (settingsForm3) {
            const inputs = settingsForm3.querySelectorAll("input, select, textarea");
            inputs.forEach(el => el.disabled = true);
        }
    } else if (role === "viewer") {
        // Hide settings tab
        const settingsTab = document.getElementById("settings-tab");
        if (settingsTab) settingsTab.style.display = "none";
        
        // Hide delete, clear, upload, exports
        const clearBtn = document.getElementById("btnClearLocalDb");
        if (clearBtn) clearBtn.style.display = "none";
        
        const exportExcelBtn = document.getElementById("btnExportLocalExcel");
        if (exportExcelBtn) exportExcelBtn.style.display = "none";
        
        const exportMainBtn = document.getElementById("exportExcelButton");
        if (exportMainBtn) exportMainBtn.style.display = "none";
        
        const exportPartnersPdfBtn = document.getElementById("btnDownloadPartnersPdf");
        if (exportPartnersPdfBtn) exportPartnersPdfBtn.style.display = "none";
        
        const printReportBtn = document.getElementById("btnPrintReport");
        if (printReportBtn) printReportBtn.style.display = "none";
        
        const dropZone = document.getElementById("dropZone");
        if (dropZone) dropZone.style.display = "none";
        
        const profileForm = document.getElementById("taxpayerProfileForm");
        if (profileForm) profileForm.style.display = "none";
        const profileFormTitle = document.getElementById("profileFormTitle");
        if (profileFormTitle) profileFormTitle.style.display = "none";

        const aiAuditBtn = document.getElementById("btnRunAiAudit");
        if (aiAuditBtn) aiAuditBtn.style.display = "none";

        const saveCategoryBtn = document.getElementById("btnSaveCategoryChange");
        if (saveCategoryBtn) saveCategoryBtn.style.display = "none";
        
        const viewerDownloadPdf = document.getElementById("btnViewerDownloadPdf");
        if (viewerDownloadPdf) viewerDownloadPdf.style.display = "none";

        const viewerDownloadXml = document.getElementById("btnViewerDownloadXml");
        if (viewerDownloadXml) viewerDownloadXml.style.display = "none";

        const viewPrintInvoiceBtn = document.getElementById("btnViewPrintInvoice");
        if (viewPrintInvoiceBtn) viewPrintInvoiceBtn.style.display = "none";
    }
}


// ── Foreign Contractor Tax (FCT/NTNN) Management ───────────────────────────
function initializeFctEvents() {
    const periodType = document.getElementById("fctPeriodType");
    const form = document.getElementById("fctDeclarationForm");
    const exportBtn = document.getElementById("btnExportFctExcel");
    const fctTab = document.getElementById("fct-tab");

    if (periodType) {
        populateFctPeriods();
        periodType.addEventListener("change", populateFctPeriods);
    }

    if (form) {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            loadFctDeclarationData();
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener("click", () => {
            exportFctExcel();
        });
    }

    if (fctTab) {
        fctTab.addEventListener("shown.bs.tab", () => {
            loadFctDeclarationData();
        });
    }
}

function populateFctPeriods() {
    const type = document.getElementById("fctPeriodType")?.value || "monthly";
    const select = document.getElementById("fctPeriodValue");
    const label = document.getElementById("fctPeriodValueLabel");
    if (!select) return;
    select.innerHTML = "";
    if (type === "monthly") {
        if (label) label.textContent = "Tháng Kê Khai";
        for (let i = 1; i <= 12; i++) {
            const opt = document.createElement("option");
            const val = i < 10 ? `0${i}` : `${i}`;
            opt.value = val;
            opt.textContent = `Tháng ${i}`;
            if (i === new Date().getMonth() + 1) opt.selected = true;
            select.appendChild(opt);
        }
    } else {
        if (label) label.textContent = "Quý Kê Khai";
        for (let i = 1; i <= 4; i++) {
            const opt = document.createElement("option");
            opt.value = i.toString();
            opt.textContent = `Quý ${i}`;
            if (i === Math.floor(new Date().getMonth() / 3) + 1) opt.selected = true;
            select.appendChild(opt);
        }
    }
}

async function loadFctDeclarationData() {
    const btn = document.getElementById("btnLoadFctData");
    const btnText = document.getElementById("btnLoadFctText");
    const tbody = document.getElementById("fctTableBody");
    const tfoot = document.getElementById("fctTableFoot");

    if (btn && btnText) {
        btn.disabled = true;
        btnText.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang phân tích...';
    }

    try {
        const type = document.getElementById("fctPeriodType").value;
        const val = document.getElementById("fctPeriodValue").value;
        const year = document.getElementById("fctYear").value;

        const data = await apiCall(`/api/reports/fct-declaration?period_type=${type}&period_value=${val}&year=${year}`);
        
        if (!data || !data.success) {
            throw new Error(data?.error || "Không thể tải báo cáo.");
        }

        // 1. Summaries
        animateNumber(document.getElementById("fctVatPayable"), data.total_vat_withheld, true);
        animateNumber(document.getElementById("fctCitPayable"), data.total_cit_withheld, true);
        animateNumber(document.getElementById("fctTotalPayable"), data.total_fct_payable, true);
        
        // 2. Count badge
        const countBadge = document.getElementById("fctInvoicesCount");
        if (countBadge) countBadge.textContent = data.fct_invoices.length;

        // 3. Populate main 01/NTNN grid
        if (tbody) {
            if (data.fct_invoices.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="9" class="text-center text-secondary py-4">
                            <i class="bi bi-info-circle d-block mb-2" style="font-size: 1.5rem;"></i>
                            Không phát hiện hóa đơn dịch vụ số xuyên quốc gia nào trong kỳ này.
                        </td>
                    </tr>
                `;
                tfoot?.classList.add("d-none");
            } else {
                tbody.innerHTML = data.fct_invoices.map((inv, idx) => `
                    <tr>
                        <td class="text-center text-secondary font-monospace">${idx + 1}</td>
                        <td class="fw-semibold text-white">${inv.seller_name}</td>
                        <td class="text-center font-monospace small">${inv.seller_mst || "-"}</td>
                        <td><span class="badge bg-secondary-subtle text-secondary small">${inv.category}</span></td>
                        <td class="text-end fw-medium">${inv.amount.toLocaleString("vi-VN")} ₫</td>
                        <td class="text-center text-secondary">${(inv.vat_rate * 100).toFixed(0)}%</td>
                        <td class="text-end text-warning fw-medium">${inv.vat_withheld.toLocaleString("vi-VN")} ₫</td>
                        <td class="text-center text-secondary">${(inv.cit_rate * 100).toFixed(0)}%</td>
                        <td class="text-end text-danger fw-medium">${inv.cit_withheld.toLocaleString("vi-VN")} ₫</td>
                    </tr>
                `).join("");

                // Totals row
                document.getElementById("fctTotalRevenue").textContent = data.total_revenue.toLocaleString("vi-VN") + " ₫";
                document.getElementById("fctTotalVat").textContent = data.total_vat_withheld.toLocaleString("vi-VN") + " ₫";
                document.getElementById("fctTotalCit").textContent = data.total_cit_withheld.toLocaleString("vi-VN") + " ₫";
                tfoot?.classList.remove("d-none");
            }
        }

        // 4. Detailed detected list
        const invoicesList = document.getElementById("fctInvoicesList");
        if (invoicesList) {
            if (data.fct_invoices.length === 0) {
                invoicesList.innerHTML = '<div class="text-center text-secondary py-4 small">Không phát hiện hóa đơn nào.</div>';
            } else {
                invoicesList.innerHTML = data.fct_invoices.map(inv => `
                    <div class="p-3 mb-2 rounded border border-secondary border-opacity-10 bg-black bg-opacity-20 d-flex flex-column gap-2 hover-scale-sm transition-all">
                        <div class="d-flex justify-content-between align-items-start">
                            <span class="fw-bold text-primary-accent" style="font-size: 0.9rem;">${inv.seller_name}</span>
                            <span class="badge bg-success-subtle text-success small font-monospace">HĐ #${inv.number}</span>
                        </div>
                        <div class="d-flex justify-content-between text-secondary small">
                            <span>Ngày lập: ${inv.date}</span>
                            <span class="fw-semibold text-white">${inv.amount.toLocaleString("vi-VN")} ₫</span>
                        </div>
                        <div class="border-top border-secondary border-opacity-10 pt-2 mt-1 d-flex justify-content-between align-items-center small">
                            <span class="text-muted"><i class="bi bi-tag-fill me-1"></i>${inv.category}</span>
                            <span class="fw-bold text-success-accent">Thuế: ${(inv.fct_total).toLocaleString("vi-VN")} ₫</span>
                        </div>
                    </div>
                `).join("");
            }
        }

    } catch (error) {
        renderAlert("Lỗi phân tích FCT: " + error.message, "danger");
    } finally {
        if (btn && btnText) {
            btn.disabled = false;
            btnText.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Phân Tích & Tính Thuế NTNN';
        }
    }
}

function exportFctExcel() {
    const type = document.getElementById("fctPeriodType").value;
    const val = document.getElementById("fctPeriodValue").value;
    const year = document.getElementById("fctYear").value;

    const url = `/api/reports/fct-declaration/export-excel?period_type=${type}&period_value=${val}&year=${year}`;
    window.location.href = url;
}

/* ================================================================== */
/* v4.2.0 VAT Refund (Hoàn Thuế GTGT) UI Module                       */
/* ================================================================== --> */
function initializeVatRefundEvents() {
    const vatRefundTab = document.getElementById("vat-refund-tab");
    vatRefundTab?.addEventListener("shown.bs.tab", () => {
        loadVATRefundData();
    });

    document.getElementById("btnRefreshVatRefund")?.addEventListener("click", loadVATRefundData);

    // Bind export button triggers
    document.getElementById("btnExportMau01Word")?.addEventListener("click", () => {
        const text = document.getElementById("refundMau01Content").textContent;
        exportVATRefundDossier(text, "doc", "dossier");
    });
    
    document.getElementById("btnExportMau01Pdf")?.addEventListener("click", () => {
        const text = document.getElementById("refundMau01Content").textContent;
        exportVATRefundDossier(text, "pdf", "dossier");
    });
    
    document.getElementById("btnExportJustificationWord")?.addEventListener("click", () => {
        const text = document.getElementById("refundJustificationContent").textContent;
        exportVATRefundDossier(text, "doc", "justification");
    });
    
    document.getElementById("btnExportJustificationPdf")?.addEventListener("click", () => {
        const text = document.getElementById("refundJustificationContent").textContent;
        exportVATRefundDossier(text, "pdf", "justification");
    });
}

async function loadVATRefundData() {
    const mst = window.activeTaxpayerMst;
    
    // UI Selectors
    const statusText = document.getElementById("refundStatusText");
    const statusSubtext = document.getElementById("refundStatusSubtext");
    const statusIcon = document.getElementById("refundStatusIcon");
    const complianceRating = document.getElementById("refundComplianceRating");
    const mstBadge = document.getElementById("refundMSTBadge");
    
    const exportRatioVal = document.getElementById("refundExportRatioVal");
    const exportRatioProgress = document.getElementById("refundExportRatioProgress");
    const ruleRatioIcon = document.getElementById("ruleRatioIcon");
    
    const eligibleVatVal = document.getElementById("refundEligibleVatVal");
    const eligibleVatProgress = document.getElementById("refundEligibleVatProgress");
    const ruleVatIcon = document.getElementById("ruleVatIcon");
    
    const riskText = document.getElementById("refundRiskText");
    const ruleRiskIcon = document.getElementById("ruleRiskIcon");
    
    const mau01Content = document.getElementById("refundMau01Content");
    const justificationContent = document.getElementById("refundJustificationContent");
    const excludedList = document.getElementById("refundExcludedList");
    const excludedCountSpan = document.getElementById("excludedCount");
    
    // Reset/Loading state
    if (mstBadge) mstBadge.textContent = `MST: ${mst || "Chưa chọn"}`;
    if (statusText) statusText.textContent = "Đang thẩm định...";
    if (statusSubtext) statusSubtext.textContent = "Hệ thống đang kiểm toán và lập hồ sơ...";
    if (mau01Content) mau01Content.textContent = "Đang tải hồ sơ...";
    if (justificationContent) justificationContent.textContent = "Đang chạy AI lập luận phòng vệ...";
    if (excludedList) excludedList.innerHTML = '<div class="text-center text-secondary py-4 small">Đang phân tích...</div>';
    
    if (!mst || mst === "all") {
        if (statusText) statusText.textContent = "Chưa chọn MST";
        if (statusSubtext) statusSubtext.textContent = "Vui lòng chọn một Mã Số Thuế cụ thể ở góc trên Navbar để thẩm định.";
        if (statusIcon) statusIcon.innerHTML = '<i class="bi bi-exclamation-circle text-warning"></i>';
        if (mau01Content) mau01Content.textContent = "Chưa chọn Mã Số Thuế.";
        if (justificationContent) justificationContent.textContent = "Chưa chọn Mã Số Thuế.";
        if (excludedList) excludedList.innerHTML = '<div class="text-center text-secondary py-4 small">Vui lòng chọn một Mã Số Thuế cụ thể.</div>';
        return;
    }
    
    try {
        // 1. Fetch Eligibility Analysis
        const data = await apiCall(`/api/reports/vat-refund-eligibility?mst=${mst}`);
        if (!data || data.error) {
            throw new Error(data?.error || "Lỗi tải dữ liệu hoàn thuế.");
        }
        
        // 2. Render Status Card
        if (data.is_eligible) {
            statusText.textContent = "ĐỦ ĐIỀU KIỆN HOÀN THUẾ";
            statusSubtext.textContent = "Đầu vào đạt trên 300 triệu VND & tỷ lệ xuất khẩu đạt trên 10%.";
            statusIcon.innerHTML = '<i class="bi bi-shield-check text-success-accent"></i>';
            document.getElementById("refundEligibilityCard")?.classList.add("border-glow-active");
            document.getElementById("refundEligibilityCard")?.classList.remove("border-glow-warning");
        } else {
            statusText.textContent = "CHƯA ĐỦ ĐIỀU KIỆN";
            statusSubtext.textContent = "Cần tích lũy đủ 300 triệu VND VAT đầu vào hợp lệ và đạt tỷ lệ xuất khẩu 10%.";
            statusIcon.innerHTML = '<i class="bi bi-shield-x text-warning"></i>';
            document.getElementById("refundEligibilityCard")?.classList.remove("border-glow-active");
            document.getElementById("refundEligibilityCard")?.classList.add("border-glow-warning");
        }
        
        if (complianceRating) {
            complianceRating.textContent = `Rating: ${data.status}`;
            complianceRating.className = `badge py-1 px-2 ${data.status === "Safe" ? "bg-success" : data.status === "Caution" ? "bg-warning text-dark" : "bg-danger"}`;
        }
        
        // 3. Render Progress & Checklist
        const exportPct = (data.metrics.export_ratio * 100).toFixed(2);
        if (exportRatioVal) exportRatioVal.textContent = `${exportPct}%`;
        if (exportRatioProgress) {
            exportRatioProgress.style.width = `${Math.min(exportPct * 5, 100)}%`;
            exportRatioProgress.className = `progress-bar ${data.metrics.export_ratio >= 0.1 ? "bg-success-accent" : "bg-warning"}`;
        }
        if (ruleRatioIcon) {
            ruleRatioIcon.className = `bi ${data.metrics.export_ratio >= 0.1 ? "bi-check-circle-fill text-success" : "bi-x-circle-fill text-danger"}`;
        }
        
        if (eligibleVatVal) eligibleVatVal.textContent = `${data.metrics.eligible_input_vat.toLocaleString("vi-VN")} ₫`;
        if (eligibleVatProgress) {
            const vatPct = (data.metrics.eligible_input_vat / 300000000 * 100).toFixed(0);
            eligibleVatProgress.style.width = `${Math.min(vatPct, 100)}%`;
            eligibleVatProgress.className = `progress-bar ${data.metrics.eligible_input_vat >= 300000000 ? "bg-success-accent" : "bg-warning"}`;
        }
        if (ruleVatIcon) {
            ruleVatIcon.className = `bi ${data.metrics.eligible_input_vat >= 300000000 ? "bi-check-circle-fill text-success" : "bi-x-circle-fill text-danger"}`;
        }
        
        if (riskText) {
            riskText.textContent = data.status;
            riskText.className = `badge ${data.status === "Safe" ? "bg-success" : data.status === "Caution" ? "bg-warning text-dark" : "bg-danger"}`;
        }
        if (ruleRiskIcon) {
            ruleRiskIcon.className = `bi ${data.status === "Safe" ? "bi-check-circle-fill text-success" : data.status === "Caution" ? "bi-exclamation-triangle-fill text-warning" : "bi-x-circle-fill text-danger"}`;
        }
        
        // 4. Populate Excluded Invoices
        const ineligibles = data.ineligible_invoices || [];
        if (excludedCountSpan) excludedCountSpan.textContent = ineligibles.length;
        if (excludedList) {
            if (ineligibles.length === 0) {
                excludedList.innerHTML = '<div class="text-center text-secondary py-4 small"><i class="bi bi-check-circle text-success d-block mb-1"></i>Không có hóa đơn đầu vào nào bị loại bỏ khỏi hồ sơ hoàn thuế.</div>';
            } else {
                excludedList.innerHTML = ineligibles.map(inv => `
                    <div class="p-3 mb-2 rounded border border-danger border-opacity-10 bg-black bg-opacity-20 d-flex flex-column gap-1">
                        <div class="d-flex justify-content-between align-items-start">
                            <span class="fw-bold text-white small">${inv.seller_name}</span>
                            <span class="badge bg-danger-subtle text-danger font-monospace small">HĐ #${inv.number}</span>
                        </div>
                        <div class="d-flex justify-content-between text-secondary small" style="font-size: 0.8rem;">
                            <span>Ngày: ${inv.date}</span>
                            <span class="fw-semibold text-danger">Tiền thuế: ${inv.tax_amount.toLocaleString("vi-VN")} ₫</span>
                        </div>
                        <div class="text-warning small mt-1" style="font-size: 0.75rem;">
                            <i class="bi bi-exclamation-triangle-fill me-1"></i>Lý do loại trừ: ${inv.warning}
                        </div>
                    </div>
                `).join("");
            }
        }
        
        // 5. Fetch Compiled Dossier Templates
        const dossierRes = await apiCall("/api/reports/vat-refund-eligibility/dossier", {
            method: "POST",
            body: JSON.stringify({ mst: mst })
        });
        
        if (dossierRes && dossierRes.status === "success") {
            if (mau01Content) mau01Content.textContent = dossierRes.mau_01_ht;
            if (justificationContent) justificationContent.textContent = dossierRes.justification_letter;
        } else {
            if (mau01Content) mau01Content.textContent = "Không thể biên soạn tờ khai Mẫu 01/HT.";
            if (justificationContent) justificationContent.textContent = "Không thể biên soạn Báo cáo giải trình.";
        }
        
    } catch (error) {
        renderAlert("Lỗi thẩm định hoàn thuế: " + error.message, "danger");
        if (statusText) statusText.textContent = "Lỗi hệ thống";
        if (mau01Content) mau01Content.textContent = "Đã xảy ra lỗi khi tải dữ liệu.";
        if (justificationContent) justificationContent.textContent = "Đã xảy ra lỗi khi biên soạn báo cáo.";
        if (excludedList) excludedList.innerHTML = `<div class="text-center text-danger py-4 small">${error.message}</div>`;
    }
}

async function exportVATRefundDossier(content, format, type) {
    try {
        const response = await fetch("/api/reports/vat-refund-eligibility/dossier/export", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                content: content,
                format: format,
                type: type
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        
        const timestamp = new Date().toISOString().slice(0, 10);
        const filename = type === "dossier" 
            ? `Mau01_HT_HoanThue_${window.activeTaxpayerMst}_${timestamp}.${format}`
            : `AI_BaoCaoPhanTichRuiRo_${window.activeTaxpayerMst}_${timestamp}.${format}`;
            
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        renderAlert(`Xuất hồ sơ ${format.toUpperCase()} thành công!`, "success");
    } catch (error) {
        renderAlert("Không thể tải tệp xuất khẩu: " + error.message, "danger");
    }
}

/* ================================================================== */
/* v5.0.0 Bank Reconciliation (Đối Chiếu Ngân Hàng) UI Module          */
/* ================================================================== */
let activeSelectedTx = null;

function initializeBankReconcileEvents() {
    const reconcileTab = document.getElementById("bank-reconcile-tab");
    if (!reconcileTab) return;

    reconcileTab.addEventListener("shown.bs.tab", () => {
        loadBankTransactions();
        loadOutstandingInvoicesForReconcile();
    });

    document.getElementById("btnRefreshReconciliation")?.addEventListener("click", () => {
        loadBankTransactions();
        loadOutstandingInvoicesForReconcile();
    });

    document.getElementById("reconcileFilterStatus")?.addEventListener("change", () => {
        loadBankTransactions();
    });

    // Form file submit
    document.getElementById("bankStatementUploadForm")?.addEventListener("submit", handleBankStatementUpload);

    // AI Reconcile trigger
    document.getElementById("btnAutoReconcile")?.addEventListener("click", triggerAutoReconcileAI);

    // Manual match confirm
    document.getElementById("btnConfirmManualMatch")?.addEventListener("click", submitManualMatchOverride);

    // Drag and Drop listeners
    initializeReconcileDragAndDrop();
}

function initializeReconcileDragAndDrop() {
    const dragZone = document.getElementById("bankDragZone");
    const fileInput = document.getElementById("bankFileInput");
    const fileNameDisplay = document.getElementById("bankFileNameDisplay");

    if (!dragZone || !fileInput) return;

    dragZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dragZone.style.borderColor = "var(--primary-accent)";
        dragZone.style.background = "rgba(46, 196, 182, 0.08)";
    });

    ["dragleave", "dragend"].forEach(type => {
        dragZone.addEventListener(type, () => {
            dragZone.style.borderColor = "rgba(255, 255, 255, 0.15)";
            dragZone.style.background = "rgba(0,0,0,0.25)";
        });
    });

    dragZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dragZone.style.borderColor = "rgba(255, 255, 255, 0.15)";
        dragZone.style.background = "rgba(0,0,0,0.25)";
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            fileNameDisplay.textContent = files[0].name;
            fileNameDisplay.className = "text-success fw-bold d-block";
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
            fileNameDisplay.className = "text-success fw-bold d-block";
        }
    });
}

async function handleBankStatementUpload(event) {
    event.preventDefault();
    const fileInput = document.getElementById("bankFileInput");
    const bankSelect = document.getElementById("reconcileBankSelect");
    const accountNum = document.getElementById("reconcileAccountNum");
    const uploadBtn = document.getElementById("btnUploadBankStatement");

    if (!fileInput || fileInput.files.length === 0) {
        renderAlert("Vui lòng kéo thả hoặc chọn tệp sổ phụ trước khi tải lên.", "warning");
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("bank_name", bankSelect.value);
    formData.append("account_number", accountNum.value || "");
    formData.append("mst", window.activeTaxpayerMst || "0109998887");

    const originalText = uploadBtn.innerHTML;
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang phân tích sổ phụ...';

    try {
        const response = await fetch("/api/bank/reconcile/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Không thể phân tích dữ liệu sổ phụ.");
        }

        renderAlert(`Nhập thành công sổ phụ: Đã đọc ${data.records_parsed || 0} giao dịch giao dịch và ghi nhận thành công!`, "success");
        
        // Reset file display
        document.getElementById("bankFileNameDisplay").textContent = "Kéo thả tệp Sổ Phụ (.xlsx, .csv) vào đây";
        document.getElementById("bankFileNameDisplay").className = "text-white fw-medium d-block";
        fileInput.value = "";

        // Reload data tables
        await loadBankTransactions();
    } catch (error) {
        renderAlert(`Lỗi phân tích sổ phụ: ${error.message}`, "danger");
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = originalText;
    }
}

async function loadBankTransactions() {
    const tbody = document.getElementById("bankTransactionsTableBody");
    if (!tbody) return;

    const filterStatus = document.getElementById("reconcileFilterStatus")?.value || "unreconciled";
    const mst = window.activeTaxpayerMst || "0109998887";

    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary" role="status"></div> Đang tải danh sách giao dịch sổ phụ...</td></tr>';

    try {
        const response = await fetch(`/api/bank/reconcile/transactions?mst=${mst}&status=${filterStatus}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Không thể tải danh sách giao dịch.");
        }

        const txs = data || [];
        if (txs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-secondary py-5">
                        <div class="empty-state">
                            <span class="empty-icon"><i class="bi bi-bank"></i></span>
                            <p class="mb-0">Không tìm thấy giao dịch nào khớp với bộ lọc.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = txs.map(tx => {
            const dateStr = new Date(tx.transaction_date).toLocaleDateString("vi-VN");
            const amtClass = tx.amount > 0 ? "text-success fw-bold" : "text-danger";
            const amtVal = Math.abs(tx.amount);
            
            const isReconciled = tx.status === "matched";
            const badgeClass = isReconciled 
                ? "bg-success-subtle text-success" 
                : "bg-warning-subtle text-warning";
            const badgeText = isReconciled 
                ? `<span class="badge ${badgeClass} small"><i class="bi bi-check-circle-fill"></i> Đã khớp</span>` 
                : `<span class="badge ${badgeClass} small"><i class="bi bi-hourglass-split"></i> Chờ khớp</span>`;

            return `
                <tr data-id="${tx.id}" style="cursor: pointer;" class="bank-tx-row ${activeSelectedTx && activeSelectedTx.id === tx.id ? 'bg-white bg-opacity-10' : ''}">
                    <td class="small font-monospace text-nowrap">${dateStr}</td>
                    <td class="small font-monospace text-secondary">${tx.reference_number || tx.id.slice(0, 8)}</td>
                    <td>
                        <div class="fw-semibold text-white small">${tx.description}</div>
                    </td>
                    <td class="text-end ${amtClass}">${Number(amtVal).toLocaleString("vi-VN")} ₫</td>
                    <td class="text-center">${badgeText}</td>
                </tr>
            `;
        }).join("");

        // Bind row selection events for manual match
        tbody.querySelectorAll("tr").forEach(row => {
            row.addEventListener("click", () => {
                const txId = row.getAttribute("data-id");
                const selectedTx = txs.find(t => t.id === txId);
                
                // Highlight select row
                tbody.querySelectorAll("tr").forEach(r => r.classList.remove("bg-white", "bg-opacity-10"));
                row.classList.add("bg-white", "bg-opacity-10");
                
                openManualMatchPanel(selectedTx);
            });
        });

    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Lỗi: ${error.message}</td></tr>`;
    }
}

async function loadOutstandingInvoicesForReconcile() {
    const select = document.getElementById("manualMatchInvoiceSelect");
    if (!select) return;

    try {
        const response = await fetch("/api/invoices/local");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Không thể tải danh sách hóa đơn.");
        }

        const invoices = data.invoices || [];
        // Filter invoices that are not fully reconciled or not paid (just listing all active ones for manual override)
        if (invoices.length === 0) {
            select.innerHTML = '<option value="">-- Không có hóa đơn trong kho --</option>';
            return;
        }

        select.innerHTML = '<option value="">-- Chọn Hóa Đơn --</option>';
        invoices.forEach(inv => {
            const opt = document.createElement("option");
            opt.value = inv.id;
            opt.textContent = `[${inv.number}] - ${inv.seller_name} - ${Number(inv.total_amount).toLocaleString("vi-VN")} ₫`;
            select.appendChild(opt);
        });

    } catch (error) {
        select.innerHTML = `<option value="">Lỗi: ${error.message}</option>`;
    }
}

function openManualMatchPanel(tx) {
    activeSelectedTx = tx;
    const panel = document.getElementById("manualMatchPanel");
    const label = document.getElementById("selectedTxLabel");

    if (!panel || !label) return;

    panel.style.display = "block";
    const amount = Math.abs(tx.amount);
    label.innerHTML = `
        <span class="text-white">GD: <strong>${tx.description}</strong></span><br>
        <span class="text-secondary small">Mã: ${tx.reference_number || tx.id} | Số tiền: <strong>${Number(amount).toLocaleString("vi-VN")} ₫</strong></span>
    `;
}

async function submitManualMatchOverride() {
    const invoiceSelect = document.getElementById("manualMatchInvoiceSelect");
    const confirmBtn = document.getElementById("btnConfirmManualMatch");

    if (!activeSelectedTx) {
        renderAlert("Vui lòng chọn một giao dịch sổ phụ ngân hàng trước.", "warning");
        return;
    }

    if (!invoiceSelect || !invoiceSelect.value) {
        renderAlert("Vui lòng chọn một hóa đơn để đối khớp thủ công.", "warning");
        return;
    }

    const payload = {
        transaction_id: activeSelectedTx.id,
        invoice_id: invoiceSelect.value,
        match_reason: "Manual operator override"
    };

    const originalText = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

    try {
        const response = await fetch("/api/bank/reconcile/manual", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Không thể thực hiện khớp thủ công.");
        }

        renderAlert("Đối khớp giao dịch thành công bằng quyền can thiệp thủ công!", "success");
        
        // Clear manual panel
        document.getElementById("manualMatchPanel").style.display = "none";
        activeSelectedTx = null;

        // Reload data
        await loadBankTransactions();
    } catch (error) {
        renderAlert(`Lỗi đối khớp: ${error.message}`, "danger");
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
    }
}

async function triggerAutoReconcileAI() {
    const btn = document.getElementById("btnAutoReconcile");
    const logBody = document.getElementById("reconcileResultsLogBody");
    const mst = window.activeTaxpayerMst || "0109998887";

    if (!btn || !logBody) return;

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang chạy đối khớp tự động...';

    logBody.innerHTML = '<tr><td colspan="3" class="text-center py-4"><div class="spinner-border spinner-border-sm text-success" role="status"></div> Trí tuệ AI đang quét chuỗi và phonetic...</td></tr>';

    try {
        const response = await fetch("/api/bank/reconcile/auto", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ mst: mst })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Không thể chạy động cơ AI đối chiếu.");
        }

        const matches = data.details || [];
        
        if (matches.length === 0) {
            logBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-secondary py-4">
                        Không tìm thấy cặp giao dịch & hóa đơn nào đủ độ tin cậy để khớp tự động trong đợt này.
                    </td>
                </tr>
            `;
            renderAlert("AI hoàn thành phân tích: Không phát hiện thêm cặp đối khớp tự động nào.", "info");
            return;
        }

        // Render matched logs beautifully
        logBody.innerHTML = matches.map(match => {
            const scoreClass = match.confidence.includes("100") || parseInt(match.confidence) >= 85 ? "text-success" : "text-warning";
            const scoreBadge = `<strong class="${scoreClass}">${match.confidence}</strong>`;
            
            return `
                <tr class="fade-in">
                    <td>
                        <div class="fw-semibold text-white small">${match.description}</div>
                        <span class="text-muted" style="font-size:0.75rem;">${Number(Math.abs(match.amount)).toLocaleString("vi-VN")} ₫</span>
                    </td>
                    <td>
                        <span class="badge bg-primary-subtle text-primary small">Số HĐ: #${match.invoice_number}</span>
                    </td>
                    <td class="text-end">${scoreBadge}</td>
                </tr>
            `;
        }).join("");

        renderAlert(`AI đã đối khớp tự động thành công ${matches.length} giao dịch với độ tin cậy tuyệt đối!`, "success");

        // Reload the left table
        await loadBankTransactions();
    } catch (error) {
        logBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger py-4">Lỗi: ${error.message}</td></tr>`;
        renderAlert(`Lỗi đối khớp AI: ${error.message}`, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Bind to startup DOM events
document.addEventListener("DOMContentLoaded", () => {
    initializeBankReconcileEvents();
    setupAgentHarnessEvents();
});

// ==========================================================================
// AGENT HARNESS MODULE
// ==========================================================================

const PROVIDER_MODELS = {
    gemini: [
        { value: 'gemini-2.5-flash', label: 'gemini-2.5-flash' },
        { value: 'gemini-2.5-pro', label: 'gemini-2.5-pro' }
    ],
    openai: [
        { value: 'gpt-4o', label: 'gpt-4o' },
        { value: 'gpt-4o-mini', label: 'gpt-4o-mini' },
        { value: 'o1-mini', label: 'o1-mini' }
    ],
    anthropic: [
        { value: 'claude-3-5-sonnet-latest', label: 'claude-3-5-sonnet' },
        { value: 'claude-3-5-haiku-latest', label: 'claude-3-5-haiku' }
    ]
};

function updateModelOptions() {
    const providerSelect = document.getElementById('agentRunProvider');
    const modelSelect = document.getElementById('agentRunModel');
    if (!providerSelect || !modelSelect) return;

    const provider = providerSelect.value;
    const models = PROVIDER_MODELS[provider] || [];
    
    modelSelect.innerHTML = models.map(m => `<option value="${m.value}">${m.label}</option>`).join('');
}

async function loadHarnessSummary() {
    try {
        const response = await fetch('/api/harness/summary');
        if (!response.ok) throw new Error("Failed to load harness summary");
        
        const data = await response.json();
        
        // Update stats
        const stats = data.stats || {};
        document.getElementById('harnessTotalStories').innerText = stats.total_stories || 0;
        document.getElementById('harnessPlannedStories').innerText = `${stats.stories_by_status?.planned || 0} planned`;
        document.getElementById('harnessInProgressStories').innerText = stats.stories_by_status?.in_progress || 0;
        document.getElementById('harnessImplementedStories').innerText = `${stats.stories_by_status?.implemented || 0} completed`;
        document.getElementById('harnessTotalTraces').innerText = stats.total_traces || 0;
        document.getElementById('harnessTotalBacklog').innerText = stats.total_backlog || 0;
        document.getElementById('harnessOpenBacklog').innerText = `${stats.backlog_by_status?.open || 0} open items`;

        // Update counts in tabs
        document.getElementById('harnessStoriesCount').innerText = data.stories?.length || 0;
        document.getElementById('harnessDecisionsCount').innerText = data.decisions?.length || 0;
        document.getElementById('harnessBacklogCount').innerText = data.backlog?.length || 0;
        document.getElementById('harnessTracesCount').innerText = data.traces?.length || 0;

        // Populate story run selector
        const runStorySelect = document.getElementById('agentRunStoryId');
        if (runStorySelect) {
            const currentSelected = runStorySelect.value;
            let options = '<option value="">-- Không có Story (Chạy tự do) --</option>';
            data.stories.forEach(s => {
                options += `<option value="${s.id}" ${s.id === currentSelected ? 'selected' : ''}>[${s.id}] ${s.title}</option>`;
            });
            runStorySelect.innerHTML = options;
        }

        // Render Stories Table
        const storiesBody = document.getElementById('harnessStoriesTableBody');
        if (storiesBody) {
            if (data.stories.length === 0) {
                storiesBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Chưa có story nào.</td></tr>';
            } else {
                storiesBody.innerHTML = data.stories.map(s => {
                    let laneBadge = '';
                    if (s.lane === 'tiny') laneBadge = '<span class="badge bg-info-subtle text-info">Tiny</span>';
                    else if (s.lane === 'high_risk') laneBadge = '<span class="badge bg-danger-subtle text-danger">High Risk</span>';
                    else laneBadge = '<span class="badge bg-secondary-subtle text-white">Normal</span>';

                    let statusBadge = '';
                    if (s.status === 'planned') statusBadge = '<span class="badge bg-warning text-dark">Planned</span>';
                    else if (s.status === 'in_progress') statusBadge = '<span class="badge bg-primary text-white">In Progress</span>';
                    else if (s.status === 'implemented') statusBadge = '<span class="badge bg-success text-white">Implemented</span>';
                    else statusBadge = `<span class="badge bg-secondary text-white">${s.status}</span>`;

                    const proofs = s.proofs || {};
                    const proofIcons = [];
                    if (proofs.unit === 1) proofIcons.push('<span class="badge bg-success" title="Unit Test Pass">UT</span>');
                    if (proofs.integration === 1) proofIcons.push('<span class="badge bg-success" title="Integration Test Pass">INT</span>');
                    if (proofs.e2e === 1) proofIcons.push('<span class="badge bg-success" title="E2E Test Pass">E2E</span>');
                    if (proofs.platform === 1) proofIcons.push('<span class="badge bg-success" title="Platform Proof Pass">PL</span>');
                    const proofHtml = proofIcons.length > 0 ? proofIcons.join(' ') : '<span class="text-muted" style="font-size:0.75rem;">Chưa kiểm</span>';

                    const escapedTitle = s.title.replace(/'/g, "\\'");
                    const escapedEvidence = (s.evidence || '').replace(/'/g, "\\'");
                    
                    return `
                        <tr>
                            <td class="font-monospace fw-bold">${s.id}</td>
                            <td>${s.title}</td>
                            <td>${laneBadge}</td>
                            <td>${statusBadge}</td>
                            <td>${proofHtml}</td>
                            <td class="text-end">
                                <button class="btn btn-sm btn-outline-light py-0 px-2" onclick="editStory('${s.id}', '${escapedTitle}', '${s.status}', '${escapedEvidence}', ${proofs.unit || 'null'}, ${proofs.integration || 'null'}, ${proofs.e2e || 'null'}, ${proofs.platform || 'null'})" style="font-size: 0.75rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);">
                                    Cập nhật
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        }

        // Render Decisions Table
        const decisionsBody = document.getElementById('harnessDecisionsTableBody');
        if (decisionsBody) {
            if (data.decisions.length === 0) {
                decisionsBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Chưa ghi nhận quyết định nào.</td></tr>';
            } else {
                decisionsBody.innerHTML = data.decisions.map(d => {
                    let statusBadge = '';
                    if (d.status === 'accepted') statusBadge = '<span class="badge bg-success">Accepted</span>';
                    else if (d.status === 'proposed') statusBadge = '<span class="badge bg-warning text-dark">Proposed</span>';
                    else if (d.status === 'rejected') statusBadge = '<span class="badge bg-danger">Rejected</span>';
                    else statusBadge = `<span class="badge bg-secondary">${d.status}</span>`;

                    const dateStr = d.timestamp ? new Date(d.timestamp).toLocaleDateString('vi-VN') : '-';
                    
                    return `
                        <tr>
                            <td class="font-monospace fw-bold">${d.id}</td>
                            <td>${d.title}</td>
                            <td>${statusBadge}</td>
                            <td class="font-monospace text-muted" style="font-size:0.75rem;">${d.verify_cmd || '-'}</td>
                            <td>${d.predicted_impact || '-'}</td>
                            <td>${dateStr}</td>
                        </tr>
                    `;
                }).join('');
            }
        }

        // Render Backlog Table
        const backlogBody = document.getElementById('harnessBacklogTableBody');
        if (backlogBody) {
            if (data.backlog.length === 0) {
                backlogBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Chưa có đề xuất backlog nào.</td></tr>';
            } else {
                backlogBody.innerHTML = data.backlog.map(b => {
                    let statusBadge = '';
                    if (b.status === 'open') statusBadge = '<span class="badge bg-warning text-dark">Open</span>';
                    else if (b.status === 'accepted') statusBadge = '<span class="badge bg-primary">Accepted</span>';
                    else if (b.status === 'implemented') statusBadge = '<span class="badge bg-success">Implemented</span>';
                    else statusBadge = `<span class="badge bg-secondary">${b.status}</span>`;

                    return `
                        <tr>
                            <td><strong>${b.title}</strong><br><span class="text-muted" style="font-size:0.7rem;">Phát hiện: ${b.discovered_in || '-'}</span></td>
                            <td style="max-width: 150px; white-space: normal;">${b.pain_points || '-'}</td>
                            <td style="max-width: 150px; white-space: normal;">${b.improvement || '-'}</td>
                            <td>${statusBadge}</td>
                            <td>${b.positive_impact || '-'}</td>
                        </tr>
                    `;
                }).join('');
            }
        }

        // Render Traces Table
        const tracesBody = document.getElementById('harnessTracesTableBody');
        if (tracesBody) {
            if (data.traces.length === 0) {
                tracesBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Chưa có dấu vết chạy agent nào.</td></tr>';
            } else {
                tracesBody.innerHTML = data.traces.map(t => {
                    const timeStr = t.timestamp ? new Date(t.timestamp).toLocaleString('vi-VN') : '-';
                    const outcomeBadge = t.outcome === 'success' 
                        ? '<span class="badge bg-success">Success</span>' 
                        : (t.outcome === 'failed' ? '<span class="badge bg-danger">Failed</span>' : `<span class="badge bg-secondary">${t.outcome}</span>`);
                    
                    return `
                        <tr>
                            <td>${timeStr}</td>
                            <td style="max-width: 180px; white-space: normal;">${t.command}</td>
                            <td class="font-monospace">${t.story_id || '-'}</td>
                            <td class="text-muted">${t.agent_name || '-'}</td>
                            <td class="font-monospace" style="font-size:0.75rem;">${t.git_commit ? t.git_commit.substring(0,7) : '-'}</td>
                            <td>${outcomeBadge}</td>
                        </tr>
                    `;
                }).join('');
            }
        }
    } catch (error) {
        console.error("Error loading harness summary:", error);
    }
}

function editStory(id, title, status, evidence, unit, integration, e2e, platform) {
    document.getElementById('updateStoryId').value = id;
    document.getElementById('updateStoryIdTitle').innerText = id;
    document.getElementById('updateStoryStatus').value = status;
    document.getElementById('updateStoryEvidence').value = evidence;
    document.getElementById('updateStoryUnit').value = unit !== null ? unit : '';
    document.getElementById('updateStoryIntegration').value = integration !== null ? integration : '';
    document.getElementById('updateStoryE2E').value = e2e !== null ? e2e : '';
    document.getElementById('updateStoryPlatform').value = platform !== null ? platform : '';

    const modal = new bootstrap.Modal(document.getElementById('updateStoryModal'));
    modal.show();
}

function clearConsoleLog() {
    const consoleLog = document.getElementById('agentConsoleLog');
    if (consoleLog) {
        consoleLog.innerHTML = '<div class="text-muted">// Console log cleared.</div>';
    }
}

let agentEventSource = null;

function setupAgentHarnessEvents() {
    // Form Run Agent
    const runForm = document.getElementById('agentRunForm');
    if (runForm) {
        runForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('btnRunAgent');
            const btnIcon = document.getElementById('runAgentBtnIcon');
            const btnText = document.getElementById('runAgentBtnText');
            const consoleLog = document.getElementById('agentConsoleLog');
            
            const storyId = document.getElementById('agentRunStoryId').value;
            const provider = document.getElementById('agentRunProvider').value;
            const model = document.getElementById('agentRunModel').value;
            const goal = document.getElementById('agentRunGoal').value.trim();
            
            if (!goal) {
                renderAlert("Vui lòng nhập mục tiêu cho Agent.", "warning");
                return;
            }

            btn.disabled = true;
            btnIcon.className = 'spinner-border spinner-border-sm';
            btnText.innerText = 'AGENT ĐANG CHẠY...';
            
            consoleLog.innerHTML = '<div class="text-info">[SYSTEM] Khởi tạo kết nối Agent...</div>';
            
            // Close any existing connection
            if (agentEventSource) {
                agentEventSource.close();
            }
            
            // Start SSE subscription directly, as this executes the agent script
            const sseUrl = `/api/harness/agent/stream?provider=${encodeURIComponent(provider)}&model=${encodeURIComponent(model)}&goal=${encodeURIComponent(goal)}&story_id=${encodeURIComponent(storyId)}`;
            
            agentEventSource = new EventSource(sseUrl);
            
            agentEventSource.onmessage = (event) => {
                let rawData = event.data;
                let messageText = rawData;
                
                try {
                    const parsed = JSON.parse(rawData);
                    if (typeof parsed === 'object' && parsed !== null) {
                        messageText = parsed.message || JSON.stringify(parsed);
                    } else {
                        messageText = parsed;
                    }
                } catch (err) {
                    // Plain text
                }
                
                const logLine = document.createElement('div');
                
                // Colorize based on contents
                if (messageText.includes('[ERROR]') || messageText.includes('failed') || messageText.includes('Failed')) {
                    logLine.className = 'text-danger';
                } else if (messageText.includes('[SUCCESS]') || messageText.includes('success') || messageText.includes('Success')) {
                    logLine.className = 'text-success';
                } else if (messageText.includes('[TOOL]') || messageText.includes('executing')) {
                    logLine.className = 'text-warning-emphasis';
                } else if (messageText.startsWith('[SYSTEM]')) {
                    logLine.className = 'text-info';
                } else {
                    logLine.className = 'text-white-50';
                }
                
                logLine.textContent = messageText;
                consoleLog.appendChild(logLine);
                consoleLog.scrollTop = consoleLog.scrollHeight;

                if (messageText.includes('[SYSTEM] Process completed successfully.') || messageText.includes('completed')) {
                    renderAlert('Agent hoàn tất tác vụ thành công!', 'success');
                }
            };
            
            agentEventSource.onerror = (err) => {
                // Since SSE auto-reconnects on close, we close it when the stream ends.
                // We assume connection close/error after activity means completion.
                console.log("Log stream connection changed state.");
                
                btn.disabled = false;
                btnIcon.className = 'bi bi-cpu';
                btnText.innerText = 'BẮT ĐẦU AGENT';
                
                if (agentEventSource) {
                    agentEventSource.close();
                    agentEventSource = null;
                    const endLine = document.createElement('div');
                    endLine.className = 'text-muted';
                    endLine.textContent = '[SYSTEM] Log stream closed.';
                    consoleLog.appendChild(endLine);
                    consoleLog.scrollTop = consoleLog.scrollHeight;
                }
                loadHarnessSummary();
            };
        });
    }

    // Form Add Story
    const addStoryForm = document.getElementById('addStoryForm');
    if (addStoryForm) {
        addStoryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const modalEl = document.getElementById('addStoryModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            
            const payload = {
                id: document.getElementById('addStoryId').value.trim(),
                title: document.getElementById('addStoryTitle').value.trim(),
                lane: document.getElementById('addStoryLane').value,
                contract_doc: document.getElementById('addStoryContract').value.trim() || null,
                status: document.getElementById('addStoryStatus').value,
                notes: document.getElementById('addStoryNotes').value.trim() || null
            };
            
            try {
                const response = await fetch('/api/harness/story', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Cannot save story");
                
                renderAlert("Thêm Story thành công!", "success");
                addStoryForm.reset();
                modal.hide();
                loadHarnessSummary();
            } catch (err) {
                renderAlert(`Lỗi thêm Story: ${err.message}`, "danger");
            }
        });
    }

    // Form Update Story
    const updateStoryForm = document.getElementById('updateStoryForm');
    if (updateStoryForm) {
        updateStoryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const modalEl = document.getElementById('updateStoryModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            
            const storyId = document.getElementById('updateStoryId').value;
            
            const valOrNull = (id) => {
                const val = document.getElementById(id).value;
                return val === '' ? null : parseInt(val);
            };

            const payload = {
                id: storyId,
                status: document.getElementById('updateStoryStatus').value,
                evidence: document.getElementById('updateStoryEvidence').value.trim() || null,
                proofs: {
                    unit: valOrNull('updateStoryUnit'),
                    integration: valOrNull('updateStoryIntegration'),
                    e2e: valOrNull('updateStoryE2E'),
                    platform: valOrNull('updateStoryPlatform')
                }
            };
            
            try {
                const response = await fetch('/api/harness/story/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Cannot update story");
                
                renderAlert("Cập nhật Story thành công!", "success");
                updateStoryForm.reset();
                modal.hide();
                loadHarnessSummary();
            } catch (err) {
                renderAlert(`Lỗi cập nhật Story: ${err.message}`, "danger");
            }
        });
    }

    // Form Add Decision
    const addDecisionForm = document.getElementById('addDecisionForm');
    if (addDecisionForm) {
        addDecisionForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const modalEl = document.getElementById('addDecisionModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            
            const payload = {
                id: document.getElementById('addDecisionId').value.trim(),
                title: document.getElementById('addDecisionTitle').value.trim(),
                status: document.getElementById('addDecisionStatus').value,
                doc_path: document.getElementById('addDecisionDoc').value.trim() || null,
                verify_cmd: document.getElementById('addDecisionVerify').value.trim() || null,
                predicted_impact: document.getElementById('addDecisionPredicted').value.trim() || null,
                notes: document.getElementById('addDecisionNotes').value.trim() || null
            };
            
            try {
                const response = await fetch('/api/harness/decision', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Cannot save decision");
                
                renderAlert("Thêm Quyết định thành công!", "success");
                addDecisionForm.reset();
                modal.hide();
                loadHarnessSummary();
            } catch (err) {
                renderAlert(`Lỗi thêm Quyết định: ${err.message}`, "danger");
            }
        });
    }

    // Form Add Backlog
    const addBacklogForm = document.getElementById('addBacklogForm');
    if (addBacklogForm) {
        addBacklogForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const modalEl = document.getElementById('addBacklogModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            
            const payload = {
                title: document.getElementById('addBacklogTitle').value.trim(),
                discovered_while: document.getElementById('addBacklogDiscovered').value.trim() || null,
                current_pain: document.getElementById('addBacklogPain').value.trim() || null,
                suggested_improvement: document.getElementById('addBacklogImprovement').value.trim() || null,
                risk: document.getElementById('addBacklogRisk').value,
                status: document.getElementById('addBacklogStatus').value,
                predicted_impact: document.getElementById('addBacklogImpact').value.trim() || null,
                notes: document.getElementById('addBacklogNotes').value.trim() || null
            };
            
            try {
                const response = await fetch('/api/harness/backlog', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Cannot save backlog item");
                
                renderAlert("Thêm đề xuất Backlog thành công!", "success");
                addBacklogForm.reset();
                modal.hide();
                loadHarnessSummary();
            } catch (err) {
                renderAlert(`Lỗi đề xuất Backlog: ${err.message}`, "danger");
            }
        });
    }

    // Hook tab activation
    const harnessTabEl = document.getElementById('agent-harness-tab');
    if (harnessTabEl) {
        harnessTabEl.addEventListener('shown.bs.tab', () => {
            loadHarnessSummary();
        });
    }

    // --- CAPTCHA & Crawler Health Monitoring Widget Logic ---
    const crawlerStatusBadge = document.getElementById("crawlerStatusBadge");
    const btnRefreshSyncHealth = document.getElementById("btnRefreshSyncHealth");

    async function fetchSyncHealth() {
        if (!crawlerStatusBadge) return;
        
        try {
            // Call API with custom options to avoid redirect on unauthorized/401
            const response = await fetch("/api/sync/health");
            if (response.status === 401 || response.status === 403) {
                crawlerStatusBadge.className = "badge bg-danger text-white px-3 py-2 text-uppercase";
                crawlerStatusBadge.textContent = "Không có quyền";
                return;
            }
            
            if (!response.ok) {
                throw new Error("HTTP error " + response.status);
            }
            
            const data = await response.json();
            
            // Update crawler status badge
            if (data.crawler_status === "running") {
                crawlerStatusBadge.className = "badge bg-warning text-dark px-3 py-2 text-uppercase text-shadow-none";
                crawlerStatusBadge.style.boxShadow = "0 0 10px rgba(245, 158, 11, 0.4)";
                crawlerStatusBadge.textContent = "Đang chạy ngầm";
            } else {
                crawlerStatusBadge.className = "badge bg-success text-white px-3 py-2 text-uppercase text-shadow-none";
                crawlerStatusBadge.style.boxShadow = "0 0 10px rgba(16, 185, 129, 0.4)";
                crawlerStatusBadge.textContent = "Đang rảnh (Idle)";
            }

            // Update Solver metrics with smooth transitions or direct values
            const accuracyEl = document.getElementById("captchaAccuracy");
            const latencyEl = document.getElementById("captchaLatency");
            const successEl = document.getElementById("captchaSuccess");
            const failEl = document.getElementById("captchaFail");

            const solverData = data.solver || data.solver_stats || {};

            if (accuracyEl) {
                // accuracy_rate is already 0-100 on the server side
                const accuracyRate = solverData.accuracy_rate || 0;
                accuracyEl.textContent = accuracyRate.toFixed(1) + "%";
                if (accuracyRate >= 80) {
                    accuracyEl.style.color = "#00f5d4";
                } else if (accuracyRate >= 50) {
                    accuracyEl.style.color = "#f59e0b";
                } else {
                    accuracyEl.style.color = "#ef4444";
                }
            }

            if (latencyEl) {
                const avgLatency = solverData.average_latency_seconds || solverData.average_latency || 0;
                latencyEl.textContent = avgLatency.toFixed(2) + "s";
            }

            if (successEl) {
                const totalSuccess = solverData.success_count || solverData.total_success || 0;
                successEl.textContent = totalSuccess.toLocaleString();
            }
            if (failEl) {
                const totalFail = solverData.fail_count || solverData.total_fail || 0;
                failEl.textContent = totalFail.toLocaleString();
            }

        } catch (error) {
            console.error("Lỗi khi tải trạng thái Sync Health:", error);
            if (crawlerStatusBadge) {
                crawlerStatusBadge.className = "badge bg-secondary text-white px-3 py-2 text-uppercase";
                crawlerStatusBadge.textContent = "Ngoại tuyến";
            }
        }
    }

    // Initial load
    if (crawlerStatusBadge) {
        fetchSyncHealth();
        // Poll every 10 seconds
        const healthInterval = setInterval(fetchSyncHealth, 10000);
        
        // Clean up interval if user leaves/reloads (standard practice)
        window.addEventListener("unload", () => {
            clearInterval(healthInterval);
        });
    }

    if (btnRefreshSyncHealth) {
        btnRefreshSyncHealth.addEventListener("click", async () => {
            const icon = btnRefreshSyncHealth.querySelector("i");
            if (icon) icon.classList.add("spin-animation");
            btnRefreshSyncHealth.disabled = true;
            
            await fetchSyncHealth();
            
            setTimeout(() => {
                if (icon) icon.classList.remove("spin-animation");
                btnRefreshSyncHealth.disabled = false;
            }, 600);
        });
    }
}


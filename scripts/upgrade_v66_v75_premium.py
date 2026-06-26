"""
Batch upgrade v66-v75 compliance hub templates with Wise Fintech Premium styling.

Changes applied to each template:
1. Insert {% block head_extra %} with Wise design tokens CSS
2. Upgrade rD() to animated robot debate bubbles
3. Add calc-pulse-effect trigger to rR()
4. Upgrade badge styles in rH() to subtle variants
"""
import re
import os

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

# ── 1. The premium CSS block to inject ──
WISE_CSS_BLOCK = """
{% block head_extra %}
<style>
    /* Wise Fintech Design Tokens for {version_label} */
    :root {
        --wise-primary: #002d04;
        --wise-primary-light: rgba(0, 45, 4, 0.05);
        --wise-accent: #02c39a;
        --wise-accent-hover: #00a896;
        --wise-dark: #122115;
        --wise-light: #f4f7f4;
        --wise-border: rgba(0, 45, 4, 0.1);
        --glass-bg: rgba(255, 255, 255, 0.75);
        --glass-border: rgba(255, 255, 255, 0.5);
        --glass-shadow: 0 8px 32px 0 rgba(0, 45, 4, 0.06);
    }

    body {
        background-color: var(--wise-light);
        font-family: 'Inter', sans-serif;
    }

    /* Premium Glass Card Adjustments */
    .glass-card {
        background: var(--glass-bg) !important;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--glass-border) !important;
        box-shadow: var(--glass-shadow) !important;
        border-radius: 16px !important;
        transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
        margin-bottom: 24px;
        overflow: hidden;
    }

    .glass-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 40px 0 rgba(0, 45, 4, 0.12) !important;
    }

    /* Form Controls Optimization */
    .form-control, .form-select {
        border-radius: 8px !important;
        border: 1px solid var(--wise-border) !important;
        padding: 0.6rem 0.75rem !important;
        font-size: 0.9rem !important;
        background-color: rgba(255, 255, 255, 0.8) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }

    .form-control:focus, .form-select:focus {
        border-color: var(--wise-accent) !important;
        box-shadow: 0 0 0 4px rgba(2, 195, 154, 0.15) !important;
        background-color: #fff !important;
    }

    /* Button Enhancements */
    .btn-info {
        background: linear-gradient(135deg, var(--wise-accent) 0%, #00a896 100%) !important;
        border: none !important;
        color: #fff !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.25rem !important;
        font-weight: 600 !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }

    .btn-info:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(2, 195, 154, 0.3) !important;
    }

    /* Result Panel Animation & Aesthetics */
    @keyframes calcPulse {
        0% {
            box-shadow: 0 0 0 0 rgba(2, 195, 154, 0.4);
            background-color: rgba(2, 195, 154, 0.15) !important;
        }
        100% {
            box-shadow: 0 0 0 12px rgba(2, 195, 154, 0);
        }
    }

    .calc-pulse-effect {
        animation: calcPulse 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* Baseline Cards Hover Glow */
    .bg-premium-light {
        transition: all 0.25s ease-in-out;
        border-radius: 12px !important;
        border: 1px solid rgba(0, 45, 4, 0.05) !important;
    }

    .bg-premium-light:hover {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-color: rgba(2, 195, 154, 0.3) !important;
        box-shadow: 0 6px 16px rgba(0, 45, 4, 0.04);
        transform: translateY(-2px);
    }

    /* Agent Debate Bubble Styling */
    .debate-message-bubble {
        transition: all 0.3s ease;
        border-radius: 14px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
    }

    .debate-message-bubble:hover {
        transform: translateX(4px);
        box-shadow: 0 4px 12px rgba(0, 45, 4, 0.05);
        border-color: rgba(2, 195, 154, 0.2) !important;
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Table Adjustments */
    .table-responsive {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(0, 45, 4, 0.08);
    }

    .table thead {
        background-color: var(--wise-primary) !important;
        color: #fff !important;
    }

    .table th {
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
        padding: 12px 16px !important;
        border-bottom: none !important;
    }

    .table td {
        padding: 14px 16px !important;
        font-size: 0.875rem;
        vertical-align: middle;
        border-bottom: 1px solid rgba(0, 45, 4, 0.05) !important;
    }

    .table tbody tr {
        transition: background-color 0.15s ease;
    }

    .table tbody tr:hover {
        background-color: rgba(2, 195, 154, 0.03) !important;
    }
</style>
{% endblock %}
"""

# ── 2. Speaker color mappings per template ──
SPEAKER_COLORS = {
    "v66": {
        "Climate Policy Auditor": "bg-success-subtle text-success border border-success",
        "Factory Environmental Manager": "bg-warning-subtle text-warning border border-warning",
        "MoNRE Climate Change Inspector": "bg-info-subtle text-info border border-info",
    },
    "v67": {
        "Customs Compliance Officer": "bg-success-subtle text-success border border-success",
        "Recycling Industry President": "bg-warning-subtle text-warning border border-warning",
        "VEPF Deposit Custodian": "bg-info-subtle text-info border border-info",
    },
    "v68": {
        "Land Administration Officer": "bg-success-subtle text-success border border-success",
        "Land Rental Policy Analyst": "bg-warning-subtle text-warning border border-warning",
        "MoF Budget Inspector": "bg-info-subtle text-info border border-info",
    },
    "v69": {
        "Forest Ranger Inspector": "bg-success-subtle text-success border border-success",
        "Timber Industry Representative": "bg-warning-subtle text-warning border border-warning",
        "Forestry Policy Advisor": "bg-info-subtle text-info border border-info",
    },
    "v71": {
        "E-Waste Recycling Inspector": "bg-success-subtle text-success border border-success",
        "Supply Chain Director": "bg-warning-subtle text-warning border border-warning",
        "Customs Compliance Specialist": "bg-info-subtle text-info border border-info",
    },
    "v72": {
        "Wastewater Treatment Inspector": "bg-success-subtle text-success border border-success",
        "Industrial Zone Manager": "bg-warning-subtle text-warning border border-warning",
        "MoNRE Environmental Counsel": "bg-info-subtle text-info border border-info",
    },
    "v73": {
        "Hazardous Waste Inspector": "bg-success-subtle text-success border border-success",
        "Licensed Transport Operator": "bg-warning-subtle text-warning border border-warning",
        "MoNRE Waste Policy Advisor": "bg-info-subtle text-info border border-info",
    },
    "v74": {
        "Noise Pollution Inspector": "bg-success-subtle text-success border border-success",
        "Industrial Facility Manager": "bg-warning-subtle text-warning border border-warning",
        "MoNRE Acoustic Advisor": "bg-info-subtle text-info border border-info",
    },
    "v75": {
        "Plastics Pollution Inspector": "bg-success-subtle text-success border border-success",
        "Packaging Industry Director": "bg-warning-subtle text-warning border border-warning",
        "MoNRE Ocean Policy Counsel": "bg-info-subtle text-info border border-info",
    },
}

# Templates to upgrade (v70 is special - has a different rD structure, handle separately)
STANDARD_TEMPLATES = ["v66", "v67", "v68", "v69", "v71", "v72", "v73", "v74", "v75"]

def inject_head_extra(content, version):
    """Insert the Wise CSS block after {% block title %}...{% endblock %}"""
    # Find the {% block content %} and insert before it
    block_content_pos = content.find("{% block content %}")
    if block_content_pos == -1:
        print(f"  [WARN] Could not find {{% block content %}} in {version}")
        return content

    # Check if head_extra already exists
    if "{% block head_extra %}" in content:
        print(f"  [SKIP] {version} already has head_extra block")
        return content

    css = WISE_CSS_BLOCK.replace("{version_label}", f"{version} Hub")
    new_content = content[:block_content_pos] + css + "\n" + content[block_content_pos:]
    print(f"  [CSS ] Injected head_extra design tokens")
    return new_content


def upgrade_debate_function(content, version):
    """Replace the old rD function with animated robot debate bubbles."""
    ver = version  # e.g. "v66"
    speakers = SPEAKER_COLORS.get(ver, {})
    if not speakers:
        print(f"  [SKIP] No speaker mapping for {ver}")
        return content

    # Build the new speaker color lines
    cl_lines = []
    for speaker, cls in speakers.items():
        cl_lines.append(f'            "{speaker}": "{cls}"')
    cl_block = ",\n".join(cl_lines)

    # Pattern: old rD function - match from "const rD = (debate, summary) =>" to the closing "};"
    old_pattern = re.compile(
        r'(    const rD = \(debate, summary\) => \{.*?'
        r'document\.getElementById\("consensus-text-' + ver.replace('v', 'v') + r'"\)\.textContent = summary;\n'
        r'    \};)',
        re.DOTALL
    )

    new_rD = f'''    const rD = (debate, summary) => {{
        const c = document.getElementById("debate-container-{ver}");
        c.innerHTML = "";
        const cl = {{
{cl_block}
        }};
        debate.forEach((m, idx) => {{
            const div = document.createElement("div");
            div.className = "d-flex gap-3 align-items-start p-3 bg-white rounded border border-light-subtle debate-message-bubble";
            div.style.animation = `fadeInUp 0.3s ease forwards ${{idx * 0.1}}s`;
            div.style.opacity = "0";
            div.innerHTML = `
                <div class="d-flex flex-column align-items-center text-center" style="min-width: 140px;">
                    <div class="rounded-circle bg-light d-flex align-items-center justify-content-center mb-2" style="width: 40px; height: 40px;">
                        <i class="bi bi-robot text-secondary fs-5"></i>
                    </div>
                    <span class="badge ${{cl[m.speaker] || "bg-secondary"}} text-wrap py-1 px-2 small">${{m.speaker}}</span>
                </div>
                <div class="text-dark small flex-grow-1 pt-1 leading-relaxed">${{m.text}}</div>
            `;
            c.appendChild(div);
        }});
        document.getElementById("consensus-text-{ver}").textContent = summary;
    }};'''

    match = old_pattern.search(content)
    if match:
        content = content[:match.start()] + new_rD + content[match.end():]
        print(f"  [rD  ] Upgraded debate function to animated robot bubbles")
    else:
        print(f"  [WARN] Could not match rD function pattern in {ver}")

    return content


def add_pulse_to_rR(content, version):
    """Add calc-pulse-effect trigger at the end of the rR function."""
    # Check if already has pulse
    if "calc-pulse-effect" in content:
        print(f"  [SKIP] {version} already has calc-pulse-effect")
        return content

    # Find the rR function closing pattern - the last line before "};" that sets content
    # We look for the rR closing and insert pulse logic before it
    rR_pattern = re.compile(
        r'(document\.getElementById\("res-exemption-reason"\)\.textContent = r\.exemption_reason \|\| "None";\n)'
        r'(    \};)',
        re.DOTALL
    )

    replacement = (
        r'\1'
        '\n'
        '        const resPanel = document.getElementById("res-effective-fee")?.closest(".bg-premium-light") || document.getElementById("res-effective-fee")?.closest(".result-panel");\n'
        '        if (resPanel) {\n'
        '            resPanel.classList.remove("calc-pulse-effect");\n'
        '            void resPanel.offsetWidth;\n'
        '            resPanel.classList.add("calc-pulse-effect");\n'
        '        }\n'
        r'\2'
    )

    new_content, count = rR_pattern.subn(replacement, content)
    if count > 0:
        print(f"  [rR  ] Added calc-pulse-effect trigger")
    else:
        # Try alternative pattern for templates where res-notes is used instead
        alt_pattern = re.compile(
            r'(document\.getElementById\("res-notes"\)\.textContent = r\.notes \|\| "None";\n)'
            r'(.*?)(    \};)',
            re.DOTALL
        )
        match = alt_pattern.search(content)
        if match:
            insert_point = match.end(1)
            pulse_code = (
                '\n'
                '        const resPanel = document.getElementById("res-final")?.closest(".bg-premium-light") || document.getElementById("res-final")?.closest(".result-panel");\n'
                '        if (resPanel) {\n'
                '            resPanel.classList.remove("calc-pulse-effect");\n'
                '            void resPanel.offsetWidth;\n'
                '            resPanel.classList.add("calc-pulse-effect");\n'
                '        }\n'
            )
            new_content = content[:insert_point] + pulse_code + content[insert_point:]
            print(f"  [rR  ] Added calc-pulse-effect trigger (alt pattern)")
        else:
            print(f"  [WARN] Could not match rR closing pattern in {version}")
            new_content = content
    return new_content


def upgrade_badge_styles(content, version):
    """Upgrade badge styles from plain bg-success/bg-danger to subtle variants."""
    replacements = [
        ('badge bg-success">', 'badge bg-success-subtle text-success border border-success">'),
        ('badge bg-danger">', 'badge bg-danger-subtle text-danger border border-danger">'),
        ('badge bg-secondary">', 'badge bg-light text-dark border">'),
    ]
    count = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            count += 1
    if count > 0:
        print(f"  [BDGE] Upgraded {count} badge style patterns to subtle variants")
    return content


def upgrade_history_id_format(content, version):
    """Upgrade history ID formatting to include hash prefix."""
    old = '<td>${l.id}</td>'
    new = '<td><span class="text-secondary small fw-bold">#${l.id}</span></td>'
    if old in content:
        content = content.replace(old, new)
        print(f"  [ID  ] Upgraded history ID to #-prefixed format")
    return content


def upgrade_monospace_fees(content, version):
    """Add font-monospace class to fee value columns in history tables."""
    old = '<td class="fw-bold text-dark">'
    new = '<td class="fw-bold text-primary font-monospace">'
    if old in content:
        content = content.replace(old, new)
        print(f"  [FONT] Added monospace font to fee value columns")
    return content


def process_template(version):
    """Process a single template file."""
    filename = f"{version}_compliance_hub.html"
    filepath = os.path.join(TEMPLATES_DIR, filename)

    if not os.path.exists(filepath):
        print(f"[MISS] {filename} not found, skipping.")
        return False

    print(f"\n{'='*60}")
    print(f"[PROC] Processing {filename}")
    print(f"{'='*60}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. Inject head_extra CSS block
    content = inject_head_extra(content, version)

    # 2. Upgrade debate function
    content = upgrade_debate_function(content, version)

    # 3. Add pulse effect to rR
    content = add_pulse_to_rR(content, version)

    # 4. Upgrade badge styles
    content = upgrade_badge_styles(content, version)

    # 5. Upgrade ID formatting
    content = upgrade_history_id_format(content, version)

    # 6. Monospace fee columns
    content = upgrade_monospace_fees(content, version)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[DONE] {filename} upgraded successfully!")
        return True
    else:
        print(f"[NOOP] {filename} - no changes needed.")
        return False


def main():
    print("=" * 60)
    print("Wise Fintech Premium Upgrade: v66–v75 Compliance Hubs")
    print("=" * 60)

    upgraded = []
    skipped = []

    for ver in STANDARD_TEMPLATES:
        if process_template(ver):
            upgraded.append(ver)
        else:
            skipped.append(ver)

    # v70 is special (different rD signature)
    v70_file = os.path.join(TEMPLATES_DIR, "v70_compliance_hub.html")
    if os.path.exists(v70_file):
        print(f"\n{'='*60}")
        print(f"[PROC] Processing v70_compliance_hub.html (special: rD has different signature)")
        print(f"{'='*60}")
        with open(v70_file, "r", encoding="utf-8") as f:
            content = f.read()
        original = content
        content = inject_head_extra(content, "v70")
        content = upgrade_badge_styles(content, "v70")
        content = upgrade_history_id_format(content, "v70")
        content = upgrade_monospace_fees(content, "v70")
        if content != original:
            with open(v70_file, "w", encoding="utf-8") as f:
                f.write(content)
            upgraded.append("v70")
            print("[DONE] v70_compliance_hub.html upgraded (CSS + badges only, rD preserved)")
        else:
            skipped.append("v70")
            print("[NOOP] v70_compliance_hub.html - no changes needed.")

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Upgraded: {len(upgraded)} templates: {', '.join(upgraded)}")
    print(f"  Skipped:  {len(skipped)} templates: {', '.join(skipped) or 'none'}")


if __name__ == "__main__":
    main()

---
trigger: always_on
glob: "*"
---
# Antigravity Operating Environment (KWSR Framework)

Tài liệu này định nghĩa môi trường hoạt động cốt lõi của **Antigravity IDE**. Hệ thống được thiết kế không chỉ như một trợ lý chat, mà là một **Agentic System** có khả năng tự nhận thức tài nguyên vật lý, tự hành động thông qua công cụ và tự duy trì tính an toàn theo cấu trúc chuẩn mực.

Mọi hành động và suy luận của Agent phải tuân thủ nghiêm ngặt khung KWSR dưới đây.

## [K] Knowledge & Brain - Bản đồ Nhận thức & Não bộ
Agent phải nắm rõ vị trí các tài nguyên vật lý để tra cứu và sử dụng chính xác:
- **KI (Knowledge Items)**: `%USERPROFILE%\.gemini\antigravity[-ide]\knowledge`. Nơi lưu trữ bộ nhớ và các pattern đã đúc kết. Bắt buộc kiểm tra KI trước khi giải quyết vấn đề mới.
- **Brain (Hội thoại & Artifacts)**: Nơi lưu vết các cuộc hội thoại cũ (`.system_generated/logs`) và không gian làm việc hiện tại. Trong quá trình giải quyết vấn đề (Planning Mode), IDE bắt buộc Agent sử dụng các Artifacts cốt lõi để kiểm soát tiến trình:
  - `implementation_plan.md`: Bản phác thảo thiết kế kiến trúc và phương án thực thi (cần User Approve).
  - `task.md`: Danh sách công việc (Checklist) để Agent tự theo dõi tiến độ.
  - `walkthrough.md`: Báo cáo nghiệm thu tóm tắt kết quả sau khi hoàn thành.
  - Các tài liệu `Artifacts` khác: Dùng cho báo cáo, bảng biểu hoặc dữ liệu nháp (lưu trong `scratch/`).
- **Skills & Workflows**: `%USERPROFILE%\.gemini\config\skills` và `global_workflows`. Nơi chứa quy trình và công năng mở rộng.
- **Luật Cục bộ (Local Rules)**: Các file Rule (.md) phải có YAML Frontmatter (trigger: manual, always_on, model_decision, glob) để IDE nhận diện.

## [W] Workflows & Tools - Năng lực Công cụ
Hệ thống cung cấp danh mục công cụ (Tools) mạnh mẽ. Agent bắt buộc phải chọn đúng Tool chuyên biệt thay vì dùng script gõ tay (VD: cấm dùng bash `grep/cat` khi đã có native tool):
- **1. Thao tác File & Code**: Đọc thư mục (`list_dir`), xem file (`view_file`), tìm kiếm mã (`grep_search`), ghi file mới (`write_to_file`), sửa code khối liền kề (`replace_file_content`), sửa nhiều khối rời rạc (`multi_replace_file_content`).
- **2. Mạng & Trình duyệt**: Tìm kiếm nội dung web (`search_web`), cào URL thuần (`read_url_content`), hoặc phân quyền Agent con điều khiển trình duyệt giả lập (`browser_subagent`).
- **3. Hệ thống & Tiến trình**: Chạy lệnh Terminal (`run_command`), quản lý/dừng tiến trình ngầm (`manage_task`), thiết lập lịch trình hoặc hẹn giờ (`schedule`).
- **4. Tương tác & Phân quyền**: Bật popup hỏi trắc nghiệm User (`ask_question`), kiểm tra quyền (`list_permissions`), xin cấp quyền hệ thống (`ask_permission`).
- **5. Sáng tạo đồ họa**: Gọi AI tạo ảnh minh họa hoặc UI mockup (`generate_image`).
- **6. Mở rộng (MCP)**: Gọi công cụ ngoài (GCP, Firebase...) qua `call_mcp_tool`, hoặc tra cứu tài nguyên qua `list_resources`, `read_resource`.

## [S] Skills & Mindsets - Tư duy Giải quyết vấn đề
- **Hành động thay vì Suy diễn (PDCA)**: Không tự suy luận trong đầu. Phải gọi công cụ lấy dữ liệu để kiểm chứng giả thuyết. Luôn tìm phản chứng.
- **Chủ động Lựa chọn thay vì Đoán mò**: Khi yêu cầu mơ hồ, KHÔNG đoán ý định, KHÔNG hỏi mở. Phải dừng lại và gọi tool `ask_question` để đưa ra **tối đa 3 câu hỏi trắc nghiệm** cho User.
- **Xử lý Xung đột & Rủi ro**: Khi hệ thống, luật lệ hoặc dữ liệu mâu thuẫn, ưu tiên dừng lại, cảnh báo rủi ro và đề xuất phương án để User quyết định.

## [R] Rule & Environment - Sàn An Toàn & Môi trường thực thi
- **Môi trường hoạt động (Windows)**: Hệ thống chạy trên hệ điều hành **Windows**. Khi cần sinh script hoặc thao tác hệ thống, **bắt buộc rà soát tài nguyên hiện có trên Windows trước**. Ưu tiên sử dụng lệnh Native Windows (PowerShell) hoặc các ngôn ngữ đa dụng (Python) để tối ưu thư viện, tránh xung đột chéo.
- **KHÔNG xóa file gốc**: Mọi hành động xóa phải chuyển file vào thư mục `_Delete` ở root. Version cũ đưa vào `_Archive`. Không tự quyết định xóa vĩnh viễn.
- **KHÔNG bịa dữ liệu**: Mọi con số trong báo cáo phải truy ngược được về file nguồn. Không có dữ liệu phải báo ngay, tuyệt đối không ngoại suy.
- **KHÔNG xung đột Cloud**: Cấm tạo các thư mục sinh file rác liên tục (`node_modules`, `venv`, `.git`, `build`...) bên trong các thư mục đồng bộ đám mây (Google Drive, OneDrive).

---

# Agent Instructions

This repository contains multi-agent orchestration guidelines and system tooling rules. Follow these instructions exactly.

<!-- HARNESS:BEGIN -->
## Harness v3.0 (Advanced Multi-Agent Orchestration)

This repo uses Harness v3.0 (Hermes-Inspired multi-agent orchestration). All task tracking, issue states, risk lanes, and telemetric traces are stored in a centralized SQLite database `harness.db`. 

### Key Rules:
1. **Durable SQLite State**: Do not attempt to use or write raw `.beads/` files or directories. Direct execution of Beads CLI tools (`br` and `bv`) will fail due to virtualization constraints. Use `python scripts/harness_win.py query matrix` or SQLite direct queries.
2. **Context & Triage First**: Prior to modifying any codebase files, fetch context and verify priorities:
   ```bash
   python scripts/harness_win.py context --story <story_id>
   ```
3. **Risk Classification**: Run risk lane assessments on user specifications:
   ```bash
   python scripts/harness_win.py evaluate-risk --text "<spec>"
   ```
4. **Execution & Sandboxing**: Execute work under the appropriate sandbox backend (`local`, `containerized`, `cloud`). Bypasses safety gates with `--yolo` flag ONLY in non-interactive pipeline states.
5. **Unified Quality Gate**: Prior to turn completion, run validation checks and generate TSA-signed UAT reports:
   ```bash
   python scripts/harness_win.py unified-gate --story <story_id> --phase <compounding|review> --summary "<summary>" --actions "<actions>" --read "<files>" --changed "<files>"
   ```
6. **Execution Telemetry**: Record a turn trace immediately upon completion:
   ```bash
   python scripts/harness_win.py trace --summary "<summary>" --outcome success --story <story_id> --agent Antigravity
   ```
<!-- HARNESS:END -->

---

## MCP Agent Mail — Multi-Agent Coordination

A mail-like layer that lets coding agents coordinate asynchronously via MCP tools and resources. Provides identities, inbox/outbox, searchable threads, and advisory file reservations with human-auditable artifacts in Git.

### Why It's Useful
- **Prevents conflicts:** Explicit file reservations (leases) for files/globs
- **Token-efficient:** Messages stored in per-project archive, not in context
- **Quick reads:** `resource://inbox/...`, `resource://thread/...`

### Same Repository Workflow
1. **Register identity:**
   ```
   ensure_project(project_key=<abs-path>)
   register_agent(project_key, program, model)
   ```
2. **Reserve files before editing:**
   ```
   file_reservation_paths(project_key, agent_name, ["src/**"], ttl_seconds=3600, exclusive=true)
   ```
3. **Communicate with threads:**
   ```
   send_message(..., thread_id="FEAT-123")
   fetch_inbox(project_key, agent_name)
   acknowledge_message(project_key, agent_name, message_id)
   ```
4. **Quick reads:**
   ```
   resource://inbox/{Agent}?project=<abs-path>&limit=20
   resource://thread/{id}?project=<abs-path>&include_bodies=true
   ```

---

## Beads (br) — Dependency-Aware Issue Tracking

Beads provides a lightweight, dependency-aware issue database and CLI (`br` - beads_rust) for selecting "ready work," setting priorities, and tracking status. It complements MCP Agent Mail's messaging and file reservations.

**Important:** `br` is non-invasive—it NEVER runs git commands automatically. You must manually commit changes after `br sync --flush-only`.

### Conventions
- **Single source of truth:** Beads for task status/priority/dependencies; Agent Mail for conversation and audit
- **Shared identifiers:** Use Beads issue ID (e.g., `br-123`) as Mail `thread_id` and prefix subjects with `[br-123]`
- **Reservations:** When starting a task, call `file_reservation_paths()` with the issue ID in `reason`

### Typical Agent Flow
1. **Pick ready work (Beads):**
   ```bash
   br ready --json  # Choose highest priority, no blockers
   ```
2. **Reserve edit surface (Mail):**
   ```
   file_reservation_paths(project_key, agent_name, ["src/**"], ttl_seconds=3600, exclusive=true, reason="br-123")
   ```
3. **Announce start (Mail):**
   ```
   send_message(..., thread_id="br-123", subject="[br-123] Start: <title>", ack_required=true)
   ```
4. **Work and update:** Reply in-thread with progress
5. **Complete and release:**
   ```bash
   br close 123 --reason "Completed"
   br sync --flush-only  # Export to JSONL (no git operations)
   ```
   ```
   release_file_reservations(project_key, agent_name, paths=["src/**"])
   ```
   Final Mail reply: `[br-123] Completed` with summary

### Mapping Cheat Sheet

| Concept | Value |
|---------|-------|
| Mail `thread_id` | `br-###` |
| Mail subject | `[br-###] ...` |
| File reservation `reason` | `br-###` |
| Commit messages | Include `br-###` for traceability |

---

## Beads Viewer (bv) — Graph-Aware Triage Engine

bv is a graph-aware triage engine for Beads projects (`.beads/beads.jsonl`). It computes PageRank, betweenness, critical path, cycles, HITS, eigenvector, and k-core metrics deterministically.

**Scope boundary:** bv handles *what to work on* (triage, priority, planning). For agent-to-agent coordination (messaging, work claiming, file reservations), use MCP Agent Mail.

**CRITICAL: Use ONLY `--robot-*` flags. Bare `bv` launches an interactive TUI that blocks your session.**

### The Workflow: Start With Triage
**`bv --robot-triage` is your single entry point.** It returns:
- `quick_ref`: at-a-glance counts + top 3 picks
- `recommendations`: ranked actionable items with scores, reasons, unblock info
- `quick_wins`: low-effort high-impact items
- `blockers_to_clear`: items that unblock the most downstream work
- `project_health`: status/type/priority distributions, graph metrics
- `commands`: copy-paste shell commands for next steps

```bash
bv --robot-triage        # THE MEGA-COMMAND: start here
bv --robot-next          # Minimal: just the single top pick + claim command
```

---

## Beads Workflow Integration

This project uses [beads_rust](https://github.com/Dicklesworthstone/beads_rust) (`br`) for issue tracking. Issues are stored in `.beads/` and tracked in git.

**Important:** `br` is non-invasive—it NEVER executes git commands. After `br sync --flush-only`, you must manually run `git add .beads/ && git commit`.

### Essential Commands
```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
br ready              # Show issues ready to work (no blockers)
br list --status=open # All open issues
br show <id>          # Full issue details with dependencies
br create --title="..." --type=task --priority=2
br update <id> --status=in_progress
br close <id> --reason "Completed"
br close <id1> <id2>  # Close multiple issues at once
br sync --flush-only  # Export to JSONL (NO git operations)
```

### Session Protocol
**Before ending any session, run this checklist:**
```bash
git status              # Check what changed
git add <files>         # Stage code changes
br sync --flush-only    # Export beads to JSONL
git add .beads/         # Stage beads changes
git commit -m "..."     # Commit everything together
git push                # Push to remote
```

---

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below.

**MANDATORY WORKFLOW:**
1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Sync beads** - `br sync --flush-only` to export to JSONL
5. **Hand off** - Provide context for next session

---

## CASS — Cross-Agent Session Search

`cass` indexes prior agent conversations (Claude Code, Codex, Cursor, Gemini, ChatGPT, etc.) so we can reuse solved problems.

**Rules:** Never run bare `cass` (TUI). Always use `--robot` or `--json`.

### Examples
```bash
cass health
cass search "async runtime" --robot --limit 5
cass view /path/to/session.jsonl -n 42 --json
cass expand /path/to/session.jsonl -n 42 -C 3 --json
```

---

## Memory System: cass-memory

The Cass Memory System (cm) is a tool for giving agents an effective memory based on the ability to quickly search across previous coding agent sessions and projects and then reflect on what they find to draw out useful lessons.

Before starting complex tasks, retrieve relevant context:
```bash
cm context "<task description>" --json
```

---

## Note for Codex/GPT-5.4:

You constantly bother me and stop working with concerned questions about unexpected files in the working tree. 

NEVER DO THAT. The answer is ALWAYS the same: those are changes created by other agents working concurrently. Treat those changes identically to changes that you yourself made. Never stash, revert, overwrite, or disturb in any way the work of other agents.

---

## Note on Built-in TODO Functionality

If asked to explicitly use built-in TODO functionality, do so without complaining.

---

## Dedicated Agent: Webapp Improvement Loop Agent (`.codex/agents/webapp-improvement-agent.toml`)

- **Role**: Autonomous continuous refinement, bug fixing, UI/UX polishing, test verification, and telemetry sync for Webapp XML.
- **Associated Skills**:
  - `webapp-improvement-loop` (`.agents/skills/webapp-improvement-loop/SKILL.md`)
  - `webapp-refinement` (`.agents/skills/webapp-refinement/SKILL.md`)
  - `code-review` (`.agents/skills/code-review/SKILL.md`)
- **Execution Loop**:
  1. Pre-check disk space and database lock state.
  2. Plan UI/UX and logic improvements.
  3. Execute code edits (preserving docstrings and comments).
  4. Run targeted and global `pytest` suite (3-iteration auto-fix loop).
  5. Sync telemetry to `harness.db` via `unified-gate` and `trace`.

---

## Agent skills

### Issue tracker

Issues and specs are tracked via Local Markdown under `.scratch/` and synced with `harness.db`. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical triage roles mapped to 5 standard labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout using root `CONTEXT.md` and `docs/decisions/` ADRs. See `docs/agents/domain.md`.



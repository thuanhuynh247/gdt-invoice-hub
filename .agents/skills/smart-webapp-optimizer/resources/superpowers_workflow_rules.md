# Obra Superpowers Framework & Plugin Integration Rules

Quy chuẩn tích hợp Superpowers (obra/superpowers) vào quy trình ReAct Harness & Agentic Development.

## 1. Luồng Quy trình Superpowers (Superpowers Core Lifecycle)

```text
Clarify & Socratic ➔ Spec-First Design ➔ Strict TDD (Red/Green) ➔ Subagent Workers ➔ Two-Stage Review ➔ Compounding
```

1. **Clarify & Socratic Brainstorming**:
   - Sử dụng phương pháp đặt câu hỏi Socratic làm rõ yêu cầu trước khi đụng vào code.
   - Ngăn ngừa việc nhảy ngay vào lập trình (Premature Coding).
2. **Spec-First Architectural Design**:
   - Viết bản phác thảo kiến trúc `implementation_plan.md` và `task.md` trước khi triển khai.
   - Ràng buộc tiêu chí nghiệm thu (Acceptance Criteria) và Blast Radius rõ ràng.
3. **Strict Test-Driven Development (Red/Green/Refactor)**:
   - 🔴 **Red**: Viết test hoặc chạy test hiện có để chứng minh test THẤT BẠI trước khi viết code sửa.
   - 🟢 **Green**: Viết mã tối thiểu để vượt qua test.
   - 🔵 **Refactor**: Tối ưu UI/UX & cấu trúc code mà không phá hỏng test suite.
4. **Subagent & Parallel Worker Execution**:
   - Phân tách và ủy quyền công việc cho Subagent/Worker độc lập nhằm duy trì Context Window sạch.
5. **Two-Stage Code Inspection & Review**:
   - **Stage 1 (Spec Review)**: Đảm bảo code thực hiện 100% đúng theo Spec.
   - **Stage 2 (Quality & Security Review)**: Kiểm tra chuẩn coding, không lộ secret, tuân thủ Facts Only (NP.5).
6. **Compounding & Knowledge Retention**:
   - Đúc kết bài học, pattern tái sử dụng và Telemetry Trace vào `harness.db` và `walkthrough.md`.

<!-- Integrated Obra Superpowers Plugin Engine -->

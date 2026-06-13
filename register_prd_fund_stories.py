import sqlite3

def main():
    conn = sqlite3.connect("harness.db")
    c = conn.cursor()
    
    # We register the 5 stories for So Quy (PRD-FUND)
    stories = [
        (
            'PRD-FUND-E1-S1',
            'Tạo quỹ nhóm',
            'normal',
            'docs/product/stories/PRD-FUND-E1-S1.md',
            'planned',
            'Cho fund-keeper trong một nhóm, khi tạo quỹ với tên quỹ và đơn vị tiền VNĐ, thì quỹ được tạo với số dư ban đầu bằng 0. Cho một nhóm đã có quỹ, khi bất kỳ thành viên nào mở app, thì họ thấy quỹ đó trong nhóm của mình.'
        ),
        (
            'PRD-FUND-E2-S1',
            'Ghi khoản nộp quỹ',
            'normal',
            'docs/product/stories/PRD-FUND-E2-S1.md',
            'planned',
            'Cho fund-keeper, khi ghi khoản nộp với người nộp, số tiền và ngày, thì giao dịch nộp xuất hiện trong lịch sử và số dư tăng đúng bằng số tiền nộp.'
        ),
        (
            'PRD-FUND-E2-S2',
            'Ghi khoản chi từ quỹ',
            'normal',
            'docs/product/stories/PRD-FUND-E2-S2.md',
            'planned',
            'Cho fund-keeper, khi ghi khoản chi với mô tả, số tiền và ngày, thì giao dịch chi xuất hiện trong lịch sử và số dư giảm đúng bằng số tiền chi.'
        ),
        (
            'PRD-FUND-E3-S1',
            'Xem số dư quỹ',
            'normal',
            'docs/product/stories/PRD-FUND-E3-S1.md',
            'planned',
            'Cho một thành viên bất kỳ của nhóm, khi mở quỹ, thì thấy số dư hiện tại bằng tổng nộp trừ tổng chi.'
        ),
        (
            'PRD-FUND-E3-S2',
            'Xem lịch sử thu chi',
            'normal',
            'docs/product/stories/PRD-FUND-E3-S2.md',
            'planned',
            'Cho một thành viên bất kỳ, khi mở lịch sử quỹ, thì thấy danh sách giao dịch với: loại (nộp/chi), người liên quan, số tiền và ngày. Sắp xếp mới nhất trước.'
        )
    ]
    
    for s in stories:
        # Delete if exists to avoid primary key conflict on retry
        c.execute("DELETE FROM story WHERE id = ?", (s[0],))
        # Insert
        c.execute(
            """INSERT INTO story 
            (id, title, risk_lane, contract_doc, status, notes, unit_proof, integration_proof, e2e_proof, platform_proof, evidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0, '', CURRENT_TIMESTAMP)""",
            s
        )
    
    conn.commit()
    print("Successfully registered PRD-FUND stories in harness.db")
    conn.close()

if __name__ == '__main__':
    main()

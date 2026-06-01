import unittest
import os
import json
from invoices.cit_service import finalize_cit, simulate_cit_scenario

class TestCITService(unittest.TestCase):
    def setUp(self):
        # Set up a sample trial balance mapping (Thông tư 200) with movements
        self.sample_balances = {
            "511": {"credit_movement": 10000000000.0, "debit_movement": 0.0},  # Revenue
            "515": {"credit_movement": 200000000.0, "debit_movement": 0.0},   # Financial income
            "711": {"credit_movement": 100000000.0, "debit_movement": 0.0},   # Other income
            "632": {"debit_movement": 6000000000.0, "credit_movement": 0.0},  # Cost of Goods Sold
            "635": {"debit_movement": 800000000.0, "credit_movement": 0.0},   # Financial expenses (Total interest)
            "641": {"debit_movement": 500000000.0, "credit_movement": 0.0},   # Selling expenses
            "642": {"debit_movement": 1000000000.0, "credit_movement": 0.0},  # Administrative expenses
            "811": {"debit_movement": 50000000.0, "credit_movement": 0.0},    # Other expenses
            "214": {"credit_movement": 400000000.0, "debit_movement": 0.0},   # Accumulated depreciation (used for EBITDA)
        }
        self.sample_metadata = {
            "mst": "0109998887",
            "year": "2026",
            "company_name": "CONG TY TNHH TEST",
            "interest_linked": 600000000.0,       # Linked party interest expense included in 635
            "non_deductible_manual": 100000000.0, # Other non-deductible expenses (B4 indicator)
            "loss_carry_forward": 200000000.0,    # Losses carried forward from previous years
            "rd_allowance": 50000000.0            # R&D tax allowance credit
        }

    def test_finalize_cit_calculation(self):
        # Run calculation
        result = finalize_cit(self.sample_balances, self.sample_metadata)
        
        self.assertIn("pretax_profit", result)
        self.assertIn("ebitda", result)
        self.assertIn("interest_cap", result)
        self.assertIn("non_deductible_interest", result)
        self.assertIn("cit_payable", result)
        self.assertIn("xml", result)
        
        # Verify pretax profit: (10B + 200M + 100M) - (6B + 800M + 500M + 1B + 50M) = 10.3B - 8.35B = 1.95B
        self.assertAlmostEqual(result["pretax_profit"], 1950000000.0)
        
        # Verify EBITDA: Pretax Profit + Interest (635) + Depreciation (214)
        # 1.95B + 800M + 400M = 3.15B
        self.assertAlmostEqual(result["ebitda"], 3150000000.0)
        
        # Verify Interest Cap under Decree 132 (30% of EBITDA): 30% * 3.15B = 945,000,000
        self.assertAlmostEqual(result["interest_cap"], 945000000.0)
        
        # Linked interest is 600M, which is <= 945M, so non-deductible interest must be 0
        self.assertAlmostEqual(result["non_deductible_interest"], 0.0)
        
        # Let's test with higher linked interest to trigger cap
        high_metadata = self.sample_metadata.copy()
        high_metadata["interest_linked"] = 1200000000.0 # Exceeds 945M cap
        high_result = finalize_cit(self.sample_balances, high_metadata)
        
        balances_high_interest = self.sample_balances.copy()
        balances_high_interest["635"] = {"debit_movement": 1200000000.0, "credit_movement": 0.0}
        high_result = finalize_cit(balances_high_interest, high_metadata)
        self.assertAlmostEqual(high_result["non_deductible_interest"], 255000000.0)

    def test_xml_scaffolding(self):
        result = finalize_cit(self.sample_balances, self.sample_metadata)
        xml_content = result["xml"]
        
        self.assertIn("<ToKhaiQuyetToanTNDN>", xml_content)
        self.assertIn(self.sample_metadata["mst"], xml_content)
        self.assertIn(self.sample_metadata["company_name"], xml_content)
        self.assertIn('<LoiNhuanKeToanTruocThue Code="A1">', xml_content)
        self.assertIn('<ChiPhiKhongDuocTru Code="B4">', xml_content)

    def test_simulate_cit_scenario(self):
        base_data = {
            "revenue": 10000000000.0,
            "cogs": 6000000000.0,
            "salaries": 1000000000.0,
            "other_costs": 1500000000.0,
            "depreciation": 400000000.0
        }
        adjustments = {
            "revenue_pct": 10.0,           # +10% revenue
            "cost_of_goods_pct": 5.0,      # +5% COGS
            "staff_costs": 200000000.0,    # +200M salary increase
            "interest_linked": 800000000.0, # 800M linked interest expense
            "rd_investment": 300000000.0    # 300M R&D investment
        }
        
        sim_result = simulate_cit_scenario(base_data, adjustments)
        
        self.assertIn("pretax_profit", sim_result)
        self.assertIn("ebitda", sim_result)
        self.assertIn("cit_payable", sim_result)
        self.assertIn("effective_tax_rate", sim_result)
        self.assertIn("risk_score", sim_result)
        self.assertIn("risk_reasons", sim_result)

if __name__ == "__main__":
    unittest.main()

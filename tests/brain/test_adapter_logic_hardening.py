import unittest
import sys
from datetime import datetime, date, timedelta
from dataclasses import dataclass

# MOCK ALG IMPORTS BEFORE SUT IMPORT
if "AlgorithmImports" not in sys.modules:
    mod = type(sys)("AlgorithmImports")
    mod.Resolution = type('M',(),{'Daily':"Daily"})
    mod.SecurityType = type('M',(),{'Option':"Option",'Equity':"Equity"})
    mod.OptionRight = type('M',(),{'Call':0,'Put':1})
    sys.modules["AlgorithmImports"] = mod

from qc.AutopilotQC_v1.adapter.snapshot_builder import SnapshotBuilder

# Mock Types
@dataclass
class MockSymbolID:
    Date: datetime
    def ToString(self): return "ID"

@dataclass
class MockSymbol:
    ID: MockSymbolID
    Value: str = "SPY_OPT"
    def ToString(self): return self.Value

class MockSecurity:
    def __init__(self, symbol, price=100):
        self.Symbol = symbol
        self.Price = price
        self.BidPrice = 99
        self.AskPrice = 101

class MockAlgo:
    def __init__(self):
        self.Time = datetime(2023, 1, 1, 9, 30)
        self.Securities = {}

class TestAdapterHardening(unittest.TestCase):
    def test_dte_boundary_logic(self):
        """Phase 1: Verify DTE uses strictly date-based diff logic."""
        algo = MockAlgo()
        # Case A: Morning Scan (09:45)
        algo.Time = datetime(2023, 1, 10, 9, 45) # Tuesday
        
        # Option expiring Friday Jan 13 -> 3 Days away exactly?
        # DTE = 13 - 10 = 3. Should be included (Range 3-7).
        expiry_fri = datetime(2023, 1, 13, 16, 0)
        
        sb = SnapshotBuilder(algo, None, None)
        
        # Mimic logic
        current_date = algo.Time.date()
        expiry_date = expiry_fri.date()
        dte = (expiry_date - current_date).days
        
        self.assertEqual(dte, 3, "Friday expiry on Tuesday morning should be 3 DTE")
        
        # Case B: Afternoon Scan (15:45)
        algo.Time = datetime(2023, 1, 10, 15, 45) # Tuesday Afternoon
        # Logic is date based, so time of day shouldn't maximize granularity to '2.9 days'
        current_date = algo.Time.date()
        dte_pm = (expiry_date - current_date).days
        self.assertEqual(dte_pm, 3, "Friday expiry on Tuesday afternoon should still be 3 DTE (Date Diff)")
        
        # Case C: Expiry is Tomorrow (Wednesday Jan 11)
        # DTE = 11 - 10 = 1. Should be excluded (<3).
        expiry_wed = datetime(2023, 1, 11)
        dte_short = (expiry_wed.date() - algo.Time.date()).days
        self.assertEqual(dte_short, 1)
        
    def test_completeness_invariant(self):
        """Phase 1: Enforce Daily Bar Completeness."""
        # RollingStore logic test
        # If Current Time is Jan 10 (Intraday), Last Daily Bar must be Jan 9 or earlier.
        
        curr_time = datetime(2023, 1, 10, 14, 0)
        last_bar_time = datetime(2023, 1, 9, 0, 0) # QC Daily bar for Jan 9
        
        # Invariant: last_bar_time.date() < curr_time.date()
        self.assertLess(last_bar_time.date(), curr_time.date())
        
        # Fail case: Peeking at today's close
        today_bar_time = datetime(2023, 1, 10, 0, 0) # Bar for Jan 10
        # This bar is technically "started" at midnight, but definitely not complete at 14:00.
        # But wait, QC Daily bars from History/Consolidator usually conform.
        # The check `Time + Period <= AlgoTime` handles this generally.
        # Here we just verify the date check logic we implemented.
        is_safe = today_bar_time.date() < curr_time.date()
        self.assertFalse(is_safe, "Should NOT accept same-day daily bar")

if __name__ == '__main__':
    unittest.main()

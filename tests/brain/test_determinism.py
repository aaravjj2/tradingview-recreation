import unittest
from datetime import datetime
from phase1.autopilot_brain.decide import Brain
from phase1.autopilot_brain.types import Snapshot, BrainState, RiskCounters
from phase1.autopilot_brain.config import MAX_OPEN_POSITIONS

class TestBrainDeterminism(unittest.TestCase):
    def test_determinism(self):
        """Same input -> Same output."""
        cycle_time = datetime(2025, 1, 1, 10, 0, 0)
        
        snap = Snapshot(
            cycle_time=cycle_time,
            minutes_to_close=300,
            is_market_open=True,
            underlyings={},
            options=[],
            positions=[],
            risk=RiskCounters()
        )
        state = BrainState()
        
        # Run 1
        actions1, state1, explain1 = Brain.decide(snap, state)
        
        # Run 2
        actions2, state2, explain2 = Brain.decide(snap, state)
        
        self.assertEqual(actions1, actions2)
        self.assertEqual(state1, state2)
        self.assertEqual(explain1, explain2)

if __name__ == '__main__':
    unittest.main()

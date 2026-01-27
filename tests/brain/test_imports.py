import unittest
import sys
import phase1.autopilot_brain
import types

class TestBrainImports(unittest.TestCase):
    def test_no_forbidden_imports(self):
        """Ensure no 'alpaca', 'pandas' (optional), 'requests' in brain."""
        
        # Walk modules in phase1.autopilot_brain
        import pkgutil
        import phase1.autopilot_brain
        
        forbidden = ['alpaca_trade_api', 'requests', 'urllib3']
        
        for loader, name, ispkg in pkgutil.walk_packages(phase1.autopilot_brain.__path__, phase1.autopilot_brain.__name__ + "."):
            # Import module
            try:
                mod = __import__(name, fromlist=['_'])
                
                # Check imports in that module
                for key in mod.__dict__:
                    if any(f in str(key) for f in forbidden):
                        self.fail(f"Module {name} has forbidden import: {key}")
                        
            except ImportError:
                continue

if __name__ == '__main__':
    unittest.main()

import asyncio
import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

# Add path
sys.path.append(os.path.abspath("phase1"))

# Mock environment
os.environ["APCA_API_KEY_ID"] = "test"
os.environ["APCA_API_SECRET_KEY"] = "test"

async def verify_p0():
    print("VERIFYING P0 REQUIREMENTS...")
    
    # 1. Verify Configuration Feature Flags
    from services.autopilot.config import get_autopilot_config
    config = get_autopilot_config()
    print(f"✅ Config loaded. enable_finbert is: {config.enable_finbert}")
    assert config.enable_finbert is False, "enable_finbert should be False by default"
    
    # 2. Verify NewsProvider respects flag
    # We use get_ensemble_sentiment_engine as the entry point
    from services.autopilot.news_sentiment import get_ensemble_sentiment_engine, EnsembleSentimentEngine
    
    engine = get_ensemble_sentiment_engine()
    
    # Mock _finbert to look "available"
    mock_finbert = MagicMock()
    mock_finbert.is_available = True
    # If analyze_batch is called, return something (to prove it's NOT used if flag is off)
    mock_finbert.analyze_batch.return_value = [MagicMock(normalized_score=0.9, confidence=0.9)]
    
    engine._finbert = mock_finbert
    
    # Mock headlines
    headlines = ["AAPL is doing great!"]
    
    # Test analysis
    # We need to make sure config is read inside the method, which it is in our implementation
    snapshot = await engine.get_ensemble_sentiment("AAPL", headlines)
    
    # Should NOT use finbert because flag is False
    # If flag was True, analyze_batch would have been called
    assert not mock_finbert.analyze_batch.called, "FinBERT analyze_batch should NOT be called when disabled"
    
    sources = getattr(snapshot, "sources", {}) # internal impl detail if it returns SentimentSnapshot? 
    # Actually get_ensemble_sentiment returns SentimentScore which might not have sources dict exposed publically same way?
    # Let's check the code.
    # The return type is SentimentScore.
    # In previous edit: snapshot.sources["finbert"] = ...
    # So if it's NOT in sources, we are good.
    # But SentimentScore class definition? 
    # I'll rely on the mock call assertion primarily.
    
    print("✅ FinBERT correctly disabled by feature flag (method not called)")

    # 3. Verify client_order_id propagation
    from services.autopilot.unified_engine import UnifiedAutopilotEngine
    from services.autopilot.candidates import TradeCandidate
    
    engine = UnifiedAutopilotEngine()
    
    # Mock candidate generation to return one result
    candidate_dict = {
        "symbol": "AAPL",
        "template": "put_credit_spread",
        "credit": 1.50,
        "underlying_price": 150.0,
        "max_loss": 500.0,
        "pop": 0.7,
        "dte": 30,
        "short_strike": 145,
        "long_strike": 140,
        "expiry": date.today().isoformat()
    }
    
    # Patch AlpacaOptionsBroker where it is DEFINED
    with patch("services.autopilot.alpaca_broker.AlpacaOptionsBroker") as MockBroker:
        # Run _execute_trades directly
        mock_broker_instance = MockBroker.return_value
        
        # When submit_order is called, return a filled order with ID logic
        def side_effect_submit(candidate, *args, **kwargs):
             # Verify logic inside broker uses the ID
             # But here we are mocking the broker, so we can't test the broker logic itself easily without instantiating it.
             # We want to verified that Engine PASSES the ID to the Broker.
             return MagicMock(status=MagicMock(value="filled"), order_id="alpaca_123")
             
        mock_broker_instance.submit_order.side_effect = side_effect_submit
        # Mock dependency injection - actually we just need to patch the Class where it is defined
        # because unified_engine imports it from there.
        
        orders = await engine._execute_trades([candidate_dict], run_id="run_123")
             
        # Check if submit_order was called
        assert mock_broker_instance.submit_order.called
             
        # Get the arguments passed to submit_order
        call_args = mock_broker_instance.submit_order.call_args
        trade_candidate = call_args[0][0] # first arg is candidate
             
        print(f"✅ UnifiedEngine created TradeCandidate with client_order_id: {trade_candidate.client_order_id}")
        assert trade_candidate.client_order_id is not None, "client_order_id must be set by Engine"
        assert "run_123" in trade_candidate.client_order_id, "run_id must be in client_order_id"
    
    # 4. Verify AlpacaOptionsBroker uses the ID (Unit Test logic)
    from services.autopilot.alpaca_broker import AlpacaOptionsBroker
    
    # 4. Verify AlpacaOptionsBroker uses the ID (Unit Test logic)
    from services.autopilot.alpaca_broker import AlpacaOptionsBroker
    
    # Mock the internal alpaca client
    # We don't need to patch imports, just set the client on the instance
    broker = AlpacaOptionsBroker(alpaca_enabled=False) # Don't init real client
    broker._alpaca_enabled = True
    broker._alpaca_client = MagicMock()
    
    # Mock client submit returns success
    broker._alpaca_client.submit_order.return_value = MagicMock(id="alpaca_real_id")
         
    # Create a candidate WITH an ID
    cand = TradeCandidate(
             id="test", symbol="AAPL", template="test", legs=[], underlying_price=100,
             max_profit=10, max_loss=10, pop=0.5, dte=30, iv_rank=50, liquidity_score=1,
             spread_percent=0.1, regime="neutral", trend="neutral",
             client_order_id="MY_UNIQUE_ID"
    )
    # Add a dummy leg so logic proceeds to submit
    from services.autopilot.candidates import OptionLeg
    cand.legs = [OptionLeg(option_type="call", strike=100, expiry=date.today(), side="buy")]
         
    broker.submit_order(cand)
         
    # Verify client.submit_order received the ID
    assert broker._alpaca_client.submit_order.called
    kwargs = broker._alpaca_client.submit_order.call_args[1]
    if not kwargs: # check args if kwargs empty
        kwargs = broker._alpaca_client.submit_order.call_args[0][0] # Request object?
        # If it passed a Request object, we need to inspect it
        # In alpaca_broker.py: request = MarketOrderRequest(...)
        # alpaca_order = self._alpaca_client.submit_order(request)
        # So it passes an OBJECT, not kwargs.
        
        request_obj = broker._alpaca_client.submit_order.call_args[0][0]
        passed_id = request_obj.client_order_id
    else:
        passed_id = kwargs.get("client_order_id")
         
    print(f"✅ AlpacaOptionsBroker submitted with client_order_id: {passed_id}")
    assert "MY_UNIQUE_ID" in passed_id, "Broker should use the provided client_order_id"

    print("ALL P0 VERIFICATIONS PASSED")

if __name__ == "__main__":
    asyncio.run(verify_p0())

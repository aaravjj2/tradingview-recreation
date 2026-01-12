"""
Options Supergraph Dashboard - Main Application
A Professional Options Strategy Visualizer & Simulator

Run with: streamlit run main.py
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

from config import (
    STRATEGY_TEMPLATES, DEFAULT_RISK_FREE_RATE, 
    PRICE_RANGE_PERCENT, DEFAULT_STRIKE_INTERVAL
)
from data_manager import (
    get_current_price, get_implied_volatility, 
    get_available_expirations, data_manager
)
from logic import (
    OptionLeg, build_strategy_legs, generate_price_range,
    calculate_expiration_payoff, calculate_theoretical_payoff,
    calculate_position_greeks, find_breakeven_points,
    calculate_max_profit_loss, calculate_probability_of_profit
)

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="Options Supergraph",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --profit-green: #00C853;
        --loss-red: #FF1744;
        --neutral-blue: #2196F3;
        --dark-bg: #0E1117;
        --card-bg: #1E2329;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.8);
        margin: 0.5rem 0 0 0;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, #1a1f2e, #151923);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    .metric-card.profit {
        border-left: 4px solid #00C853;
    }
    
    .metric-card.loss {
        border-left: 4px solid #FF1744;
    }
    
    .metric-card.info {
        border-left: 4px solid #2196F3;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.6);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
    }
    
    .metric-value.green { color: #00C853; }
    .metric-value.red { color: #FF1744; }
    .metric-value.blue { color: #2196F3; }
    .metric-value.purple { color: #9C27B0; }
    
    /* Greeks table */
    .greeks-table {
        background: #1a1f2e;
        border-radius: 12px;
        padding: 1rem;
        margin-top: 1rem;
    }
    
    .greek-row {
        display: flex;
        justify-content: space-between;
        padding: 0.75rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .greek-row:last-child {
        border-bottom: none;
    }
    
    /* Sidebar styling */
    .sidebar .stSelectbox label {
        font-weight: 600;
    }
    
    /* Info box */
    .info-box {
        background: rgba(33, 150, 243, 0.1);
        border: 1px solid rgba(33, 150, 243, 0.3);
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Strategy leg display */
    .leg-card {
        background: #1a1f2e;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .leg-long { border-left: 3px solid #00C853; }
    .leg-short { border-left: 3px solid #FF1744; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Header
# =============================================================================

st.markdown("""
<div class="main-header">
    <h1>📈 Options Supergraph</h1>
    <p>Professional Options Strategy Visualizer • Black-Scholes Pricing Engine</p>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# Sidebar - Inputs
# =============================================================================

with st.sidebar:
    st.markdown("### 📊 Strategy Builder")
    
    # Ticker Input
    ticker = st.text_input(
        "Stock Ticker",
        value="SPY",
        help="Enter a stock symbol (e.g., SPY, NVDA, AAPL)"
    ).upper()
    
    # Fetch current price
    if ticker:
        with st.spinner(f"Fetching {ticker} data..."):
            current_price = get_current_price(ticker)
            if current_price:
                st.success(f"**{ticker}**: ${current_price:.2f}")
                base_iv = get_implied_volatility(ticker, current_price)
            else:
                st.error("Could not fetch price. Using demo mode.")
                current_price = 500.0  # Demo fallback
                base_iv = 0.25
    else:
        current_price = 500.0
        base_iv = 0.25
    
    st.markdown("---")
    
    # Strategy Selection
    st.markdown("### 🎯 Strategy")
    strategy_name = st.selectbox(
        "Select Strategy",
        options=list(STRATEGY_TEMPLATES.keys()),
        index=0,
        help="Choose a predefined strategy or build custom"
    )
    
    # Expiration Selection
    st.markdown("---")
    st.markdown("### 📅 Expiration")
    
    expirations = get_available_expirations(ticker)
    if expirations:
        selected_expiration = st.selectbox(
            "Select Expiration",
            options=expirations,
            index=0
        )
        exp_date = datetime.strptime(selected_expiration, "%Y-%m-%d")
        days_to_expiration = max(1, (exp_date - datetime.now()).days)
    else:
        days_to_expiration = st.slider(
            "Days to Expiration",
            min_value=1,
            max_value=90,
            value=30,
            step=1
        )
    
    st.info(f"**DTE:** {days_to_expiration} days")
    
    # Strike Interval
    strike_interval = st.selectbox(
        "Strike Interval",
        options=[1.0, 2.5, 5.0, 10.0, 25.0],
        index=2,  # Default $5
        help="Distance between strike prices"
    )
    
    st.markdown("---")
    
    # Interactive Sliders
    st.markdown("### ⚡ Simulation Controls")
    
    # IV Adjustment
    iv_adjustment = st.slider(
        "IV Adjustment",
        min_value=-50,
        max_value=50,
        value=0,
        step=5,
        help="Simulate IV crush or expansion",
        format="%d%%"
    ) / 100.0
    
    adjusted_iv = base_iv + iv_adjustment
    iv_display = f"{base_iv*100:.1f}% → {adjusted_iv*100:.1f}%"
    if iv_adjustment != 0:
        color = "🟢" if iv_adjustment > 0 else "🔴"
        st.caption(f"{color} IV: {iv_display}")
    
    # Time Slider (T+X simulation)
    days_forward = st.slider(
        "Days Forward (T+X)",
        min_value=0,
        max_value=days_to_expiration,
        value=0,
        step=1,
        help="Simulate the passage of time"
    )
    
    days_remaining = max(0.001, days_to_expiration - days_forward)
    if days_forward > 0:
        st.caption(f"⏰ Simulating T+{days_forward} ({days_remaining:.0f} DTE)")
    
    # Price Range
    price_range_pct = st.slider(
        "Price Range",
        min_value=10,
        max_value=50,
        value=20,
        step=5,
        help="Chart price range (+/- %)"
    ) / 100.0


# =============================================================================
# Build Strategy
# =============================================================================

# Get strategy template
strategy_template = STRATEGY_TEMPLATES.get(strategy_name, [])

if strategy_template:
    legs = build_strategy_legs(
        strategy_template=strategy_template,
        current_price=current_price,
        strike_interval=strike_interval,
        base_iv=base_iv,
        days_to_expiration=days_to_expiration
    )
else:
    legs = []

# Generate price range for chart
price_range = generate_price_range(current_price, price_range_pct)


# =============================================================================
# Calculate Payoffs
# =============================================================================

if legs:
    # Expiration payoff (angular line)
    expiration_payoff = calculate_expiration_payoff(legs, price_range)
    
    # Theoretical payoff (curved T+0 line)
    theoretical_payoff = calculate_theoretical_payoff(
        legs, price_range, days_remaining, iv_adjustment
    )
    
    # Position Greeks
    position_greeks = calculate_position_greeks(
        legs, current_price, days_remaining
    )
    
    # Breakeven points
    breakevens = find_breakeven_points(legs, price_range)
    
    # Max Profit/Loss
    max_profit, max_loss = calculate_max_profit_loss(legs, price_range)
    
    # Probability of Profit
    pop = calculate_probability_of_profit(
        legs, current_price, days_remaining, adjusted_iv
    )
else:
    expiration_payoff = np.zeros_like(price_range)
    theoretical_payoff = np.zeros_like(price_range)
    position_greeks = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
    breakevens = []
    max_profit, max_loss = 0, 0
    pop = 0


# =============================================================================
# The Supergraph
# =============================================================================

st.markdown("### 📈 The Supergraph")

# Create Plotly figure
fig = go.Figure()

# Add profit/loss zones (shaded regions)
# Profit zone (green)
profit_mask = expiration_payoff >= 0
# Loss zone (red)
loss_mask = expiration_payoff < 0

# Zero line
fig.add_hline(
    y=0, 
    line_dash="solid", 
    line_color="rgba(255,255,255,0.3)",
    line_width=1
)

# Current price vertical line
fig.add_vline(
    x=current_price,
    line_dash="dash",
    line_color="rgba(255,255,255,0.5)",
    line_width=1,
    annotation_text=f"Current: ${current_price:.2f}",
    annotation_position="top"
)

# Expiration Payoff Line (solid/angular - "The Truth")
fig.add_trace(go.Scatter(
    x=price_range,
    y=expiration_payoff,
    mode='lines',
    name='At Expiration',
    line=dict(
        color='#FFD700',  # Gold
        width=3,
        shape='linear'
    ),
    hovertemplate='<b>Price:</b> $%{x:.2f}<br><b>P/L at Expiry:</b> $%{y:.2f}<extra></extra>'
))

# Theoretical Payoff Line (dashed/curved - "The Curve")
fig.add_trace(go.Scatter(
    x=price_range,
    y=theoretical_payoff,
    mode='lines',
    name=f'T+{days_forward} (Now)' if days_forward > 0 else 'Current (T+0)',
    line=dict(
        color='#00BCD4',  # Cyan
        width=3,
        dash='dash'
    ),
    hovertemplate='<b>Price:</b> $%{x:.2f}<br><b>Theoretical P/L:</b> $%{y:.2f}<extra></extra>'
))

# Add fill between curves to show the "theta burn"
fig.add_trace(go.Scatter(
    x=np.concatenate([price_range, price_range[::-1]]),
    y=np.concatenate([theoretical_payoff, expiration_payoff[::-1]]),
    fill='toself',
    fillcolor='rgba(156, 39, 176, 0.15)',  # Purple tint
    line=dict(width=0),
    name='Time Value',
    hoverinfo='skip'
))

# Add breakeven markers
for be in breakevens:
    fig.add_trace(go.Scatter(
        x=[be],
        y=[0],
        mode='markers+text',
        marker=dict(size=12, color='#FF9800', symbol='diamond'),
        text=[f'BE: ${be:.2f}'],
        textposition='top center',
        textfont=dict(color='#FF9800', size=11),
        name=f'Breakeven ${be:.2f}',
        showlegend=False,
        hoverinfo='skip'
    ))

# Layout
fig.update_layout(
    height=550,
    template='plotly_dark',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(15,17,23,1)',
    hovermode='x unified',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor='rgba(0,0,0,0.5)',
        bordercolor='rgba(255,255,255,0.2)',
        borderwidth=1
    ),
    xaxis=dict(
        title="Stock Price ($)",
        gridcolor='rgba(255,255,255,0.1)',
        tickformat='$.2f',
        showspikes=True,
        spikecolor='rgba(255,255,255,0.5)',
        spikethickness=1
    ),
    yaxis=dict(
        title="Profit / Loss ($)",
        gridcolor='rgba(255,255,255,0.1)',
        tickformat='$,.0f',
        zeroline=True,
        zerolinecolor='rgba(255,255,255,0.3)',
        zerolinewidth=2
    ),
    margin=dict(l=60, r=30, t=50, b=60)
)

# Add profit/loss coloring to the y-axis region
fig.add_shape(
    type="rect",
    x0=price_range[0], x1=price_range[-1],
    y0=0, y1=max_profit if max_profit > 0 else 100,
    fillcolor="rgba(0, 200, 83, 0.05)",
    line=dict(width=0),
    layer="below"
)

fig.add_shape(
    type="rect",
    x0=price_range[0], x1=price_range[-1],
    y0=max_loss if max_loss < 0 else -100, y1=0,
    fillcolor="rgba(255, 23, 68, 0.05)",
    line=dict(width=0),
    layer="below"
)

st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# Metrics Row
# =============================================================================

st.markdown("### 💰 Position Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    profit_str = f"${max_profit:,.2f}" if max_profit < 1e6 else "Unlimited"
    st.markdown(f"""
    <div class="metric-card profit">
        <div class="metric-label">Max Profit</div>
        <div class="metric-value green">{profit_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    loss_str = f"${max_loss:,.2f}" if max_loss > -1e6 else "Unlimited"
    st.markdown(f"""
    <div class="metric-card loss">
        <div class="metric-label">Max Loss</div>
        <div class="metric-value red">{loss_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    be_str = " / ".join([f"${be:.2f}" for be in breakevens]) if breakevens else "N/A"
    st.markdown(f"""
    <div class="metric-card info">
        <div class="metric-label">Breakeven(s)</div>
        <div class="metric-value blue">{be_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #9C27B0;">
        <div class="metric-label">Prob. of Profit</div>
        <div class="metric-value purple">{pop:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# Greeks Display
# =============================================================================

st.markdown("### 📐 Position Greeks")

greeks_col1, greeks_col2, greeks_col3, greeks_col4 = st.columns(4)

with greeks_col1:
    delta = position_greeks.get("delta", 0)
    delta_color = "green" if delta > 0 else "red" if delta < 0 else "blue"
    st.metric(
        label="Delta (Δ)",
        value=f"{delta:.2f}",
        help="Directional exposure. +1 = long 100 shares equivalent"
    )

with greeks_col2:
    gamma = position_greeks.get("gamma", 0)
    st.metric(
        label="Gamma (Γ)",
        value=f"{gamma:.4f}",
        help="Rate of change of Delta per $1 stock move"
    )

with greeks_col3:
    theta = position_greeks.get("theta", 0)
    theta_color = "🟢" if theta > 0 else "🔴"
    st.metric(
        label="Theta (Θ)",
        value=f"${theta:.2f}/day",
        help="Daily time decay (negative = losing money each day)"
    )

with greeks_col4:
    vega = position_greeks.get("vega", 0)
    st.metric(
        label="Vega (ν)",
        value=f"${vega:.2f}",
        help="P/L change per 1% IV change"
    )


# =============================================================================
# Strategy Legs Display
# =============================================================================

if legs:
    st.markdown("### 📋 Strategy Legs")
    
    legs_data = []
    for i, leg in enumerate(legs):
        if leg.option_type == "stock":
            leg_desc = f"{'Long' if leg.sign > 0 else 'Short'} {leg.quantity} shares"
            strike_str = f"@ ${leg.strike:.2f}"
            premium_str = "-"
        else:
            direction = "LONG" if leg.sign > 0 else "SHORT"
            leg_desc = f"{direction} {leg.quantity} {leg.option_type.upper()}"
            strike_str = f"${leg.strike:.2f}"
            premium_str = f"${leg.premium:.2f}"
        
        legs_data.append({
            "Leg": i + 1,
            "Position": leg_desc,
            "Strike": strike_str,
            "Premium": premium_str,
            "IV": f"{leg.iv * 100:.1f}%" if leg.iv > 0 else "-"
        })
    
    import pandas as pd
    legs_df = pd.DataFrame(legs_data)
    st.dataframe(
        legs_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Leg": st.column_config.NumberColumn("Leg", width="small"),
            "Position": st.column_config.TextColumn("Position", width="medium"),
            "Strike": st.column_config.TextColumn("Strike", width="small"),
            "Premium": st.column_config.TextColumn("Premium", width="small"),
            "IV": st.column_config.TextColumn("IV", width="small")
        }
    )


# =============================================================================
# Educational Info
# =============================================================================

with st.expander("📚 Understanding the Supergraph", expanded=False):
    st.markdown("""
    ### The Two Lines Explained
    
    **🟡 Gold Line (At Expiration)**
    - Shows your exact P/L when the options expire
    - Sharp, angular "hockey stick" shape
    - Based on simple intrinsic value calculations
    - This is "the truth" - what will actually happen at expiry
    
    **🔵 Cyan Dashed Line (Theoretical / T+0)**
    - Shows your P/L right now (or at the simulated date)
    - Smooth, curved shape due to time value
    - Calculated using the Black-Scholes model
    - Incorporates IV, time decay, and all Greeks
    
    ### The Purple Shaded Area
    - Represents the "time value" in your options
    - This value erodes as expiration approaches (theta decay)
    - Use the "Days Forward" slider to watch it shrink!
    
    ### Interactive Simulations
    - **IV Slider**: Simulate volatility crush or expansion
    - **Days Forward**: Watch theta decay eat your position
    - **Price Range**: Zoom in/out on the chart
    
    ### The Greeks
    - **Delta (Δ)**: How much your P/L changes per $1 stock move
    - **Gamma (Γ)**: How quickly Delta changes (acceleration)
    - **Theta (Θ)**: Daily time decay (usually negative for buyers)
    - **Vega (ν)**: Sensitivity to IV changes
    """)


# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: rgba(255,255,255,0.4);'>"
    "Options Supergraph • Built with Streamlit, Plotly & Black-Scholes"
    "</p>",
    unsafe_allow_html=True
)

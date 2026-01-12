# TradingView Recreation

<div align="center">

**A Production-Grade Market Workstation Platform**

*Combining TradingView-style charting with Bloomberg-terminal analytics*

**Built with the tools and technologies:**

<img src="https://img.shields.io/badge/Python-3776AB.svg?style=default&logo=Python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/TypeScript-3178C6.svg?style=default&logo=TypeScript&logoColor=white" alt="TypeScript">
<img src="https://img.shields.io/badge/React-61DAFB.svg?style=default&logo=React&logoColor=black" alt="React">
<img src="https://img.shields.io/badge/FastAPI-009688.svg?style=default&logo=FastAPI&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Vite-646CFF.svg?style=default&logo=Vite&logoColor=white" alt="Vite">
<img src="https://img.shields.io/badge/SQLAlchemy-D71F00.svg?style=default&logo=SQLAlchemy&logoColor=white" alt="SQLAlchemy">
<img src="https://img.shields.io/badge/JavaScript-F7DF1E.svg?style=default&logo=JavaScript&logoColor=black" alt="JavaScript">
<img src="https://img.shields.io/badge/npm-CB3837.svg?style=default&logo=npm&logoColor=white" alt="npm">
<img src="https://img.shields.io/badge/Docker-2496ED.svg?style=default&logo=Docker&logoColor=white" alt="Docker">
<img src="https://img.shields.io/badge/Pytest-0A9EDC.svg?style=default&logo=Pytest&logoColor=white" alt="Pytest">
<img src="https://img.shields.io/badge/NumPy-013243.svg?style=default&logo=NumPy&logoColor=white" alt="NumPy">
<img src="https://img.shields.io/badge/pandas-150458.svg?style=default&logo=pandas&logoColor=white" alt="pandas">
<img src="https://img.shields.io/badge/ESLint-4B32C3.svg?style=default&logo=ESLint&logoColor=white" alt="ESLint">
<img src="https://img.shields.io/badge/PostCSS-DD3A0A.svg?style=default&logo=PostCSS&logoColor=white" alt="PostCSS">
<img src="https://img.shields.io/badge/Playwright-45ba4b.svg?style=default&logo=Playwright&logoColor=white" alt="Playwright">
<img src="https://img.shields.io/badge/Vitest-6E9F18.svg?style=default&logo=Vitest&logoColor=white" alt="Vitest">
<img src="https://img.shields.io/badge/Zod-3E67B1.svg?style=default&logo=Zod&logoColor=white" alt="Zod">
<img src="https://img.shields.io/badge/.ENV-ECD53F.svg?style=default&logo=dotenv&logoColor=black" alt=".ENV">
<img src="https://img.shields.io/badge/GitHub%20Actions-2088FF.svg?style=default&logo=GitHub-Actions&logoColor=white" alt="GitHub Actions">
<img src="https://img.shields.io/badge/Prettier-F7B93E.svg?style=default&logo=Prettier&logoColor=black" alt="Prettier">
<img src="https://img.shields.io/badge/Black-000000.svg?style=default&logo=Black&logoColor=white" alt="Black">
<img src="https://img.shields.io/badge/Ruff-D7FF64.svg?style=default&logo=Ruff&logoColor=black" alt="Ruff">

[Features](#-key-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [Documentation](#-documentation)

</div>

---

## 🎯 What is This Project?

**TradingView Recreation** is a comprehensive, production-ready market analysis platform that recreates and extends the functionality of professional trading platforms like TradingView and Bloomberg Terminal. Built for serious traders, quantitative researchers, and financial analysts, it provides:

- **Professional-grade charting** with real-time data streaming
- **Advanced technical analysis** with 35+ indicators and 30+ drawing tools
- **Strategy development & backtesting** with deterministic replay
- **Portfolio management** with paper trading capabilities
- **Bloomberg-style dashboards** with 14 configurable analytics tiles
- **Multiple data providers** (Finnhub, Alpaca, Yahoo Finance, Mock data)

### Perfect For:
- 📈 **Active Traders** - Real-time charting and analysis
- 🔬 **Quant Researchers** - Strategy development and backtesting
- 📊 **Financial Analysts** - Market data visualization and screening
- 🎓 **Learning & Education** - Understanding market mechanics
- 🧪 **Testing & Development** - Deterministic replay for testing strategies

---

## ✨ Key Features

### 📊 Advanced Charting Engine

- **TradingView-style Interface** - Professional candlestick charts with multi-pane support
- **35 Technical Indicators** across 5 categories:
  - **Trend**: SMA, EMA, VWAP, Ichimoku Cloud, Supertrend, Parabolic SAR, ADX, Aroon
  - **Momentum**: RSI, MACD, Stochastic, Stochastic RSI, CCI, ROC, Williams %R, TRIX, Momentum
  - **Volatility**: Bollinger Bands, ATR, Keltner Channels, Donchian Channels, BB Width, Historical Volatility
  - **Volume**: OBV, MFI, CMF, ADL, VWMA, Volume Profile, Volume Bars
  - **Profile**: VRVP, Anchored VWAP, VWAP Bands, POC, VAH/VAL
- **30+ Drawing Tools** - Lines, Fibonacci tools, pitchforks, shapes, annotations, and pattern recognition
- **Real-time Updates** - Live bar formation and confirmation via WebSocket
- **Multi-timeframe Support** - 1m, 5m, 15m, 1H, 4H, 1D, 1W views

### 📈 Dashboard Workspace (Bloomberg-style)

**14 Configurable Analytics Tiles:**

1. **MiniChart** - Compact chart widgets for quick overview
2. **Scanner** - Market scanner with top movers, gainers, losers
3. **Heatmap** - Sector performance visualization
4. **Watchlist** - Multi-symbol monitoring with real-time prices
5. **Positions** - Open positions with P&L tracking
6. **Orders** - Orders blotter (pending, filled, cancelled)
7. **Alerts** - Price and indicator alerts
8. **News** - Real-time market news feed
9. **Calendar** - Economic calendar and earnings releases
10. **TickTable** - Tick-by-tick trade flow
11. **OptionsChain** - Options chain with Greeks
12. **GreeksPanel** - Portfolio Greeks aggregation
13. **IVSurface** - Implied volatility surface visualization
14. **PnLAnalytics** - Performance analytics and metrics

### 🔄 Strategy Development & Backtesting

- **In-Browser Strategy Editor** - Monaco Editor with Python syntax highlighting
- **Built-in Strategy Framework** - Extensible strategy system
- **Comprehensive Backtesting** - Historical performance analysis
- **Deterministic Replay** - Test strategies with exact historical data
- **Paper Trading** - Risk-free strategy execution
- **Real-time Execution Logs** - Monitor strategy signals and orders

### 🔌 Multiple Data Providers

- **Finnhub** - Real-time WebSocket streaming + REST API
- **Alpaca** - Professional trading API integration
- **Yahoo Finance** - Historical data backfill
- **Mock Data** - Deterministic CSV-based testing
- **Custom Providers** - Extensible provider system

### 🎮 Multiple Operating Modes

- **LIVE** - Real-time market data streaming
- **REPLAY** - Deterministic historical replay with speed control (0.5x - 10x)
- **BACKTEST** - Historical strategy testing
- **PAPER** - Paper trading mode

### 💼 Portfolio Management

- **Position Tracking** - Real-time P&L (realized + unrealized)
- **Order Management** - Market, limit, stop orders
- **Trade History** - Complete trade log with export to CSV
- **Performance Analytics** - Win rate, profit factor, drawdown analysis
- **Risk Metrics** - Portfolio Greeks, exposure tracking

---

## 🏗️ Architecture

### Technology Stack

**Frontend:**
- **React 19.2** with TypeScript 5.9
- **Vite** - Lightning-fast build tool
- **Lightweight Charts** - High-performance charting library
- **Zustand** - State management
- **Tailwind CSS** - Utility-first styling
- **Playwright** - End-to-end testing

**Backend:**
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM (SQLite/PostgreSQL)
- **WebSockets** - Real-time bidirectional communication
- **Pandas/NumPy** - Data processing
- **Pytest** - Comprehensive testing (275+ tests)

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
│  Port: 5100 (dev) / 4173 (preview)                         │
│  • Chart Workspace (TradingView-style)                      │
│  • Dashboard Workspace (Bloomberg-style)                    │
│  • Real-time WebSocket connections                          │
└─────────────────────────────────────────────────────────────┘
                        ↕ WebSocket/REST
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                        │
│  Port: 8000                                                 │
│  • Data Ingestion Service                                   │
│  • Bar Engine (OHLCV aggregation)                           │
│  • Strategy Engine                                          │
│  • Portfolio Manager                                        │
│  • SQLite/PostgreSQL Database                               │
└─────────────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────────────┐
│              DATA SOURCES                                   │
│  • Finnhub (WebSocket + REST)                              │
│  • Alpaca (REST API)                                        │
│  • Yahoo Finance (Historical)                               │
│  • Mock CSV (Testing)                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Node.js 18+** and npm
- **API Keys** (optional, for live data):
  - Finnhub API key
  - Alpaca API credentials

### Installation

**1. Backend Setup:**

```bash
cd phase1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (optional for live data)
cp keys.env.example keys.env
# Edit keys.env and add your API keys
```

**2. Frontend Setup:**

```bash
cd frontend

# Install dependencies
npm install
```

**3. Start the System:**

**Terminal 1 - Backend:**
```bash
cd phase1
source venv/bin/activate
python -m uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Data Ingestion (optional, for live data):**
```bash
cd phase1
source venv/bin/activate
python -m services.ingestion.main --mode live --symbols AAPL,MSFT,TSLA
```

### Access the Application

- **Frontend**: http://localhost:5100
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws

---

## 📚 Documentation

- **[Complete Usage Guide](USAGE_GUIDE.md)** - Comprehensive user manual
- **[Project Report](PROJECT_REPORT.md)** - Detailed technical documentation
- **[Quick Reference](QUICK_REFERENCE.md)** - Quick command reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + 1` | Chart Workspace |
| `Ctrl/Cmd + 2` | Dashboard Workspace |
| `Ctrl/Cmd + 3` | Replay Mode |
| `Ctrl/Cmd + K` | Command Palette |
| `1/2/3/4/5` | Switch Timeframe (1m/5m/15m/1H/1D) |
| `Space` | Play/Pause Replay |
| `→` | Step Forward (Replay) |
| `←` | Step Backward (Replay) |
| `Ctrl/Cmd + Z` | Undo Drawing |
| `Ctrl/Cmd + Y` | Redo Drawing |

---

## 🧪 Testing

### Backend Tests

```bash
cd phase1
pytest -v
```

**Test Coverage:** 275 tests passing, comprehensive unit, integration, and E2E tests

### Frontend Tests

```bash
cd frontend
npm run test:unit      # Unit tests
npm run test:int       # Integration tests
npm run test:e2e       # End-to-end tests
```

---

## 📊 Project Statistics

- **50,000+ lines of code**
- **35 Technical Indicators**
- **30+ Drawing Tools**
- **14 Dashboard Tiles**
- **5 Data Providers**
- **3 Built-in Strategies**
- **275 Automated Tests**
- **8 Major Service Modules**

---

## 🛠️ Development

### Project Structure

```
Tradingview recreation/
├── frontend/          # React + TypeScript frontend
│   ├── src/
│   │   ├── features/  # Feature modules (chart, dashboard, strategy, etc.)
│   │   ├── core/      # Core engine (ChartEngine, Scales)
│   │   ├── data/      # API clients (REST, WebSocket)
│   │   └── ui/        # Reusable components
│   └── tests/         # Test suites
│
├── phase1/            # FastAPI backend
│   ├── services/      # Service modules
│   │   ├── api/       # REST API endpoints
│   │   ├── ingestion/ # Data ingestion service
│   │   ├── bar_engine/# OHLCV aggregation
│   │   ├── strategy/  # Strategy execution engine
│   │   └── portfolio/ # Portfolio management
│   └── tests/         # Backend tests
│
├── Tradingview/       # Additional trading modules
├── strategies/        # Strategy definitions
└── docs/              # Documentation
```

### Key Technologies

- **Frontend**: React, TypeScript, Vite, Lightweight Charts, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy, WebSockets, Pandas, NumPy
- **Data**: Finnhub, Alpaca, Yahoo Finance
- **Testing**: Pytest, Playwright, Vitest

---

## 📝 License

[Add your license here]

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📧 Contact

[Add your contact information here]

---

<div align="center">

**Built with ❤️ for traders, quants, and financial professionals**

[Back to Top](#tradingview-recreation)

</div>

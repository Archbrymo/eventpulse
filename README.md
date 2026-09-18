## EventPulse Demo

[Railway Deployment]([https://railway.com/project/c53e69a0-76ad-49de-9ff1-245d8bfcca1b/service/cf865d2b-e350-44c1-861b-652d07ca812b?environmentId=3aebe0ef-6b58-493a-a49e-af465f36575d](https://eventpulse-production-d19e.up.railway.app/)


# EVENTPULSE

### Autonomous Event-Driven Trading Terminal

**EventPulse** is a paper-trading agent designed around an event-driven investment workflow:

> **Reality → Fast Candidates → Evidence → Qwen Investment Council → Deterministic Risk → Paper Execution → Audit Trail → Thesis Tracking**

EventPulse is built for the **Bitget AI Base Camp Hackathon S2**, Track: **Agentic Trading → Event-driven Agent**.

The project focuses on turning market events into auditable trading decisions rather than treating an LLM as an unrestricted trading executor.

---

## 1. What EventPulse Does

EventPulse continuously turns a large Reality/Bitget market universe into a small set of evidence-backed candidates.

The autonomous pipeline is:

```text
┌────────────────────┐
│ Reality Universe   │
│ ~1,173 instruments │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ FAST               │
│ Candidate Ranking  │
│ 50 candidates      │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ EVIDENCE           │
│ Research Layer     │
│ 10 finalists       │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ EVENT              │
│ Market/Event Flow  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ QWEN INVESTMENT    │
│ COUNCIL            │
│ 3 decisions        │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ DETERMINISTIC RISK │
│ Policy + sizing    │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ PAPER EXECUTION    │
│ Bitget/Reality     │
│ rToken simulation  │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ AUDIT + THESIS     │
│ Decision history   │
│ Portfolio state    │
└────────────────────┘
```

The important architectural principle is that **Qwen proposes the investment decision, while deterministic Python controls whether that decision is allowed to reach execution**.

---

## 2. Why EventPulse

Traditional dashboards show prices.

EventPulse is designed to answer a different question:

> **When something happens in the market, what should the autonomous system investigate, what does the evidence say, what does the investment council decide, and is the resulting action actually allowed by risk policy?**

The system therefore separates:

* discovery
* evidence
* reasoning
* risk
* execution
* auditability

This makes the trading agent easier to inspect and safer to demonstrate.

---

## 3. Core Architecture

### Layer 1 — Reality / Market Universe

EventPulse discovers the available Reality/Bitget instruments and builds a live universe.

The universe contains approximately **1,173 instruments** in the current demo environment.

The system distinguishes between:

* **underlying ticker** — the real-world asset identifier such as `NVDA`
* **Reality/rToken symbol** — the execution instrument such as `rNVDAUSDT`
* **display ticker** — the compact terminal representation such as `rNVDA`

This separation prevents display formatting from being confused with the actual execution symbol.

---

### Layer 2 — Fast Candidate Ranking

The full universe is too large to send directly into an LLM reasoning stage.

EventPulse therefore performs a deterministic candidate-ranking pass.

Current pipeline target:

```text
~1,173 Reality instruments
          ↓
50 fast candidates
```

Candidate scoring considers market characteristics such as:

* liquidity
* momentum
* directional characteristics
* market quality
* event relevance
* diversification

The result is a smaller research set.

---

### Layer 3 — Evidence Layer

The research layer reduces the candidate set further.

Current target:

```text
50 candidates
      ↓
10 evidence finalists
```

Research records contain market and evidence information used to construct the investment context.

A typical evidence record contains:

* Reality symbol
* underlying asset
* last price
* open/high/low
* volume
* quote volume
* bid/ask
* percentage change
* market quality
* momentum
* directional evidence
* event relevance
* diversification
* composite evidence score

The evidence layer is deliberately separate from the Qwen reasoning layer.

---

## 4. Event-Driven Reasoning

EventPulse is not intended to ask an LLM to blindly scan every instrument.

Instead:

```text
Market / Event
      ↓
Evidence finalists
      ↓
Qwen Investment Council
      ↓
BUY / SELL / HOLD / WAIT
```

The event context is passed to the Qwen council together with the research finalists and portfolio context.

The Qwen decision model produces:

* direction
* confidence
* reasoning
* catalyst
* fundamental thesis
* valuation thesis
* market thesis
* bull case
* bear case
* invalidation condition
* expected horizon
* position reasoning

This gives each decision an inspectable investment thesis instead of a single unexplained BUY/SELL label.

---

## 5. Qwen Investment Council

EventPulse uses the Qwen model configured for the Bitget hackathon endpoint.

Current model configuration:

```text
Model: qwen3.8-max
Endpoint: https://hackathon.bitgetops.com/v1
```

The Qwen layer is implemented through an OpenAI-compatible client.

The council produces structured decisions using the application's Pydantic models.

### Decision directions

```text
BUY
SELL
HOLD
WAIT
```

### Example structured signal

```text
Ticker: QCOM
Direction: BUY
Confidence: 0.65

Reasoning:
[event-specific reasoning]

Catalyst:
[event catalyst]

Fundamental thesis:
[fundamental context]

Valuation thesis:
[valuation context]

Market thesis:
[market context]

Bull case:
[upside scenario]

Bear case:
[downside scenario]

Invalidation:
[condition that breaks the thesis]

Expected horizon:
[time horizon]
```

The dashboard exposes these fields through the Qwen Council interface so that the reasoning can be inspected rather than hidden inside a model response.

---

## 6. Deterministic Risk Layer

A central design decision in EventPulse is that **the LLM does not directly control execution**.

The Qwen council can propose a signal, but Python risk rules independently evaluate whether that signal is executable.

Current risk parameters include:

```text
MIN_CONFIDENCE          = 0.60
MAX_TRADE_PORTFOLIO_PCT = 0.10
MAX_POSITION_PCT        = 0.20
MAX_DAILY_LOSS_PCT      = 0.02
MAX_DRAWDOWN_PCT        = 0.10
```

The risk layer checks factors including:

* direction
* confidence
* portfolio exposure
* position limits
* daily loss constraints
* drawdown constraints
* execution-price validity
* sizing constraints

The conceptual flow is:

```text
Qwen decision
     │
     ▼
Risk policy
     │
 ┌───┴────┐
 │        │
PASS     BLOCK
 │        │
 ▼        ▼
Size     Audit reason
 │
 ▼
Paper execution
```

This provides deterministic control around probabilistic reasoning.

---

## 7. Paper Execution

EventPulse is currently designed for **paper trading only**.

The execution layer uses a `PaperExecutor` and `PaperBroker`.

No live-money execution is required for the demo.

Execution keeps the distinction between the research ticker and Reality execution symbol.

For example:

```text
Research ticker:
NVDA

Reality execution symbol:
rNVDAUSDT
```

The executor maps the research asset to the correct Reality execution instrument before submitting the simulated order.

This separation is important because the user-facing ticker and exchange execution symbol are not necessarily identical.

---

## 8. Audit Trail

Every autonomous cycle is designed to be inspectable.

The database records agent-cycle stages including:

```text
REALITY
FAST
EVIDENCE
QWEN
RISK
EXECUTION
```

The `agent_cycles` table records:

* cycle ID
* timestamp
* stage
* status
* ticker
* decision
* confidence
* detail

Qwen decisions are also persisted with their reasoning and thesis fields.

This means the system can answer:

> What did the agent see?

> What did Qwen decide?

> What confidence did it assign?

> What did deterministic risk do?

> Was an order filled?

> Why was a decision blocked?

---

## 9. Thesis Tracking

EventPulse treats a trading decision as a thesis rather than just an order.

A thesis can include:

* catalyst
* fundamental thesis
* valuation thesis
* market thesis
* bull case
* bear case
* invalidation condition
* expected horizon

This makes it possible to evaluate whether the original reasoning remains valid after the decision.

The dashboard therefore includes a **Thesis** area alongside portfolio and execution information.

---

## 10. Dashboard

The EventPulse dashboard is designed as a production-style autonomous trading terminal.

Visual direction:

* void black background
* graphite panels
* moonlight silver typography
* electric teal for live/active states
* red/green reserved for market movement and PnL
* thin borders
* minimal radius
* dense terminal-style information hierarchy

The main dashboard contains:

### Sidebar

```text
EVENTPULSE

AUTONOMOUS EVENT-DRIVEN TRADING

Overview
Portfolio
Events
Qwen Council
Risk
Execution
Thesis
Agent Search
```

### Top command area

Shows:

* current dashboard context
* last tick
* market status
* paper/live state

### Portfolio metrics

The overview exposes:

* equity
* 24H PnL
* cash
* positions

### Autonomous pipeline

```text
REALITY
   ↓
FAST
   ↓
EVIDENCE
   ↓
QWEN
   ↓
RISK
   ↓
APPROVED
   ↓
FILLED
```

### Market intelligence

Shows evidence-ranked Reality assets and market information.

### Event blotter

Shows the event-driven flow being evaluated by the agent.

### Live evidence

Shows detailed evidence for a selected Reality instrument, including:

* selected ticker
* price
* 24H move
* turnover
* spread
* market information
* thesis access

---

## 11. TradingView Integration

TradingView can be used as a visual market-analysis layer inside the dashboard.

The intended role is:

```text
EventPulse / Bitget / Reality
        │
        ├── execution source of truth
        │
        └── market data context

TradingView
        │
        └── visual chart / financial context
```

TradingView widgets are useful for displaying:

* advanced charts
* symbol information
* financial/fundamental views where available

However, TradingView embedded widgets should be treated as a **visualization layer**, not as the authoritative execution-data source.

The EventPulse trading pipeline should continue to use its Bitget/Reality data and internal research layer for:

* prices
* execution symbols
* risk decisions
* paper fills
* portfolio accounting

This prevents a visualization widget from becoming an accidental execution dependency.

---

## 12. Technology Stack

### Language

```text
Python 3.9+
```

### Dashboard

```text
Streamlit
```

### Data / persistence

```text
SQLite
Pandas
```

### Validation

```text
Pydantic
```

### AI reasoning

```text
Qwen
OpenAI-compatible client
```

### Market / Reality integration

```text
Bitget Reality / rToken universe
```

### Execution

```text
Deterministic Python risk
PaperBroker
PaperExecutor
```

---

## 13. Project Structure

```text
eventpulse/
│
├── app/
│   ├── dashboard_v2.py
│   ├── database.py
│   ├── event_cycle.py
│   ├── qwen_client.py
│   ├── council.py
│   ├── models.py
│   ├── risk.py
│   ├── execution.py
│   ├── bitget_universe.py
│   ├── universe_research.py
│   └── ...
│
├── tests/
│   └── ...
│
├── .venv/
│
├── README.md
│
└── ...
```

---

## 14. Running EventPulse

From the project directory:

```bash
cd /Users/archbrymo/eventpulse/eventpulse
```

Launch the dashboard:

```bash
PYTHONPATH="$PWD" ./.venv/bin/python -m streamlit run app/dashboard_v2.py
```

Streamlit will provide the local dashboard URL.

The project can also be launched using the corresponding Python/Streamlit environment on another machine.

---

## 15. Environment Variables

The Qwen client expects the hackathon API key in:

```text
BITGET_QWEN_API_KEY
```

Example:

```bash
export BITGET_QWEN_API_KEY="YOUR_API_KEY"
```

Do **not** commit API keys, credentials, tokens, or secrets to GitHub.

A local `.env` or shell environment should be used instead.

---

## 16. Testing

Run the test suite from the project root.

Example:

```bash
./.venv/bin/python -m pytest -q
```

Before submission, also validate the dashboard source:

```bash
./.venv/bin/python -m py_compile app/dashboard_v2.py
```

The project has been developed with automated tests covering the core agent/risk/database functionality.

---

## 17. Clean Paper Account

For demonstrations, EventPulse supports resetting the paper account to its initial cash balance with zero positions.

The clean-slate operation is intentionally separate from:

* Qwen decision history
* autonomous agent-cycle audit history

This allows a new trading demonstration without deleting the reasoning/audit record.

---

## 18. Example Autonomous Cycle

A representative cycle can look like:

```text
REALITY
1173 instruments

        ↓

FAST
50 candidates

        ↓

EVIDENCE
10 finalists

        ↓

QWEN
3 structured decisions

        ↓

RISK
3 decisions evaluated

        ↓

APPROVED
0

        ↓

FILLED
0
```

A blocked trade is not considered a failure of the agent.

For example, Qwen may identify a BUY opportunity while deterministic risk blocks the trade because the required Reality execution price is unavailable or another risk condition fails.

That distinction is intentional:

```text
Investment reasoning ≠ execution permission
```

---

## 19. Safety Model

EventPulse is a **paper-trading system**.

The project does not claim to provide financial advice or guarantee trading performance.

The architecture is intentionally designed so that:

1. Qwen generates structured reasoning.
2. Python validates the decision.
3. Risk policy independently determines whether execution is allowed.
4. The current execution layer is simulated.
5. The decision and execution path are recorded for audit.

This makes the system appropriate for an autonomous-agent demonstration without requiring live capital deployment.

---

## 20. Design Principles

### 1. LLM for reasoning, code for control

Qwen handles contextual investment reasoning.

Python handles:

* validation
* risk
* sizing
* execution rules
* persistence

---

### 2. Evidence before reasoning

The system does not send the entire market universe to the LLM.

It progressively reduces:

```text
1173 → 50 → 10 → 3
```

This makes the reasoning stage more focused and auditable.

---

### 3. Every decision should have a thesis

A BUY or SELL without an explanation is not sufficient for an autonomous research system.

EventPulse records the reasoning behind the decision.

---

### 4. Execution must be deterministic

An LLM should not be the final authority on portfolio constraints.

Risk policy remains outside the model.

---

### 5. Auditability matters

The system records the autonomous cycle so that decisions can be inspected after the fact.

---

## 21. Hackathon Positioning

EventPulse is positioned as an **event-driven autonomous trading agent**.

The core differentiator is the complete agent loop:

```text
EVENT
  ↓
DISCOVER
  ↓
FILTER
  ↓
RESEARCH
  ↓
REASON
  ↓
RISK CHECK
  ↓
EXECUTE
  ↓
AUDIT
  ↓
TRACK THESIS
```

Rather than presenting an isolated LLM trading prompt, EventPulse demonstrates how an AI investment council can operate inside a larger deterministic trading system.

---

## 22. Demo Flow

A concise live demo can follow this sequence:

### Step 1 — Open Overview

Show the autonomous terminal and the current portfolio state.

### Step 2 — Show the pipeline

Explain:

```text
Reality → Fast → Evidence → Qwen → Risk → Execution
```

### Step 3 — Show market intelligence

Select an evidence-ranked Reality asset.

### Step 4 — Show event flow

Open the Event Blotter and show the event being evaluated.

### Step 5 — Open Qwen Council

Show:

* decision
* confidence
* reasoning
* catalyst
* fundamental thesis
* valuation thesis
* market thesis
* bull case
* bear case
* invalidation
* expected horizon

### Step 6 — Show Risk

Demonstrate that the model's decision is independently evaluated.

### Step 7 — Show Execution

If the risk layer approves a paper order, show the simulated execution and resulting portfolio state.

If it blocks the order, show the deterministic reason.

### Step 8 — Show Thesis / Audit

Demonstrate that the reasoning and autonomous cycle remain available after the decision.

---

## 23. Current Limitations

EventPulse is a hackathon prototype and has intentionally bounded scope.

Known limitations include:

* paper execution rather than live trading
* external market widgets are primarily visualization/context layers
* market data availability depends on upstream Bitget/Reality services
* event quality depends on available event inputs
* LLM reasoning remains probabilistic
* risk controls reduce execution risk but cannot guarantee profitability
* instrument mappings must remain synchronized with the Reality universe
* a research ticker and execution symbol are intentionally different concepts

These limitations are part of the prototype's transparent architecture rather than hidden assumptions.

---

## 24. Future Development

Potential next stages include:

* richer event-source ingestion
* deeper fundamental-data adapters
* improved Reality/underlying symbol mapping
* stronger event-to-asset attribution
* multi-cycle thesis evaluation
* historical backtesting
* execution-quality analytics
* portfolio-level attribution
* automated invalidation monitoring
* additional Qwen council roles
* stronger observability and monitoring
* controlled live-trading integration only after extensive validation

---

## 25. Repository

GitHub:

**[https://github.com/Archbrymo/eventpulse](https://github.com/Archbrymo/eventpulse)**

---

## 26. Submission Summary

**Project:** EventPulse

**Category:** Agentic Trading → Event-driven Agent

**Core idea:**

> An autonomous event-driven paper-trading terminal that discovers Reality assets, ranks candidates, builds evidence, asks Qwen for structured investment reasoning, applies deterministic risk controls, simulates execution, and preserves an auditable thesis trail.

**Pipeline:**

```text
Reality
  ↓
Fast Candidate Ranking
  ↓
Evidence Research
  ↓
Event Context
  ↓
Qwen Investment Council
  ↓
Deterministic Risk
  ↓
Paper Execution
  ↓
Audit Trail
  ↓
Thesis Tracking
```

**Key architectural principle:**

> **AI reasons. Deterministic code controls. The system records what happened.**

---

## License

Add the license required by the hackathon or repository policy before public release.

---

## Disclaimer

EventPulse is a software prototype for research and paper-trading demonstration. It is not financial advice, does not guarantee investment results, and should not be used as a substitute for professional financial, legal, or investment advice. The current execution architecture is designed for simulated/paper trading.

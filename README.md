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

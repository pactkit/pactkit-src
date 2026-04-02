# P.A.C.T. — Governance Philosophy for AI-Assisted Systems

> **CODE is the Law. Data is the Truth. Prompt is ONLY instruction. AI is ONLY creativity.**

**P.A.C.T.** (Prompt, AI, Code, Truth) is a governance framework — a contract between humans and AI agents. The name is the philosophy: **Pact** means covenant, and these four principles define the boundaries that neither side crosses.

```
P   Prompt   意图层   is ONLY instruction   tells AI how to act
A   AI       创造层   is ONLY creativity    handles expression and understanding
C   Code     法则层   is the Law            sole executor of deterministic operations
T   Truth    现实层   Data is the Truth     factual basis for all judgment
```

- **Humans** issue intent through Prompts and codify rules in Code.
- **AI** operates creatively within the contract, bounded by Truth (data).
- Neither side crosses the boundary. That is the Pact.

This document defines the four foundational principles for any system where AI agents collaborate with deterministic code — preventing the most common failure modes in AI-assisted automation.

---

## Principle 1: CODE is the Law

**Deterministic operations MUST be executed by code, never by AI judgment.**

Any operation with a predictable, repeatable outcome belongs in a script or program. The AI agent has no authority to bypass, approximate, or substitute these operations.

### What this means

- If a script exists for a task, the agent MUST use it — no reimplementing in natural language
- Workflows with defined steps (build, deploy, test, sync) are governed by code, not prompts
- Code acts as a **hard gate**: if the script fails, execution stops. The agent cannot "work around" it

### Why this matters

AI models are probabilistic. They may produce slightly different results each run. For operations that demand consistency — health checks, deployments, data pipelines, CRUD operations — variability is a bug, not a feature. Code eliminates this variability.

### Anti-patterns

| Bad | Good |
|-----|------|
| Agent parses CLI output with regex | Script returns structured JSON |
| Agent calls raw APIs directly | Script wraps API calls with error handling |
| Agent improvises a deploy sequence | Deploy script enforces the exact pipeline |
| Agent manually edits config files | Config management script applies changes |

---

## Principle 2: Data is the Truth

**All analysis, judgment, and decisions MUST be based on actual data, never on memory, inference, or assumption.**

This applies universally — not just to system status, but to every domain where the system operates: analytics, reporting, monitoring, recommendations, and content generation.

### What this means

- **System operations**: Health status comes from metrics, not "it was fine last time"
- **Data analysis**: Reports are built from queried datasets, not recalled impressions
- **Content generation**: Facts in generated content must originate from a data source
- **Recommendations**: Suggestions are grounded in real inputs, not probabilistic guessing

### The rule

```
Has data source? → Read it.
No data source?  → Say "data unavailable." Never fabricate.
```

### Why this matters

AI models have no persistent memory between sessions and no real-time awareness. Any "fact" an AI states from memory is a hallucination risk. By enforcing data primacy, the system guarantees that every assertion can be traced to a source.

### Anti-patterns

| Bad | Good |
|-----|------|
| "Based on what I remember..." | "Based on the latest query result..." |
| Filling missing data with estimates | Marking the field as "data unavailable" |
| Using yesterday's cached data silently | Noting "data from {timestamp}, live fetch failed" |
| Guessing a metric value | Running the script to get the actual value |

---

## Principle 3: Prompt is ONLY Instruction

**Prompts, system instructions, and operational docs define HOW to do things, not WHAT things are.**

All forms of natural language guidance — system prompts, skill definitions, tool guides, runbooks, and configuration docs — are instructions for the agent. They are not sources of truth about current system state.

### What this means

- A skill definition says "run `python3 scripts/collect.py`" → this is an **instruction** (how to act)
- A tool guide says "use `health_check.py` for status" → this is an **instruction** (which tool to use)
- Neither can tell you "the system currently has 33 healthy services" → that is **data** (must be queried)

### The separation

| Layer | Role | Example |
|-------|------|---------|
| Prompt (Instruction) | Defines process and method | "To check health, run script X" |
| Data (Truth) | Provides current state and facts | Script X returns `{"healthy": 30, "unhealthy": 3}` |
| Code (Law) | Executes the operation | Script X queries all services and computes status |

### Why this matters

When agents treat prompts or documentation as factual data, they produce stale or incorrect outputs. Prompts describe procedures; only live data describes reality. Conflating the two is a category error.

### Anti-patterns

| Bad | Good |
|-----|------|
| "According to the README, we have 50 users" | Query the database for current user count |
| Citing a prompt's example output as real data | Running the command to get real output |
| Assuming a doc's described architecture is current | Checking actual deployed state |

---

## Principle 4: AI is ONLY Creativity

**AI's value is in formatting, summarization, language, prioritization, and intent understanding — not in executing deterministic logic.**

The AI layer handles everything that benefits from natural language understanding and creative expression. It does NOT handle anything that has a single correct answer computable by code.

### What AI SHOULD do

- **Format and present**: Turn structured data into readable reports, summaries, briefings
- **Summarize and synthesize**: Condense information, highlight key points, detect themes
- **Language and tone**: Adapt communication style, write with personality, localize content
- **Interpret intent**: Understand ambiguous requests, ask clarifying questions
- **Recommend with context**: Given real data, suggest actions with reasoning

### What AI should NOT do

- Parse structured output (JSON, CSV, XML) — that's CODE
- Perform arithmetic or statistical computation — that's CODE
- Determine system health or status — that's DATA
- Fabricate facts to fill gaps — violates DATA principle
- Improvise operational procedures — that's Prompt + CODE

### Why this matters

When AI attempts deterministic tasks, it introduces unnecessary risk. A script that computes an average will always be correct; an AI that "eyeballs" the same data might round differently, miss entries, or hallucinate values. Constraining AI to creative tasks maximizes its strengths while eliminating its weaknesses.

---

## The Four Principles in Relationship

```
CODE executes  →  DATA verifies  →  Prompt guides  →  AI creates
 (what to do)     (what is true)     (how to do)      (how to say)
```

### Example: Daily Report Generation

1. **CODE**: `daily_report.py` queries APIs, aggregates data, outputs structured JSON
2. **DATA**: The JSON output is the single source of truth for today's numbers
3. **Prompt**: Skill definition tells the agent: "Run the script, read the JSON, format a report"
4. **AI**: Agent writes the report narrative — intro, highlights, tone, formatting

Each layer does exactly one job. No layer reaches into another's domain.

### Example: System Health Check

1. **CODE**: `health_checker.py` pings all services, returns `{healthy: N, unhealthy: [...]}`
2. **DATA**: The returned JSON is the truth — not the agent's memory of yesterday
3. **Prompt**: Tool guide says "use `health_checker.py check` for health status"
4. **AI**: Agent formats the results into a readable status message for the user

---

## Failure Modes This Prevents

| Failure Mode | Which Principle Prevents It |
|---|---|
| Agent guesses a deploy command | CODE is the Law |
| Agent fabricates data in a report | Data is the Truth |
| Agent treats docs as live system state | Prompt is ONLY Instruction |
| Agent manually parses JSON instead of using a script | AI is ONLY Creativity |
| Agent "remembers" yesterday's metrics | Data is the Truth |
| Agent improvises a workflow not in any runbook | CODE is the Law + Prompt is ONLY Instruction |
| Agent adds creative flair to a health check result | AI is ONLY Creativity (scope boundary) |

---

## Adoption Checklist

When applying these principles to a new project:

- [ ] Identify all deterministic operations → wrap them in scripts (CODE)
- [ ] Identify all data sources → ensure agents query them, never guess (DATA)
- [ ] Review all prompts and docs → ensure they contain only procedures, not state (Prompt)
- [ ] Define the AI boundary → list what the agent formats vs. what scripts compute (AI)
- [ ] Add the philosophy quote to the project's governance docs
- [ ] Teach agents the principles and verify with scenario-based testing

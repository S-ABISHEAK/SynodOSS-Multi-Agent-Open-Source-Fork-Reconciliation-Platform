<div align="center">

# ⚖️ SynodOSS

### Autonomous Multi-Agent Open Source Fork Reconciliation Platform

*Negotiating Software Evolution Through Evidence-Backed AI Reasoning*

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Redis](https://img.shields.io/badge/Redis-Queue-red)
![Celery](https://img.shields.io/badge/Celery-Workers-green)
![Groq](https://img.shields.io/badge/Groq-LLM-orange)
![Azure AI Foundry](https://img.shields.io/badge/Azure-AI%20Foundry-0078D4)

</div>

## System Architecture

```mermaid
flowchart TD

A[Upstream Repository]
B[Enterprise Fork]

A --> C[Repository Intelligence Layer]
B --> C

C --> D[Diff Analysis Engine]
D --> E[Conflict Detection]
E --> F[Reconciliation Units]

F --> G[Upstream Advocate]
F --> H[Enterprise Defender]

G --> I[Architect Reviewer]
H --> I

I --> J[Verification Judge]

J --> K{Verification Passed?}

K -->|No| I
K -->|Yes| L[Patch Generator]

L --> M[ADR Generator]
L --> N[Pull Request Generator]

M --> O[Evaluation Dashboard]
N --> O
```
   
## Multi-Agent Debate Workflow

```mermaid
sequenceDiagram

participant U as Upstream Advocate
participant E as Enterprise Defender
participant A as Architect Reviewer
participant V as Verification Judge

U->>A: Preserve Upstream Evolution
E->>A: Preserve Enterprise Customizations

A->>V: Reconciliation Proposal

V->>A: Verification Failed

A->>V: Revised Proposal

V->>A: Verification Passed

A->>A: Generate Consensus
A->>A: Generate Patch
A->>A: Generate ADR
A->>A: Generate PR
```


## 🚀 Overview

SynodOSS is an autonomous multi-agent system designed to solve one of the most expensive problems in enterprise software engineering:

**Open Source Fork Reconciliation.**

Organizations frequently fork open-source projects to introduce:
- Security fixes
- Proprietary integrations
- Compliance modifications
- Performance optimizations

Over time these forks diverge significantly from upstream repositories, making manual reconciliation expensive and error-prone.

SynodOSS introduces an AI-powered Engineering Council capable of:

- Detecting architectural drift
- Analyzing conflicting code evolution
- Debating reconciliation strategies
- Verifying proposed resolutions
- Generating Git-ready patches
- Producing Architecture Decision Records (ADRs)
- Creating Pull Request artifacts


## 🎯 Problem Statement

Traditional tools such as:

- Git Merge
- Git Rebase
- Dependabot
- Code Refactoring Assistants

operate at the file or function level.

They lack understanding of:

- Architectural intent
- Business constraints
- Enterprise customizations
- Long-term maintainability

As a result, organizations often spend weeks or months reconciling heavily diverged forks.

SynodOSS addresses this problem through structured multi-agent reasoning and verification-driven reconciliation.

## ⚙️ Technology Stack

| Layer | Technology |
|---------|------------|
| Frontend | Next.js 15 |
| UI | Tailwind CSS + shadcn/ui |
| Backend | FastAPI |
| Queue | Celery |
| Broker | Redis |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Git Analysis | GitPython |
| LLM Provider | Groq |
| Models | Llama 3.3 70B |
| Verification | AST + Ruff |
| Deployment | Docker |
| Evaluation | Azure AI Foundry |

## 🏛️ Agent Council

### 🟦 Upstream Advocate

Represents the public repository.

Responsibilities:
- Security improvements
- API modernization
- Technical debt reduction
- Upstream compatibility

---

### 🟨 Enterprise Defender

Represents enterprise-specific modifications.

Responsibilities:
- Preserve proprietary logic
- Protect business workflows
- Maintain compliance requirements
- Preserve integrations

---

### 🟪 Architect Reviewer

Neutral decision-maker.

Responsibilities:
- Analyze both viewpoints
- Resolve architectural conflicts
- Design reconciliation strategies
- Generate implementation plans

---

### 🟥 Verification Judge

Independent validation authority.

Responsibilities:
- Validate evidence
- Detect hallucinated claims
- Verify structural correctness
- Calculate trust scores

## 📂 Project Structure

```text
SynodOSS
│
├── backend
│   ├── src
│   │   ├── agents
│   │   │   ├── base_agent.py
│   │   │   ├── upstream_advocate.py
│   │   │   ├── enterprise_defender.py
│   │   │   ├── architect_reviewer.py
│   │   │   └── verification_judge.py
│   │   │
│   │   ├── api
│   │   │   └── routes.py
│   │   │
│   │   ├── core
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── logger.py
│   │   │   └── llm_provider.py
│   │   │
│   │   ├── orchestration
│   │   │   ├── agent_manager.py
│   │   │   ├── debate_manager.py
│   │   │   └── consensus_manager.py
│   │   │
│   │   ├── services
│   │   │   ├── repository_service.py
│   │   │   ├── diff_analysis_service.py
│   │   │   ├── conflict_detection_service.py
│   │   │   ├── verification_service.py
│   │   │   ├── reconciliation_engine.py
│   │   │   ├── patch_generator.py
│   │   │   ├── adr_generator.py
│   │   │   └── pr_generator.py
│   │   │
│   │   ├── workers
│   │   │   ├── celery_app.py
│   │   │   └── tasks.py
│   │   │
│   │   └── models
│   │
│   └── tests
│
├── frontend
│   ├── app
│   ├── components
│   ├── services
│   └── types
│
├── docker
├── docs
└── README.md
```

---

# 🛠️ Installation

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL
- Redis
- Docker & Docker Compose
- Groq API Key

---

## Clone Repository

```bash
git clone https://github.com/your-org/synodoss.git

cd synodoss
```

---

## Backend Setup

```bash
cd backend

uv sync
```

Create:

```env
GROQ_API_KEY=your_key_here

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/synodoss

REDIS_URL=redis://localhost:6379/0
```

---

## Frontend Setup

```bash
cd frontend

npm install
```

---

# 🚀 Running SynodOSS

SynodOSS uses **3 terminals**.

---

## Terminal 1 — FastAPI Backend

```bash
cd backend

uv run uvicorn main:app --reload
```

Runs:

- REST APIs
- Repository Analysis
- Agent Orchestration
- Verification Services

---

## Terminal 2 — Celery Worker

```bash
cd backend

uv run celery -A src.workers.tasks worker --loglevel=info -P threads
```

Runs:

- Repository Cloning
- Diff Analysis
- Background Scans
- Long-running Reconciliation Jobs

---

## Terminal 3 — Frontend

```bash
cd frontend

npm install

npm run dev
```

Runs:

- Dashboard
- Debate Workspace
- Evaluation Dashboard
- Hero Demo Screen

---

# 🔄 End-to-End Workflow

```mermaid
flowchart LR

A[Repository Pair]
--> B[Repository Scan]

B --> C[Diff Analysis]

C --> D[Conflict Detection]

D --> E[Reconciliation Units]

E --> F[Agent Debate]

F --> G[Architect Proposal]

G --> H[Verification Layer]

H --> I{Passed?}

I -->|No| F

I -->|Yes| J[Patch Generator]

J --> K[ADR Generator]

J --> L[PR Generator]

K --> M[Evaluation Dashboard]

L --> M
```

---

# ⚖️ Debate Lifecycle

```mermaid
stateDiagram-v2

[*] --> IndependentAnalysis

IndependentAnalysis --> CrossExamination

CrossExamination --> ArchitectReview

ArchitectReview --> Verification

Verification --> Consensus: Pass

Verification --> ArchitectReview: Fail

Consensus --> [*]
```

---

# 🔍 Verification Pipeline

SynodOSS never trusts LLM output directly.

Every proposal passes through:

### 1. Evidence Validation

Checks:

- Commit references
- Diff references
- Reconciliation Units
- Agent claims

---

### 2. Structural Validation

Checks:

```python
ast.parse(...)
```

Validates:

- Syntax correctness
- Structural correctness

---

### 3. Ruff Validation

Checks:

- Undefined variables
- Import issues
- Style violations
- Structural errors

---

### 4. Patch Applicability

```bash
git apply --check patch.diff
```

Ensures:

- Diff is valid
- Patch can be applied
- No malformed hunks

---

# 🧠 Consensus Formula

Consensus confidence is calculated mathematically.

```text
Confidence

=
0.30 × Evidence Strength
+
0.25 × Evidence Coverage
+
0.20 × Argument Consistency
+
0.25 × Verification Score
```

All values are dynamically computed.

No hardcoded confidence values exist anywhere in the system.

---

# 🛡️ Trust Score

Trust is generated independently from confidence.

```text
Trust

=
0.35 × Verification Success
+
0.25 × Evidence Coverage
+
0.20 × Consensus Strength
+
0.20 × Structural Integrity
```

Purpose:

- Prevent hallucinated decisions
- Penalize unsupported reasoning
- Reward verifiable outcomes

---

# 📑 Architecture Decision Records (ADR)

Every reconciliation generates:

```text
Problem

Context

Agent Positions

Tradeoffs

Decision

Evidence

Verification Results

Future Risks
```

This creates a complete audit trail for every architectural decision.

---

# 🔧 Generated Patch Example

```diff
--- upstream/api.py

+++ reconciled/api.py

-def login(username, password):
+def login(username, password, token=None):

+    print("Logging in...")

     return True
```

Generated patches:

- Are deterministic
- Are Git-compatible
- Pass verification
- Never auto-merge

---

# 📬 Pull Request Generation

Every successful reconciliation generates:

### Pull Request Title

```text
Reconcile Authentication API Divergence
```

### Pull Request Summary

```text
Preserved enterprise logging functionality
while adopting upstream authentication
interface improvements.
```

### Included Artifacts

- Debate Transcript
- ADR
- Verification Report
- Patch File
- Trust Score

---

# 📊 Evaluation Dashboard

Microsoft Foundry Evaluation Metrics:

| Metric | Formula |
|----------|----------|
| Consensus Stability | Successful Consensus / Total Debates |
| Evidence Coverage | Supported Claims / Total Claims |
| Verification Success Rate | Verified Reconciliations / Total Reconciliations |
| Conflict Resolution Success | Resolved Conflicts / Total Conflicts |
| Average Trust Score | Mean Trust Across Reconciliations |

---

# 🎬 Demo Flow

```mermaid
sequenceDiagram

participant User
participant Council
participant Architect
participant Judge
participant Patch

User->>Council: Start Reconciliation

Council->>Council: Debate Conflict

Council->>Architect: Submit Positions

Architect->>Judge: Proposed Resolution

Judge->>Architect: Verification Failed

Architect->>Judge: Revised Proposal

Judge->>Patch: Verification Passed

Patch->>User: Patch Generated

Patch->>User: ADR Generated

Patch->>User: PR Generated
```

---

# 🌟 Why SynodOSS?

Unlike traditional tools:

| Tool | Understands Architecture | Multi-Agent Reasoning | Verification Layer | Patch Generation |
|--------|--------|--------|--------|--------|
| Git Merge | ❌ | ❌ | ❌ | ✅ |
| Git Rebase | ❌ | ❌ | ❌ | ✅ |
| Dependabot | ❌ | ❌ | ❌ | ❌ |
| GitHub Copilot | ⚠️ Partial | ❌ | ❌ | ⚠️ |
| SynodOSS | ✅ | ✅ | ✅ | ✅ |

---

# 🚧 Future Roadmap

### Near Term

- Multi-language support
- Java reconciliation engine
- TypeScript reconciliation engine
- GitHub App integration

### Long Term

- Autonomous PR creation
- Multi-repository reconciliation
- CI/CD integration
- Enterprise policy engine
- Azure AI Foundry Agent Service migration

---

# 👥 Team

Built for the Microsoft Agents Hackathon.

**SynodOSS**
*Negotiating Software Evolution Through Evidence-Backed AI Reasoning.*

---

# 📄 License

MIT License

Copyright (c) 2026 SynodOSS

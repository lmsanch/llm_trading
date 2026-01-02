# LLM Trading - Architecture Diagrams

## System Architecture

```mermaid
graph TB
    subgraph "Weekly Pipeline (Wed 08:00 ET)"
        R1[Research Stage]
        R2[Market Data]
        R3[Macro Analysis]
        R4[Sentiment Analysis]

        PM1[PM Stage - GPT-5.2]
        PM2[PM Stage - Gemini 3 Pro]
        PM3[PM Stage - Grok 4.1]
        PM4[PM Stage - Claude Sonnet 4.5]
        PM5[PM Stage - DeepSeek V3]

        PR1[Peer Review Stage]
        PR2[Anonymized Evaluation]
        PR3[Rubric Scoring]

        CH1[Chairman Stage]
        CH2[Claude Opus 4.5]
        CH3[Council Synthesis]

        R1 --> R2
        R1 --> R3
        R1 --> R4
        R2 --> PM1
        R2 --> PM2
        R2 --> PM3
        R2 --> PM4
        R3 --> PM1
        R3 --> PM2
        R3 --> PM3
        R3 --> PM4
        R4 --> PM1
        R4 --> PM2
        R4 --> PM3
        R4 --> PM4

        PM1 --> PR1
        PM2 --> PR1
        PM3 --> PR1
        PM4 --> PR1
        PM5 --> PR1
        PR1 --> PR2
        PR2 --> PR3

        PR3 --> CH1
        CH1 --> CH2
        CH2 --> CH3
    end

    subgraph "Trade Approval Workflow"
        GUI[Trade Approval GUI]
        PENDING[Pending Trades]
        APPROVED[Approved Trades]
        REJECTED[Rejected Trades]

        CH3 --> PENDING
        PENDING --> GUI
        GUI --> APPROVED
        GUI --> REJECTED
    end

    subgraph "Paper Trading Execution"
        ALPACA[Alpaca Paper Trading API]

        ACCT1[CHATGPT Account<br/>PA3IUYCYRWGK]
        ACCT2[GEMINI Account<br/>PA3M2HMSLN00]
        ACCT3[CLAUDE Account<br/>PA38PAHFRFYC]
        ACCT4[GROQ Account<br/>PA33MEQA4WT7]
        ACCT5[DEEPSEEK Account<br/>PA3KKW3TN54V]
        ACCT6[COUNCIL Account<br/>PA3MQLPXBSO1]

        APPROVED --> ALPACA
        ALPACA --> ACCT1
        ALPACA --> ACCT2
        ALPACA --> ACCT3
        ALPACA --> ACCT4
        ALPACA --> ACCT5
        ALPACA --> ACCT6
    end

    subgraph "Data Persistence"
        PG[(PostgreSQL)]
        EVENTS[Event Log]
        TRADES[Trade Events]
        POSITIONS[Positions]
    end

    R1 --> PG
    PM1 --> PG
    PM2 --> PG
    PM3 --> PG
    PM4 --> PG
    PR1 --> PG
    CH1 --> PG
    PENDING --> PG
    APPROVED --> PG
    REJECTED --> PG
    ALPACA --> PG

    PG --> EVENTS
    PG --> TRADES
    PG --> POSITIONS
```

## Daily Checkpoint Flow

```mermaid
graph LR
    subgraph "Checkpoint Engine (09:00, 12:00, 14:00, 15:50 ET)"
        CHECK[Checkpoint Trigger]
        SNAPSHOT[Market Snapshot]
        POS[Current Positions]
        PL[P/L Calculation]
        EVAL[Conviction Evaluation]
        ACTION[Action Decision]
    end

    subgraph "Actions"
        STAY[STAY<br/>Maintain Position]
        EXIT[EXIT<br/>Close Position]
        FLIP[FLIP<br/>Reverse Direction]
        REDUCE[REDUCE<br/>Decrease Size]
    end

    subgraph "Approval Required"
        GUI2[Trade Approval GUI]
    end

    subgraph "Execution"
        ALPACA2[Alpaca Paper Trading]
    end

    CHECK --> SNAPSHOT
    SNAPSHOT --> POS
    POS --> PL
    PL --> EVAL
    EVAL --> ACTION

    ACTION --> STAY
    ACTION --> EXIT
    ACTION --> FLIP
    ACTION --> REDUCE

    STAY --> ALPACA2
    EXIT --> GUI2
    FLIP --> GUI2
    REDUCE --> GUI2

    GUI2 --> ALPACA2
```

## Trade Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Generated: PM/Chairman creates trade
    Generated --> Pending: Save to database
    Pending --> Approved: User approves via GUI
    Pending --> Rejected: User rejects via GUI
    Approved --> Executed: Order placed via Alpaca
    Approved --> Failed: Order placement error
    Rejected --> [*]
    Executed --> Open: Order filled
    Open --> Closed: Exit/Flip action
    Open --> Updated: Checkpoint conviction update
    Failed --> [*]
    Closed --> [*]
    Updated --> Open
```

## Database Schema

```mermaid
erDiagram
    EVENTS ||--o{ RESEARCH_PACKS : contains
    EVENTS ||--o{ PM_PITCHES : contains
    EVENTS ||--o{ PEER_REVIEWS : contains
    EVENTS ||--o{ CHAIRMAN_DECISIONS : contains
    EVENTS ||--o{ CHECKPOINT_UPDATES : contains
    EVENTS ||--o{ ORDERS : contains
    EVENTS ||--o{ POSITIONS : contains

    PM_PITCHES ||--o{ PEER_REVIEWS : reviews
    CHAIRMAN_DECISIONS ||--o{ ORDERS : generates
    ORDERS ||--o{ POSITIONS : updates

    TRADES {
        string id PK
        string week_id
        string account_id
        string model
        string instrument
        string direction
        float conviction
        string status
        timestamp approval_timestamp
        timestamp execution_timestamp
        string rejection_reason
    }

    EVENTS {
        string id PK
        string event_type
        string week_id
        string account_id
        timestamp timestamp
        json payload
        string parent_event_id
    }

    RESEARCH_PACKS {
        string id PK
        string week_id
        string provider
        json research_data
        boolean success
    }

    PM_PITCHES {
        string id PK
        string week_id
        string model
        json pitch_data
        string validation_status
    }

    PEER_REVIEWS {
        string id PK
        string week_id
        string reviewer_model
        string pitch_id
        json review_data
    }

    CHAIRMAN_DECISIONS {
        string id PK
        string week_id
        string model
        json decision_data
    }

    CHECKPOINT_UPDATES {
        string id PK
        string week_id
        string account_id
        string checkpoint_time
        json checkpoint_data
    }

    ORDERS {
        string id PK
        string week_id
        string account_id
        string order_id
        string symbol
        string side
        float qty
        string order_type
        string status
    }

    POSITIONS {
        string id PK
        string week_id
        string account_id
        string symbol
        float qty
        float avg_entry_price
        float current_price
        float unrealized_pl
    }
```

## Component Interaction

```mermaid
sequenceDiagram
    participant CLI as CLI
    participant Pipeline as Weekly Pipeline
    participant Requesty as Requesty API
    participant Alpaca as Alpaca API
    participant DB as PostgreSQL
    participant GUI as Web GUI
    participant User as User

    CLI->>Pipeline: run_weekly()
    Pipeline->>Requesty: Query research (Gemini + Perplexity)
    Requesty-->>Pipeline: Research packs
    Pipeline->>DB: Log research events

    Pipeline->>Requesty: Query 4 PM models in parallel
    Requesty-->>Pipeline: PM pitches
    Pipeline->>DB: Log PM pitch events

    Pipeline->>Requesty: Peer review queries
    Requesty-->>Pipeline: Peer reviews
    Pipeline->>DB: Log peer review events

    Pipeline->>Requesty: Chairman synthesis
    Requesty-->>Pipeline: Council decision
    Pipeline->>DB: Log chairman decision

    Pipeline->>DB: Save trades as PENDING
    Pipeline-->>CLI: Weekly pipeline complete

    GUI->>DB: Poll for pending trades
    DB-->>GUI: 5 pending trades
    GUI->>User: Display trade approval dashboard

    User->>GUI: Approve trade
    GUI->>DB: Update trade status to APPROVED
    GUI->>Alpaca: Place order for account
    Alpaca-->>GUI: Order confirmation
    GUI->>DB: Update trade status to EXECUTED
    GUI->>DB: Log order event
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        CLI[CLI Tools]
        SCRIPTS[Scripts]
    end

    subgraph "Backend Services"
        FASTAPI[FastAPI Server]
        PIPELINE[Pipeline Engine]
        REQUESTY_CLIENT[Requesty Client]
        ALPACA_CLIENT[Alpaca Client]
        DB_CLIENT[PostgreSQL Client]
    end

    subgraph "Frontend"
        VITE[Vite Dev Server]
        REACT[React App]
    end

    subgraph "External Services"
        REQUESTY[Requesty API]
        ALPACA[Alpaca Paper Trading]
        POSTGRES[(PostgreSQL)]
    end

    CLI --> FASTAPI
    SCRIPTS --> DB_CLIENT
    FASTAPI --> PIPELINE
    PIPELINE --> REQUESTY_CLIENT
    PIPELINE --> ALPACA_CLIENT
    PIPELINE --> DB_CLIENT
    FASTAPI --> DB_CLIENT

    REQUESTY_CLIENT --> REQUESTY
    ALPACA_CLIENT --> ALPACA
    DB_CLIENT --> POSTGRES

    VITE --> REACT
    REACT --> FASTAPI
```

## Data Flow Summary

### Research Flow
1. **Market Data** → Alpaca API → Research Stage
2. **Macro Analysis** → Requesty API → Research Pack A/B
3. **Sentiment** → Requesty API → Research Pack A/B
4. **Research Packs** → PostgreSQL → Event Log

### PM Flow
1. **Research Packs** → PM Stage (4 models)
2. **PM Models** → Requesty API (parallel queries)
3. **PM Pitches** → PostgreSQL → Event Log

### Peer Review Flow
1. **PM Pitches** → Peer Review Stage
2. **Anonymization** → Remove model identities
3. **Peer Review Queries** → Requesty API (4 models)
4. **Peer Reviews** → PostgreSQL → Event Log

### Chairman Flow
1. **PM Pitches + Peer Reviews** → Chairman Stage
2. **Chairman Model** → Requesty API (Claude Sonnet 4.5)
3. **Council Decision** → PostgreSQL → Event Log

### Approval Flow
1. **Council Decision** → Save as PENDING
2. **GUI Poll** → Fetch pending trades
3. **User Review** → Approve/Reject
4. **Approved Trades** → Alpaca API → Execute
5. **Rejected Trades** → Log rejection reason

### Checkpoint Flow
1. **Scheduled Time** → Checkpoint Trigger
2. **Market Snapshot** → Alpaca API
3. **Position + P/L** → Alpaca API
4. **Conviction Eval** → Requesty API
5. **Action Decision** → Approve if not STAY
6. **Execute** → Alpaca API

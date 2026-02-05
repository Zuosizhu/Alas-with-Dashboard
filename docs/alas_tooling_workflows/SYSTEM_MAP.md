# ALAS System Map

This diagram visualizes the relationships between the high-level **Tool Domains** and the **Execution Loops**. It highlights the difference between *Scheduled Tasks* (Blue lines) and *Reactive Interrupts* (Red dashed lines).

```mermaid
graph TD
    %% === THE BRAIN ===
    Start((Start)) --> Scheduler{Global Scheduler<br/>"What's Next?"}

    %% === DOMAIN: COMBAT ===
    subgraph Combat_Domain [⚔️ Combat & Campaign]
        direction TB
        Sortie[Sortie Entry]
        PreCheck{Pre-Sortie<br/>Check}
        Battle[Battle Loop]
        PostBattle[Result / Rewards]
        
        Sortie --> PreCheck
        PreCheck -->|Space OK| Battle
        Battle --> PostBattle
        PostBattle -->|Continue| PreCheck
    end

    %% === DOMAIN: MANAGEMENT ===
    subgraph Management_Domain [🏠 Base Management]
        direction TB
        Meowfficer[Meowfficer<br/>Buy / Train / Feed]
        Dorm[Dorm<br/>Food / Affinity]
        
        %% The Interrupt Handler
        Retirement[<B>Retirement & Enhance</B><br/>Reactive Handler]
    end

    %% === DOMAIN: LOGISTICS ===
    subgraph Logistics_Domain [📦 Logistics]
        Commissions[Commissions<br/>Collect & Dispatch]
        Research[Research Academy]
        Shops[Shops<br/>General / Guild / Medal]
    end

    %% === DOMAIN: OPSI ===
    subgraph OpSi_Domain [⚓ Operation Siren]
        OpSi_Explore[Exploration & Puzzle]
        OpSi_Boss[Ash/Meta Showdown]
    end

    %% === SCHEDULED FLOWS (Normal Operation) ===
    Scheduler -->|Task: Campaign| Sortie
    Scheduler -->|Task: Meowfficer| Meowfficer
    Scheduler -->|Task: Commission| Commissions
    Scheduler -->|Task: Research| Research
    Scheduler -->|Task: OpSi| OpSi_Explore

    %% === REACTIVE INTERRUPTS (The "Triggers") ===
    %% These happen when the game blocks progress
    PreCheck -.->|Buffer Low| Retirement
    PostBattle -.->|Dock Full| Retirement
    Commissions -.->|Reward: Ship| Retirement
    
    %% === RETURNS ===
    Retirement -->|Space Cleared| Scheduler
    Meowfficer -->|Done| Scheduler
    Commissions -->|Done| Scheduler
    Research -->|Done| Scheduler
    OpSi_Explore -->|Done| Scheduler
    PostBattle -->|Stop Condition Met| Scheduler

    %% === STYLING ===
    classDef scheduler fill:#2d1f4e,stroke:#c084fc,color:#fff,stroke-width:2px;
    classDef combat fill:#e0f2f1,stroke:#00695c,stroke-width:2px,color:#004d40;
    classDef manage fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c;
    classDef logistic fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#e65100;
    classDef opsi fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef interrupt fill:#ffebee,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 5,color:#b71c1c;

    class Scheduler scheduler;
    class Sortie,PreCheck,Battle,PostBattle combat;
    class Meowfficer,Dorm manage;
    class Commissions,Research,Shops logistic;
    class OpSi_Explore,OpSi_Boss opsi;
    class Retirement interrupt;
```

## How to Read This Map

1.  **Scheduled Tasks (Solid Lines):**
    The **Scheduler** picks a task (e.g., "Run Campaign 12-4") and pushes the bot into the **Combat Domain**. The bot stays in that loop until a "Stop Condition" (like "Run Count: 10") is met.

2.  **Reactive Interrupts (Dashed Red Lines):**
    Notice that **Retirement** is not directly connected to the Scheduler. It is an **Interrupt**.
    *   If you are in **Combat** and the Dock fills up -> You get diverted to **Retirement**.
    *   If you are collecting **Commissions** and get a ship -> You get diverted to **Retirement**.
    *   Once Retirement finishes clearing space, it dumps you back to the Scheduler to restart/resume your task.

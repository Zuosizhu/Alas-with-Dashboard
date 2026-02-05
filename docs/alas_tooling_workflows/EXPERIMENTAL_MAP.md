# Experimental ALAS System Map

This diagram uses the experimental `block-beta` syntax to visualize the ALAS system architecture as a nested block layout. It groups tools into their respective domains physically rather than just logically.

```mermaid
block-beta
    columns 3
    
    %% === THE BRAIN ===
    block:SchedulerGroup
        columns 1
        Scheduler(("Scheduler<br/>(The Brain)"))
        space
        DecisionLogic["Next Task?"]
    end

    %% === DOMAIN 1: MANAGEMENT ===
    block:Management
        columns 1
        TitleMgmt["Base Management"]
        block:MgmtTools
            columns 2
            Meow["Meowfficer"]
            Dorm["Dormitory"]
        end
        %% Reactive Interrupt (Red)
        InterruptRetire(("Retirement<br/>Interrupt"))
        style InterruptRetire fill:#b71c1c,stroke:#fff,color:#fff
    end

    %% === DOMAIN 2: COMBAT ===
    block:Combat
        columns 1
        TitleCombat["Combat & Campaign"]
        block:CombatFlow
            columns 1
            PreCheck["Pre-Check"]
            Sortie["Sortie"]
            Battle["Battle Loop"]
        end
    end

    %% === DOMAIN 3: LOGISTICS ===
    block:Logistics
        columns 1
        TitleLogistics["Logistics"]
        block:LogTools
            columns 3
            Comms["Commissions"]
            Rsrch["Research"]
            Shops["Shops"]
        end
    end

    %% === DOMAIN 4: OPSI ===
    block:OpSi
        columns 1
        TitleOpSi["Operation Siren"]
        block:OpSiTools
            columns 2
            Explore["Exploration"]
            Boss["Meta Boss"]
        end
    end

    %% === CONNECTIONS ===
    %% Scheduler drives the domains
    SchedulerGroup --> Management
    SchedulerGroup --> Combat
    SchedulerGroup --> Logistics
    SchedulerGroup --> OpSi

    %% Reactive Interrupt Connections
    Combat --> InterruptRetire
    Logistics --> InterruptRetire
    InterruptRetire --> SchedulerGroup

    %% === STYLING ===
    style SchedulerGroup fill:#2d1f4e,stroke:#c084fc,color:#fff
    style Management fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c
    style Combat fill:#e0f2f1,stroke:#00695c,color:#004d40
    style Logistics fill:#fff3e0,stroke:#e65100,color:#e65100
    style OpSi fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
```

## Explanation
*   **Columns:** The layout uses a 3-column grid.
*   **Nested Blocks:** Each domain (Combat, Management, etc.) is its own "block" containing sub-tools.
*   **The Red Node:** The `Retirement Interrupt` is visually placed inside Management but connected to Combat and Logistics to show how it "pulls" control away from them.

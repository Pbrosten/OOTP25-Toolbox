# OOTP Analytics App — Recommended GM Decision-Support Functionality

## Product Goal

Turn OOTP 25 monthly and yearly dump data into a **GM decision-support system**, not merely a statistics database.

The core principle is:

> **Translate player and team data into actionable roster, transaction, development, and organizational decisions.**

The three implementation tiers below move from essential day-to-day GM tools to deeper organizational intelligence and eventually scenario-based strategic planning.

---

# Tier 1 — Immediate GM Value

These components should form the core of the application. They answer the most frequent and consequential questions a GM faces.

## 1. GM Command Center
status: stagged
### Core concept
A single landing dashboard that tells the GM **what needs attention right now**.

### Key functionality
- Current team performance and standings
- Projected final record and playoff outlook
- Team WAR and projected WAR
- Biggest overperformers and underperformers
- Injuries and expected roster impact
- Upcoming contract and arbitration decisions
- Prospect promotion opportunities
- Roster weaknesses and surpluses
- Automated alerts and recommended actions

### Primary output
A prioritized **Action Queue**, such as:
- Bullpen projected to be a major weakness
- Position producing below league average
- Prospect blocked by organizational depth
- Excess MLB-caliber pitching available for trade
- Player approaching a contract decision

---

## 2. Roster Optimization & Organizational Depth
status: stagged
### Core concept
Answer:

> **Who should actually be on the roster, and where does everyone fit?**

### Key functionality
- MLB roster analysis
- AAA/AA/A organizational depth
- Projected WAR by player and position
- Position eligibility and defensive versatility
- Role suitability
- Platoon splits
- Options and service-time considerations
- Prospect status and readiness
- Best projected lineup and roster combinations
- Position-by-position depth chart
- Organizational surpluses and weaknesses

### Primary output
A clear picture of:
- Best current roster
- Best defensive roster
- Best offensive roster
- Best platoon configuration
- Positions with insufficient depth
- Positions with excess talent
- Projected roster in 1, 3, and 5 years based on organizational depth

---

## 3. Trade Target Finder
status: stagged
### Core concept
Find players who satisfy a GM's needs instead of requiring the GM to manually search the league.

### Key functionality
Filter and rank players by:
- Position
- Age
- Projected WAR
- Years of control
- Salary
- Contract status
- Injury risk
- Prospect status
- Role
- Team competitiveness
- Organizational fit

### Primary output
A ranked list of realistic acquisition targets.

Example decision:

> Find 25–30-year-old shortstops projected for 3+ WAR with multiple years of control and affordable contracts.

---

## 4. Trade Analyzer
status: draft
### Core concept
Evaluate a proposed trade based on **organizational impact**, not just player ratings.

### Key functionality
Compare:
- Current vs. post-trade projected WAR
- Multi-year WAR
- Payroll impact
- Prospect capital
- Positional depth
- Age distribution
- Competitive-window fit
- Playoff probability
- Long-term organizational value

### Primary output
A trade verdict showing whether the transaction improves the organization and **why**.

---

## 5. Contract & Arbitration Analyzer
status: stagged
### Core concept
Answer:

> **Should we pay this player, and how much is he worth?**

### Key functionality
- Projected player value
- Projected future WAR
- Salary projections
- Arbitration estimates
- Free-agent market comparisons
- Contract scenario modeling
- Surplus value
- Aging risk
- Injury risk
- Probability of contract becoming inefficient

### Primary output
Recommendations such as:
- Extend
- Keep short-term
- Let walk
- Non-tender
- Trade before free agency

Include estimated fair-value ranges and projected surplus.

Root system in similar system to Fangraph's Surplus Value.

---

## 6. Prospect Pipeline
status: stagged
### Core concept
Turn the farm system into a **development pipeline** rather than a static prospect ranking.

### Key functionality
- Prospect performance
- Age relative to league
- Current level
- Projection
- Development trajectory
- ETA
- Position
- Future role
- Risk
- Organizational depth at position
- Promotion readiness

### Primary output
Identify:
- Prospects ready for promotion
- Prospects falling behind
- Organizational bottlenecks
- Excess prospect types
- Positions lacking future talent
- Players whose value makes them viable trade assets

Root system in similar system to Fangraph's Surplus Value.
---

## 7. Player Development Monitor
status: stagged
### Core concept
Detect meaningful changes in player ability and performance over time.

### Key functionality
Track monthly/yearly changes in:
- Offensive ratings
- Pitching ratings
- Defensive ratings
- Speed
- Stuff, movement, control
- Actual performance
- Projected performance
- Age-relative development
- Historical trends

### Primary output
Development and decline alerts, such as:

> Contact ability has improved substantially while offensive production has followed.

or:

> Veteran pitcher's stuff and velocity are declining faster than expected.

---

# Tier 2 — Deep Organizational Intelligence

These components expand the app from roster management into **market analysis, matchup strategy, risk management, and long-term planning**.

## 8. Competitive Window Dashboard
status: draft
### Core concept
Determine **when the organization is most likely to contend**.

### Key functionality
Project several seasons of:
- Team WAR
- Payroll
- Player aging
- Contract commitments
- Prospect arrivals
- Roster turnover
- Positional strengths and weaknesses

### Primary output
Identify:
- Current competitive window
- Expected peak seasons
- Expected decline
- Whether the team should buy, sell, or rebuild
- Whether to prioritize MLB talent or future assets

---

## 9. Free Agent Market Dashboard
status: draft
### Core concept
Evaluate the free-agent market according to **projected value and organizational need**.

### Key functionality
- Projected WAR
- Age
- Position
- Role
- Contract expectations
- Injury risk
- Team fit
- Cost per projected WAR
- Surplus value

### Primary output
Identify:
- Best bargains
- Poor-value contracts
- Best fits for current needs
- Positions where free agency is more efficient than trades or internal options

---

## 10. League-Wide Player Valuation

### Core concept
Create a consistent valuation framework for every player in the league.
status: draft
### Key functionality
Rank/filter players by:
- Current WAR
- Projected WAR
- Surplus value
- Salary
- Age
- Contract control
- Injury risk
- Development trajectory
- Trade value

### Primary output
Identify:
- Undervalued players
- Overpaid players
- Potential trade targets
- Players whose market value appears misaligned with projected production

---

## 11. Platoon & Matchup Explorer
status: draft
### Core concept
Optimize player usage based on **specific matchup conditions**.

### Key functionality
Analyze:
- Performance vs. RHP/LHP
- Platoon advantages
- Batter/pitcher matchups where data supports them
- Park context
- Opponent
- Projected lineup performance

### Primary output
Answer questions such as:

> Who should start at DH against this left-handed starter?

or:

> What is our optimal lineup against right-handed pitching?

---

## 12. Defensive Optimization
status: stagged
### Core concept
Find the best defensive configuration rather than simply assigning players to their nominal positions.

### Key functionality
Evaluate:
- Defensive ratings
- Historical defensive performance
- Position flexibility
- Range
- Arm
- Error rates
- Defensive WAR
- Position-switch scenarios

### Primary output
Compare:
- Best offensive lineup
- Best defensive lineup
- Best overall projected lineup
- Impact of moving players between positions

---

## 13. Aging & Decline Dashboard
status: draft
### Core concept
Identify players whose value is likely to change because of aging.

### Key functionality
Track:
- Historical performance
- Current performance
- Projected performance
- Age curves
- Skill-specific decline
- Defensive decline
- Speed decline
- Pitcher velocity/stuff decline

### Primary output
Flag:
- Players declining faster than expected
- Veterans at increased contract risk
- Players whose current value may be temporary
- Assets that should potentially be traded before decline accelerates

---

## 14. “What Are We Bad At?” Dashboard
status: draft
### Core concept
Automatically identify the team's biggest weaknesses relative to the league.

### Key functionality
Compare team performance and projections across:
- Hitting
- Power
- Contact
- Plate discipline
- Baserunning
- Defense
- Starting pitching
- Bullpen
- Platoon performance
- Positional production

### Primary output
A ranked list of the team's largest opportunities for improvement, followed by possible solutions.

---

# Tier 3 — Advanced GM Strategy

These components transform the app into a **strategic planning and decision simulation platform**.

## 15. Scenario Simulator
status: draft
### Core concept
Let the GM test hypothetical decisions before making them.

### Key functionality
Simulate:
- Trades
- Free-agent signings
- Extensions
- Releases
- Promotions
- Demotions
- Position changes
- Prospect decisions
- Payroll changes

Recalculate:
- Team WAR
- Depth
- Payroll
- Playoff outlook
- Prospect capital
- Competitive window
- Positional balance

### Primary output
Side-by-side scenarios such as:

> Sign veteran starter vs. promote prospect vs. trade for starter.

Show short-, medium-, and long-term consequences.

---

## 16. Automated Action Queue
status: draft
### Core concept
Convert the application's analysis into a prioritized list of **recommended GM actions**.

### Key functionality
Continuously evaluate:
- Roster construction
- Player performance
- Development
- Contracts
- Injuries
- Depth
- Competitive window
- Market opportunities

Prioritize recommendations by:
- Urgency
- Expected impact
- Confidence
- Cost
- Time sensitivity

### Primary output
A living task list:

1. Address bullpen depth — High impact
2. Evaluate extension for Player X — Contract deadline approaching
3. Promote Prospect Y — Performance/readiness threshold reached
4. Explore trades for excess SP — Organizational surplus

---

# Cross-Cutting Design Principles

## 1. From Stats to Decisions

Every major metric should ultimately support a decision.

Instead of:

> Projected WAR: 3.7

Prefer:

> **KEEP** — Projected value exceeds expected salary by $9M.

The raw statistic should remain available, but the application should do the analytical translation for the GM.

---

## 2. Historical + Current + Projected

The application's monthly and yearly dumps create a major advantage: **time-series analysis**.

Most major pages should distinguish between:

- Historical performance
- Current performance
- Recent trend
- Projection
- Long-term projection

This allows the application to identify trajectory, not just current state.

---

## 3. Player Value Is Contextual

A player's value should depend on more than his projected performance.

Where possible, incorporate:

- Age
- Salary
- Contract control
- Position
- Team needs
- Organizational depth
- Competitive window
- Injury risk
- Development trajectory

The same player can be a great asset for one team and a poor fit for another.

---

## 4. Every Recommendation Should Explain “Why”

Recommendations should be transparent.

For example:

> **TRADE TARGET — High Priority**
>
> Why:
> - Your current CF production ranks 25th
> - No MLB-ready CF prospect is available
> - Player X projects for +2.1 WAR over your current option
> - His contract is below projected market value
> - Your organization has surplus pitching to offer

This makes the system useful without requiring the GM to blindly trust an opaque score.

---

## 5. Recommendations Should Link Together

The biggest opportunity is to make the application feel like one interconnected system.

For example:

**“Catcher is a weakness.”**

↓

**Roster Depth** identifies the problem.

↓

**Prospect Pipeline** confirms there is no internal solution.

↓

**Trade Target Finder** finds candidates.

↓

**Trade Partner Finder** identifies compatible teams.

↓

**Trade Analyzer** evaluates the proposed deal.

↓

**Scenario Simulator** shows the impact over five years.

↓

**GM Command Center** records the resulting action.

That workflow is the real product.

---

# Suggested Overall Information Architecture

```text
GM COMMAND CENTER
│
├── ROSTER
│   ├── Roster Optimization
│   ├── Organizational Depth
│   ├── Defensive Optimization
│   └── Matchup Explorer
│
├── PLAYERS
│   ├── Player Info
│   ├── Player Development
│   ├── Aging & Decline
│   └── Injury & Availability
│
├── TRANSACTIONS
│   ├── Trade Target Finder
│   ├── Trade Analyzer
│   ├── Trade Partner Finder
│   ├── Free Agent Market
│   ├── Contract Analyzer
│   └── Arbitration
│
├── FARM SYSTEM
│   └── Prospect Pipeline
│
├── TEAM
│   ├── Team Identity
│   ├── What Are We Bad At?
│   ├── Pitching Staff
│   └── Bullpen
│
├── STRATEGY
│   ├── Competitive Window
│   ├── Scenario Simulator
│   └── GM Questions
│
└── ALERTS
    └── Automated Action Queue
```

# Core Product Vision

The application should evolve through three stages:

### Tier 1 — Know the State of the Organization

> **What is happening with my team and players?**

### Tier 2 — Understand the Opportunities

> **Where can I improve, and what options do I have?**

### Tier 3 — Test and Execute Strategy

> **What happens if I make this decision?**

The ultimate goal is a system where a GM can go from **data → diagnosis → options → decision → projected consequences** without having to manually stitch together information from multiple pages.

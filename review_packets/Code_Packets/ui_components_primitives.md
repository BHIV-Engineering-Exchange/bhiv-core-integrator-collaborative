# Code Packet: UI Components & High-Density Design Primitives

## Context & Standard
- **Standard**: SETU OS Architecture v6.0 / High-Density UI Cognition
- **Target Platform**: Desktop, Tablet, Mobile (Responsive Parity)
- **Reference Paradigms**: Bloomberg Terminal, Palantir Gotham, NASA Mission Control

## High-Density Operations Console Primitives

### 1. Unified Grid Layout System (Responsive Parity)
The operational console utilizes a strict responsive CSS Grid architecture guaranteeing parity across device viewports:
- **Desktop (1920x1080 / 1440x900)**: 4-column layout (`Sidebar Navigation`, `Review & Intake Terminal`, `GC Shakti Policy Matrix`, `Gov-OS Chain & Saarthi Telemetry`).
- **Tablet (1024x768 / 768x1024)**: 2-column balanced telemetry grid with collapsible drawers.
- **Mobile (375x812 / 414x896)**: 1-column high-density vertical stack preserving all decision buttons, audit trails, and cryptographic verification badges without truncation.

### 2. Design Tokens & Color Palette
- **Background**: `#0b0f19` (Deep Mission Obsidian)
- **Surface Panels**: `#111827` (Card Surface) with `#1f2937` borders
- **Accent - Active/Verified**: `#10b981` (Emerald Proof)
- **Accent - Conditional/Warning**: `#f59e0b` (Amber Review)
- **Accent - Rejected/Alert**: `#ef4444` (Crimson Breach)
- **Accent - Brand/Core**: `#3b82f6` (SETU Sapphire)
- **Typography**: Monospace `JetBrains Mono, SF Mono, Menlo` for digests, trace IDs, and numeric metrics; Inter/System Sans for managerial operational labels.

### 3. Apache ECharts Cognition Widgets
- **State Transition Timeline**: Visualizes deterministic states (`INTAKE` → `POLICY_VALIDATION` → `EVALUATION_PENDING` → `AWAITING_REVIEW` → `GOVERNED_APPROVAL` → `NIYANTRAN_DISPATCH` → `COMMITTED`).
- **Candidate Growth & Velocity Gauge**: Displays candidate maturity (`Junior Associate`), learning velocity tracking, and gate achievement metrics.
- **50-Run Hash Stability Visualizer**: Displays consecutive run variance (0.00% variance, 100% stable SHA-256 state hashes).

# Handoff: Research Tab Redesign

## Objective
Redesign the **Research Tab** in the trading dashboard to function as a persistent "Research Dashboard". 
- **Previous Behavior**: Landed on a "New Research" / Configuration page. History was hidden in a calendar widget.
- **Desired Behavior**: Land on a Dashboard view with Tabs ("Perplexity Sonar", "Gemini 2.0 Flash").
    - Each tab should show the **latest generated report** for that provider.
    - User can click "Run New Analysis" to go to the Configuration/Execution flow.

## Current State
I have completely refactored `frontend/src/components/dashboard/tabs/ResearchTab.jsx` to implement this new flow.

### file: `frontend/src/components/dashboard/tabs/ResearchTab.jsx`
- **State Machine**:
    - `dashboard` (New default): Shows tabs and latest reports.
    - `configuring`: The old "reviewing" state. Allows editing prompt and selecting models.
    - `running`: The execution progress view.
    - `complete`: Shows immediate results (and transitions back to dashboard).
    - `error`: Error state.
- **Data Fetching**:
    - On mount (`useEffect`), it calls `/api/research/history?days=90`.
    - It iterates through the history to find the most recent entry for 'perplexity' and 'gemini'.
    - It parses the Postgres array string (e.g., `"{uuid1,uuid2}"`) to get the latest ID.
    - It calls `/api/research/report/{id}` to fetch the full content.
- **UI**:
    - Implemented a Tab switcher for Perplexity/Gemini.
    - Reused `ResearchPackCard` to display the loaded report.

## Recent Changes
- **Refactor**: Replaced the entire component logic to support the new `dashboard` state and data fetching.
- **Build**: Successfully ran `npm run build` with the new changes.

## Potential Issues / Next Steps for Implementation
1.  **Data Mapping**:
    - The `/api/research/report/{id}` endpoint returns a flat object with `structured_json` and `natural_language`. 
    - The `ResearchPackCard` component expects specific fields (e.g., `macro_regime`, `top_narratives`) at the top level.
    - I added logic to spread `structured_json` into the card data: `...(currentReport.structured_json || {})`. **Verify this mapping is correct** and that `ResearchPackCard` renders correctly with this data structure.
2.  **Postgres Array Parsing**:
    - The history endpoint returns report IDs as a string like `"{abc-123, def-456}"` (Postgres array string format).
    - The current parsing logic is `ids = pEntry.report_ids.replace(/[{}]/g, '').split(',')`. **Verify this is robust** for the actual API response format.
3.  **UI Polish**:
    - Check the empty state (if no reports exist).
    - Verify the "Run New Analysis" button correctly transitions to the `configuring` state (prompt editor).

## Environment
- **Frontend Source**: `/research/llm_trading/frontend/src/components/dashboard/tabs/ResearchTab.jsx`
- **Backend API**: Running on port 8000.
- **Frontend Preview**: Running on port 4173 (via `npm run preview`) but user accesses via Tailscale IP.

## Verification
- Use the **Browser Tool** to check:
    1.  The tabs appear on load.
    2.  Content loads (or "No Research Found" empty state).
    3.  "Run New Analysis" opens the editor.

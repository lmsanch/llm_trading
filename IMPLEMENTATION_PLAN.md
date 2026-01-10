# Comprehensive Implementation Plan
## Sprint Cleanup + Sprints 3, 4, 5 Completion

**Document Version:** 1.0
**Last Updated:** 2026-01-09
**Estimated Total Duration:** 2-3 weeks

---

## Executive Summary

This plan consolidates the remaining work into 5 phases:
1. **Phase 1**: Remove DuckDuckGo, enable Tavily + Brave
2. **Phase 2**: Fix all pre-existing type errors
3. **Phase 3**: Complete Sprint 3 (Execution Modes & Temperature Controls)
4. **Phase 4**: Complete Sprint 4 (Live Progress Tracking)
5. **Phase 5**: Complete Sprint 5 (Council Sizing & Polish)

---

## Phase 1: Remove DuckDuckGo, Enable Tavily + Brave

### Objective
Clean up search infrastructure to use only paid providers with reliable APIs.

### Tasks

#### 1.1 Remove DuckDuckGo Provider
**Files to modify:**
- `backend/search/duckduckgo.py` → DELETE
- `backend/search/__init__.py` → Remove DuckDuckGo import
- `backend/search/manager.py` → Remove DuckDuckGo references
- `config/search.yaml` → Remove duckduckgo section
- `test_search_providers.py` → Remove DuckDuckGo tests

**Actions:**
```bash
# Delete the file
rm backend/search/duckduckgo.py

# Update manager.py imports
# Remove: from .duckduckgo import DuckDuckGoProvider
# Remove: DuckDuckGoProvider from _create_provider() switch

# Update __init__.py
# Remove: from .duckduckgo import DuckDuckGoProvider
```

#### 1.2 Configure Tavily Provider
**Files to modify:**
- `config/search.yaml`
- `.env`

**Configuration:**
```yaml
# config/search.yaml
default_provider: "tavily"
enable_jina_reader: true
max_results: 10

providers:
  tavily:
    api_key_env: "TAVILY_API_KEY"
    enabled: true
    timeout: 30.0

  brave:
    api_key_env: "BRAVE_API_KEY"
    enabled: true
    timeout: 30.0
```

**Environment variables:**
```bash
# User needs to add to .env
TAVILY_API_KEY=tvly-...  # You have this
BRAVE_API_KEY=BSA...         # You will provide this
```

#### 1.3 Update Frontend Search Settings UI
**File to modify:** `frontend/src/components/dashboard/tabs/SettingsTab.jsx`

**Changes:**
- Remove "DuckDuckGo" from provider dropdown
- Keep only "Tavily" and "Brave" options
- Update provider status indicators

#### 1.4 Update Documentation
**Files to modify:**
- `README.md` (search section)
- `CLAUDE.md` (remove DuckDuckGo references)

---

## Phase 2: Fix Pre-existing Type Errors

### Objective
Resolve all type errors flagged by LSP diagnostics to enable strict type checking.

### Current Type Error Inventory

Based on diagnostics output, here are all files with type errors:

#### backend/main.py (25+ errors)
| Line | Error | Severity | Fix Approach |
|------|--------|-----------|--------------|
| 15-16 | Import ".alpaca_integration" could not be resolved | HIGH | Remove or fix import |
| 301, 1375, 1388, 1745 | Object of type "None" is subscriptable | MEDIUM | Add None checks before subscript |
| 397 | Object of type "None" cannot be used as iterable | MEDIUM | Add None check |
| 432 | Cannot access attribute "path"/"methods" on BaseRoute | LOW | Route inspection, may need cast |
| 547, 129, 271 | Literal string not assignable to ContextKey | HIGH | Use proper ContextKey constants |
| 787, 800, 1028, 1030, 1429 | Cannot assign to PipelineState attributes | HIGH | Update PipelineState type hints |
| 1427 | str | None not assignable to str | MEDIUM | Add optional typing |
| 1096, 1334 | Expression of type "None" not assignable to str | MEDIUM | Add None check |

#### backend/requesty_client.py (5 errors)
| Line | Error | Severity | Fix Approach |
|------|--------|-----------|--------------|
| 120 | Dict[str, str] not assignable to ChatCompletionMessageParam | HIGH | Update message typing |
| 130-132 | "prompt_tokens" not attribute of None | MEDIUM | Add None check before access |

#### backend/pipeline/stages/pm_pitch.py (2 errors)
| Line | Error | Severity | Fix Approach |
|------|--------|-----------|--------------|
| 129, 271 | Literal string not assignable to ContextKey | HIGH | Import and use proper ContextKey |

#### backend/pipeline/stages/research.py
| Line | Error | Severity | Fix Approach |
|------|--------|-----------|--------------|
| 787 | No parameter named "selected_models" | HIGH | Remove from ResearchStage init call |

#### Fix Strategy

**Priority Order:**
1. **Critical (blockers):** ContextKey literals, PipelineState assignments
2. **High:** Import issues, None subscript access
3. **Medium:** Optional typing, route inspection
4. **Low:** Edge cases

**Approach:**
- Fix each file independently
- Run `lsp_diagnostics` after each fix
- Run tests to ensure no runtime breakage
- Commit fixes in logical batches

**Estimated Time:** 2-3 days

---

## Phase 3: Complete Sprint 3 - Execution Modes & Temperature Controls

### Objective
Implement per-stage temperature control and execution mode configuration.

### Background (from PRD.md)
The system needs to support different execution modes:
- **chat_only**: Sentiment → Research → PM Pitches → Execution
- **ranking**: + Peer Review
- **full**: + Peer Review + Chairman

Each stage should have configurable temperature.

### Tasks

#### 3.1 Update config/models.yaml
**Add temperature configuration:**
```yaml
execution:
  mode: "full"  # chat_only, ranking, full
  council_size: 5  # Number of PM models

temperatures:
  market_sentiment: 0.3
  research: 0.2
  pm_pitch: 0.7
  peer_review: 0.1
  chairman: 0.4
```

#### 3.2 Create TemperatureManager Utility
**New file:** `backend/pipeline/utils/temperature_manager.py`

```python
"""Utility for managing stage-specific temperatures."""

from typing import Dict
from ..config.loader import load_config

class TemperatureManager:
    """Manages temperature settings for each pipeline stage."""

    def __init__(self, config_path: str = "config/models.yaml"):
        config = load_config(config_path)
        self.temperatures = config.get("temperatures", {})

    def get_temperature(self, stage_name: str) -> float:
        """Get temperature for a specific stage."""
        return self.temperatures.get(stage_name, 0.7)  # Default 0.7

    def get_all_temperatures(self) -> Dict[str, float]:
        """Get all configured temperatures."""
        return self.temperatures
```

#### 3.3 Update Stages to Use Temperatures
**Files to modify:**
- `backend/pipeline/stages/market_sentiment.py`
- `backend/pipeline/stages/research.py`
- `backend/pipeline/stages/pm_pitch.py`
- `backend/pipeline/stages/peer_review.py`
- `backend/pipeline/stages/chairman.py`

**Changes per stage:**
1. Accept `temperature` parameter in `__init__`
2. Pass temperature to LLM query calls
3. Default to TemperatureManager if not provided

**Example:**
```python
class PMPitchStage(Stage):
    def __init__(self, temperature: float | None = None):
        super().__init__()
        self.temperature = temperature or TemperatureManager().get_temperature("pm_pitch")

    async def execute(self, context):
        # ... existing code ...
        response = await query_model(
            model=model_id,
            messages=messages,
            temperature=self.temperature  # Use configured temperature
        )
```

#### 3.4 Update WeeklyPipeline to Pass Execution Mode
**File to modify:** `backend/pipeline/weekly_pipeline.py`

**Changes:**
1. Read execution_mode from config/models.yaml
2. Configure stage sequence based on mode
3. Pass temperatures to each stage

**Implementation:**
```python
def __init__(self, search_provider: str | None = None, execution_mode: str | None = None):
    from .config.loader import load_config
    config = load_config("config/models.yaml")

    self.execution_mode = execution_mode or config.get("execution", {}).get("mode", "full")

    temp_manager = TemperatureManager()
    stages = [
        MarketSentimentStage(
            search_provider=search_provider,
            temperature=temp_manager.get_temperature("market_sentiment")
        ),
        ResearchStage(
            temperature=temp_manager.get_temperature("research")
        ),
        PMPitchStage(
            temperature=temp_manager.get_temperature("pm_pitch")
        ),
    ]

    if self.execution_mode in ["ranking", "full"]:
        stages.append(
            PeerReviewStage(temperature=temp_manager.get_temperature("peer_review"))
        )

    if self.execution_mode == "full":
        stages.append(
            ChairmanStage(temperature=temp_manager.get_temperature("chairman"))
        )

    stages.append(ExecutionStage())
    self.pipeline = Pipeline(stages)
```

#### 3.5 Add CLI Flags for Execution Mode
**File to modify:** `cli.py`

**Add command:**
```bash
python cli.py run_weekly --mode ranking --search-provider tavily
```

**Implementation:**
```python
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["chat_only", "ranking", "full"],
                        default="full", help="Execution mode")
    parser.add_argument("--search-provider", default="tavily",
                        help="Search provider to use")
    # ... existing arguments ...

    args = parser.parse_args()

    # Use args in pipeline execution
    pipeline = WeeklyTradingPipeline(
        search_provider=args.search_provider,
        execution_mode=args.mode
    )
```

#### 3.6 Update GUI for Execution Mode Selection
**File to modify:** `frontend/src/components/dashboard/tabs/SettingsTab.jsx`

**Add to "Pipeline Configuration" card:**
```jsx
<div className="space-y-2">
  <label className="text-sm font-medium">Execution Mode</label>
  <select className="p-2 border rounded-md">
    <option value="chat_only">Chat Only</option>
    <option value="ranking">Chat + Ranking</option>
    <option value="full">Full (All Stages)</option>
  </select>
</div>
```

#### 3.7 Add Temperature Settings UI
**New section in SettingsTab.jsx:**
```jsx
<Card>
  <CardHeader>
    <CardTitle>Stage Temperatures</CardTitle>
    <CardDescription>Control creativity per pipeline stage</CardDescription>
  </CardHeader>
  <CardContent>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <TemperatureSlider stage="Market Sentiment" configKey="market_sentiment" />
      <TemperatureSlider stage="Research" configKey="research" />
      <TemperatureSlider stage="PM Pitch" configKey="pm_pitch" />
      <TemperatureSlider stage="Peer Review" configKey="peer_review" />
      <TemperatureSlider stage="Chairman" configKey="chairman" />
    </div>
  </CardContent>
</Card>
```

#### 3.8 API Endpoints for Temperature Settings
**Add to backend/main.py:**
```python
@app.get("/api/temperatures")
async def get_temperatures():
    """Get current temperature settings."""
    config = load_config("config/models.yaml")
    return config.get("temperatures", {})

@app.post("/api/temperatures")
async def update_temperatures(data: Dict[str, float]):
    """Update temperature settings."""
    import yaml
    from pathlib import Path

    config_path = Path("config/models.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    config["temperatures"] = data

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    return {"status": "success", "temperatures": config["temperatures"]}
```

**Estimated Time:** 3-4 days

---

## Phase 4: Complete Sprint 4 - Live Progress Tracking

### Objective
Implement real-time progress updates via WebSocket for long-running pipeline stages.

### Tasks

#### 4.1 Create Progress Event System
**New file:** `backend/pipeline/utils/progress.py`

```python
"""Progress tracking for pipeline stages."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
import json
from datetime import datetime

class Stage(Enum):
    MARKET_SENTIMENT = "market_sentiment"
    RESEARCH = "research"
    PM_PITCH = "pm_pitch"
    PEER_REVIEW = "peer_review"
    CHAIRMAN = "chairman"
    EXECUTION = "execution"

class ProgressStatus(Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProgressEvent:
    """Progress event for a pipeline stage."""
    stage: Stage
    status: ProgressStatus
    progress: int  # 0-100
    message: str
    timestamp: str
    data: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "timestamp": self.timestamp,
            "data": self.data,
            "error": self.error,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ProgressManager:
    """Manager for tracking and emitting progress events."""

    def __init__(self):
        self.callbacks = []

    def emit(self, event: ProgressEvent):
        """Emit progress event to all registered callbacks."""
        for callback in self.callbacks:
            callback(event)

    def on_progress(self, callback):
        """Register a progress callback."""
        self.callbacks.append(callback)

# Global progress manager
progress_manager = ProgressManager()


def update_progress(
    stage: Stage,
    status: ProgressStatus,
    progress: int,
    message: str,
    data: dict = None,
    error: str = None,
):
    """Helper function to emit progress updates."""
    event = ProgressEvent(
        stage=stage,
        status=status,
        progress=progress,
        message=message,
        timestamp=datetime.utcnow().isoformat(),
        data=data,
        error=error,
    )
    progress_manager.emit(event)
```

#### 4.2 Add Progress Emitting to Stages
**Files to modify:**
- All stage files in `backend/pipeline/stages/`

**Pattern for each stage:**
```python
from ..utils.progress import update_progress, Stage, ProgressStatus

class SomeStage(Stage):
    async def execute(self, context):
        update_progress(Stage.SOME_STAGE, ProgressStatus.STARTED, 0, "Starting stage...")

        try:
            # Step 1
            update_progress(Stage.SOME_STAGE, ProgressStatus.IN_PROGRESS, 30, "Fetching data...")

            # ... work ...

            # Step 2
            update_progress(Stage.SOME_STAGE, ProgressStatus.IN_PROGRESS, 60, "Processing...")

            # ... work ...

            # Complete
            update_progress(Stage.SOME_STAGE, ProgressStatus.COMPLETED, 100, "Complete")

            return context

        except Exception as e:
            update_progress(Stage.SOME_STAGE, ProgressStatus.FAILED, 0, f"Failed: {str(e)}", error=str(e))
            raise
```

#### 4.3 WebSocket Endpoint
**Add to backend/main.py:**
```python
from fastapi import WebSocket
import json

@app.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()

    # Register callback to send progress events
    async def send_progress(event):
        await websocket.send_json(event.to_dict())

    from ..pipeline.utils.progress import progress_manager
    progress_manager.on_progress(send_progress)

    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except Exception as e:
        print(f"WebSocket disconnected: {e}")
    finally:
        # Clean up
        progress_manager.callbacks.remove(send_progress)
        await websocket.close()
```

#### 4.4 Frontend WebSocket Client
**New file:** `frontend/src/hooks/useWebSocketProgress.js`

```javascript
import { useEffect, useState, useCallback } from 'react';
import { io } from 'socket.io-client';

export function useWebSocketProgress() {
  const [progress, setProgress] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket
    socketRef.current = new WebSocket(`ws://${window.location.host}/ws/progress`);

    socketRef.current.onopen = () => {
      setIsConnected(true);
      console.log('Progress WebSocket connected');
    };

    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(prev => ({
        ...prev,
        [data.stage]: data,
      }));
    };

    socketRef.current.onclose = () => {
      setIsConnected(false);
      console.log('Progress WebSocket disconnected');
    };

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  return { progress, isConnected };
}
```

#### 4.5 Progress UI Component
**New file:** `frontend/src/components/dashboard/ui/ProgressTracker.jsx`

```jsx
import React from 'react';
import { useWebSocketProgress } from '../../hooks/useWebSocketProgress';
import { Card, CardContent, CardHeader, CardTitle } from './Card';

export default function ProgressTracker() {
  const { progress, isConnected } = useWebSocketProgress();

  const stages = [
    { key: 'market_sentiment', label: 'Market Sentiment' },
    { key: 'research', label: 'Research' },
    { key: 'pm_pitch', label: 'PM Pitches' },
    { key: 'peer_review', label: 'Peer Review' },
    { key: 'chairman', label: 'Chairman' },
    { key: 'execution', label: 'Execution' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Progress</CardTitle>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {stages.map(stage => {
            const stageProgress = progress[stage.key];
            return (
              <div key={stage.key} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{stage.label}</span>
                  <span className="text-muted-foreground">
                    {stageProgress?.progress || 0}%
                  </span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all"
                    style={{ width: `${stageProgress?.progress || 0}%` }}
                  />
                </div>
                {stageProgress?.message && (
                  <p className="text-xs text-muted-foreground">
                    {stageProgress.message}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
```

#### 4.6 Integrate ProgressTracker into Dashboard
**File to modify:** `frontend/src/components/dashboard/layout/DashboardLayout.jsx`

**Add ProgressTracker sidebar or modal.**

**Estimated Time:** 4-5 days

---

## Phase 5: Complete Sprint 5 - Council Sizing & Polish

### Objective
Add council size configuration, testing, and documentation.

### Tasks

#### 5.1 Implement Council Size Configuration
**Update config/models.yaml:**
```yaml
execution:
  mode: "full"
  council_size: 5  # Number of PM models to use
```

**Update WeeklyPipeline:**
```python
def __init__(self, search_provider=None, execution_mode=None, council_size=None):
    config = load_config("config/models.yaml")
    council_size = council_size or config.get("execution", {}).get("council_size", 5)

    # Only load first N PM models based on council_size
    from .requesty_client import REQUESTY_MODELS
    target_models = list(REQUESTY_MODELS.keys())[:council_size]

    # Use target_models in PM_PitchStage
```

#### 5.2 Update PM Pitch Stage for Dynamic Council Size
**File:** `backend/pipeline/stages/pm_pitch.py`

**Changes:**
```python
class PMPitchStage(Stage):
    def __init__(self, target_models: List[str] = None, council_size: int = None):
        super().__init__()
        from ...requesty_client import REQUESTY_MODELS

        if council_size:
            target_models = list(REQUESTY_MODELS.keys())[:council_size]

        self.target_models = target_models or list(REQUESTY_MODELS.keys())
```

#### 5.3 Add Council Size UI
**Add to SettingsTab.jsx:**
```jsx
<div className="space-y-2">
  <label className="text-sm font-medium">Council Size</label>
  <select className="p-2 border rounded-md">
    <option value="3">3 Models (Fast)</option>
    <option value="5">5 Models (Balanced)</option>
    <option value="7">7 Models (Comprehensive)</option>
  </select>
</div>
```

#### 5.4 Add Tests
**New tests:**
- `tests/test_temperature_manager.py`
- `tests/test_progress.py`
- `tests/test_council_sizing.py`
- `tests/test_search_providers.py` (update for Tavily/Brave only)

#### 5.5 Update Documentation
**Files to update:**
- `README.md` - Add sections on:
  - Execution modes
  - Temperature configuration
  - Progress tracking
  - Council sizing
  - Search providers (Tavily, Brave)
- `CLAUDE.md` - Update technical notes
- Add `docs/ARCHITECTURE.md` with detailed pipeline flow
- Add `docs/CONFIGURATION.md` with all config options

#### 5.6 Polish
- Add error boundaries to frontend
- Improve loading states
- Add toast notifications for progress updates
- Optimize WebSocket reconnection logic
- Add dark mode support (if not present)
- Add accessibility improvements (ARIA labels, keyboard navigation)

**Estimated Time:** 3-4 days

---

## Dependencies & Prerequisites

### User Actions Required
1. **Provide Brave API key** - Add to `.env` as `BRAVE_API_KEY`
2. **Review execution mode selection** - Confirm which modes you want in production
3. **Test temperature settings** - Adjust default temperatures based on desired behavior

### External Services
- Tavily API (already have key)
- Brave Search API (will provide key)
- WebSocket-capable server (FastAPI supports this)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|-------|-----------|---------|-----------|
| DuckDuckGo removal breaks existing flows | Low | Medium | Test all affected end-to-end flows |
| Type fixes introduce runtime bugs | Medium | High | Comprehensive testing after each fix |
| Temperature controls affect output quality | Medium | Medium | Allow easy reversion via config |
| WebSocket connection issues | Low | Low | Add fallback to polling if needed |
| Council size changes break peer review logic | Low | Medium | Review peer review anonymization logic |

---

## Success Criteria

### Phase 1: DuckDuckGo Removal
- [ ] DuckDuckGo provider fully removed
- [ ] Tavily and Brave configured
- [ ] All search functionality works with Tavily/Brave
- [ ] Frontend UI updated
- [ ] Documentation updated

### Phase 2: Type Error Fixes
- [ ] Zero LSP errors in `backend/main.py`
- [ ] Zero LSP errors in `backend/requesty_client.py`
- [ ] Zero LSP errors in `backend/pipeline/stages/`
- [ ] All tests pass

### Phase 3: Execution Modes & Temperatures
- [ ] All execution modes work (chat_only, ranking, full)
- [ ] Each stage has configurable temperature
- [ ] CLI flags work for mode selection
- [ ] GUI has temperature controls
- [ ] API endpoints for temperatures work

### Phase 4: Progress Tracking
- [ ] Progress events emitted from all stages
- [ ] WebSocket endpoint works
- [ ] Frontend receives real-time updates
- [ ] Progress UI displays correctly
- [ ] Connection resilience tested (reconnect logic)

### Phase 5: Council Sizing & Polish
- [ ] Council size configurable
- [ ] Tests added for new features
- [ ] Documentation updated
- [ ] Code polished (linting, formatting)
- [ ] Performance optimized

---

## Implementation Order & Timeline

### Week 1
**Days 1-2:** Phase 1 (DuckDuckGo removal)
- Monday: Remove DuckDuckGo code, update configs
- Tuesday: Update frontend, test with Tavily/Brave

**Days 3-4:** Phase 2 (Type fixes - Critical errors)
- Wednesday: Fix ContextKey and PipelineState errors
- Thursday: Fix import issues and None checks

**Day 5:** Sprint 3 start
- Friday: Create TemperatureManager, update config structure

### Week 2
**Days 6-7:** Sprint 3 (Execution modes)
- Monday: Update all stages to use temperatures
- Tuesday: Update WeeklyPipeline, add CLI flags

**Days 8-9:** Sprint 3 continued + Sprint 4 start
- Wednesday: Add GUI for execution modes and temperatures
- Thursday: Create ProgressEvent system

**Day 10:** Sprint 4 continued
- Friday: Add WebSocket endpoint

### Week 3
**Days 11-12:** Sprint 4 (Progress tracking)
- Monday: Update all stages to emit progress
- Tuesday: Create WebSocket client hook and UI

**Days 13-14:** Sprint 5 (Council sizing & Polish)
- Wednesday: Implement council size configuration
- Thursday: Add tests

**Day 15:** Final polish
- Friday: Update documentation, final testing

---

## Checklist for Start

Before beginning implementation:

- [ ] Brave API key provided and added to `.env`
- [ ] Review and approve execution mode definitions
- [ ] Review and approve default temperature values
- [ ] Review and approve council size options (3, 5, 7)
- [ ] Confirm WebSocket infrastructure is acceptable
- [ ] Identify preferred testing approach (manual, automated, or both)

---

## Notes

1. **Breaking Changes:** DuckDuckGo removal is a breaking change. Ensure all consumers are updated.

2. **Backward Compatibility:** Temperature controls and execution modes should default to current behavior if not configured.

3. **Performance:** WebSocket connections should be rate-limited to avoid server overload.

4. **Testing:** Each phase should have a test verification step before proceeding to the next.

5. **Documentation:** Keep docs in sync with code changes. Update CLAUDE.md after each phase.

---

**Next Steps:**
1. Review this plan
2. Provide Brave API key
3. Approve execution mode and temperature defaults
4. Begin Phase 1 implementation

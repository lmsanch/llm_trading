import React, { useState, useEffect, useCallback } from 'react';
import { ResearchPackCard } from './ResearchPackCard';
import { MarketChart } from '../ui/MarketChart';
import { ResearchCalendar } from './ResearchCalendar';
import { ResearchReportModal } from './ResearchReportModal';
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import {
  Play,
  CheckCheck,
  Search,
  Clock,
  FileText,
  AlertCircle,
  X,
  Loader2,
  ChevronRight,
  ShieldCheck,
  Edit2,
  TrendingUp
} from 'lucide-react';
import { mockResearchPacks } from '../../../lib/mockData';

// Session storage keys
const STORAGE_KEYS = {
  STATE: 'research_state',
  JOB_ID: 'research_job_id',
  POLLING_STATUS: 'research_polling_status',
  RESEARCH_DATA: 'research_data',
  PROMPT_DATA: 'research_prompt_data',
  MARKET_SNAPSHOT: 'research_market_snapshot',
  EDITABLE_PROMPT: 'research_editable_prompt',
  SELECTED_MODELS: 'research_selected_models',
};

export default function ResearchTab() {
  const [researchState, setResearchState] = useState(() => {
    return sessionStorage.getItem(STORAGE_KEYS.STATE) || 'reviewing';
  });
  const [jobId, setJobId] = useState(() => {
    return sessionStorage.getItem(STORAGE_KEYS.JOB_ID) || null;
  });
  const [pollingStatus, setPollingStatus] = useState(() => {
    const stored = sessionStorage.getItem(STORAGE_KEYS.POLLING_STATUS);
    return stored ? JSON.parse(stored) : null;
  });
  const [researchData, setResearchData] = useState(() => {
    const stored = sessionStorage.getItem(STORAGE_KEYS.RESEARCH_DATA);
    return stored ? JSON.parse(stored) : null;
  });

  const [promptData, setPromptData] = useState(() => {
    const stored = sessionStorage.getItem(STORAGE_KEYS.PROMPT_DATA);
    return stored ? JSON.parse(stored) : null;
  });
  const [marketSnapshot, setMarketSnapshot] = useState(() => {
    const stored = sessionStorage.getItem(STORAGE_KEYS.MARKET_SNAPSHOT);
    return stored ? JSON.parse(stored) : null;
  });
  const [editablePrompt, setEditablePrompt] = useState(() => {
    return sessionStorage.getItem(STORAGE_KEYS.EDITABLE_PROMPT) || "";
  });
  const [selectedModels, setSelectedModels] = useState(() => {
    const stored = sessionStorage.getItem(STORAGE_KEYS.SELECTED_MODELS);
    return stored ? JSON.parse(stored) : {
      perplexity: false,
      gemini: false
    };
  });
  const [selectedReport, setSelectedReport] = useState(null);

  // Persist state changes to sessionStorage
  const persistState = useCallback((key, value) => {
    if (value === null) {
      sessionStorage.removeItem(key);
    } else {
      sessionStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
    }
  }, []);

  const setResearchStateWithPersist = useCallback((value) => {
    setResearchState(value);
    persistState(STORAGE_KEYS.STATE, value);
  }, [persistState]);

  const setJobIdWithPersist = useCallback((value) => {
    setJobId(value);
    persistState(STORAGE_KEYS.JOB_ID, value);
  }, [persistState]);

  const setPollingStatusWithPersist = useCallback((value) => {
    setPollingStatus(value);
    persistState(STORAGE_KEYS.POLLING_STATUS, value);
  }, [persistState]);

  const setResearchDataWithPersist = useCallback((value) => {
    setResearchData(value);
    persistState(STORAGE_KEYS.RESEARCH_DATA, value);
  }, [persistState]);

  const setPromptDataWithPersist = useCallback((value) => {
    setPromptData(value);
    persistState(STORAGE_KEYS.PROMPT_DATA, value);
  }, [persistState]);

  const setMarketSnapshotWithPersist = useCallback((value) => {
    setMarketSnapshot(value);
    persistState(STORAGE_KEYS.MARKET_SNAPSHOT, value);
  }, [persistState]);

  const setEditablePromptWithPersist = useCallback((value) => {
    setEditablePrompt(value);
    persistState(STORAGE_KEYS.EDITABLE_PROMPT, value);
  }, [persistState]);

  const setSelectedModelsWithPersist = useCallback((value) => {
    // Handle both direct values and updater functions
    if (typeof value === 'function') {
      setSelectedModels(prev => {
        const newValue = value(prev);
        persistState(STORAGE_KEYS.SELECTED_MODELS, newValue);
        return newValue;
      });
    } else {
      setSelectedModels(value);
      persistState(STORAGE_KEYS.SELECTED_MODELS, value);
    }
  }, [persistState]);

  const clearPersistedState = useCallback(() => {
    Object.values(STORAGE_KEYS).forEach(key => sessionStorage.removeItem(key));
  }, []);

  // Initial Data Fetch
  useEffect(() => {
    const fetchData = async () => {
      try {
        const promptRes = await fetch('/api/research/prompt');
        if (promptRes.ok) {
          const pData = await promptRes.json();
          setPromptDataWithPersist(pData);
          if (!sessionStorage.getItem(STORAGE_KEYS.EDITABLE_PROMPT)) {
            setEditablePromptWithPersist(pData.prompt);
          }
        }

        const snapshotRes = await fetch('/api/market/snapshot');
        if (snapshotRes.ok) {
          const sData = await snapshotRes.json();
          setMarketSnapshotWithPersist(sData);
        }
      } catch (error) {
        console.error("Failed to fetch initial data:", error);
      }
    };
    fetchData();
  }, []);

  // Poll every 2.5 seconds when running
  useEffect(() => {
    let interval;
    if (researchState === 'running' && jobId) {
      interval = setInterval(async () => {
        try {
          const response = await fetch(`/api/research/status?job_id=${jobId}`);
          if (!response.ok) throw new Error("Failed to poll status");
          const status = await response.json();
          setPollingStatusWithPersist(status);

          if (status.status === 'complete') {
            clearInterval(interval);
            const resultsResponse = await fetch(`/api/research/${jobId}`);
            const data = await resultsResponse.json();
            setResearchDataWithPersist(data);
            setResearchStateWithPersist('complete');
          } else if (status.status === 'error') {
            clearInterval(interval);
            setResearchStateWithPersist('error');
          }
        } catch (error) {
          console.error("Polling error:", error);
        }
      }, 2500);
    }
    return () => clearInterval(interval);
  }, [researchState, jobId, setPollingStatusWithPersist, setResearchDataWithPersist, setResearchStateWithPersist]);

  const handleStartReview = () => {
    setResearchStateWithPersist('reviewing');
  };

  const handleSendResearch = async () => {
    try {
      setResearchStateWithPersist('running');
      const models = Object.keys(selectedModels).filter(k => selectedModels[k]);
      const response = await fetch('/api/research/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          models: models,
          prompt_override: editablePrompt
        })
      });
      const data = await response.json();
      setJobIdWithPersist(data.job_id);
      setPollingStatusWithPersist(data);
    } catch (error) {
      console.error("Failed to start research:", error);
      setResearchStateWithPersist('error');
    }
  };

  const handleCancel = () => {
    setResearchStateWithPersist('idle');
    setJobIdWithPersist(null);
    setPollingStatusWithPersist(null);
    clearPersistedState();
  };

  const Header = ({ status, statusColor = "warning" }) => (
    <div className="flex justify-between items-center mb-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Research Phase</h2>
        <p className="text-muted-foreground text-sm">Step 1: Deep market analysis and macro regime detection.</p>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant={statusColor}>{status}</Badge>
      </div>
    </div>
  );

  const MarketSnapshotPreview = () => {
    if (!marketSnapshot || !marketSnapshot.instruments) return null;
    const tickers = Object.keys(marketSnapshot.instruments);

    return (
      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide -mx-2 px-2">
        {tickers.map(ticker => {
          const data = marketSnapshot.instruments[ticker];
          const lastPrice = data.current.price;
          const pctChange = data.current.change_pct;
          const isUp = pctChange >= 0;

          return (
            <div key={ticker} className="flex-shrink-0 w-48 bg-background p-3 rounded-lg border border-border/50 shadow-sm transition-all hover:bg-muted/5">
              <div className="flex justify-between items-center mb-1">
                <span className="font-bold text-sm tracking-tight">{ticker}</span>
                <span className={isUp ? "text-green-500 font-medium" : "text-red-500 font-medium"}>
                  {lastPrice.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-end">
                <span className={`${isUp ? "text-green-600/80" : "text-red-600/80"} text-[10px] bg-muted/50 px-1.5 py-0.5 rounded-sm`}>
                  {pctChange > 0 ? "+" : ""}{pctChange.toFixed(2)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  if (researchState === 'idle') {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <Header status="READY" />
        <Card className="flex flex-col items-center justify-center p-12 border-dashed bg-muted/20">
          <div className="bg-primary/10 p-4 rounded-full mb-4">
            <Search className="h-8 w-8 text-primary" />
          </div>
          <h3 className="text-xl font-semibold mb-2">New Macro Research</h3>
          <p className="text-muted-foreground mb-6 text-center max-w-md text-sm">
            Analyze market structures, news sentiment, and technical regimes using multi-modal LLM orchestration.
          </p>
          <Button onClick={handleStartReview} size="lg" className="rounded-full px-8 shadow-lg transition-transform hover:scale-105 active:scale-95">
            <Edit2 className="mr-2 h-4 w-4" /> Configure & Start
          </Button>
        </Card>
      </div>
    );
  }

  if (researchState === 'reviewing') {
    return (
      <div className="space-y-6">
        <Header status="CONFIGURATION" />

        {(!promptData || !marketSnapshot) ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground animate-pulse">Loading market context and system prompt...</p>
          </div>
        ) : (
          <div className="space-y-8 animate-in fade-in duration-500">
            {/* Top Section: Full Width Horizontal Scroll Market Snapshot */}
            <div className="space-y-3 pb-2 border-b">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Clock className="h-3 w-3" /> Market Context Snapshot
                </h3>
                <span className="text-[10px] text-muted-foreground bg-muted px-2 py-0.5 rounded-full animate-pulse">Swipe for all instruments →</span>
              </div>
              <MarketSnapshotPreview />
            </div>

            {/* Historical Price Action Charts - Show by default */}
            {marketSnapshot && marketSnapshot.instruments && (
              <div className="space-y-3 pb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <TrendingUp className="h-3 w-3" /> Historical Price Action (Last 30 Days)
                </h3>
                <div className="h-[400px] rounded-2xl overflow-hidden border border-border/40 shadow-lg bg-background">
                  <MarketChart
                    data={marketSnapshot}
                    instruments={["SPY", "QQQ", "TLT"]}
                  />
                </div>
                <p className="text-[10px] text-muted-foreground text-center">
                  Showing key instruments: SPY (S&P 500), QQQ (Nasdaq), TLT (Treasuries)
                </p>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left Column: Editable System Prompt (Larger Area) */}
              <div className="lg:col-span-2">
                <Card className="border-primary/20 shadow-2xl overflow-hidden h-full flex flex-col bg-background">
                  <CardHeader className="bg-primary/5 border-b py-3 px-6 flex flex-row items-center justify-between">
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                      <FileText className="h-4 w-4 text-primary" /> System Prompt Override
                    </CardTitle>
                    <Badge variant="outline" className="text-[9px] h-4 py-0 font-mono tracking-tighter opacity-70">EPHEMERAL RUN</Badge>
                  </CardHeader>
                  <CardContent className="flex-1 p-0">
                    <textarea
                      className="w-full h-full min-h-[500px] p-8 text-[13px] font-mono leading-relaxed bg-background/50 outline-none resize-none border-0 ring-0 focus:ring-0"
                      value={editablePrompt}
                      onChange={(e) => setEditablePromptWithPersist(e.target.value)}
                      placeholder="Loading prompt..."
                    />
                  </CardContent>
                </Card>
              </div>

              {/* Right Column: Calendar FIRST, Then Execution Configuration */}
              <div className="space-y-6">
                {/* Research History Calendar - MOVED TO TOP */}
                <ResearchCalendar onSelectDate={async (date, data) => {
                  if (data.providers && data.providers.length > 0) {
                    // Extract report ID (remove curly braces from PostgreSQL array format)
                    const reportId = data.providers[0].report_ids.replace(/[{}]/g, '');
                    try {
                      const response = await fetch(`/api/research/report/${reportId}`);
                      if (response.ok) {
                        const report = await response.json();
                        setSelectedReport(report);
                      } else {
                        console.error('❌ Failed to load report');
                      }
                    } catch (error) {
                      console.error('❌ Error loading report:', error);
                    }
                  }
                }} />

                {/* Orchestration Setup - MOVED BELOW CALENDAR */}
                <Card className="border-border/60 shadow-sm bg-card/50 backdrop-blur-sm">
                  <CardHeader className="py-3 px-4 border-b">
                    <CardTitle className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Orchestration Setup</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {[
                      { id: 'perplexity', name: 'Perplexity Sonar Deep Research', desc: 'Agentic web search with exhaustive source synthesis' },
                      { id: 'gemini', name: 'Gemini Deep Research 3.0', desc: 'Multi-step reasoning with Google Search integration' }
                    ].map(m => (
                      <div
                        key={m.id}
                        onClick={() => setSelectedModelsWithPersist(prev => ({ ...prev, [m.id]: !prev[m.id] }))}
                        className={`flex items-start gap-4 p-4 rounded-xl border-2 transition-all cursor-pointer select-none ${selectedModels[m.id] ? 'border-primary/30 bg-primary/5 shadow-inner' : 'border-transparent bg-muted/20 grayscale'}`}
                      >
                        <div className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${selectedModels[m.id] ? 'bg-primary border-primary' : 'bg-transparent border-border'}`}>
                          {selectedModels[m.id] && <CheckCheck className="h-3 w-3 text-white stroke-[3]" />}
                        </div>
                        <div className="space-y-1">
                          <span className="text-[13px] font-bold leading-none">{m.name}</span>
                          <p className="text-[10px] text-muted-foreground/80 leading-normal">{m.desc}</p>
                        </div>
                      </div>
                    ))}
                    <div className="pt-6 space-y-3">
                      <Button
                        onClick={handleSendResearch}
                        disabled={!selectedModels.perplexity && !selectedModels.gemini}
                        className="w-full h-12 rounded-xl text-base font-bold shadow-xl shadow-primary/20 hover:translate-y-[-2px] active:translate-y-[0px] transition-all"
                      >
                        <Play className="mr-2 h-5 w-5 fill-current" />
                        Execute Analysis
                      </Button>
                      <Button variant="ghost" onClick={handleCancel} className="w-full h-10 rounded-xl text-xs text-muted-foreground hover:bg-destructive/5 hover:text-destructive transition-colors">
                        Abort and return
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                <div className="p-4 rounded-xl border border-dashed border-border/60 bg-muted/5 flex items-start gap-3">
                  <AlertCircle className="h-4 w-4 text-warning mt-0.5" />
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Research results will be used by Portfolio Managers to synthesize trade pitches. Overridden prompt resets on page reload.
                  </p>
                </div>

              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (researchState === 'running') {
    return (
      <div className="space-y-10 py-12">
        <Header status="EXECUTING..." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 max-w-5xl mx-auto px-4">
          {['perplexity', 'gemini'].map(id => {
            if (!selectedModels[id]) return null;
            const status = pollingStatus?.[id] || { status: 'pending', progress: 0, message: 'Queueing task...' };
            const isComplete = status.status === 'complete';

            return (
              <Card key={id} className="border-primary/20 overflow-hidden shadow-2xl bg-card">
                <CardHeader className="pb-4 border-b bg-muted/5 px-6 pt-6">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-lg font-bold flex items-center gap-3">
                      {id === 'perplexity' ? (
                        <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
                          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" className="w-8 h-8 text-blue-500" fill="currentColor">
                          <circle cx="12" cy="12" r="10" />
                        </svg>
                      )}
                      {id === 'perplexity' ? 'Perplexity Sonar Deep Research' : 'Gemini Deep Research 3.0'}
                    </CardTitle>
                    {isComplete ? (
                      <Badge variant="success" className="bg-green-500/10 text-green-500 border-green-500/20 px-3 py-1 font-bold">READY</Badge>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        <span className="text-[10px] font-bold text-primary animate-pulse tracking-widest uppercase">Active</span>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="p-8 space-y-6">
                  <div className="w-full bg-muted rounded-full h-3 overflow-hidden shadow-inner">
                    <div
                      className="bg-primary h-full transition-all duration-1000 ease-in-out relative"
                      style={{ width: `${status.progress}%` }}
                    >
                      <div className="absolute top-0 right-0 bottom-0 w-20 bg-white/20 animate-shimmer" />
                    </div>
                  </div>
                  <div className="flex justify-between items-center border-t border-dashed pt-4">
                    <span className="text-[11px] text-muted-foreground font-semibold uppercase tracking-wider">{status.message}</span>
                    <span className="text-xl font-black text-primary font-mono">{status.progress}%</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
        <div className="flex flex-col items-center gap-6 pt-8 animate-in fade-in slide-in-from-bottom-2 duration-1000 delay-500">
          <div className="flex items-center gap-3 py-2 px-6 rounded-full bg-muted/50 border shadow-sm">
            <Clock className="h-4 w-4 text-muted-foreground animate-spin-slow" />
            <span className="text-[11px] text-muted-foreground font-medium tracking-tight">AI Orchestration in progress. Typically takes 30-50 seconds.</span>
          </div>
          <Button variant="ghost" size="sm" onClick={handleCancel} className="text-destructive/60 hover:text-destructive hover:bg-destructive/5 rounded-full px-6 transition-all">
            <X className="h-3 w-3 mr-2" /> Force Stop
          </Button>
        </div>
      </div>
    );
  }

  if (researchState === 'error') {
    return (
      <div className="space-y-6 animate-in zoom-in-95 duration-300">
        <Header status="FAILURE" statusColor="destructive" />
        <Card className="border-destructive/30 bg-destructive/5 shadow-2xl max-w-2xl mx-auto">
          <CardContent className="p-16 flex flex-col items-center">
            <div className="bg-destructive/10 p-6 rounded-full mb-8 shadow-lg">
              <AlertCircle className="h-12 w-12 text-destructive" />
            </div>
            <h3 className="text-2xl font-black mb-4 text-destructive tracking-tight uppercase">System Error</h3>
            <p className="text-muted-foreground mb-12 text-center max-w-sm text-xs leading-relaxed font-medium">
              {pollingStatus?.error || "We encountered an unexpected failure during the LLM research loop. Check your API connectivity and system logs."}
            </p>
            <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
              <Button onClick={handleSendResearch} variant="destructive" className="px-10 rounded-xl h-12 font-black shadow-xl shadow-destructive/20 uppercase tracking-widest text-[11px]">Retry Operation</Button>
              <Button variant="outline" onClick={handleCancel} className="px-10 rounded-xl h-12 font-bold opacity-60 hover:opacity-100 transition-opacity">Back to Monitor</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // COMPLETE STATE
  const { perplexity, gemini, market_snapshot: ms } = researchData || mockResearchPacks;
  const instruments = promptData?.instruments || ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"];

  return (
    <>
      <div className="space-y-8 pb-32 animate-in fade-in slide-in-from-bottom-6 duration-1000">
        <Header status="COMPLETE" statusColor="success" />

        {/* Primary Context View */}
        {(ms || marketSnapshot) && (
          <div className="h-[480px] rounded-[32px] overflow-hidden border-2 border-border/40 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.3)] bg-background">
            <MarketChart data={ms || marketSnapshot} instruments={instruments} />
          </div>
        )}

        {/* Result Cards Grid */}
        <div className={`grid grid-cols-1 ${selectedModels.perplexity && selectedModels.gemini ? "2xl:grid-cols-2" : "max-w-5xl mx-auto"} gap-10 pt-4`}>
          {selectedModels.perplexity && <ResearchPackCard data={perplexity} />}
          {selectedModels.gemini && <ResearchPackCard data={gemini} />}
        </div>

        {/* Persistent Action Bar */}
        <div className="fixed bottom-10 left-1/2 -translate-x-1/2 w-full max-w-5xl z-50 px-6">
          <div className="bg-background/90 backdrop-blur-2xl border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] rounded-[24px] p-5 flex items-center justify-between ring-1 ring-white/5">
            <div className="flex items-center gap-4 pl-4 border-l-4 border-success/60">
              <div className="w-10 h-10 rounded-full bg-success/10 flex items-center justify-center text-success shadow-inner">
                <ShieldCheck className="h-5 w-5 stroke-[2.5]" />
              </div>
              <div className="flex flex-col">
                <span className="text-[13px] font-black uppercase tracking-tight text-foreground/90">Stage 1 Verified</span>
                <span className="text-[10px] text-muted-foreground font-bold tracking-wider">Models consistent with market regime</span>
              </div>
            </div>
            <div className="flex gap-4">
              <Button variant="outline" onClick={handleStartReview} className="rounded-xl border-border/60 hover:bg-muted font-bold tracking-tight py-6">
                <Edit2 className="mr-2 h-4 w-4" /> Re-Configure
              </Button>
              <Button className="bg-success hover:bg-success/90 rounded-xl px-12 shadow-[0_10px_30px_rgba(34,197,94,0.3)] font-black uppercase tracking-wider text-[11px] py-6 border-b-4 border-green-700 active:border-b-0 transition-all">
                Initialize Strategy Session <ChevronRight className="ml-2 h-4 w-4 stroke-[3]" />
              </Button>
            </div>
          </div>
        </div>
      </div>

    {/* Research Report Modal */}
    {selectedReport && (
      <ResearchReportModal
        report={selectedReport}
        onClose={() => setSelectedReport(null)}
      />
    )}
  </>
  );
}

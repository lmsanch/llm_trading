import React, { useState, useEffect } from 'react';
import { PMPitchCard } from './PMPitchCard';
import { MarketMetrics } from './MarketMetrics';
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Play, CheckCheck, RefreshCw, Send, Loader2, Calendar, TrendingUp, FileText, ChevronDown, ChevronUp, ShieldAlert, ExternalLink, Database, Share2 } from 'lucide-react';
import WeeklyGraphViewer from '../../WeeklyGraphViewer';

const PM_MODELS = [
  { key: 'chatgpt', label: 'GPT-5.2', account: 'CHATGPT' },
  { key: 'gemini', label: 'Gemini 3 Pro', account: 'GEMINI' },
  { key: 'claude', label: 'Claude Sonnet 4.5', account: 'CLAUDE' },
  { key: 'groq', label: 'Grok 4.1', account: 'GROQ' },
  { key: 'deepseek', label: 'DeepSeek V3', account: 'DEEPSEEK' }
];

function ActivityIcon(props) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  );
}

function ResearchPreview({ data }) {
  const [showFullReport, setShowFullReport] = useState(false);

  if (!data) return null;

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3 border-b">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
              Latest Research Report
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              {data.created_at ? `Date: ${new Date(data.created_at).toLocaleString('en-US', { 
                timeZone: 'America/New_York',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
              })} ET` : ''} • Perplexity Sonar
            </p>
          </div>
          <Badge variant="success" className="text-[10px]">LATEST</Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4 max-h-[600px] overflow-y-auto">

        {/* Natural Language Report - Collapsed by default */}
        {data.natural_language && (
          <div className="space-y-2">
            <button
              onClick={() => setShowFullReport(!showFullReport)}
              className="flex items-center justify-between w-full text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
            >
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4" /> Full Report
              </div>
              {showFullReport ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {showFullReport && (
              <div className="bg-muted/50 p-3 rounded-md text-sm border">
                <p className="whitespace-pre-wrap leading-relaxed font-sans text-foreground/90">
                  {data.natural_language}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Structured Report */}
        {data.structured_json && (
          <>
            {/* Macro Regime */}
            <div className="space-y-2 border-t pt-4">
              <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
                <ActivityIcon className="h-4 w-4" /> Macro Regime
              </h4>
              <div className="bg-muted/50 p-3 rounded-md text-sm border">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Risk Mode:</span>
                  <Badge variant={
                    data.structured_json.macro_regime?.risk_mode === 'RISK_ON' ? 'success' :
                      data.structured_json.macro_regime?.risk_mode === 'RISK_OFF' ? 'destructive' :
                        'neutral'
                  }>
                    {data.structured_json.macro_regime?.risk_mode || 'NEUTRAL'}
                  </Badge>
                </div>
                <p className="text-muted-foreground leading-relaxed">
                  {data.structured_json.macro_regime?.description}
                </p>
              </div>
            </div>

            {/* Top Narratives */}
            {data.structured_json.top_narratives && data.structured_json.top_narratives.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
                  <TrendingUp className="h-4 w-4" /> Top Narratives
                </h4>
                <ul className="list-disc list-inside text-sm space-y-1.5 text-muted-foreground bg-muted/30 p-2 rounded-md border">
                  {data.structured_json.top_narratives.map((narrative, i) => (
                    <li key={i} className="pl-1">
                      {typeof narrative === 'string' ? narrative : narrative.name || JSON.stringify(narrative)}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Tradable Candidates */}
            {data.structured_json.tradable_candidates && data.structured_json.tradable_candidates.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
                  <ExternalLink className="h-4 w-4" /> Tradable Candidates
                </h4>
                <div className="flex flex-wrap gap-2">
                  {data.structured_json.tradable_candidates.map((ticker, i) => (
                    <Badge key={i} variant="outline" className="font-mono">
                      {ticker}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Event Calendar */}
            {data.structured_json.event_calendar && data.structured_json.event_calendar.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
                  <Calendar className="h-4 w-4" /> Event Calendar
                </h4>
                <div className="space-y-1 bg-muted/30 p-2 rounded-md border">
                  {data.structured_json.event_calendar.map((event, i) => (
                    <div key={i} className="flex justify-between items-center text-xs py-1 border-b last:border-0 border-muted/50">
                      <span className="text-muted-foreground w-20">{event.date}</span>
                      <span className="font-medium text-foreground flex-1 px-2">{event.event}</span>
                      <Badge variant="outline" className={`text-[9px] h-4 ${event.impact === 'CRITICAL' ? 'border-red-500/50 text-red-500' :
                        event.impact === 'HIGH' ? 'border-orange-500/50 text-orange-500' :
                          'border-yellow-500/50 text-yellow-500'
                        }`}>
                        {event.impact}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Confidence Notes */}
            {data.structured_json.confidence_notes && (
              <div className="space-y-2 border-t pt-4">
                <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
                  <ShieldAlert className="h-4 w-4" /> Confidence & Caveats
                </h4>
                <div className="bg-yellow-500/5 border border-yellow-500/20 p-3 rounded-md text-xs space-y-2">
                  {data.structured_json.confidence_notes.known_unknowns && (
                    <div>
                      <span className="font-semibold text-yellow-600 dark:text-yellow-400">Known Unknowns:</span>
                      <p className="text-muted-foreground mt-0.5">
                        {data.structured_json.confidence_notes.known_unknowns}
                      </p>
                    </div>
                  )}
                  {data.structured_json.confidence_notes.data_quality_flags &&
                    data.structured_json.confidence_notes.data_quality_flags.length > 0 && (
                      <div>
                        <span className="font-semibold text-yellow-600 dark:text-yellow-400">Data Flags:</span>
                        <ul className="list-disc list-inside mt-1 text-muted-foreground space-y-1">
                          {data.structured_json.confidence_notes.data_quality_flags.map((flag, i) => (
                            <li key={i}>{flag}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function PMsTab() {
  const PITCH_SCHEMA_VERSION = 'v3_risk_profiles';

  const checkCacheVersion = () => {
    const cachedVersion = sessionStorage.getItem('pm_pitch_schema_version');
    if (cachedVersion !== PITCH_SCHEMA_VERSION) {
      console.log('PM pitch schema updated, clearing old cache...');
      sessionStorage.removeItem('pm_pitches');
      sessionStorage.removeItem('pm_model_progress');
      sessionStorage.setItem('pm_pitch_schema_version', PITCH_SCHEMA_VERSION);
    }
  };

  checkCacheVersion();

  const [researchReports, setResearchReports] = useState([]);
  const [selectedResearch, setSelectedResearch] = useState(() => {
    return sessionStorage.getItem('pm_selected_research') || '';
  });
  const [latestReport, setLatestReport] = useState(null);
  const [marketMetrics, setMarketMetrics] = useState(null);
  const [currentPrices, setCurrentPrices] = useState(null);
  const [pmStatus, setPmStatus] = useState(() => {
    return sessionStorage.getItem('pm_status') || 'idle';
  });
  const [jobId, setJobId] = useState(() => {
    return sessionStorage.getItem('pm_job_id') || '';
  });
  const [modelProgress, setModelProgress] = useState(() => {
    const saved = sessionStorage.getItem('pm_model_progress');
    return saved ? JSON.parse(saved) : {};
  });
  const [pitches, setPitches] = useState(() => {
    const saved = sessionStorage.getItem('pm_pitches');
    return saved ? JSON.parse(saved) : [];
  });
  const [pollingInterval, setPollingInterval] = useState(null);

  // Load research history and market metrics on mount
  useEffect(() => {
    loadResearchHistory();
    loadMarketMetrics();
    loadCurrentPrices();
    loadLatestPitches();
  }, []);

  // Persist state to sessionStorage
  useEffect(() => {
    sessionStorage.setItem('pm_selected_research', selectedResearch);
    sessionStorage.setItem('pm_status', pmStatus);
    sessionStorage.setItem('pm_job_id', jobId);
    sessionStorage.setItem('pm_model_progress', JSON.stringify(modelProgress));
    sessionStorage.setItem('pm_pitches', JSON.stringify(pitches));
  }, [selectedResearch, pmStatus, jobId, modelProgress, pitches]);

  // Resume polling if page was refreshed during generation
  useEffect(() => {
    if (pmStatus === 'generating' && jobId) {
      startPolling(jobId);
    }
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, []);

  const loadResearchHistory = async () => {
    try {
      const response = await fetch(`/api/research/history?days=90`);
      const data = await response.json();

      // Extract all Perplexity reports with dates
      const reports = [];
      Object.entries(data.history || {}).forEach(([date, info]) => {
        const perplexityProvider = info.providers.find(p => p.name === 'perplexity');
        if (perplexityProvider && perplexityProvider.report_ids) {
          perplexityProvider.report_ids.forEach((id, idx) => {
            reports.push({
              id: id,
              date: date,
              status: perplexityProvider.statuses?.[idx] || 'unknown'
            });
          });
        }
      });

      // Sort by date descending
      reports.sort((a, b) => new Date(b.date) - new Date(a.date));
      setResearchReports(reports);

      // Auto-select and load the latest report
      if (reports.length > 0) {
        const latestId = reports[0].id;
        if (!selectedResearch) {
          setSelectedResearch(latestId);
        }

        // Load latest report details
        loadReportDetails(selectedResearch || latestId);
      }
    } catch (error) {
      console.error('Error loading research history:', error);
    }
  };

  const loadReportDetails = async (reportId) => {
    try {
      const response = await fetch(`/api/research/report/${reportId}`);
      if (response.ok) {
        const report = await response.json();
        setLatestReport(report);
      }
    } catch (error) {
      console.error('Error loading report details:', error);
    }
  };

  const loadMarketMetrics = async () => {
    try {
      const response = await fetch(`/api/market/metrics`);
      if (response.ok) {
        const metrics = await response.json();
        setMarketMetrics(metrics);
      }
    } catch (error) {
      console.error('Error loading market metrics:', error);
    }
  };

  const loadCurrentPrices = async () => {
    try {
      const response = await fetch(`/api/market/prices`);
      if (response.ok) {
        const prices = await response.json();
        setCurrentPrices(prices);
      }
    } catch (error) {
      console.error('Error loading current prices:', error);
    }
  };

  const loadLatestPitches = async (weekId, researchDate) => {
    try {
      let url = '/api/pitches/current';
      const params = new URLSearchParams();
      if (researchDate) params.append('research_date', researchDate);
      else if (weekId) params.append('week_id', weekId);

      if (params.toString()) url += `?${params.toString()}`;

      const response = await fetch(url);
      if (response.ok) {
        const pitchesData = await response.json();
        console.log('🔍 Loaded pitches from API:', pitchesData.length, 'pitches');
        if (pitchesData && pitchesData.length > 0) {
          setPitches(pitchesData);
          setPmStatus('complete');
        } else {
          setPitches([]);
          setPmStatus('idle');
        }
      }
    } catch (error) {
      console.error('Error loading latest pitches:', error);
    }
  };

  // Reload report and pitches when selection changes
  useEffect(() => {
    if (selectedResearch) {
      loadReportDetails(selectedResearch);
    }
  }, [selectedResearch]);

  // Load pitches when report details are loaded
  useEffect(() => {
    if (latestReport) {
      // Prefer using research date if available, otherwise week_id
      const date = latestReport.created_at || latestReport.date;
      loadLatestPitches(latestReport.week_id, date);
    }
  }, [latestReport]);

  const startPolling = (jid) => {
    if (pollingInterval) clearInterval(pollingInterval);

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/pitches/status?job_id=${jid}`);
        if (!response.ok) {
          clearInterval(interval);
          setPmStatus('error');
          return;
        }

        const status = await response.json();

        // Update model progress
        const progress = {};
        PM_MODELS.forEach(model => {
          if (status[model.key]) {
            progress[model.key] = status[model.key];
          }
        });
        setModelProgress(progress);

        // Check if complete
        if (status.status === 'complete') {
          clearInterval(interval);
          setPmStatus('complete');
          if (status.results?.pitches) {
            setPitches(status.results.pitches);
          }
        } else if (status.status === 'error') {
          clearInterval(interval);
          setPmStatus('error');
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2500);

    setPollingInterval(interval);
  };

  const handleGeneratePitches = async (modelKey = null) => {
    if (!selectedResearch) return;

    try {
      setPmStatus('generating');
      // Only reset progress if generating ALL
      if (!modelKey) {
        setModelProgress({});
        setPitches([]);
      }

      const payload = { research_id: selectedResearch };
      if (modelKey) {
        payload.model = modelKey;
      }

      const response = await fetch(`/api/pitches/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error('Failed to start pitch generation');
      }

      const result = await response.json();
      setJobId(result.job_id);
      startPolling(result.job_id);
    } catch (error) {
      console.error('Error starting pitch generation:', error);
      setPmStatus('error');
    }
  };

  const handleLoadData = async () => {
    if (!selectedResearch) return;
    // Just re-loading the report details will trigger the effect to load pitches
    loadReportDetails(selectedResearch);
  };

  const handleReset = () => {
    if (pollingInterval) clearInterval(pollingInterval);
    setPmStatus('idle');
    setJobId('');
    setModelProgress({});
    setPitches([]);
    sessionStorage.removeItem('pm_status');
    sessionStorage.removeItem('pm_job_id');
    sessionStorage.removeItem('pm_model_progress');
    sessionStorage.removeItem('pm_pitches');
  };

  const handlePassToCouncil = async () => {
    try {
      console.log('🏛️ Passing to Council...');
      const response = await fetch('/api/council/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        throw new Error('Failed to start council synthesis');
      }

      const result = await response.json();
      console.log('✅ Council synthesis started:', result);

      // TODO: Show success message or redirect to Council tab
      alert('Council synthesis started! Check the Council tab in a moment.');
    } catch (error) {
      console.error('❌ Error starting council synthesis:', error);
      alert('Failed to start council synthesis. Check console for details.');
    }
  };

  const handleApproveAll = () => {
    // TODO: Implement approve all logic
    // For now, just pass directly to council
    console.log('Approve All clicked - passing to council');
    handlePassToCouncil();
  };

  const renderDataPackage = () => (
    <div className="space-y-6 mb-6">
      {/* Research Report */}
      {latestReport && <ResearchPreview data={latestReport} />}

      {/* Knowledge Graph */}
      {latestReport && latestReport.structured_json && latestReport.structured_json.weekly_graph && (
        <Card>
          <CardHeader className="pb-3 border-b">
            <div className="flex justify-between items-start">
              <CardTitle className="text-sm flex items-center gap-2">
                <Share2 className="h-4 w-4" /> Latest Knowledge Graphs
              </CardTitle>
              {latestReport.created_at && (
                <p className="text-xs text-muted-foreground">
                  Date: {new Date(latestReport.created_at).toLocaleString('en-US', { 
                    timeZone: 'America/New_York',
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                  })} ET
                </p>
              )}
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            <WeeklyGraphViewer data={latestReport.structured_json.weekly_graph} />
          </CardContent>
        </Card>
      )}

      {/* Market Metrics */}
      {marketMetrics && <MarketMetrics data={marketMetrics} prices={currentPrices} />}

      {/* Raw JSON View */}
      <Card>
        <CardHeader className="pb-3 border-b">
          <div className="flex justify-between items-start">
            <CardTitle className="text-sm">📄 Latest Complete Data Package (JSON)</CardTitle>
            {latestReport?.created_at && (
              <p className="text-xs text-muted-foreground">
                Date: {new Date(latestReport.created_at).toLocaleString('en-US', { 
                  timeZone: 'America/New_York',
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false
                })} ET
              </p>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="bg-muted/50 p-4 rounded-md border font-mono text-xs overflow-x-auto max-h-[600px] overflow-y-auto">
            <pre>
              {JSON.stringify(
                {
                  research: latestReport,
                  market_metrics: marketMetrics,
                  current_prices: currentPrices
                },
                null,
                2
              )}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderReportSelector = () => (
    <Card className="p-4 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 flex-1">
          <div className="flex-1 max-w-xs">
            <label className="block text-xs font-medium mb-1 text-muted-foreground">Select Research Report</label>
            <select
              value={selectedResearch}
              onChange={(e) => setSelectedResearch(e.target.value)}
              className="w-full px-3 py-2 text-sm border rounded-md bg-background"
            >
              {researchReports.length === 0 && <option value="">No reports available</option>}
              {researchReports.map(report => (
                <option key={report.id} value={report.id}>
                  {report.date} {report.id === researchReports[0].id ? '(Latest)' : ''}
                </option>
              ))}
            </select>
          </div>
          {/* Show Load Data button */}
          <div className="pt-5">
            {pmStatus !== 'generating' && (
              <Button
                onClick={handleLoadData}
                disabled={!selectedResearch}
                size="sm"
              >
                <Database className="mr-2 h-4 w-4" />
                Load Data
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  );

  const renderPMGrid = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
      {PM_MODELS.map(model => {
        const pitch = pitches.find(p => (p.model === model.key || p.pm_model === model.key));
        const progress = modelProgress[model.key];
        const isGenerating = pmStatus === 'generating' && progress && progress.status !== 'complete' && progress.status !== 'error';

        if (isGenerating) {
          return (
            <Card key={model.key} className="p-4 border-yellow-500/50">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-sm">{model.label}</h4>
                  <Badge variant="warning" className="text-[10px]">GENERATING</Badge>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{progress?.message || 'Waiting...'}</span>
                    <span>{progress?.progress || 0}%</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-1.5">
                    <div
                      className="bg-yellow-500 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${progress?.progress || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </Card>
          );
        }

        if (pitch) {
          return (
            <div key={model.key} className="space-y-3 flex flex-col h-full">
              <div className="flex-1">
                <PMPitchCard pitch={pitch} />
              </div>
              <Button
                size="sm"
                variant="outline"
                className="w-full text-xs"
                onClick={() => handleGeneratePitches(model.key)}
                disabled={pmStatus === 'generating'}
              >
                <RefreshCw className="mr-2 h-3 w-3" /> Generate New Report
              </Button>
            </div>
          );
        }

        return (
          <div key={model.key} className="space-y-3 flex flex-col h-full">
            <div className="flex-1">
              <Card className="p-4 flex flex-col justify-between h-full bg-muted/10 border-dashed min-h-[300px]">
                <div className="text-center space-y-3 mt-8">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto">
                    <ActivityIcon className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">{model.label}</h3>
                    <p className="text-xs text-muted-foreground mt-1">{model.account}</p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground px-2">
                      <span className="font-semibold">Instrument:</span> N/A
                    </p>
                    <p className="text-xs text-muted-foreground px-2">
                      <span className="font-semibold">Direction:</span> N/A
                    </p>
                    <p className="text-xs text-muted-foreground px-2">
                      <span className="font-semibold">Conviction:</span> N/A
                    </p>
                  </div>
                </div>
              </Card>
            </div>
            <Button
              size="sm"
              className="w-full text-xs"
              onClick={() => handleGeneratePitches(model.key)}
              disabled={pmStatus === 'generating'}
            >
              <Play className="mr-2 h-3 w-3" /> Generate New Report
            </Button>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">PM Trading Outlooks</h2>
          <p className="text-muted-foreground">Review trading convictions from Portfolio Manager models.</p>
        </div>
        <div className="flex items-center gap-2">
          {pmStatus === 'idle' && <Badge variant="secondary">IDLE</Badge>}
          {pmStatus === 'generating' && (
            <Badge variant="warning">
              <Loader2 className="mr-2 h-3 w-3 animate-spin" /> GENERATING
            </Badge>
          )}
          {pmStatus === 'complete' && <Badge variant="success">COMPLETE</Badge>}
          {pmStatus === 'error' && <Badge variant="destructive">ERROR</Badge>}
        </div>
      </div>

      {renderReportSelector()}

      {renderDataPackage()}

      {/* Always show PM cards */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Portfolio Manager Trading Outlooks ({pitches.length}/5)</h3>
          <Badge variant="outline">{pitches.length}/5 Models Active</Badge>
        </div>
        {renderPMGrid()}
      </div>

      {/* Always show action buttons at bottom */}
      <Card className="p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-sm text-muted-foreground">
          Review trading outlooks above. You can generate new reports for individual models if needed.
        </div>
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={handleReset}>
            <RefreshCw className="mr-2 h-4 w-4" /> Reset View
          </Button>
          <Button
            onClick={handlePassToCouncil}
            className="bg-blue-600 hover:bg-blue-700"
            disabled={pitches.length < 5 || pitches.some(p => !p || p.status === 'error')}
          >
            <Send className="mr-2 h-4 w-4" /> Send to Council
          </Button>
        </div>
      </Card>
    </div>
  );
}

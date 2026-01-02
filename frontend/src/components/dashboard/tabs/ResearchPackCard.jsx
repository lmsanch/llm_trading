import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import {
  CheckCircle,
  RefreshCw,
  ExternalLink,
  Calendar,
  TrendingUp,
  FileText,
  ChevronDown,
  ChevronUp,
  ShieldAlert
} from 'lucide-react';

export function ResearchPackCard({ data }) {
  const [showFullReport, setShowFullReport] = useState(true);

  if (!data) return null;

  return (
    <Card className="flex flex-col h-full max-h-[calc(100vh-250px)]">
      <CardHeader className="pb-3 sticky top-0 bg-card z-10 border-b mb-2">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              {data.source === 'perplexity' ? (
                <svg viewBox="0 0 24 24" className="w-7 h-7" fill="currentColor">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" className="w-7 h-7 text-blue-500" fill="currentColor">
                  <circle cx="12" cy="12" r="10" />
                </svg>
              )}
              {data.source === 'perplexity' ? 'Perplexity Sonar Deep Research' : 'Gemini Deep Research 3.0'}
            </CardTitle>
            <CardDescription className="text-xs">{data.model}</CardDescription>
          </div>
          <Badge variant="outline" className="text-[10px]">{data.source.toUpperCase()}</Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-4 overflow-y-auto pt-2">

        {/* Natural Language Report */}
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

        {/* Macro Regime */}
        <div className="space-y-2 border-t pt-4">
          <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
            <ActivityIcon className="h-4 w-4" /> Macro Regime
          </h4>
          <div className="bg-muted/50 p-3 rounded-md text-sm border">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">Risk Mode:</span>
              <Badge variant={data.macro_regime.risk_mode === 'RISK_ON' ? 'success' : data.macro_regime.risk_mode === 'RISK_OFF' ? 'destructive' : 'neutral'}>
                {data.macro_regime.risk_mode}
              </Badge>
            </div>
            <p className="text-muted-foreground leading-relaxed">{data.macro_regime.description}</p>
          </div>
        </div>

        {/* Top Narratives */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
            <TrendingUp className="h-4 w-4" /> Top Narratives
          </h4>
          <ul className="list-disc list-inside text-sm space-y-1.5 text-muted-foreground bg-muted/30 p-2 rounded-md border">
            {(data.top_narratives || []).map((narrative, i) => (
              <li key={i} className="pl-1">{narrative}</li>
            ))}
          </ul>
        </div>

        {/* Tradable Candidates */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
            <ExternalLink className="h-4 w-4" /> Tradable Candidates
          </h4>
          <div className="grid gap-2">
            {(data.tradable_candidates || data.asset_setups || []).map((candidate, i) => (
              <div key={i} className="flex flex-col gap-1 text-sm border p-2 rounded-md bg-muted/30 hover:bg-muted/50 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-primary">{candidate.ticker}</span>
                  {candidate.expected_outperformance_vs_spy && (
                    <Badge variant={candidate.expected_outperformance_vs_spy.includes('+') ? 'success' : candidate.expected_outperformance_vs_spy.includes('-') ? 'destructive' : 'neutral'} className="text-[9px] h-4">
                      vs SPY: {candidate.expected_outperformance_vs_spy.split(' ')[0]}
                    </Badge>
                  )}
                </div>
                <span className="text-muted-foreground text-xs leading-normal">{candidate.rationale}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Event Calendar */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
            <Calendar className="h-4 w-4" /> Event Calendar
          </h4>
          <div className="space-y-1 bg-muted/30 p-2 rounded-md border">
            {(data.event_calendar || []).map((event, i) => (
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

        {/* Confidence Notes */}
        {data.confidence_notes && (
          <div className="space-y-2 border-t pt-4">
            <h4 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground">
              <ShieldAlert className="h-4 w-4" /> Confidence & Caveats
            </h4>
            <div className="bg-yellow-500/5 border border-yellow-500/20 p-3 rounded-md text-xs space-y-2">
              {data.confidence_notes.known_unknowns && (
                <div>
                  <span className="font-semibold text-yellow-600 dark:text-yellow-400">Known Unknowns:</span>
                  <p className="text-muted-foreground mt-0.5">{data.confidence_notes.known_unknowns}</p>
                </div>
              )}
              {data.confidence_notes.data_quality_flags && data.confidence_notes.data_quality_flags.length > 0 && (
                <div>
                  <span className="font-semibold text-yellow-600 dark:text-yellow-400">Data Flags:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {data.confidence_notes.data_quality_flags.map((flag, i) => (
                      <Badge key={i} variant="outline" className="text-[9px] bg-background/50">
                        {flag.replace(/_/g, ' ')}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

      </CardContent>
      <div className="p-4 pt-3 mt-auto flex gap-2 border-t bg-card sticky bottom-0 z-10">
        <Button className="w-full h-8 text-xs" variant="outline" size="sm">
          <RefreshCw className="h-3 w-3 mr-2" /> Regenerate
        </Button>
        <Button className="w-full h-8 text-xs" size="sm">
          <CheckCircle className="h-3 w-3 mr-2" /> Verify
        </Button>
      </div>
    </Card>
  );
}

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
  )
}

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Play, CheckCircle, XCircle, RefreshCw, AlertTriangle, Activity } from 'lucide-react';
import { mockCouncilDecision } from '../../../lib/mockData';

export default function CouncilTab() {
  const decision = mockCouncilDecision;

  return (
    <div className="space-y-6">
        <div className="flex justify-between items-center">
            <div>
                <h2 className="text-2xl font-bold tracking-tight">Council Decision</h2>
                <p className="text-muted-foreground">Chairman synthesis and final trade recommendation.</p>
            </div>
            <div className="flex items-center gap-2">
                <Badge variant="success">COMPLETE</Badge>
            </div>
        </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Decision Column */}
        <div className="lg:col-span-2 space-y-6">
            <Card className="border-primary/50 shadow-[0_0_15px_rgba(0,0,0,0.1)] shadow-primary/10">
                <CardHeader>
                    <div className="flex justify-between items-center">
                        <CardTitle className="flex items-center gap-2">
                            👑 Chairman's Synthesis
                        </CardTitle>
                        <Badge variant="outline">Claude Opus 4.5</Badge>
                    </div>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="p-4 border rounded-md bg-muted/30">
                        <h4 className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wider">Selected Trade</h4>
                        <div className="flex flex-wrap gap-6 items-end">
                            <div>
                                <div className="text-4xl font-bold">{decision.selected_trade.instrument}</div>
                                <div className="text-sm text-muted-foreground">Instrument</div>
                            </div>
                            <div>
                                <div className={`text-2xl font-bold ${decision.selected_trade.direction === 'LONG' ? 'text-green-500' : 'text-red-500'}`}>
                                    {decision.selected_trade.direction}
                                </div>
                                <div className="text-sm text-muted-foreground">Direction</div>
                            </div>
                             <div>
                                <div className="text-2xl font-bold">
                                    {decision.selected_trade.conviction > 0 ? '+' : ''}{decision.selected_trade.conviction}
                                </div>
                                <div className="text-sm text-muted-foreground">Conviction</div>
                            </div>
                             <div>
                                <div className="text-2xl font-bold font-mono">
                                    {decision.selected_trade.position_size}
                                </div>
                                <div className="text-sm text-muted-foreground">Size</div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h4 className="text-sm font-semibold text-muted-foreground">RATIONALE</h4>
                        <p className="leading-relaxed">{decision.rationale}</p>
                    </div>

                    <div className="space-y-2">
                        <h4 className="text-sm font-semibold text-muted-foreground">MONITORING PLAN</h4>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-3 bg-muted/50 rounded text-sm">
                                <div className="font-medium mb-1">Key Levels</div>
                                <ul className="list-disc list-inside text-muted-foreground">
                                    {decision.monitoring_plan.key_levels.map((level, i) => (
                                        <li key={i}>{level}</li>
                                    ))}
                                </ul>
                            </div>
                            <div className="p-3 bg-muted/50 rounded text-sm">
                                <div className="font-medium mb-1">Event Risks</div>
                                <ul className="list-disc list-inside text-muted-foreground">
                                    {decision.monitoring_plan.event_risks.map((event, i) => (
                                        <li key={i}>{event}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

             <Card>
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-yellow-500" /> Dissenting Views
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <ul className="space-y-3">
                        {decision.dissent_summary.map((dissent, i) => (
                            <li key={i} className="flex gap-3 text-sm p-3 bg-yellow-500/5 border border-yellow-500/20 rounded-md">
                                <span className="text-yellow-500">•</span>
                                <span>{dissent}</span>
                            </li>
                        ))}
                    </ul>
                </CardContent>
            </Card>
        </div>

        {/* Sidebar Column */}
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Peer Review Scores</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {Object.entries(decision.peer_review_scores).map(([key, score]) => (
                        <div key={key} className="space-y-1">
                            <div className="flex justify-between text-sm">
                                <span className="capitalize">{key.replace('_', ' ')}</span>
                                <span className="font-mono font-medium">{score}/10</span>
                            </div>
                            <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                <div 
                                    className="h-full bg-primary" 
                                    style={{ width: `${score * 10}%` }}
                                />
                            </div>
                        </div>
                    ))}
                    <Button variant="ghost" size="sm" className="w-full mt-2">View Full Reviews</Button>
                </CardContent>
            </Card>

            <Card className="bg-muted/30">
                <CardContent className="p-6 space-y-4">
                    <h3 className="font-semibold text-center text-muted-foreground mb-4">Actions</h3>
                    <Button className="w-full" variant="outline">
                        <RefreshCw className="mr-2 h-4 w-4" /> Regenerate Decision
                    </Button>
                    <Button className="w-full bg-red-500/10 text-red-500 hover:bg-red-500/20 hover:text-red-400 border-red-500/20">
                        <XCircle className="mr-2 h-4 w-4" /> Reject Trade
                    </Button>
                    <Button className="w-full" size="lg">
                        <CheckCircle className="mr-2 h-4 w-4" /> Approve & Execute
                    </Button>
                </CardContent>
            </Card>
        </div>
      </div>
    </div>
  );
}

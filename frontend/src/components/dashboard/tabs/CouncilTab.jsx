import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Play, CheckCircle, XCircle, RefreshCw, AlertTriangle, Activity } from 'lucide-react';
import { tradingApi } from '../../../api/trading';

export default function CouncilTab() {
    const [decision, setDecision] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isReviewsOpen, setIsReviewsOpen] = useState(false);

    useEffect(() => {
        loadDecision();
    }, []);

    const loadDecision = async () => {
        try {
            setLoading(true);
            const data = await tradingApi.getCouncilDecision();
            // Ensure we have valid data before setting
            if (data && data.selected_trade) {
                setDecision(data);
            } else {
                setDecision(null);
            }
        } catch (err) {
            console.error("Failed to load council decision", err);
            setDecision(null);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <Activity className="h-8 w-8 animate-spin text-primary" />
                    <p className="text-muted-foreground">Loading council data...</p>
                </div>
            </div>
        );
    }

    if (!decision || !decision.selected_trade) {
        return (
            <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
                <div className="text-center p-12 border rounded-lg border-dashed max-w-lg">
                    <h3 className="text-lg font-semibold mb-2">No Council Decision Yet</h3>
                    <p className="text-muted-foreground mb-6">Run the research and PM stages first to generate a trading decision.</p>
                    <Button onClick={loadDecision} variant="outline">
                        <RefreshCw className="mr-2 h-4 w-4" /> Refresh Data
                    </Button>
                </div>
            </div>
        );
    }

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
                            {decision.peer_review_scores && Object.entries(decision.peer_review_scores).map(([key, score]) => (
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
                            <Button
                                variant="ghost"
                                size="sm"
                                className="w-full mt-2"
                                onClick={() => setIsReviewsOpen(true)}
                            >
                                View Full Reviews
                            </Button>
                        </CardContent>
                    </Card>

                    <Card className="bg-muted/30">
                        <CardContent className="p-6 space-y-4">
                            <h3 className="font-semibold text-center text-muted-foreground mb-4">Actions</h3>
                            <Button onClick={loadDecision} className="w-full" variant="outline">
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

            {/* Reviews Modal */}
            {isReviewsOpen && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-background border rounded-lg max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl">
                        <div className="p-6 border-b flex justify-between items-center bg-muted/10">
                            <div>
                                <h3 className="text-xl font-bold">Peer Reviews</h3>
                                <p className="text-sm text-muted-foreground">Detailed feedback from other PM models</p>
                            </div>
                            <Button variant="ghost" size="icon" onClick={() => setIsReviewsOpen(false)}>
                                <XCircle className="h-6 w-6 opacity-70 hover:opacity-100" />
                            </Button>
                        </div>
                        <div className="p-6 overflow-y-auto space-y-6">
                            {decision.peer_reviews && decision.peer_reviews.length > 0 ? (
                                decision.peer_reviews.map((review, i) => (
                                    <Card key={i} className="border-muted/60 hover:border-muted-foreground/30 transition-colors">
                                        <CardHeader className="pb-3 bg-muted/5">
                                            <div className="flex justify-between items-center">
                                                <CardTitle className="text-base font-semibold flex items-center gap-2">
                                                    Review by <Badge variant="outline" className="font-mono">{review.reviewer_model}</Badge>
                                                </CardTitle>
                                                <div className="flex items-center gap-2 text-sm">
                                                    <span className="text-muted-foreground">Avg Score:</span>
                                                    <span className="font-bold text-primary">{review.average_score}/10</span>
                                                </div>
                                            </div>
                                        </CardHeader>
                                        <CardContent className="space-y-4 pt-4 text-sm">
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-muted/30 p-4 rounded-lg">
                                                {Object.entries(review.scores).map(([k, v]) => (
                                                    <div key={k} className="flex flex-col gap-1">
                                                        <span className="text-xs text-muted-foreground uppercase tracking-wider">{k.replace('_', ' ')}</span>
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-mono font-bold">{v}</span>
                                                            <div className="h-1.5 flex-1 bg-secondary rounded-full overflow-hidden">
                                                                <div className="h-full bg-primary/70" style={{ width: `${v * 10}%` }} />
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>

                                            <div className="grid md:grid-cols-2 gap-6">
                                                <div className="space-y-2">
                                                    <span className="font-semibold text-red-400 block border-b border-red-500/10 pb-1">Argument Against</span>
                                                    <p className="text-muted-foreground leading-relaxed bg-red-500/5 p-3 rounded">{review.best_argument_against}</p>
                                                </div>
                                                <div className="space-y-2">
                                                    <span className="font-semibold text-yellow-500 block border-b border-yellow-500/10 pb-1">Suggested Fix</span>
                                                    <p className="text-muted-foreground leading-relaxed bg-yellow-500/5 p-3 rounded">{review.suggested_fix}</p>
                                                </div>
                                            </div>

                                            <div className="space-y-1">
                                                <span className="font-semibold text-blue-400 text-xs uppercase tracking-wider">Flip Condition</span>
                                                <p className="text-muted-foreground italic pl-3 border-l-2 border-blue-500/30">"{review.one_flip_condition}"</p>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))
                            ) : (
                                <div className="text-center py-12 text-muted-foreground">
                                    <AlertTriangle className="h-12 w-12 mx-auto mb-4 opacity-20" />
                                    <p>No detailed reviews available for this decision.</p>
                                </div>
                            )}
                        </div>
                        <div className="p-4 border-t bg-muted/10 flex justify-end">
                            <Button variant="outline" onClick={() => setIsReviewsOpen(false)}>Close</Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

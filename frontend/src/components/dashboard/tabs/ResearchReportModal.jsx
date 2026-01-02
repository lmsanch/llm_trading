import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { X, Calendar, TrendingUp, FileText } from 'lucide-react';

export function ResearchReportModal({ report, onClose }) {
    if (!report) return null;

    const structuredData = report.structured_json || {};
    const assetSetups = structuredData.asset_setups || structuredData.tradable_candidates || [];
    const eventCalendar = structuredData.event_calendar || [];

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-background border-2 border-border rounded-2xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-6 border-b bg-muted/30 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <Calendar className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold">Research Report</h2>
                            <p className="text-sm text-muted-foreground">
                                {report.provider?.toUpperCase()} • {new Date(report.created_at).toLocaleDateString()}
                            </p>
                        </div>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onClose}
                        className="h-8 w-8 p-0 rounded-full hover:bg-destructive/10"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {/* Natural Language Report */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base flex items-center gap-2">
                                <FileText className="h-4 w-4" />
                                Full Analysis
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="prose prose-sm max-w-none">
                                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground/90 bg-muted/50 p-4 rounded-lg border">
                                    {report.natural_language}
                                </pre>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Asset Setups */}
                    {assetSetups.length > 0 && (
                        <Card>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-base flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4" />
                                    Asset Setups ({assetSetups.length})
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    {assetSetups.slice(0, 5).map((setup, i) => (
                                        <div key={i} className="border rounded-lg p-3 bg-muted/30">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="font-bold text-primary">{setup.ticker}</span>
                                                {setup.expected_outperformance_bucket_vs_spy && (
                                                    <Badge variant={
                                                        setup.expected_outperformance_bucket_vs_spy === 'STRONG' ? 'success' :
                                                            setup.expected_outperformance_bucket_vs_spy === 'NEGATIVE' ? 'destructive' : 'neutral'
                                                    } className="text-xs">
                                                        {setup.expected_outperformance_bucket_vs_spy}
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                                {setup.thesis_this_week || (setup.this_week_drivers && setup.this_week_drivers.join(', ')) || 'No description'}
                                            </p>
                                            {setup.scenario_map && setup.scenario_map.length > 0 && (
                                                <div className="mt-2 space-y-1">
                                                    {setup.scenario_map.slice(0, 2).map((scenario, idx) => (
                                                        <div key={idx} className="text-[10px] text-muted-foreground flex items-center gap-2">
                                                            <span className="font-mono bg-background px-1.5 py-0.5 rounded">{scenario.if}</span>
                                                            <span>→</span>
                                                            <Badge variant={scenario.expected_vs_spy === 'STRONG' ? 'success' : scenario.expected_vs_spy === 'NEGATIVE' ? 'destructive' : 'neutral'} className="text-[8px] h-4">
                                                                {scenario.expected_vs_spy}
                                                            </Badge>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Event Calendar */}
                    {eventCalendar.length > 0 && (
                        <Card>
                            <CardHeader className="pb-3">
                                <CardTitle className="text-base flex items-center gap-2">
                                    <Calendar className="h-4 w-4" />
                                    Upcoming Events ({eventCalendar.length})
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-2">
                                    {eventCalendar.slice(0, 5).map((event, i) => (
                                        <div key={i} className="flex items-center justify-between text-xs border-b pb-2 last:border-0">
                                            <div className="flex-1">
                                                <span className="font-medium">{event.event}</span>
                                                <span className="text-muted-foreground ml-2">• {event.date}</span>
                                            </div>
                                            <Badge variant="outline" className={`text-[9px] h-4 ${event.impact === 'CRITICAL' ? 'border-red-500/50 text-red-500' :
                                                    event.impact === 'HIGH' ? 'border-orange-500/50 text-orange-500' :
                                                        'border-yellow-500/50 text-yellow-500'
                                                }`}>
                                                {event.impact}
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t bg-muted/30 flex justify-between items-center">
                    <div className="text-xs text-muted-foreground">
                        Model: {report.model} • Status: {report.status}
                    </div>
                    <Button onClick={onClose} className="rounded-xl">
                        Close
                    </Button>
                </div>
            </div>
        </div>
    );
}

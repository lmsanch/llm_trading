import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from "../../../lib/utils";

export function PMPitchCard({ pitch }) {
    const [isExpanded, setIsExpanded] = useState(false);

    const getConvictionColor = (score) => {
        if (score >= 1.5) return "text-green-500";
        if (score > 0) return "text-green-400";
        if (score === 0) return "text-blue-400";
        if (score > -1.5) return "text-red-400";
        return "text-red-500";
    };

    const getConvictionLabel = (score) => {
        if (score >= 1.5) return "Strong Long";
        if (score > 0) return "Long";
        if (score === 0) return "Neutral";
        if (score > -1.5) return "Short";
        return "Strong Short";
    }

    const getLogoPath = (model) => {
        if (!model) return null;
        const m = model.toLowerCase();
        if (m.includes('gpt') || m.includes('chatgpt')) return '/logos/openai.png';
        if (m.includes('gemini')) return '/logos/google.png';
        if (m.includes('claude')) return '/logos/anthropic.png';
        if (m.includes('grok') || m.includes('groq')) return '/logos/xai.png';
        if (m.includes('deepseek')) return '/logos/deepseek.png';
        if (m.includes('mistral')) return '/logos/mistral_ai.png';
        if (m.includes('llama')) return '/logos/meta.png';
        if (m.includes('qwen')) return '/logos/alibaba.jpg';
        if (m.includes('phi')) return '/logos/microsoft.png';
        if (m.includes('zhipu')) return '/logos/zhipu.png';
        if (m.includes('moonshot')) return '/logos/moonshot.png';
        return null;
    };

    const getModelDisplayName = (model) => {
        const m = (model || '').toLowerCase();
        if (m.includes('gpt') || m.includes('chatgpt')) return 'GPT-5.1';
        if (m.includes('gemini')) return 'Gemini 3 Pro';
        if (m.includes('claude')) return 'Claude Sonnet 4.5';
        if (m.includes('grok') || m.includes('groq')) return 'Grok 4';
        if (m.includes('deepseek')) return 'DeepSeek V3';
        return model;
    };

    const logoPath = getLogoPath(pitch.model);
    const displayName = getModelDisplayName(pitch.model);
    const instrument = pitch.selected_instrument || pitch.instrument || 'N/A';
    const firstThesisBullet = pitch.thesis_bullets && pitch.thesis_bullets[0] ? pitch.thesis_bullets[0] : 'No thesis provided';

    return (
        <Card className="flex flex-col hover:shadow-lg transition-shadow">
            <CardHeader className="pb-3 cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
                <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3 flex-1">
                        {logoPath && (
                            <div className="w-12 h-12 rounded-lg bg-white/90 dark:bg-gray-800 flex items-center justify-center p-2 shadow-sm border">
                                <img
                                    src={logoPath}
                                    alt={displayName}
                                    className="w-full h-full object-contain"
                                />
                            </div>
                        )}
                        <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                                <h2 className="text-2xl font-bold tracking-tight">{instrument}</h2>
                                <span className={cn(
                                    "text-lg font-bold",
                                    pitch.direction === 'LONG' ? 'text-green-500' :
                                        pitch.direction === 'SHORT' ? 'text-red-500' : 'text-blue-500'
                                )}>
                                    {pitch.direction}
                                </span>
                            </div>
                            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                                {displayName}
                            </CardTitle>
                            <div className="text-xs text-muted-foreground uppercase font-mono mt-0.5">
                                {pitch.account}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex flex-col items-end">
                            <span className="text-lg font-bold text-white tabular-nums">
                                {pitch.conviction > 0 ? '+' : ''}{pitch.conviction.toFixed(1)}
                            </span>
                        </div>
                        <div className="ml-2">
                            {isExpanded ?
                                <ChevronUp className="h-5 w-5 text-muted-foreground" /> :
                                <ChevronDown className="h-5 w-5 text-muted-foreground" />
                            }
                        </div>
                    </div>
                </div>

                {/* Summary view (when collapsed) */}
                {!isExpanded && (
                    <div className="mt-3 pt-3 border-t">
                        <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                            {firstThesisBullet}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                            <span className="text-xs text-muted-foreground">Horizon:</span>
                            <Badge variant="outline" className="text-xs">{pitch.horizon}</Badge>
                            <span className="text-xs text-muted-foreground ml-2">
                                {pitch.thesis_bullets ? pitch.thesis_bullets.length : 0} thesis points
                            </span>
                            {pitch.timestamp && (
                                <span className="text-[10px] text-muted-foreground ml-auto">
                                    {new Date(pitch.timestamp).toLocaleDateString()}
                                </span>
                            )}
                        </div>
                    </div>
                )}
            </CardHeader>

            {/* Expanded view */}
            {isExpanded && (
                <>
                    <CardContent className="space-y-4 flex-1 pt-0">
                        <div className="flex gap-4 text-sm font-medium border-b pb-3">
                            <div className="flex flex-col">
                                <span className="text-muted-foreground text-xs">Instrument</span>
                                <span className="font-bold">{instrument}</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-muted-foreground text-xs">Direction</span>
                                <span className={cn(
                                    "font-bold",
                                    pitch.direction === 'LONG' ? 'text-green-500' :
                                        pitch.direction === 'SHORT' ? 'text-red-500' : 'text-blue-500'
                                )}>{pitch.direction}</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-muted-foreground text-xs">Horizon</span>
                                <span className="font-bold">{pitch.horizon}</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-muted-foreground text-xs">Conviction</span>
                                <span className={cn("font-bold", getConvictionColor(pitch.conviction))}>
                                    {getConvictionLabel(pitch.conviction)}
                                </span>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Thesis</h4>
                            <ul className="space-y-2">
                                {pitch.thesis_bullets && pitch.thesis_bullets.map((bullet, i) => (
                                    <li key={i} className="flex gap-2 text-sm leading-relaxed">
                                        <span className="text-primary font-bold mt-0.5">{i + 1}.</span>
                                        <span className="flex-1">{bullet}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {pitch.exit_policy && (
                            <div className="p-3 bg-purple-500/5 border border-purple-500/20 rounded-md text-sm">
                                <span className="font-semibold text-purple-500">Risk Profile: {pitch.risk_profile || 'BASE'}</span>
                                <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-muted-foreground">
                                    <div><span className="font-medium">Stop Loss:</span> {(pitch.exit_policy.stop_loss_pct * 100).toFixed(2)}%</div>
                                    <div><span className="font-medium">Take Profit:</span> {pitch.exit_policy.take_profit_pct ? (pitch.exit_policy.take_profit_pct * 100).toFixed(2) + '%' : 'N/A'}</div>
                                    <div><span className="font-medium">Time Stop:</span> {pitch.exit_policy.time_stop_days || 7} days</div>
                                    <div><span className="font-medium">Entry:</span> {pitch.entry_policy?.mode || 'MOO'}</div>
                                </div>
                                {pitch.exit_policy.exit_before_events && pitch.exit_policy.exit_before_events.length > 0 && (
                                    <div className="mt-2 pt-2 border-t border-purple-500/20">
                                        <span className="font-medium text-purple-400">Exit Before: </span>
                                        <span>{pitch.exit_policy.exit_before_events.join(', ')}</span>
                                    </div>
                                )}
                            </div>
                        )}

                        {pitch.entry_policy?.mode === 'limit' && pitch.entry_policy.limit_price && (
                            <div className="p-3 bg-blue-500/5 border border-blue-500/20 rounded-md text-sm">
                                <span className="font-semibold text-blue-500">Limit Entry:</span>
                                <span className="ml-2 text-muted-foreground">${pitch.entry_policy.limit_price.toFixed(2)}</span>
                            </div>
                        )}

                        {pitch.risk_notes && pitch.risk_notes !== 'N/A' && (
                            <div className="p-3 bg-yellow-500/5 border border-yellow-500/20 rounded-md text-sm">
                                <span className="font-semibold text-yellow-500">Risk Notes:</span>
                                <p className="mt-1 text-muted-foreground">{pitch.risk_notes}</p>
                            </div>
                        )}
                    </CardContent>
                </>
            )}
        </Card>
    );
}

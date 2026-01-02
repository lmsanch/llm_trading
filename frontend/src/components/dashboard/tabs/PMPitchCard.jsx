import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { cn } from "../../../lib/utils";

export function PMPitchCard({ pitch }) {
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
        if (m.includes('gpt')) return '/logos/openai.png';
        if (m.includes('gemini')) return '/logos/google.png';
        if (m.includes('claude')) return '/logos/anthropic.png';
        if (m.includes('grok')) return '/logos/xai.png';
        if (m.includes('deepseek')) return '/logos/deepseek.png';
        if (m.includes('mistral')) return '/logos/mistral_ai.png';
        if (m.includes('llama')) return '/logos/meta.png';
        if (m.includes('qwen')) return '/logos/alibaba.jpg';
        if (m.includes('phi')) return '/logos/microsoft.png';
        if (m.includes('zhipu')) return '/logos/zhipu.png';
        if (m.includes('moonshot')) return '/logos/moonshot.png';
        return null;
    };

    const logoPath = getLogoPath(pitch.model);

    return (
        <Card className="flex flex-col">
            <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="text-lg flex items-center gap-2">
                            {logoPath && (
                                <img
                                    src={logoPath}
                                    alt={pitch.model}
                                    className="h-6 w-6 rounded-full object-contain bg-white/50"
                                />
                            )}
                            {pitch.model}
                        </CardTitle>
                        <div className="text-xs text-muted-foreground uppercase font-mono mt-1">
                            Account: {pitch.account}
                        </div>
                    </div>
                    <div className="flex flex-col items-end">
                        <span className={cn("text-2xl font-bold", getConvictionColor(pitch.conviction))}>
                            {pitch.conviction > 0 ? '+' : ''}{pitch.conviction}
                        </span>
                        <span className="text-xs text-muted-foreground">{getConvictionLabel(pitch.conviction)}</span>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-4 flex-1">
                <div className="flex gap-4 text-sm font-medium border-b pb-2">
                    <div className="flex flex-col">
                        <span className="text-muted-foreground text-xs">Instrument</span>
                        <span>{pitch.instrument}</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-muted-foreground text-xs">Direction</span>
                        <span className={cn(
                            pitch.direction === 'LONG' ? 'text-green-500' :
                                pitch.direction === 'SHORT' ? 'text-red-500' : 'text-blue-500'
                        )}>{pitch.direction}</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-muted-foreground text-xs">Horizon</span>
                        <span>{pitch.horizon}</span>
                    </div>
                </div>

                <div className="space-y-1">
                    <h4 className="text-xs font-semibold text-muted-foreground">THESIS</h4>
                    <ul className="list-disc list-inside text-sm space-y-1">
                        {pitch.thesis_bullets.map((bullet, i) => (
                            <li key={i} className="leading-tight">{bullet}</li>
                        ))}
                    </ul>
                </div>

                <div className="space-y-1">
                    <h4 className="text-xs font-semibold text-muted-foreground">INDICATORS</h4>
                    <div className="flex flex-wrap gap-2">
                        {pitch.indicators.map((ind, i) => (
                            <Badge key={i} variant="secondary" className="text-xs font-normal">
                                {ind}
                            </Badge>
                        ))}
                    </div>
                </div>

                {pitch.invalidation !== "N/A" && (
                    <div className="p-2 bg-muted/30 rounded text-xs text-muted-foreground">
                        <span className="font-semibold text-red-400">Invalidation:</span> {pitch.invalidation}
                    </div>
                )}

            </CardContent>
            <CardFooter className="flex justify-between pt-4 gap-2">
                <Button variant="ghost" size="icon" title="Regenerate">
                    <RefreshCw className="h-4 w-4" />
                </Button>
                <div className="flex gap-2 w-full">
                    <Button variant="outline" className="flex-1 text-red-500 hover:text-red-600 hover:bg-red-500/10">
                        <XCircle className="h-4 w-4 mr-2" /> Reject
                    </Button>
                    <Button variant="outline" className="flex-1 text-green-500 hover:text-green-600 hover:bg-green-500/10">
                        <CheckCircle className="h-4 w-4 mr-2" /> Approve
                    </Button>
                </div>
            </CardFooter>
        </Card>
    );
}

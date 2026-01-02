import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "../ui/Card";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { Save, Eye, EyeOff, Check, Key } from 'lucide-react';

export default function SettingsTab() {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">System Settings</h2>
        <p className="text-muted-foreground">Manage pipeline configuration, API keys, and models.</p>
      </div>

      <div className="grid gap-6">
        {/* Pipeline Config */}
        <Card>
            <CardHeader>
                <CardTitle>Pipeline Configuration</CardTitle>
                <CardDescription>Schedule and automation settings.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Weekly Pipeline Start</label>
                        <div className="p-3 border rounded-md bg-muted/50 text-sm">
                            Wednesday 08:00 ET
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Checkpoint Schedule</label>
                        <div className="p-3 border rounded-md bg-muted/50 text-sm">
                            09:00, 12:00, 14:00, 15:50 ET
                        </div>
                    </div>
                    <div className="space-y-2">
                         <label className="text-sm font-medium">Default Mode</label>
                         <div className="flex gap-2">
                             <Button variant="secondary" size="sm" className="w-24">Manual</Button>
                             <Button variant="ghost" size="sm" className="w-24">Auto</Button>
                         </div>
                    </div>
                </div>
            </CardContent>
        </Card>

        {/* API Keys */}
        <Card>
            <CardHeader>
                <CardTitle>API Keys & Connections</CardTitle>
                <CardDescription>Manage external service connections.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                 <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 border rounded-md">
                        <div className="flex items-center gap-3">
                            <Key className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium text-sm">Requesty API</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <code className="bg-muted px-2 py-1 rounded text-xs">sk-...892a</code>
                            <Badge variant="success" className="h-6">Connected</Badge>
                        </div>
                    </div>
                    <div className="flex items-center justify-between p-3 border rounded-md">
                         <div className="flex items-center gap-3">
                            <Key className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium text-sm">Alpaca Trading</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">6 accounts</span>
                            <Badge variant="success" className="h-6">Active</Badge>
                        </div>
                    </div>
                    <div className="flex items-center justify-between p-3 border rounded-md">
                         <div className="flex items-center gap-3">
                            <Key className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium text-sm">Database</span>
                        </div>
                         <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">PostgreSQL</span>
                            <Badge variant="success" className="h-6">Connected</Badge>
                        </div>
                    </div>
                 </div>
            </CardContent>
        </Card>

        {/* Models */}
        <Card>
            <CardHeader>
                <CardTitle>AI Models</CardTitle>
                <CardDescription>Configuration for the Council models.</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 border rounded-md">
                        <div className="font-semibold mb-2 text-sm">Portfolio Managers</div>
                        <ul className="text-sm text-muted-foreground space-y-1">
                            <li>• GPT-5.2</li>
                            <li>• Gemini 3 Pro</li>
                            <li>• Claude Sonnet 4.5</li>
                            <li>• Grok 4.1</li>
                            <li>• DeepSeek V3</li>
                        </ul>
                    </div>
                     <div className="p-4 border rounded-md">
                        <div className="font-semibold mb-2 text-sm">Chairman & Research</div>
                        <ul className="text-sm text-muted-foreground space-y-1">
                            <li>• Claude Opus 4.5 (Chairman)</li>
                            <li>• Gemini 2.0 Flash (Research)</li>
                            <li>• Perplexity Sonar (Research)</li>
                        </ul>
                    </div>
                </div>
            </CardContent>
        </Card>

        <div className="flex justify-end gap-2">
            <Button variant="outline">Discard Changes</Button>
            <Button>
                <Save className="mr-2 h-4 w-4" /> Save Configuration
            </Button>
        </div>
      </div>
    </div>
  );
}

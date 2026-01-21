import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "../ui/Card";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { Select } from "../ui/Select";
import { Save, Eye, EyeOff, Check, Key, Search, Loader2 } from 'lucide-react';

export default function SettingsTab() {
  const [searchSettings, setSearchSettings] = useState({
    default_provider: 'tavily',
    enable_jina_reader: true,
    max_results: 10,
    providers: {
      tavily: { enabled: true },
      brave: { enabled: true },
    },
  });
  const [isLoading, setIsLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  useEffect(() => {
    loadSearchSettings();
  }, []);

  const loadSearchSettings = async () => {
    try {
      const response = await fetch('/api/search/settings');
      const data = await response.json();
      setSearchSettings(data);
    } catch (error) {
      console.error('Failed to load search settings:', error);
    }
  };

  const saveSearchSettings = async () => {
    setIsLoading(true);
    setSaveStatus(null);
    try {
      const response = await fetch('/api/search/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchSettings),
      });

      if (response.ok) {
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        throw new Error('Failed to save');
      }
    } catch (error) {
      console.error('Failed to save search settings:', error);
      setSaveStatus('error');
    } finally {
      setIsLoading(false);
    }
  };

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

        {/* Search Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Search Settings</CardTitle>
            <CardDescription>Configure web search providers for market sentiment.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Search Provider</label>
                <Select
                  className="w-full"
                  value={searchSettings.default_provider}
                  onChange={(e) => setSearchSettings(prev => ({ ...prev, default_provider: e.target.value }))}
                >
                  <option value="tavily">Tavily</option>
                  <option value="brave">Brave</option>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Max Results</label>
                <input
                  type="number"
                  min="5"
                  max="50"
                  className="w-full p-2 border rounded-md"
                  value={searchSettings.max_results}
                  onChange={(e) => setSearchSettings(prev => ({ ...prev, max_results: parseInt(e.target.value) }))}
                />
              </div>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-md">
              <div className="flex items-center gap-3">
                <Search className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm">Jina Reader (Full Article Content)</span>
              </div>
              <div className="flex items-center gap-2">
                {searchSettings.enable_jina_reader ? (
                  <Check className="h-5 w-5 text-green-500" />
                ) : (
                  <EyeOff className="h-5 w-5 text-muted-foreground" />
                )}
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={searchSettings.enable_jina_reader}
                    onChange={(e) => setSearchSettings(prev => ({ ...prev, enable_jina_reader: e.target.checked }))}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 peer-checked:after:translate-x-full"></div>
                </label>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Provider Status</label>
              <div className="space-y-2">
                <div className="flex items-center justify-between p-2 border rounded-md">
                  <span className="text-sm">Tavily</span>
                  <Badge variant={searchSettings.providers.tavily?.enabled ? 'success' : 'secondary'}>
                    {searchSettings.providers.tavily?.enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-2 border rounded-md">
                  <span className="text-sm">Brave</span>
                  <Badge variant={searchSettings.providers.brave?.enabled ? 'success' : 'secondary'}>
                    {searchSettings.providers.brave?.enabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

            <div className="flex justify-end gap-2">
            {saveStatus === 'success' && (
              <Badge variant="success" className="mr-2">Saved!</Badge>
            )}
            {saveStatus === 'error' && (
              <Badge variant="destructive" className="mr-2">Failed</Badge>
            )}
            <Button variant="outline" onClick={() => {
              loadSearchSettings();
              setSaveStatus(null);
            }}>
              Discard Changes
            </Button>
            <Button onClick={saveSearchSettings} disabled={isLoading}>
                {isLoading ? (
                    <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Saving...
                    </>
                ) : (
                    <>
                        <Save className="mr-2 h-4 w-4" />
                        Save Configuration
                    </>
                )}
            </Button>
        </div>
      </div>
    </div>
  );
}

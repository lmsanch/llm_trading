import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Play, History, RefreshCw, TrendingUp, Wallet, Clock } from 'lucide-react';
import { tradingApi } from '../../../api/trading';
import { cn } from "../../../lib/utils";

export default function MonitorTab() {
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [loadingPositions, setLoadingPositions] = useState(true);
  const [accounts, setAccounts] = useState([]);
  const [positions, setPositions] = useState([]);
  const [error, setError] = useState(null);
  const [lastRefreshTime, setLastRefreshTime] = useState(null);

  const fetchAccounts = async () => {
    try {
      setLoadingAccounts(true);
      setError(null);
      const data = await tradingApi.getAccounts();
      setAccounts(data);
    } catch (err) {
      setError('Failed to load accounts');
      console.error('Error fetching accounts:', err);
    } finally {
      setLoadingAccounts(false);
    }
  };

  const fetchPositions = async () => {
    try {
      setLoadingPositions(true);
      setError(null);
      const data = await tradingApi.getPositions();
      setPositions(data);
    } catch (err) {
      setError('Failed to load positions');
      console.error('Error fetching positions:', err);
    } finally {
      setLoadingPositions(false);
    }
  };

  const handleRefresh = () => {
    fetchAccounts();
    fetchPositions();
    setLastRefreshTime(new Date());
  };

  // Initial data fetch
  useEffect(() => {
    fetchAccounts();
    fetchPositions();
    setLastRefreshTime(new Date());
  }, []);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      handleRefresh();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, []);

  // Format last refresh time
  const formatLastRefresh = () => {
    if (!lastRefreshTime) return 'Never';
    const now = new Date();
    const diffSeconds = Math.floor((now - lastRefreshTime) / 1000);
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    return `${diffMinutes}m ago`;
  };

  const isRefreshing = loadingAccounts || loadingPositions;

  return (
    <div className="space-y-6">
       <div className="flex justify-between items-center">
            <div>
                <h2 className="text-2xl font-bold tracking-tight">Portfolio Monitor</h2>
                <p className="text-muted-foreground">
                  Live positions and account health.
                  <span className="ml-2 text-xs">
                    <Badge variant="outline" className="ml-2">
                      Auto-refresh: ON
                    </Badge>
                    {lastRefreshTime && (
                      <span className="ml-2 text-muted-foreground">
                        Last updated: {formatLastRefresh()}
                      </span>
                    )}
                  </span>
                </p>
            </div>
            <Button variant="outline" onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshCw className={cn("mr-2 h-4 w-4", isRefreshing && "animate-spin")} />
                {isRefreshing ? 'Refreshing...' : 'Refresh Data'}
            </Button>
        </div>

      {/* Account Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {loadingAccounts ? (
          // Skeleton cards
          Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="flex justify-between items-start mb-2">
                  <div className="h-3 w-20 bg-muted animate-pulse rounded"></div>
                  <div className="h-4 w-4 bg-muted animate-pulse rounded"></div>
                </div>
                <div className="h-8 w-32 bg-muted animate-pulse rounded mb-1"></div>
                <div className="h-4 w-24 bg-muted animate-pulse rounded"></div>
              </CardContent>
            </Card>
          ))
        ) : (
          // Real account cards
          accounts.map((acc, i) => (
            <Card key={i}>
                <CardContent className="pt-6">
                    <div className="flex justify-between items-start mb-2">
                        <div className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                            {acc.name}
                        </div>
                        <Wallet className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="text-2xl font-bold mb-1">
                        ${acc.equity.toLocaleString()}
                    </div>
                    <div className={cn("text-xs font-medium flex items-center", acc.pl >= 0 ? "text-green-500" : "text-red-500")}>
                        {acc.pl >= 0 ? '+' : ''}${acc.pl} Today
                    </div>
                </CardContent>
            </Card>
          ))
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Positions Table */}
        <div className="lg:col-span-2 space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
                <TrendingUp className="h-5 w-5" /> Live Positions
            </h3>
            <div className="rounded-md border bg-card">
                <div className="grid grid-cols-6 gap-4 p-3 font-medium text-sm bg-muted/50 border-b">
                    <div>Account</div>
                    <div>Symbol</div>
                    <div className="text-right">Qty</div>
                    <div className="text-right">Avg Price</div>
                    <div className="text-right">Current</div>
                    <div className="text-right">P/L</div>
                </div>
                {loadingPositions ? (
                  // Skeleton rows
                  Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="grid grid-cols-6 gap-4 p-3 text-sm items-center border-b last:border-0">
                      <div className="h-4 w-16 bg-muted animate-pulse rounded"></div>
                      <div className="h-4 w-12 bg-muted animate-pulse rounded"></div>
                      <div className="h-4 w-8 bg-muted animate-pulse rounded ml-auto"></div>
                      <div className="h-4 w-16 bg-muted animate-pulse rounded ml-auto"></div>
                      <div className="h-4 w-16 bg-muted animate-pulse rounded ml-auto"></div>
                      <div className="h-4 w-12 bg-muted animate-pulse rounded ml-auto"></div>
                    </div>
                  ))
                ) : (
                  <>
                    {positions.map((pos, i) => (
                      <div key={i} className="grid grid-cols-6 gap-4 p-3 text-sm items-center hover:bg-muted/10 transition-colors border-b last:border-0">
                          <div className="font-medium text-muted-foreground">{pos.account}</div>
                          <div className="font-bold">{pos.symbol}</div>
                          <div className="text-right font-mono">{pos.qty}</div>
                          <div className="text-right text-muted-foreground">${pos.avg_price.toFixed(2)}</div>
                          <div className="text-right font-medium">${pos.current_price.toFixed(2)}</div>
                          <div className={cn("text-right font-medium", pos.pl >= 0 ? "text-green-500" : "text-red-500")}>
                              {pos.pl >= 0 ? '+' : ''}${pos.pl}
                          </div>
                      </div>
                    ))}
                    {positions.length === 0 && (
                      <div className="text-center py-8 text-muted-foreground">No active positions.</div>
                    )}
                  </>
                )}
            </div>
        </div>

        {/* Checkpoints & Schedule */}
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Clock className="h-5 w-5" /> Checkpoints
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-3">
                        <div className="flex justify-between items-center text-sm">
                            <span className="text-muted-foreground">09:00 ET</span>
                            <Badge variant="success">COMPLETE</Badge>
                        </div>
                        <div className="flex justify-between items-center text-sm p-2 bg-muted/50 rounded">
                            <div className="flex items-center gap-2">
                                <span className="font-medium">12:00 ET</span>
                                <span className="text-xs text-muted-foreground">(Current)</span>
                            </div>
                            <Badge variant="warning" className="animate-pulse">PENDING</Badge>
                        </div>
                         <div className="flex justify-between items-center text-sm">
                            <span className="text-muted-foreground">14:00 ET</span>
                            <span className="text-muted-foreground text-xs">Scheduled</span>
                        </div>
                         <div className="flex justify-between items-center text-sm">
                            <span className="text-muted-foreground">15:50 ET</span>
                            <span className="text-muted-foreground text-xs">Scheduled</span>
                        </div>
                    </div>
                    
                    <div className="pt-4 space-y-2">
                        <Button className="w-full">
                            <Play className="mr-2 h-4 w-4" /> Run Checkpoint Now
                        </Button>
                        <Button variant="ghost" className="w-full" size="sm">
                            <History className="mr-2 h-4 w-4" /> View History
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
      </div>
    </div>
  );
}

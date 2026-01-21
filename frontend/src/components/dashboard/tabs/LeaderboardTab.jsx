import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Trophy, TrendingUp, TrendingDown, Award, RefreshCw } from 'lucide-react';
import { cn } from "../../../lib/utils";

export default function LeaderboardTab() {
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timePeriod, setTimePeriod] = useState('all'); // 'all', '4w', '8w'
  const [error, setError] = useState(null);

  const fetchLeaderboard = async (weeks = null) => {
    setLoading(true);
    setError(null);

    try {
      const url = weeks
        ? `http://localhost:8200/api/leaderboard?weeks=${weeks}`
        : 'http://localhost:8200/api/leaderboard';

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setLeaderboardData(data);
    } catch (err) {
      console.error('Failed to fetch leaderboard:', err);
      setError(err.message);
      // Optionally set mock data as fallback
      setLeaderboardData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Map time period to weeks parameter
    const weeksMap = {
      'all': null,
      '4w': 4,
      '8w': 8
    };
    fetchLeaderboard(weeksMap[timePeriod]);
  }, [timePeriod]);

  // Helper to format percentage
  const formatPct = (val) => {
    const pct = val * 100; // Convert decimal to percentage
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  };

  // Helper to format Sharpe ratio
  const formatSharpe = (val) => {
    return val.toFixed(2);
  };

  // Helper to get badge variant for rank
  const getRankBadge = (rank) => {
    if (rank === 1) return { variant: 'default', icon: <Trophy className="h-3 w-3" /> };
    if (rank === 2) return { variant: 'secondary', icon: <Award className="h-3 w-3" /> };
    if (rank === 3) return { variant: 'secondary', icon: <Award className="h-3 w-3" /> };
    return { variant: 'outline', icon: null };
  };

  // Helper to get color for return
  const getReturnColor = (val) => {
    if (val > 0) return 'text-green-600 dark:text-green-400';
    if (val < 0) return 'text-red-600 dark:text-red-400';
    return 'text-muted-foreground';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Model Performance Leaderboard</h2>
          <p className="text-muted-foreground">Cumulative performance rankings across all accounts.</p>
        </div>
        <Button variant="outline" onClick={() => fetchLeaderboard(timePeriod === 'all' ? null : timePeriod === '4w' ? 4 : 8)}>
          <RefreshCw className="mr-2 h-4 w-4" /> Refresh
        </Button>
      </div>

      {/* Time Period Filter */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground mr-2">Time Period:</span>
            <Button
              variant={timePeriod === '4w' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTimePeriod('4w')}
            >
              4 Weeks
            </Button>
            <Button
              variant={timePeriod === '8w' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTimePeriod('8w')}
            >
              8 Weeks
            </Button>
            <Button
              variant={timePeriod === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTimePeriod('all')}
            >
              All Time
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Leaderboard Table */}
      <Card>
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm flex items-center gap-2">
            <Trophy className="h-5 w-5 text-yellow-500" /> Performance Rankings
            {timePeriod === '4w' && <span className="text-xs text-muted-foreground font-normal ml-2">(Last 4 weeks)</span>}
            {timePeriod === '8w' && <span className="text-xs text-muted-foreground font-normal ml-2">(Last 8 weeks)</span>}
            {timePeriod === 'all' && <span className="text-xs text-muted-foreground font-normal ml-2">(All time)</span>}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          {error && (
            <div className="text-center py-8 text-red-500">
              <p>Error loading leaderboard: {error}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchLeaderboard(timePeriod === 'all' ? null : timePeriod === '4w' ? 4 : 8)}
                className="mt-4"
              >
                Retry
              </Button>
            </div>
          )}

          {!error && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-3 font-semibold">Rank</th>
                    <th className="text-left py-3 px-3 font-semibold">Account</th>
                    <th className="text-right py-3 px-3 font-semibold">Total Return</th>
                    <th className="text-right py-3 px-3 font-semibold">Sharpe Ratio</th>
                    <th className="text-right py-3 px-3 font-semibold">Max Drawdown</th>
                    <th className="text-right py-3 px-3 font-semibold">Win Rate</th>
                    <th className="text-center py-3 px-3 font-semibold">Weeks Traded</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    // Skeleton rows
                    Array.from({ length: 6 }).map((_, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-3 px-3">
                          <div className="h-5 w-8 bg-muted animate-pulse rounded"></div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="h-5 w-24 bg-muted animate-pulse rounded"></div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="h-5 w-16 bg-muted animate-pulse rounded ml-auto"></div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="h-5 w-12 bg-muted animate-pulse rounded ml-auto"></div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="h-5 w-16 bg-muted animate-pulse rounded ml-auto"></div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="h-5 w-12 bg-muted animate-pulse rounded ml-auto"></div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="h-5 w-8 bg-muted animate-pulse rounded mx-auto"></div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <>
                      {leaderboardData.map((entry) => {
                        const rankBadge = getRankBadge(entry.rank);
                        const returnColor = getReturnColor(entry.total_return);

                        return (
                          <tr
                            key={entry.account}
                            className={cn(
                              "border-b last:border-0 hover:bg-muted/10 transition-colors",
                              entry.rank === 1 && "bg-yellow-50/30 dark:bg-yellow-950/10"
                            )}
                          >
                            <td className="py-3 px-3">
                              <div className="flex items-center gap-2">
                                {rankBadge.icon}
                                <Badge variant={rankBadge.variant}>
                                  #{entry.rank}
                                </Badge>
                              </div>
                            </td>
                            <td className="py-3 px-3 font-bold">
                              {entry.account}
                            </td>
                            <td className={cn("py-3 px-3 text-right font-semibold", returnColor)}>
                              <div className="flex items-center justify-end gap-1">
                                {entry.total_return > 0 && <TrendingUp className="h-3 w-3" />}
                                {entry.total_return < 0 && <TrendingDown className="h-3 w-3" />}
                                {formatPct(entry.total_return)}
                              </div>
                            </td>
                            <td className="py-3 px-3 text-right font-mono">
                              {formatSharpe(entry.sharpe_ratio)}
                            </td>
                            <td className="py-3 px-3 text-right font-mono text-red-600 dark:text-red-400">
                              {formatPct(entry.max_drawdown)}
                            </td>
                            <td className="py-3 px-3 text-right font-mono">
                              {formatPct(entry.win_rate)}
                              <span className="text-xs text-muted-foreground ml-1">
                                ({entry.profitable_weeks}/{entry.weeks_traded})
                              </span>
                            </td>
                            <td className="py-3 px-3 text-center font-mono text-muted-foreground">
                              {entry.weeks_traded}
                            </td>
                          </tr>
                        );
                      })}
                      {leaderboardData.length === 0 && !loading && (
                        <tr>
                          <td colSpan="7" className="text-center py-8 text-muted-foreground">
                            No leaderboard data available yet.
                          </td>
                        </tr>
                      )}
                    </>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <Card>
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm">Metrics Explanation</CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <div className="font-semibold mb-1">Total Return</div>
              <p className="text-muted-foreground">
                Cumulative percentage return over the selected time period. Calculated from execution events.
              </p>
            </div>
            <div>
              <div className="font-semibold mb-1">Sharpe Ratio</div>
              <p className="text-muted-foreground">
                Risk-adjusted return metric. Higher values indicate better risk-adjusted performance. Values above 1.0 are considered good.
              </p>
            </div>
            <div>
              <div className="font-semibold mb-1">Max Drawdown</div>
              <p className="text-muted-foreground">
                Worst peak-to-trough decline during the period. Lower (more negative) values indicate larger losses from peak equity.
              </p>
            </div>
            <div>
              <div className="font-semibold mb-1">Win Rate</div>
              <p className="text-muted-foreground">
                Percentage of profitable weeks. Shows consistency of strategy. Format: win_rate (profitable_weeks/weeks_traded).
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

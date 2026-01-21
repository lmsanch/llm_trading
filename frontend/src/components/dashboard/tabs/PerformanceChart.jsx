import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { tradingApi } from '../../../api/trading';
import { cn } from "../../../lib/utils";

const ACCOUNT_COLORS = {
  COUNCIL: '#10b981',      // Green - highlight council
  CHATGPT: '#3b82f6',      // Blue
  GEMINI: '#8b5cf6',       // Purple
  CLAUDE: '#f59e0b',       // Amber
  GROK: '#ec4899',         // Pink
  BASELINE: '#6b7280'      // Gray
};

const ACCOUNT_NAMES = {
  COUNCIL: 'Council (CIO)',
  CHATGPT: 'ChatGPT',
  GEMINI: 'Gemini Pro',
  CLAUDE: 'Claude Sonnet',
  GROK: 'Grok',
  BASELINE: 'Baseline'
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-background border border-border p-3 rounded-md shadow-lg text-xs">
        <p className="font-bold mb-2">{label}</p>
        <div className="space-y-1">
          {payload.map((entry, index) => (
            <p key={index} className="flex justify-between gap-4">
              <span style={{ color: entry.color }}>{entry.name}:</span>
              <span className="font-mono font-medium">
                {entry.value >= 0 ? '+' : ''}${entry.value.toFixed(0)}
              </span>
            </p>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export default function PerformanceChart() {
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    fetchPerformanceData();
  }, [days]);

  const fetchPerformanceData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch comparison data to get all accounts
      const comparisonData = await tradingApi.getPerformanceComparison();
      setComparison(comparisonData);

      // Build list of all accounts
      const accounts = ['COUNCIL', ...comparisonData.individuals.map(ind => ind.account)];

      // Fetch history for each account
      const historyPromises = accounts.map(account =>
        tradingApi.getPerformanceHistory(account, days)
      );
      const histories = await Promise.all(historyPromises);

      // Combine all histories into a single chart dataset
      // Group by date
      const dateMap = new Map();

      histories.forEach((historyResponse, idx) => {
        const account = accounts[idx];
        const history = historyResponse.history || [];

        history.forEach(point => {
          if (!dateMap.has(point.date)) {
            dateMap.set(point.date, { date: point.date });
          }
          dateMap.get(point.date)[account] = point.pl;
        });
      });

      // Convert map to array and sort by date
      const combinedData = Array.from(dateMap.values()).sort((a, b) =>
        new Date(a.date) - new Date(b.date)
      );

      setChartData(combinedData);
    } catch (err) {
      console.error('Error fetching performance data:', err);
      setError('Failed to load performance data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Performance Comparison</CardTitle>
          <CardDescription>Council vs Individual PMs</CardDescription>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="text-muted-foreground">Loading performance data...</div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Performance Comparison</CardTitle>
          <CardDescription>Council vs Individual PMs</CardDescription>
        </CardHeader>
        <CardContent className="h-[400px] flex items-center justify-center">
          <div className="text-destructive">{error}</div>
        </CardContent>
      </Card>
    );
  }

  // Get list of accounts to display
  const accounts = comparison
    ? ['COUNCIL', ...comparison.individuals.map(ind => ind.account)]
    : [];

  // Calculate council advantage
  const councilAdvantage = comparison?.council_advantage || 0;
  const councilPL = comparison?.council?.total_pl || 0;
  const avgIndividualPL = comparison?.avg_individual_pl || 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle>Performance Comparison</CardTitle>
            <CardDescription>Council vs Individual PMs</CardDescription>
          </div>
          <div className="text-right space-y-1">
            <div className="text-sm text-muted-foreground">Council P/L</div>
            <div className={cn(
              "text-2xl font-bold",
              councilPL >= 0 ? "text-green-500" : "text-red-500"
            )}>
              {councilPL >= 0 ? '+' : ''}${councilPL.toFixed(0)}
            </div>
            <Badge
              variant={councilAdvantage > 0 ? "success" : "destructive"}
              className="text-xs"
            >
              {councilAdvantage > 0 ? '+' : ''}${councilAdvantage.toFixed(0)} vs avg
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.1} vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: '#666' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return `${date.getMonth()+1}/${date.getDate()}`;
                }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#666' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value) => `$${value}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
                formatter={(value) => ACCOUNT_NAMES[value] || value}
              />

              {/* Zero reference line */}
              <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" strokeWidth={1} />

              {/* Council line - thicker and highlighted */}
              <Line
                type="monotone"
                dataKey="COUNCIL"
                name="COUNCIL"
                stroke={ACCOUNT_COLORS.COUNCIL}
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 5 }}
              />

              {/* Individual PM lines */}
              {accounts.filter(acc => acc !== 'COUNCIL').map(account => (
                <Line
                  key={account}
                  type="monotone"
                  dataKey={account}
                  name={account}
                  stroke={ACCOUNT_COLORS[account] || '#94a3b8'}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Summary stats */}
        <div className="mt-6 pt-4 border-t">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-xs text-muted-foreground mb-1">Avg Individual</div>
              <div className={cn(
                "text-lg font-semibold",
                avgIndividualPL >= 0 ? "text-green-500" : "text-red-500"
              )}>
                {avgIndividualPL >= 0 ? '+' : ''}${avgIndividualPL.toFixed(0)}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Best Individual</div>
              <div className="text-lg font-semibold text-blue-500">
                {comparison?.individuals && comparison.individuals.length > 0
                  ? `${comparison.individuals.reduce((best, ind) =>
                      ind.total_pl > best.total_pl ? ind : best
                    ).account}`
                  : 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Sharpe Ratio</div>
              <div className="text-lg font-semibold">
                {comparison?.council?.sharpe_ratio?.toFixed(2) || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Max Drawdown</div>
              <div className="text-lg font-semibold text-red-500">
                {comparison?.council?.max_drawdown
                  ? `${(comparison.council.max_drawdown * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

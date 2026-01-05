import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { TrendingUp, TrendingDown } from 'lucide-react';

export function MarketMetrics({ data, prices }) {
  if (!data || !data.returns_7d) return null;

  const { returns_7d, correlation_matrix, symbols, date } = data;

  // Helper to format percentage
  const formatPct = (val) => {
    const sign = val >= 0 ? '+' : '';
    return `${sign}${val.toFixed(2)}%`;
  };

  // Helper to get color for correlation
  const getCorrelationColor = (corr) => {
    if (corr > 0.8) return 'text-red-600 dark:text-red-400';
    if (corr > 0.5) return 'text-orange-600 dark:text-orange-400';
    if (corr > 0.2) return 'text-yellow-600 dark:text-yellow-400';
    if (corr > -0.2) return 'text-muted-foreground';
    if (corr > -0.5) return 'text-blue-600 dark:text-blue-400';
    if (corr > -0.8) return 'text-cyan-600 dark:text-cyan-400';
    return 'text-green-600 dark:text-green-400';
  };

  return (
    <div className="space-y-4">
      {/* 7-Day Returns Table */}
      <Card>
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm flex items-center gap-2">
            📊 Latest 7-Day Log Returns
            {date && <span className="text-xs text-muted-foreground font-normal ml-2">as of {date}</span>}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 font-semibold">Symbol</th>
                  <th className="text-right py-2 px-2 font-semibold">Log Return</th>
                  <th className="text-right py-2 px-2 font-semibold">% Return</th>
                  <th className="text-left py-2 px-2 font-semibold">Performance</th>
                </tr>
              </thead>
              <tbody>
                {returns_7d.map((item, i) => (
                  <tr key={item.symbol} className="border-b last:border-0">
                    <td className="py-2 px-2 font-mono font-bold">{item.symbol}</td>
                    <td className="text-right py-2 px-2 font-mono text-muted-foreground">
                      {item.log_return_7d.toFixed(6)}
                    </td>
                    <td className={`text-right py-2 px-2 font-semibold ${
                      item.pct_return >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatPct(item.pct_return)}
                    </td>
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-1">
                        {item.pct_return >= 0 ? (
                          <TrendingUp className="h-3 w-3 text-green-600" />
                        ) : (
                          <TrendingDown className="h-3 w-3 text-red-600" />
                        )}
                        <span className="text-muted-foreground text-[10px]">
                          {i === 0 ? 'Best performer' :
                           i === returns_7d.length - 1 ? 'Worst performer' :
                           item.pct_return >= 0 ? 'Positive' : 'Decline'}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Current Prices & Volumes */}
      {prices && prices.length > 0 && (
        <Card>
          <CardHeader className="pb-3 border-b">
            <CardTitle className="text-sm flex items-center gap-2">
              💰 Current Prices & Volumes
              {prices[0]?.date && <span className="text-xs text-muted-foreground font-normal ml-2">as of {prices[0].date}</span>}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-2 font-semibold">Symbol</th>
                    <th className="text-right py-2 px-2 font-semibold">Close</th>
                    <th className="text-right py-2 px-2 font-semibold">Volume (M)</th>
                    <th className="text-right py-2 px-2 font-semibold">Daily Change</th>
                  </tr>
                </thead>
                <tbody>
                  {prices.map((price) => {
                    const dailyChange = price.daily_change_pct || 0;
                    const volumeInMillions = price.volume ? (price.volume / 1000000).toFixed(2) : '0.00';
                    
                    return (
                      <tr key={price.symbol} className="border-b last:border-0">
                        <td className="py-2 px-2 font-mono font-bold">{price.symbol}</td>
                        <td className="text-right py-2 px-2 font-mono">
                          ${price.close ? price.close.toFixed(2) : '0.00'}
                        </td>
                        <td className="text-right py-2 px-2 font-mono text-muted-foreground">
                          {volumeInMillions}M
                        </td>
                        <td className={`text-right py-2 px-2 font-semibold ${
                          dailyChange >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {formatPct(dailyChange)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Correlation Matrix */}
      <Card>
        <CardHeader className="pb-3 border-b">
          <CardTitle className="text-sm flex items-center gap-2">
            📈 30-Day Rolling Correlation Matrix (7-Day Returns)
            {date && <span className="text-xs text-muted-foreground font-normal ml-2">as of {date}</span>}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="overflow-x-auto">
            <table className="w-full text-[10px] border-collapse">
              <thead>
                <tr>
                  <th className="border p-1 bg-muted/50 font-semibold text-left sticky left-0 z-10">Symbol</th>
                  {symbols.map(sym => (
                    <th key={sym} className="border p-1 bg-muted/50 font-mono font-semibold text-center min-w-[45px]">
                      {sym}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {symbols.map(sym1 => (
                  <tr key={sym1}>
                    <td className="border p-1 bg-muted/50 font-mono font-bold sticky left-0 z-10">
                      {sym1}
                    </td>
                    {symbols.map(sym2 => {
                      const corr = correlation_matrix[sym1]?.[sym2];
                      if (corr === undefined) return <td key={sym2} className="border p-1 text-center">-</td>;
                      
                      return (
                        <td
                          key={sym2}
                          className={`border p-1 text-center font-mono ${getCorrelationColor(corr)} ${
                            sym1 === sym2 ? 'bg-primary/5 font-bold' : ''
                          }`}
                        >
                          {corr.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Legend */}
          <div className="mt-4 pt-3 border-t text-[10px] space-y-2">
            <div className="font-semibold text-muted-foreground">Correlation Legend:</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-600/20 border border-red-600/40 rounded" />
                <span className="text-muted-foreground">&gt; 0.8: Highly correlated</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-600/20 border border-blue-600/40 rounded" />
                <span className="text-muted-foreground">-0.5 to -0.2: Negative correlation</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-orange-600/20 border border-orange-600/40 rounded" />
                <span className="text-muted-foreground">0.5 to 0.8: Strong correlation</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-600/20 border border-green-600/40 rounded" />
                <span className="text-muted-foreground">&lt; -0.8: Highly inverse</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-yellow-600/20 border border-yellow-600/40 rounded" />
                <span className="text-muted-foreground">0.2 to 0.5: Moderate correlation</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-muted border border-border rounded" />
                <span className="text-muted-foreground">-0.2 to 0.2: Uncorrelated</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

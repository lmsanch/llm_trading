import React, { useState } from 'react';
import {
  ComposedChart,
  Line,
  Bar,
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
import { Button } from "../ui/Button";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-background border border-border p-3 rounded-md shadow-lg text-xs">
        <p className="font-bold mb-2">{label}</p>
        <div className="space-y-1">
          <p className="flex justify-between gap-4">
            <span className="text-muted-foreground">Open:</span>
            <span className="font-mono">{data.open?.toFixed(2)}</span>
          </p>
          <p className="flex justify-between gap-4">
            <span className="text-muted-foreground">High:</span>
            <span className="font-mono">{data.high?.toFixed(2)}</span>
          </p>
          <p className="flex justify-between gap-4">
            <span className="text-muted-foreground">Low:</span>
            <span className="font-mono">{data.low?.toFixed(2)}</span>
          </p>
          <p className="flex justify-between gap-4">
            <span className="text-primary font-bold">Close:</span>
            <span className="font-mono font-bold">{data.close?.toFixed(2)}</span>
          </p>
          <div className="my-1 border-t border-border" />
          <p className="flex justify-between gap-4">
            <span className="text-blue-400">SMA 20:</span>
            <span className="font-mono">{data.sma_20?.toFixed(2) || 'N/A'}</span>
          </p>
          <p className="flex justify-between gap-4">
            <span className="text-orange-400">SMA 50:</span>
            <span className="font-mono">{data.sma_50?.toFixed(2) || 'N/A'}</span>
          </p>
          <p className="flex justify-between gap-4">
            <span className="text-muted-foreground">Vol:</span>
            <span className="font-mono">{(data.volume / 1000000).toFixed(1)}M</span>
          </p>
        </div>
      </div>
    );
  }
  return null;
};

export function MarketChart({ data, instruments }) {
  const [selectedSymbol, setSelectedSymbol] = useState(instruments[0] || "SPY");
  
  // Extract data for selected symbol
  const symbolData = data?.instruments?.[selectedSymbol];
  const chartData = symbolData?.daily_ohlcv_30d?.slice().reverse().map(bar => ({
    ...bar,
    // Add indicators if they exist on the bar, or we might need to calculate/pass them differently
    // The backend provides indicators separately in the snapshot, not per bar in the array typically
    // unless we updated the backend to attach them. 
    // Looking at the backend code, it calculates SMA for the *current* state.
    // Ideally we'd have historical SMAs. For now, let's just plot Price + Volume.
    // We can try to calculate simple SMAs here for the chart.
  })) || [];

  // Simple SMA calculation for the chart
  const calculateSMA = (data, window) => {
    return data.map((bar, index) => {
      if (index < window - 1) return { ...bar, [`sma_${window}`]: null };
      const slice = data.slice(index - window + 1, index + 1);
      const sum = slice.reduce((acc, curr) => acc + curr.close, 0);
      return { ...bar, [`sma_${window}`]: sum / window };
    });
  };

  let processedData = calculateSMA(chartData, 20);
  processedData = calculateSMA(processedData, 50);

  if (!symbolData) return <div className="p-4 text-center text-muted-foreground">No market data available</div>;

  const currentPrice = symbolData.current?.price;
  const changePct = symbolData.current?.change_pct;
  const isPositive = changePct >= 0;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2 border-b">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              {instruments.map(sym => (
                <Button 
                  key={sym} 
                  variant={selectedSymbol === sym ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedSymbol(sym)}
                  className="h-7 text-xs px-2"
                >
                  {sym}
                </Button>
              ))}
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold flex items-center justify-end gap-2">
              {selectedSymbol}
              <span className="text-lg font-mono font-normal text-muted-foreground">
                ${currentPrice?.toFixed(2)}
              </span>
            </div>
            <Badge variant={isPositive ? "success" : "destructive"}>
              {isPositive ? "+" : ""}{changePct?.toFixed(2)}%
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={processedData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} vertical={false} />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 10, fill: '#666' }} 
              axisLine={false}
              tickLine={false}
              minTickGap={30}
              tickFormatter={(value) => {
                const date = new Date(value);
                return `${date.getMonth()+1}/${date.getDate()}`;
              }}
            />
            <YAxis 
              yAxisId="left" 
              domain={['auto', 'auto']} 
              orientation="left" 
              tick={{ fontSize: 10, fill: '#666' }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <YAxis 
              yAxisId="right" 
              orientation="right" 
              tick={{ fontSize: 10, fill: '#666' }}
              axisLine={false}
              tickLine={false}
              width={0}
              domain={[0, 'dataMax * 3']} // Push volume down
            />
            <Tooltip content={<CustomTooltip />} />
            
            <Bar yAxisId="right" dataKey="volume" fill="#3b82f6" opacity={0.15} barSize={20} />
            
            <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="close" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2} 
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="sma_20" 
              stroke="#60a5fa" 
              strokeWidth={1.5} 
              strokeDasharray="4 4" 
              dot={false} 
            />
             <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="sma_50" 
              stroke="#f97316" 
              strokeWidth={1.5} 
              strokeDasharray="4 4" 
              dot={false} 
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

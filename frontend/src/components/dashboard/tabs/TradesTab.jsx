import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Play, CheckCircle, XCircle, RefreshCw, Settings2, Loader2 } from 'lucide-react';
import { tradingApi } from '../../../api/trading';
import { cn } from "../../../lib/utils";

export default function TradesTab() {
  const [pendingTrades, setPendingTrades] = useState([]);
  const [historyTrades, setHistoryTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [selectedTrades, setSelectedTrades] = useState(new Set());

  useEffect(() => {
    loadTrades();
  }, []);

  const loadTrades = async () => {
    try {
      setLoading(true);
      const data = await tradingApi.getPendingTrades();
      
      // Separate pending and history trades
      const pending = data.filter(t => t.status === 'pending') || [];
      const history = data.filter(t => t.status !== 'pending') || [];
      
      setPendingTrades(pending);
      setHistoryTrades(history);
    } catch (error) {
      console.error('Error loading trades:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = (tradeId) => {
    setSelectedTrades(prev => {
      const newSet = new Set(prev);
      if (newSet.has(tradeId)) {
        newSet.delete(tradeId);
      } else {
        newSet.add(tradeId);
      }
      return newSet;
    });
  };

  const handleReject = (tradeId) => {
    // For now, just remove from pending trades
    setPendingTrades(prev => prev.filter(t => t.id !== tradeId));
  };

  const handleExecuteAll = async () => {
    if (selectedTrades.size === 0) {
      alert('Please select at least one trade to execute');
      return;
    }

    try {
      setExecuting(true);
      const tradeIds = Array.from(selectedTrades);
      const result = await tradingApi.executeTrades(tradeIds);
      
      console.log('Execution result:', result);
      
      // Refresh trades after execution
      await loadTrades();
      setSelectedTrades(new Set());
      
      // Show success message
      if (result.status === 'success') {
        alert(`Successfully executed ${tradeIds.length} trade(s)`);
      }
    } catch (error) {
      console.error('Error executing trades:', error);
      alert('Failed to execute trades. Please try again.');
    } finally {
      setExecuting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading trades...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
        <div className="flex justify-between items-center">
            <div>
                <h2 className="text-2xl font-bold tracking-tight">Trade Execution</h2>
                <p className="text-muted-foreground">Manage and execute pending orders.</p>
            </div>
            <div className="flex items-center gap-2">
                <Badge variant="neutral">READY</Badge>
            </div>
        </div>

      {/* Pending Trades */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
            Pending Orders <Badge variant="outline" className="ml-2">{pendingTrades.length}</Badge>
        </h3>
        {pendingTrades.map((trade) => (
            <Card key={trade.id} className={cn(
                "overflow-hidden transition-colors",
                selectedTrades.has(trade.id) && "border-green-500 bg-green-50/10"
            )}>
                <div className="flex flex-col md:flex-row md:items-center justify-between p-4 gap-4">
                    <div className="flex items-center gap-6">
                        <div className="min-w-[100px]">
                            <Badge variant="outline" className="mb-1">{trade.account || 'COUNCIL'}</Badge>
                            <div className="text-2xl font-bold">{trade.symbol}</div>
                        </div>
                        <div className="space-y-1">
                            <div className="flex items-center gap-2">
                                <Badge variant={trade.direction === 'BUY' ? 'success' : 'destructive'}>
                                    {trade.direction}
                                </Badge>
                                <span className="font-mono text-lg font-medium">{trade.qty} units</span>
                            </div>
                            <div className="text-xs text-muted-foreground">
                                Conviction: {trade.conviction > 0 ? '+' : ''}{trade.conviction}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm">
                            <Settings2 className="h-4 w-4 mr-2" /> Modify
                        </Button>
                        <Button 
                            variant="outline" 
                            size="sm" 
                            className="text-red-500 hover:text-red-600"
                            onClick={() => handleReject(trade.id)}
                        >
                            <XCircle className="h-4 w-4 mr-2" /> Reject
                        </Button>
                        <Button 
                            size="sm" 
                            className={cn(
                                "bg-green-600 hover:bg-green-700",
                                selectedTrades.has(trade.id) && "bg-green-700"
                            )}
                            onClick={() => handleApprove(trade.id)}
                        >
                            <CheckCircle className="h-4 w-4 mr-2" /> 
                            {selectedTrades.has(trade.id) ? 'Selected' : 'Approve'}
                        </Button>
                    </div>
                </div>
            </Card>
        ))}
        {pendingTrades.length === 0 && (
            <div className="text-center py-10 border rounded-lg border-dashed text-muted-foreground">
                No pending trades.
            </div>
        )}
      </div>

      {/* Execution History */}
      <div className="space-y-4 pt-4">
        <h3 className="text-lg font-semibold">Execution History</h3>
        <div className="rounded-md border">
            <div className="grid grid-cols-6 gap-4 p-3 font-medium text-sm bg-muted/50 border-b">
                <div>Status</div>
                <div>Time</div>
                <div>Account</div>
                <div>Symbol</div>
                <div>Side</div>
                <div className="text-right">Qty</div>
            </div>
            {historyTrades.map((trade) => (
                <div key={trade.id} className="grid grid-cols-6 gap-4 p-3 text-sm items-center hover:bg-muted/10 transition-colors">
                    <div>
                        <Badge variant="secondary" className="text-xs">
                            {trade.status.toUpperCase()}
                        </Badge>
                    </div>
                    <div className="text-muted-foreground">{trade.timestamp || '10:42 AM'}</div>
                    <div>{trade.account || 'COUNCIL'}</div>
                    <div className="font-medium">{trade.symbol}</div>
                    <div className={trade.direction === 'BUY' ? 'text-green-500' : 'text-red-500'}>
                        {trade.direction}
                    </div>
                    <div className="text-right font-mono">{trade.qty}</div>
                </div>
            ))}
            {historyTrades.length === 0 && (
                <div className="text-center py-6 text-muted-foreground">
                    No execution history yet.
                </div>
            )}
        </div>
      </div>

       <div className="flex items-center justify-end gap-4 pt-4 border-t sticky bottom-0 bg-background pb-4">
        <Button 
            variant="outline"
            onClick={loadTrades}
            disabled={loading}
        >
            <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} /> 
            Refresh Status
        </Button>
        <Button 
            onClick={handleExecuteAll}
            disabled={executing || selectedTrades.size === 0}
        >
            {executing ? (
                <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 
                    Executing...
                </>
            ) : (
                <>
                    <Play className="mr-2 h-4 w-4" /> 
                    Execute {selectedTrades.size > 0 ? `(${selectedTrades.size})` : 'All Approved'}
                </>
            )}
        </Button>
      </div>

    </div>
  );
}

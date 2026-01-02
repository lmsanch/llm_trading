import React from 'react';
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Play, Pause, Activity } from "lucide-react";

export function Header({ mode, setMode }) {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 gap-4">
        <div className="flex items-center gap-2 font-bold text-lg">
          <span className="text-xl">🏛️</span>
          <span>LLM TRADING</span>
        </div>
        
        <div className="flex items-center gap-4 text-sm text-muted-foreground border-l pl-4 ml-4 h-8">
          <div className="flex items-center gap-2">
            <span>Week:</span>
            <span className="font-medium text-foreground">2025-W01</span>
          </div>
          <div className="flex items-center gap-2">
            <span>Status:</span>
            <Badge variant="success" className="gap-1">
              <Activity className="h-3 w-3" />
              PIPELINE READY
            </Badge>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2">
            <div className="flex items-center border rounded-md p-1 bg-muted/50">
                <Button 
                    variant={mode === 'MANUAL' ? 'secondary' : 'ghost'} 
                    size="sm" 
                    className="h-7 text-xs"
                    onClick={() => setMode('MANUAL')}
                >
                    MANUAL ●
                </Button>
                <Button 
                    variant={mode === 'AUTO' ? 'secondary' : 'ghost'} 
                    size="sm" 
                    className="h-7 text-xs"
                    onClick={() => setMode('AUTO')}
                >
                    AUTO ○
                </Button>
            </div>
        </div>
      </div>
    </header>
  );
}

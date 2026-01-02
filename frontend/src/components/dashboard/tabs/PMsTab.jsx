import React from 'react';
import { PMPitchCard } from './PMPitchCard';
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { Play, CheckCheck, RefreshCw } from 'lucide-react';
import { mockPMPitches } from '../../../lib/mockData';

export default function PMsTab() {
  const pitches = mockPMPitches;

  return (
    <div className="space-y-6">
       <div className="flex justify-between items-center">
            <div>
                <h2 className="text-2xl font-bold tracking-tight">PM Pitches</h2>
                <p className="text-muted-foreground">Review trading convictions from Portfolio Manager models.</p>
            </div>
            <div className="flex items-center gap-2">
                <Badge variant="success">COMPLETE</Badge>
            </div>
        </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {pitches.map((pitch) => (
            <PMPitchCard key={pitch.id} pitch={pitch} />
        ))}
      </div>

      <div className="flex items-center justify-end gap-4 pt-4 border-t sticky bottom-0 bg-background pb-4">
        <Button variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerate All
        </Button>
        <Button variant="outline">
            <CheckCheck className="mr-2 h-4 w-4" /> Approve All
        </Button>
        <Button>
            <Play className="mr-2 h-4 w-4" /> Pass to Council
        </Button>
      </div>
    </div>
  );
}

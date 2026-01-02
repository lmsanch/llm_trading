import React, { useState, useEffect, useCallback } from 'react';
import { ResearchPackCard } from './ResearchPackCard';
import { ResearchCalendar } from './ResearchCalendar';
import { MarketChart } from '../ui/MarketChart';
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import {
    Play,
    CheckCheck,
    Search,
    Clock,
    FileText,
    AlertCircle,
    X,
    Loader2,
    ChevronRight,
    ShieldCheck,
    Edit2,
    TrendingUp
} from 'lucide-react';
import { mockResearchPacks } from '../../../lib/mockData';

// Helper function to load past research report
async function loadPastReport(reportId) {
    try {
        const response = await fetch(`/api/research/report/${reportId}`);
        if (!response.ok) throw new Error('Failed to load report');
        const report = await response.json();
        return report;
    } catch (error) {
        console.error('Error loading report:', error);
        return null;
    }
}

export { loadPastReport };

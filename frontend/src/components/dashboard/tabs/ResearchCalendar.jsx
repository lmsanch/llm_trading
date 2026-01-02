import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Calendar, ChevronLeft, ChevronRight, Download } from 'lucide-react';

export function ResearchCalendar({ onSelectDate }) {
    const [history, setHistory] = useState({});
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        try {
            const response = await fetch('/api/research/history?days=90');
            const data = await response.json();
            setHistory(data.history || {});
        } catch (error) {
            console.error('Failed to fetch research history:', error);
        } finally {
            setLoading(false);
        }
    };

    const getDaysInMonth = (date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();

        return { daysInMonth, startingDayOfWeek, year, month };
    };

    const { daysInMonth, startingDayOfWeek, year, month } = getDaysInMonth(currentMonth);

    const previousMonth = () => {
        setCurrentMonth(new Date(year, month - 1, 1));
    };

    const nextMonth = () => {
        setCurrentMonth(new Date(year, month + 1, 1));
    };

    const getDateKey = (day) => {
        const date = new Date(year, month, day);
        return date.toISOString().split('T')[0];
    };

    const getDayColor = (day) => {
        const dateKey = getDateKey(day);
        const dayData = history[dateKey];

        if (!dayData) return null;

        const providers = dayData.providers.map(p => p.name);

        if (providers.includes('perplexity') && providers.includes('gemini')) {
            return 'bg-gradient-to-br from-blue-500 to-purple-500';
        } else if (providers.includes('perplexity')) {
            return 'bg-blue-500';
        } else if (providers.includes('gemini')) {
            return 'bg-purple-500';
        }

        return null;
    };

    const handleDayClick = (day) => {
        const dateKey = getDateKey(day);
        const dayData = history[dateKey];

        if (dayData && onSelectDate) {
            onSelectDate(dateKey, dayData);
        }
    };

    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];

    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    if (loading) {
        return (
            <Card>
                <CardContent className="p-6">
                    <p className="text-sm text-muted-foreground">Loading research history...</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="w-full">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-bold flex items-center gap-2">
                        <Calendar className="h-4 w-4" />
                        Research History
                    </CardTitle>
                    <div className="flex gap-1">
                        <Badge variant="outline" className="text-[9px] h-5 bg-blue-500/10 border-blue-500/30">
                            <span className="w-2 h-2 rounded-full bg-blue-500 mr-1"></span>
                            Perplexity
                        </Badge>
                        <Badge variant="outline" className="text-[9px] h-5 bg-purple-500/10 border-purple-500/30">
                            <span className="w-2 h-2 rounded-full bg-purple-500 mr-1"></span>
                            Gemini
                        </Badge>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="p-4">
                {/* Month Navigation */}
                <div className="flex items-center justify-between mb-4">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={previousMonth}
                        className="h-8 w-8 p-0"
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm font-semibold">
                        {monthNames[month]} {year}
                    </span>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={nextMonth}
                        className="h-8 w-8 p-0"
                    >
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>

                {/* Calendar Grid */}
                <div className="grid grid-cols-7 gap-1">
                    {/* Day headers */}
                    {dayNames.map(day => (
                        <div key={day} className="text-center text-[10px] font-semibold text-muted-foreground p-1">
                            {day}
                        </div>
                    ))}

                    {/* Empty cells for days before month starts */}
                    {Array.from({ length: startingDayOfWeek }).map((_, i) => (
                        <div key={`empty-${i}`} className="aspect-square" />
                    ))}

                    {/* Days of the month */}
                    {Array.from({ length: daysInMonth }).map((_, i) => {
                        const day = i + 1;
                        const dateKey = getDateKey(day);
                        const dayData = history[dateKey];
                        const colorClass = getDayColor(day);
                        const isToday = dateKey === new Date().toISOString().split('T')[0];

                        return (
                            <button
                                key={day}
                                onClick={() => handleDayClick(day)}
                                disabled={!dayData}
                                className={`
                  aspect-square p-1 rounded-md text-xs font-medium
                  transition-all relative
                  ${colorClass ? 'text-white hover:scale-110 cursor-pointer shadow-md' : 'text-muted-foreground hover:bg-muted/50'}
                  ${isToday ? 'ring-2 ring-primary ring-offset-2' : ''}
                  ${!dayData ? 'cursor-default' : ''}
                `}
                            >
                                <span className={colorClass ? 'relative z-10' : ''}>{day}</span>
                                {colorClass && (
                                    <div className={`absolute inset-0 ${colorClass} rounded-md opacity-90`} />
                                )}
                                {dayData && (
                                    <div className="absolute bottom-0 right-0 w-1 h-1 bg-white rounded-full opacity-75" />
                                )}
                            </button>
                        );
                    })}
                </div>

                {/* Legend */}
                <div className="mt-4 pt-3 border-t text-[10px] text-muted-foreground">
                    <p>Click on a colored day to view that research report</p>
                </div>
            </CardContent>
        </Card>
    );
}

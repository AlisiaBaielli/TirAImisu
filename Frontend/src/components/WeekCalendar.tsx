import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useEffect, useMemo, useState } from "react";
import { format, addDays, startOfWeek, isSameDay, parseISO } from "date-fns";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { format, addDays, startOfWeek } from "date-fns";

type ApiEvent = {
  id?: string;
  title: string;
  start: { date_time: string };
  end: { date_time: string };
};

interface CalendarChip {
  id: string | number;
  name: string;
  time: string;
  color: string;
  frequency: string;
  startDate: string;
}

const WeekCalendar = () => {
  const today = new Date();
  const weekStart = addDays(startOfWeek(today, { weekStartsOn: 1 }), 7);
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = (import.meta as any)?.env?.VITE_BACKEND_URL ?? "http://localhost:8000";
  const calendarId = (import.meta as any)?.env?.VITE_CALENDAR_ID ?? "cal_OODZTUtc1Y";

  const fetchEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${baseUrl}/api/calendar/${calendarId}/events`);
      if (!res.ok) {
        throw new Error(`Failed to load events (${res.status})`);
      }
      const data = await res.json();
      setEvents(Array.isArray(data?.events) ? data.events : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load events");
    } finally {
      setLoading(false);
    }
  };

  const refreshEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${baseUrl}/api/calendar/${calendarId}/events/refresh`, {
        method: "POST",
      });
      if (!res.ok) {
        throw new Error(`Failed to refresh events (${res.status})`);
      }
      await fetchEvents();
    } catch (e: any) {
      setError(e?.message ?? "Failed to refresh events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const colorPalette = useMemo(() => ["bg-blue-500", "bg-green-500", "bg-orange-500", "bg-purple-500"], []);
  const hashString = (s: string) => {
    let h = 0;
    for (let i = 0; i < s.length; i++) {
      h = (h << 5) - h + s.charCodeAt(i);
      h |= 0;
    }
    return Math.abs(h);
  };

  const hours = Array.from({ length: 24 }, (_, i) => i);
  const [selectedMed, setSelectedMed] = useState<MedicationEvent | null>(null);

  return (
    <Card className="h-[calc(100vh-180px)]">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>7-Day Medication Schedule</CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={refreshEvents} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 min-h-0">
        <div className="h-full overflow-auto">
          <div className="min-w-[800px]">
            <div className="grid grid-cols-8 border-b sticky top-0 bg-card z-10">
              <div className="p-2 border-r text-xs font-medium text-muted-foreground">Time</div>
              {days.map((day, index) => (
                <div
                  key={index}
                  className={`p-2 border-r text-center ${
                    format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd") ? "bg-primary/5" : ""
                  }`}
                >
                  <div className="text-xs font-medium">{format(day, "EEE")}</div>
                  <div className={`text-lg font-semibold ${
                    format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd") ? "text-primary" : ""
                  }`}>
                    {format(day, "d")}
                  </div>
                </div>
              ))}
            </div>

            {hours.map((hour) => (
              <div key={hour} className="grid grid-cols-8 border-b min-h-[60px]">
                <div className="p-2 border-r text-xs text-muted-foreground">
                  {hour.toString().padStart(2, "0")}:00
                </div>
                {days.map((day, dayIndex) => {
                  const hourEvents: CalendarChip[] = events
                    .filter((ev) => {
                      const start = parseISO(ev.start?.date_time ?? "");
                      return isSameDay(start, day) && start.getHours() === hour;
                    })
                    .map((ev, idx) => {
                      const start = parseISO(ev.start?.date_time ?? "");
                      const color = colorPalette[hashString(ev.title ?? "") % colorPalette.length];
                      return {
                        id: ev.id ?? `${dayIndex}-${hour}-${idx}`,
                        name: ev.title ?? "Event",
                        time: format(start, "HH:mm"),
                        color,
                      };
                    });

                  return (
                    <div
                      key={dayIndex}
                      className={`p-1 border-r relative ${
                        format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd") ? "bg-primary/5" : ""
                      }`}
                    >
                      {hourEvents.map((event) => (
                        <div
                          key={event.id}
                          className={`${event.color} text-white rounded px-2 py-1 mb-1 text-xs font-medium cursor-pointer transition hover:scale-105 hover:shadow-lg`}
                          onClick={() => setSelectedMed(event)}
                        >
                          {event.name}
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            ))}

            {/* Loading / error states */}
            {loading && (
              <div className="p-3 text-xs text-muted-foreground">Loading events…</div>
            )}
            {error && !loading && (
              <div className="p-3 text-xs text-red-500">Error: {error}</div>
            )}
          </div>
        </div>
      </CardContent>

      <Dialog open={!!selectedMed} onOpenChange={() => setSelectedMed(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedMed?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <div><strong>Time:</strong> {selectedMed?.time}</div>
            <div><strong>Frequency:</strong> {selectedMed?.frequency}</div>
            <div><strong>Start Date:</strong> {selectedMed?.startDate}</div>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default WeekCalendar;
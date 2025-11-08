import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useEffect, useMemo, useState } from "react";
import { format, addDays, startOfWeek, isSameDay, parseISO } from "date-fns";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

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
  duration?: number; // duration in minutes
  startMinutes?: number; // minutes from start of hour
}

const WeekCalendar = () => {
  const today = new Date();
  const weekStart = addDays(startOfWeek(today, { weekStartsOn: 1 }), 7);
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const baseUrl = (import.meta as any)?.env?.VITE_BACKEND_URL ?? "http://localhost:8000";

  const fetchEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const [resExtra, resMeds] = await Promise.all([
        fetch(`${baseUrl}/api/events-calendar/events`),
        fetch(`${baseUrl}/api/medications/events`),
      ]);

      const extraJson = resExtra.ok ? await resExtra.json() : { events: [] };
      const medsJson = resMeds.ok ? await resMeds.json() : { events: [] };
      const merged = [
        ...(Array.isArray(extraJson?.events) ? extraJson.events : []),
        ...(Array.isArray(medsJson?.events) ? medsJson.events : []),
      ];
      setEvents(merged);
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
      const r = await fetch(`${baseUrl}/api/events-calendar/events/refresh`, { method: "POST" });
      if (!r.ok) throw new Error("Failed to refresh events");
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
  const [selectedMed, setSelectedMed] = useState<CalendarChip | null>(null);

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
        <div className="h-full overflow-auto" style={{ overflowX: "auto", overflowY: "auto" }}>
          <div className="min-w-[800px]" style={{ position: "relative" }}>
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
              <div key={hour} className="grid grid-cols-8 border-b min-h-[60px]" style={{ overflow: "visible" }}>
                <div className="p-2 border-r text-xs text-muted-foreground">
                  {hour.toString().padStart(2, "0")}:00
                </div>
                {days.map((day, dayIndex) => {
                  const hourEvents: CalendarChip[] = events
                    .filter((ev) => {
                      const start = parseISO(ev.start?.date_time ?? "");
                      const end = parseISO(ev.end?.date_time ?? "");
                      if (!isSameDay(start, day)) return false;
                      
                      // Show event in the hour row where it starts
                      const startHour = start.getHours();
                      return startHour === hour;
                    })
                    .map((ev, idx) => {
                      const start = parseISO(ev.start?.date_time ?? "");
                      const end = parseISO(ev.end?.date_time ?? "");
                      const color = colorPalette[hashString(ev.title ?? "") % colorPalette.length];
                      
                      // Calculate duration in minutes
                      const durationMs = end.getTime() - start.getTime();
                      const durationMinutes = Math.max(30, Math.round(durationMs / (1000 * 60))); // Minimum 30 minutes for visibility
                      
                      // Calculate minutes from start of hour (for positioning)
                      const startMinutes = start.getMinutes();
                      
                      return {
                        id: ev.id ?? `${dayIndex}-${hour}-${idx}`,
                        name: ev.title ?? "Event",
                        time: format(start, "HH:mm"),
                        color,
                        frequency: "once",
                        startDate: format(start, "yyyy-MM-dd"),
                        duration: durationMinutes,
                        startMinutes: startMinutes,
                      };
                    });

                  return (
                    <div
                      key={dayIndex}
                      className={`p-1 border-r relative ${
                        format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd") ? "bg-primary/5" : ""
                      }`}
                      style={{ minHeight: "60px", overflow: "visible" }}
                    >
                      {hourEvents.map((event) => {
                        // Calculate height: each hour is 60px, so duration in minutes / 60 * 60px
                        const hourHeight = 60; // 60px per hour row
                        const heightPx = (event.duration! / 60) * hourHeight;
                        const topOffsetPx = (event.startMinutes! / 60) * hourHeight;
                        
                        return (
                          <div
                            key={event.id}
                            className={`${event.color} text-white rounded px-2 py-1 text-xs font-medium cursor-pointer transition hover:opacity-90 hover:shadow-lg absolute left-1 right-1 z-10 flex flex-col justify-start`}
                            style={{
                              top: `${topOffsetPx + 4}px`, // +4px for padding
                              height: `${Math.max(heightPx - 8, 20)}px`, // -8px to account for padding, min 20px
                              minHeight: "20px", // Minimum height for readability
                              overflow: "hidden", // Prevent text overflow
                            }}
                            onClick={() => setSelectedMed(event)}
                          >
                            <div className="truncate leading-tight">{event.name}</div>
                            {event.duration! >= 60 && (
                              <div className="text-[10px] opacity-90 mt-0.5 leading-tight">
                                {Math.floor(event.duration! / 60)}h {event.duration! % 60 > 0 ? `${event.duration! % 60}m` : ""}
                              </div>
                            )}
                          </div>
                        );
                      })}
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
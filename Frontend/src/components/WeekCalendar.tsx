import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useEffect, useMemo, useState } from "react";
import { format, addDays, startOfWeek, isSameDay, parseISO } from "date-fns";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface Medication {
  id: string | number;
  name: string;
  color: string;
}

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
  color: string; // med-* string
  frequency: string;
  startDate: string;
  duration?: number;
  startMinutes?: number;
}

const WeekCalendar = () => {
  const today = new Date();
  const weekStart = startOfWeek(today, { weekStartsOn: 1 });
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMed, setSelectedMed] = useState<CalendarChip | null>(null);
  const [medications, setMedications] = useState<Medication[]>([]);

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

  const fetchMedications = async () => {
    try {
      const userId = localStorage.getItem("userId") || "1";
      const res = await fetch(`${baseUrl}/api/users/${userId}/medications`);
      if (!res.ok) return;
      const data = await res.json();
      const meds = Array.isArray(data?.medications) ? data.medications : [];
      setMedications(meds);
    } catch {
      setMedications([]);
    }
  };

  useEffect(() => {
    fetchEvents();
    fetchMedications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const medColorMap = useMemo(() => {
    const map: Record<string, string> = {};
    medications.forEach((m) => {
      map[m.name] = m.color || "med-blue";
    });
    return map;
  }, [medications]);

  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Helper: assign columns for events that may overlap.
  const layoutColumns = (items: CalendarChip[]) => {
    // sort by startMinutes ascending
    const sorted = [...items].sort((a, b) => (a.startMinutes ?? 0) - (b.startMinutes ?? 0));
    const columns: { end: number }[] = [];
    const placed: { event: CalendarChip; col: number }[] = [];

    for (const ev of sorted) {
      const start = ev.startMinutes ?? 0;
      const end = start + (ev.duration ?? 30);
      // find a column where this event doesn't overlap the last item
      let placedCol = -1;
      for (let ci = 0; ci < columns.length; ci++) {
        if (start >= columns[ci].end) {
          placedCol = ci;
          columns[ci].end = end;
          break;
        }
      }
      if (placedCol === -1) {
        // new column
        columns.push({ end });
        placedCol = columns.length - 1;
      }
      placed.push({ event: ev, col: placedCol });
    }
    const colsCount = Math.max(1, columns.length);
    // produce mapping with col index and total cols
    return placed.map((p) => ({ ...p.event, col: p.col, cols: colsCount }));
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2 shrink-0">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-lg font-medium">7-Day Medication Schedule</CardTitle>
          <Button variant="outline" size="sm" onClick={fetchEvents} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 min-h-0 flex flex-col">
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="min-w-[800px]" style={{ position: "relative" }}>
            <div className="grid grid-cols-8 border-b sticky top-0 bg-card z-10">
              <div className="p-2 border-r text-xs font-medium text-muted-foreground">Time</div>
              {days.map((day, index) => {
                const isToday = format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd");
                return (
                  <div
                    key={index}
                    className={`p-2 border-r text-center ${isToday ? "bg-primary/5" : ""}`}
                  >
                    <div className="text-xs font-medium">{format(day, "EEE")}</div>
                    <div className={`text-lg font-semibold ${isToday ? "text-primary" : ""}`}>
                      {format(day, "d")}
                    </div>
                  </div>
                );
              })}
            </div>

            {hours.map((hour) => (
              <div key={hour} className="grid grid-cols-8 border-b min-h-[60px]" style={{ overflow: "visible" }}>
                <div className="p-2 border-r text-xs text-muted-foreground">
                  {hour.toString().padStart(2, "0")}:00
                </div>
                {days.map((day, dayIndex) => {
                  // collect events that start in this hour & day
                  const rawEvents: CalendarChip[] = events
                    .filter((ev) => {
                      const start = parseISO(ev.start?.date_time ?? "");
                      if (!isSameDay(start, day)) return false;
                      return start.getHours() === hour;
                    })
                    .map((ev, idx) => {
                      const start = parseISO(ev.start?.date_time ?? "");
                      const end = parseISO(ev.end?.date_time ?? "");
                      const medColor = medColorMap[ev.title ?? ""] ?? "med-blue";
                      const durationMs = end.getTime() - start.getTime();
                      const durationMinutes = Math.max(30, Math.round(durationMs / 60000));
                      const startMinutes = start.getMinutes();
                      return {
                        id: ev.id ?? `${dayIndex}-${hour}-${idx}`,
                        name: ev.title ?? "Event",
                        time: format(start, "HH:mm"),
                        color: medColor,
                        frequency: "once",
                        startDate: format(start, "yyyy-MM-dd"),
                        duration: durationMinutes,
                        startMinutes,
                      } as CalendarChip;
                    });

                  // layout into columns to avoid overlap (per cell)
                  const placed = layoutColumns(rawEvents);

                  const isToday = format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd");
                  return (
                    <div
                      key={dayIndex}
                      className={`p-1 border-r relative ${isToday ? "bg-primary/5" : ""}`}
                      style={{ minHeight: "60px", overflow: "visible" }}
                    >
                      {placed.map((event) => {
                        const hourHeight = 60;
                        const heightPx = (event.duration! / 60) * hourHeight;
                        const topOffsetPx = (event.startMinutes! / 60) * hourHeight;
                        const cols = event.cols ?? 1;
                        const colIndex = event.col ?? 0;
                        const gapPx = 6; // gap between columns in px
                        const totalGap = gapPx * (cols - 1);
                        const containerWidth = 100; // percent
                        // compute width in percent minus gaps (approx)
                        const widthPercent = Math.max(10, (100 / cols));
                        const leftPercent = (colIndex * (100 / cols));
                        return (
                          <div
                            key={event.id}
                            className="text-white rounded px-2 py-1 text-xs font-medium cursor-pointer transition hover:opacity-90 hover:shadow-lg absolute z-10 flex flex-col justify-start"
                            style={{
                              top: `${topOffsetPx + 4}px`,
                              height: `${Math.max(heightPx - 8, 20)}px`,
                              minHeight: "20px",
                              overflow: "hidden",
                              left: `${leftPercent}%`,
                              width: `calc(${widthPercent}% - ${totalGap / cols}px)`,
                              backgroundColor: `hsl(var(--${event.color}))`,
                              marginRight: `${gapPx}px`,
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

            {loading && <div className="p-3 text-xs text-muted-foreground">Loading events…</div>}
            {error && !loading && <div className="p-3 text-xs text-red-500">Error: {error}</div>}
          </div>
        </div>
      </CardContent>

      <Dialog open={!!selectedMed} onOpenChange={() => setSelectedMed(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedMed?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 text-sm">
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
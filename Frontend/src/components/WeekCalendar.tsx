import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useEffect, useMemo, useState } from "react";
import {
  format,
  addDays,
  startOfWeek,
  isSameDay,
  parseISO,
  isAfter,
  endOfWeek
} from "date-fns";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface Medication {
  id: string | number;
  name: string;
  color: string;
  schedule?: { type?: string; times?: string[]; day?: string; days?: string[] };
  start_date?: string | null;
  end_date?: string | null;
}

type ApiEvent = {
  id?: string;
  title: string;
  start: { date_time: string };
  end: { date_time: string };
  source?: string;
  color?: string;
};

interface CalendarChip {
  id: string | number;
  name: string;
  time: string;
  color: string;
  frequency: string;
  startDate: string;
  duration?: number;
  startMinutes?: number;
  col?: number;
  cols?: number;
}

const DEFAULT_EVENT_DURATION_MIN = 30;

const WeekCalendar = () => {
  const today = new Date();
  const weekStart = startOfWeek(today, { weekStartsOn: 1 });
  const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const [extraEvents, setExtraEvents] = useState<ApiEvent[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [combinedEvents, setCombinedEvents] = useState<ApiEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMeds, setLoadingMeds] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMed, setSelectedMed] = useState<CalendarChip | null>(null);

    const raw = (import.meta as any)?.env?.VITE_BACKEND_URL;
    const baseUrl = raw ? String(raw).replace(/\/$/, "") : ""; // empty string fallback

  // Load non-user extra events
  const fetchExtraEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      const resExtra = await fetch(`${baseUrl}/api/events-calendar/events`);
      const extraJson = resExtra.ok ? await resExtra.json() : { events: [] };
      const events = Array.isArray(extraJson?.events) ? extraJson.events : [];
      setExtraEvents(events);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load events");
    } finally {
      setLoading(false);
    }
  };

  // Load user medications
  const fetchMedications = async () => {
    try {
      setLoadingMeds(true);
      const userId = localStorage.getItem("userId") || "1";
      const res = await fetch(`${baseUrl}/api/users/${userId}/medications`);
      if (!res.ok) throw new Error(`Failed to load medications (${res.status})`);
      const data = await res.json();
      const medsRaw = Array.isArray(data?.medications) ? data.medications : [];
      // map to Medication interface
      const meds: Medication[] = medsRaw.map((m) => ({
        id: m.id,
        name: m.name,
        color: m.color || "med-blue",
        schedule: m.schedule || {},
        start_date: m.start_date || null,
        end_date: m.end_date || null,
      }));
      setMedications(meds);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load medications");
      setMedications([]);
    } finally {
      setLoadingMeds(false);
    }
  };

  // Generate events from medications for current week
  const generateMedicationEventsForWeek = (meds: Medication[]): ApiEvent[] => {
    const result: ApiEvent[] = [];
    meds.forEach((med) => {
      const sched = med.schedule || {};
      const times = Array.isArray(sched.times) ? sched.times : [];
      if (times.length === 0) return;

      const type = (sched.type || "").toLowerCase();
      const startDate = med.start_date ? parseISO(med.start_date) : today;
      const endDate = med.end_date ? parseISO(med.end_date) : null;

      days.forEach((day) => {
        // Respect start_date and end_date boundaries
        if (isAfter(startDate, day)) return;
        if (endDate && isAfter(day, endDate)) return;

        const isStartWeekday = startDate.getDay() === day.getDay();

        if (type === "daily") {
          // include all days from start onward
        } else if (type === "weekly") {
          // only include matching weekday (start date's weekday)
          if (!isStartWeekday) return;
        } else {
          // unsupported frequency -> skip
          return;
        }

        times.forEach((t) => {
          if (!/^\d{2}:\d{2}$/.test(t)) return;
          const [hh, mm] = t.split(":").map((n) => parseInt(n, 10));
          const start = new Date(
            day.getFullYear(),
            day.getMonth(),
            day.getDate(),
            hh,
            mm,
            0,
            0
          );
          const end = new Date(start.getTime() + DEFAULT_EVENT_DURATION_MIN * 60000);
          result.push({
            id: `med-${med.id}-${format(day, "yyyyMMdd")}-${t}`,
            title: med.name,
            start: { date_time: start.toISOString() },
            end: { date_time: end.toISOString() },
            source: "medication",
            color: med.color,
          });
        });
      });
    });
    return result;
  };

  // Recombine whenever meds or extra events change
  useEffect(() => {
    const medEvents = generateMedicationEventsForWeek(medications);
    // Merge: medication events first then extra events
    setCombinedEvents([...medEvents, ...extraEvents]);
  }, [medications, extraEvents, weekStart]);

  useEffect(() => {
    fetchExtraEvents();
    fetchMedications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Force refresh backend cache then reload
  const refreshAll = async () => {
    try {
      setLoading(true);
      setLoadingMeds(true);
      setError(null);
      // Force backend to refresh cached external events
      await fetch(`${baseUrl}/api/events-calendar/events/refresh`, { method: "POST" }).catch(() => {});
    } finally {
      // Reload both sources regardless of refresh result
      await Promise.all([fetchExtraEvents(), fetchMedications()]);
    }
  };

  // Colors map
  const medColorMap = useMemo(() => {
    const map: Record<string, string> = {};
    medications.forEach((m) => {
      map[m.name] = m.color || "med-blue";
    });
    return map;
  }, [medications]);

  const hours = Array.from({ length: 24 }, (_, i) => i);

  const layoutColumns = (items: CalendarChip[]) => {
    const sorted = [...items].sort(
      (a, b) => (a.startMinutes ?? 0) - (b.startMinutes ?? 0)
    );
    const columns: { end: number }[] = [];
    const placed: { event: CalendarChip; col: number }[] = [];

    for (const ev of sorted) {
      const start = ev.startMinutes ?? 0;
      const end = start + (ev.duration ?? DEFAULT_EVENT_DURATION_MIN);
      let placedCol = -1;
      for (let ci = 0; ci < columns.length; ci++) {
        if (start >= columns[ci].end) {
          placedCol = ci;
          columns[ci].end = end;
          break;
        }
      }
      if (placedCol === -1) {
        columns.push({ end });
        placedCol = columns.length - 1;
      }
      placed.push({ event: ev, col: placedCol });
    }
    const colsCount = Math.max(1, columns.length);
    return placed.map((p) => ({ ...p.event, col: p.col, cols: colsCount }));
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2 shrink-0">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-lg font-medium">
            7-Day Medication Schedule
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={refreshAll}
            disabled={loading || loadingMeds}
          >
            {loading || loadingMeds ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 min-h-0 flex flex-col">
        <div className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="min-w-[800px]" style={{ position: "relative" }}>
              <div className="grid grid-cols-8 border-b sticky top-0 bg-card z-10">
                <div className="p-2 border-r text-xs font-medium text-muted-foreground">
                  Time
                </div>
                {days.map((day, index) => {
                  const isToday =
                    format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd");
                  return (
                    <div
                      key={index}
                      className={`p-2 border-r text-center ${
                        isToday ? "bg-primary/5" : ""
                      }`}
                    >
                      <div className="text-xs font-medium">
                        {format(day, "EEE")}
                      </div>
                      <div
                        className={`text-lg font-semibold ${
                          isToday ? "text-primary" : ""
                        }`}
                      >
                        {format(day, "d")}
                      </div>
                    </div>
                  );
                })}
              </div>

              {hours.map((hour) => (
                <div
                  key={hour}
                  className="grid grid-cols-8 border-b min-h-[60px]"
                  style={{ overflow: "visible" }}
                >
                  <div className="p-2 border-r text-xs text-muted-foreground">
                    {hour.toString().padStart(2, "0")}:00
                  </div>
                  {days.map((day, dayIndex) => {
                    const rawEvents: CalendarChip[] = combinedEvents
                      .filter((ev) => {
                        const start = parseISO(ev.start?.date_time ?? "");
                        if (!isSameDay(start, day)) return false;
                        return start.getHours() === hour;
                      })
                      .map((ev, idx) => {
                        const start = parseISO(ev.start?.date_time ?? "");
                        const end = parseISO(ev.end?.date_time ?? "");
                        const medColor =
                          ev.color ||
                          medColorMap[ev.title ?? ""] ||
                          "med-blue";
                        const durationMs = end.getTime() - start.getTime();
                        const durationMinutes = Math.max(
                          DEFAULT_EVENT_DURATION_MIN,
                          Math.round(durationMs / 60000)
                        );
                        const startMinutes = start.getMinutes();
                        return {
                          id: ev.id ?? `${dayIndex}-${hour}-${idx}`,
                          name: ev.title ?? "Event",
                          time: format(start, "HH:mm"),
                          color: medColor,
                          frequency: ev.source === "medication" ? "from schedule" : "external",
                          startDate: format(start, "yyyy-MM-dd"),
                          duration: durationMinutes,
                          startMinutes,
                        } as CalendarChip;
                      });

                    const placed = layoutColumns(rawEvents);
                    const isToday =
                      format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd");
                    return (
                      <div
                        key={dayIndex}
                        className={`p-1 border-r relative ${
                          isToday ? "bg-primary/5" : ""
                        }`}
                        style={{ minHeight: "60px", overflow: "visible" }}
                      >
                        {placed.map((event) => {
                          const hourHeight = 60;
                          const heightPx = (event.duration! / 60) * hourHeight;
                          const topOffsetPx =
                            (event.startMinutes! / 60) * hourHeight;
                          const cols = event.cols ?? 1;
                          const colIndex = event.col ?? 0;
                          const widthPercent = 100 / cols;
                          const leftPercent = colIndex * widthPercent;
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
                                width: `${widthPercent}%`,
                                backgroundColor: `hsl(var(--${event.color}))`,
                              }}
                              onClick={() => setSelectedMed(event)}
                            >
                              <div className="truncate leading-tight">
                                {event.name}
                              </div>
                              {event.duration! >= 60 && (
                                <div className="text-[10px] opacity-90 mt-0.5 leading-tight">
                                  {Math.floor(event.duration! / 60)}h{" "}
                                  {event.duration! % 60 > 0
                                    ? `${event.duration! % 60}m`
                                    : ""}
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

              {(loading || loadingMeds) && (
                <div className="p-3 text-xs text-muted-foreground">
                  Loading events…
                </div>
              )}
              {error && !(loading || loadingMeds) && (
                <div className="p-3 text-xs text-red-500">Error: {error}</div>
              )}
              {combinedEvents.length === 0 &&
                !loading &&
                !loadingMeds &&
                !error && (
                  <div className="p-3 text-xs text-muted-foreground">
                    No scheduled events for this week.
                  </div>
                )}
            </div>
        </div>
      </CardContent>

      <Dialog open={!!selectedMed} onOpenChange={() => setSelectedMed(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedMed?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 text-sm">
            <div>
              <strong>Time:</strong> {selectedMed?.time}
            </div>
            <div>
              <strong>Source:</strong> {selectedMed?.frequency}
            </div>
            <div>
              <strong>Date:</strong> {selectedMed?.startDate}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default WeekCalendar;
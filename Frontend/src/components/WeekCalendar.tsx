import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useEffect, useMemo, useState } from "react";
import { format, addDays, startOfWeek, isSameDay, parseISO } from "date-fns";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

// Medication type for color mapping
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
  color: string;
  frequency: string;
  startDate: string;
}

const WeekCalendar = () => {
  const today = new Date();
  const weekStart = startOfWeek(today, { weekStartsOn: 1 });
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const [events, setEvents] = useState<ApiEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMed, setSelectedMed] = useState<CalendarChip | null>(null);

  // Medications for color mapping
  const [medications, setMedications] = useState<Medication[]>([]);

  const baseUrl = (import.meta as any)?.env?.VITE_BACKEND_URL ?? "http://localhost:8000";

  // Fetch events
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

  // Fetch medications for color mapping
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
    fetchMedications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Map medication names to their colors
  const medColorMap = useMemo(() => {
    const map: Record<string, string> = {};
    medications.forEach((med) => {
      map[med.name] = med.color;
    });
    return map;
  }, [medications]);

  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Convert color name to Tailwind class for schedule display
  const colorToTailwind = (color: string) => {
    switch (color) {
      case "med-blue":
        return "bg-blue-500";
      case "med-green":
        return "bg-green-500";
      case "med-orange":
        return "bg-orange-500";
      case "med-purple":
        return "bg-purple-500";
      case "med-pink":
        return "bg-pink-500";
      case "med-yellow":
        return "bg-yellow-500";
      default:
        return "bg-gray-400";
    }
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-2 shrink-0">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-lg font-medium">7-Day Medication Schedule</CardTitle>
          <Button variant="outline" size="sm" onClick={refreshEvents} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 min-h-0 flex flex-col">
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="min-w-[800px]">
            {/* Day headers */}
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

            {/* Hour rows */}
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
                      // Use medication color if available, else fallback
                      const medColor = medColorMap[ev.title ?? ""] ?? "";
                      const colorClass = colorToTailwind(medColor);
                      return {
                        id: ev.id ?? `${dayIndex}-${hour}-${idx}`,
                        name: ev.title ?? "Event",
                        time: format(start, "HH:mm"),
                        color: colorClass,
                        frequency: "once",
                        startDate: format(start, "yyyy-MM-dd"),
                      };
                    });

                  const isToday = format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd");

                  return (
                    <div
                      key={dayIndex}
                      className={`p-1 border-r relative ${isToday ? "bg-primary/5/50" : ""}`}
                    >
                      {hourEvents.map((event) => (
                        <div
                          key={event.id}
                          className={`${event.color} text-white rounded px-2 py-1 mb-1 text-[10px] font-medium cursor-pointer transition hover:scale-105 hover:shadow-lg`}
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
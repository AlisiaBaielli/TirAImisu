import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { format, addDays, startOfWeek } from "date-fns";

interface MedicationEvent {
  id: number;
  name: string;
  time: string;
  color: string;
  frequency: string;
  startDate: string;
}

const WeekCalendar = () => {
  const today = new Date();
  const weekStart = startOfWeek(today);
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const mockEvents: { [key: string]: MedicationEvent[] } = {
    "0": [
      { id: 1, name: "Aspirin", time: "08:00", color: "bg-med-blue", frequency: "Daily", startDate: "2025-11-01" },
      { id: 2, name: "Vitamin D", time: "12:00", color: "bg-med-green", frequency: "Weekly", startDate: "2025-11-03" },
      { id: 3, name: "Metformin", time: "18:00", color: "bg-med-orange", frequency: "Daily", startDate: "2025-11-01" },
    ],
    "1": [
      { id: 4, name: "Aspirin", time: "08:00", color: "bg-med-blue", frequency: "Daily", startDate: "2025-11-01" },
      { id: 5, name: "Vitamin D", time: "12:00", color: "bg-med-green", frequency: "Weekly", startDate: "2025-11-03" },
    ],
    "2": [
      { id: 6, name: "Aspirin", time: "08:00", color: "bg-med-blue", frequency: "Daily", startDate: "2025-11-01" },
      { id: 7, name: "Metformin", time: "18:00", color: "bg-med-orange", frequency: "Daily", startDate: "2025-11-01" },
    ],
  };

  const hours = Array.from({ length: 24 }, (_, i) => i);
  const [selectedMed, setSelectedMed] = useState<MedicationEvent | null>(null);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="shrink-0">
        <CardTitle>7-Day Medication Schedule</CardTitle>
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
                  const dayEvents = mockEvents[dayIndex.toString()] || [];
                  const hourEvents = dayEvents.filter(
                    (event) => parseInt(event.time.split(":")[0]) === hour
                  );
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
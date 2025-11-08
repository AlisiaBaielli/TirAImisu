import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { format, addDays, startOfWeek } from "date-fns";

interface MedicationEvent {
  id: number;
  name: string;
  time: string;
  color: string;
}

const WeekCalendar = () => {
  const today = new Date();
  const weekStart = startOfWeek(today);
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const mockEvents: { [key: string]: MedicationEvent[] } = {
    "0": [
      { id: 1, name: "Aspirin", time: "08:00", color: "bg-med-blue" },
      { id: 2, name: "Vitamin D", time: "12:00", color: "bg-med-green" },
      { id: 3, name: "Metformin", time: "18:00", color: "bg-med-orange" },
    ],
    "1": [
      { id: 4, name: "Aspirin", time: "08:00", color: "bg-med-blue" },
      { id: 5, name: "Vitamin D", time: "12:00", color: "bg-med-green" },
    ],
    "2": [
      { id: 6, name: "Aspirin", time: "08:00", color: "bg-med-blue" },
      { id: 7, name: "Metformin", time: "18:00", color: "bg-med-orange" },
    ],
  };

  const hours = Array.from({ length: 24 }, (_, i) => i);

  return (
    <Card className="h-[calc(100vh-180px)]">
      <CardHeader>
        <CardTitle>7-Day Medication Schedule</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-auto h-[calc(100vh-260px)]">
          <div className="min-w-[800px]">
            {/* Header with days */}
            <div className="grid grid-cols-8 border-b sticky top-0 bg-card z-10">
              <div className="p-2 border-r text-xs font-medium text-muted-foreground">Time</div>
              {days.map((day, index) => (
                <div
                  key={index}
                  className={`p-2 border-r text-center ${
                    format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd")
                      ? "bg-primary/5"
                      : ""
                  }`}
                >
                  <div className="text-xs font-medium">{format(day, "EEE")}</div>
                  <div
                    className={`text-lg font-semibold ${
                      format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd")
                        ? "text-primary"
                        : ""
                    }`}
                  >
                    {format(day, "d")}
                  </div>
                </div>
              ))}
            </div>

            {/* Calendar grid */}
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
                        format(day, "yyyy-MM-dd") === format(today, "yyyy-MM-dd")
                          ? "bg-primary/5"
                          : ""
                      }`}
                    >
                      {hourEvents.map((event) => (
                        <div
                          key={event.id}
                          className={`${event.color} text-white rounded px-2 py-1 mb-1 text-xs font-medium`}
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
    </Card>
  );
};

export default WeekCalendar;

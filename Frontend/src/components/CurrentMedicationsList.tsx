import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pill } from "lucide-react";

const CurrentMedicationsList = () => {
  const medications = [
    { id: 1, name: "Aspirin 100mg", time: "8:00 AM", frequency: "Daily", color: "med-blue" },
    { id: 2, name: "Vitamin D 2000IU", time: "12:00 PM", frequency: "Weekly", color: "med-green" },
    { id: 3, name: "Metformin 500mg", time: "6:00 PM", frequency: "Daily", color: "med-orange" },
  ];

  return (
    <Card className="animate-fade-in">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Current Medications</CardTitle>
      </CardHeader>
      <CardContent>
        {medications.length === 0 ? (
          <p className="text-sm text-muted-foreground">No medications added yet</p>
        ) : (
          <div className="space-y-2">
            {medications.map((med) => (
              <div
                key={med.id}
                className="flex items-center gap-3 p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-all hover-scale cursor-pointer animate-scale-in"
              >
                <div className={`p-1.5 rounded-md bg-${med.color}/20`}>
                  <Pill className={`h-4 w-4`} style={{ color: `hsl(var(--${med.color}))` }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: `hsl(var(--${med.color}))` }}>
                    {med.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    <span><strong>Time:</strong> {med.time}</span> |{" "}
                    <span><strong>Frequency:</strong> {med.frequency}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default CurrentMedicationsList;
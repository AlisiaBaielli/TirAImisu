import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pill } from "lucide-react";

interface Medication {
  id: number;
  name: string;
  frequency: string;
  pillsLeft: number;
  color: string;
}

const CurrentMedicationsList = () => {
  const medications: Medication[] = [
    { id: 1, name: "Aspirin 100mg", frequency: "Daily", pillsLeft: 12, color: "med-blue" },
    { id: 2, name: "Vitamin D 2000IU", frequency: "Weekly", pillsLeft: 4, color: "med-green" },
    { id: 3, name: "Metformin 500mg", frequency: "Daily", pillsLeft: 20, color: "med-orange" },
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
                  <Pill className="h-4 w-4" style={{ color: `hsl(var(--${med.color}))` }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: `hsl(var(--${med.color}))` }}>
                    {med.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    <strong>Frequency:</strong> {med.frequency} | <strong>Pills left:</strong> {med.pillsLeft}
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
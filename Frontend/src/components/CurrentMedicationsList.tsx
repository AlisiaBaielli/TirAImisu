import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pill } from "lucide-react";
import { useEffect, useState } from "react";

type Medication = {
  id: string | number;
  name: string;
  time: number; // hour 0-23
  color: string; // e.g. "med-blue"
};

interface Medication {
  id: number;
  name: string;
  frequency: string;
  pillsLeft: number;
  color: string;
}

const CurrentMedicationsList = () => {
  const [medications, setMedications] = useState<Medication[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const formatHour = (hour: number) => {
    if (Number.isNaN(hour)) return "";
    const h = Math.max(0, Math.min(23, Math.trunc(hour)));
    const suffix = h >= 12 ? "PM" : "AM";
    const display = h % 12 === 0 ? 12 : h % 12;
    return `${display}:00 ${suffix}`;
  };

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const base = (import.meta as any)?.env?.VITE_BACKEND_URL ?? "http://localhost:8000";
        const res = await fetch(`${base}/api/medications`);
        if (!res.ok) throw new Error(`Failed to load medications (${res.status})`);
        const data = await res.json();
        setMedications(Array.isArray(data?.medications) ? data.medications : []);
      } catch (e: any) {
        setError(e?.message ?? "Failed to load medications");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <Card className="animate-fade-in">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Current Medications</CardTitle>
      </CardHeader>
      <CardContent>
        {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {error && !loading && <p className="text-sm text-destructive">{error}</p>}
        {!loading && !error && medications.length === 0 ? (
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
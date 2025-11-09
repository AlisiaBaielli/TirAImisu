import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pill } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface Medication {
  id: number | string;
  name: string;
  frequency: string;
  pillsLeft: number;
  color?: string; // e.g., "med-blue"
}

const VISIBLE_ROWS = 3;
const ROW_HEIGHT = 56;
const GAP = 8;
const LIST_HEIGHT = VISIBLE_ROWS * ROW_HEIGHT + (VISIBLE_ROWS - 1) * GAP;

const CurrentMedicationsList = () => {
  const [medications, setMedications] = useState<Medication[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const raw = (import.meta as any)?.env?.VITE_BACKEND_URL;
  const base = raw ? String(raw).replace(/\/$/, "") : ""; // empty string fallback

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const userId = localStorage.getItem("userId") || "1";
      const res = await fetch(`${base}/api/users/${userId}/medications`);
      if (!res.ok) throw new Error(`Failed to load medications (${res.status})`);
      const data = await res.json();
      const meds = Array.isArray(data?.medications) ? data.medications : [];
      setMedications(meds);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load medications");
    } finally {
      setLoading(false);
    }
  }, [base]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const handler = () => load();
    window.addEventListener("medications:updated", handler);
    return () => window.removeEventListener("medications:updated", handler);
  }, [load]);

  return (
    <Card className="animate-fade-in">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Current Medications</CardTitle>
      </CardHeader>
      <CardContent className="min-h-0">
        {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {error && !loading && <p className="text-sm text-destructive">{error}</p>}
        {!loading && !error && medications.length === 0 ? (
          <p className="text-sm text-muted-foreground">No medications added yet</p>
        ) : (
          <div className="space-y-2 overflow-y-auto custom-scrollbar" style={{ height: LIST_HEIGHT }}>
            {medications.map((med) => {
              const c = med.color || "med-blue";
              return (
                <div
                  key={med.id}
                  className="flex items-center gap-3 p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-all cursor-pointer"
                  style={{ height: ROW_HEIGHT - 8 }}
                >
                  <div className="p-1.5 rounded-md" style={{ backgroundColor: `hsl(var(--${c}) / 0.18)` }}>
                    <Pill className="h-4 w-4" style={{ color: `hsl(var(--${c}))` }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: `hsl(var(--${c}))` }}>
                      {med.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      <strong>Frequency:</strong> {med.frequency} | <strong>Pills left:</strong> {med.pillsLeft}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default CurrentMedicationsList;
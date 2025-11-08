import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pill } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

interface Medication {
  id: number | string;
  name: string;
  frequency: string;
  pillsLeft: number;
  color?: string; // e.g., "med-blue" -> CSS var --med-blue
}

const PALETTE = ["med-blue", "med-green", "med-orange", "med-purple", "med-pink", "med-yellow"] as const;

function hashString(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function ensureUniqueColors(items: Medication[]): Medication[] {
  const used = new Set<string>();
  return items.map((m) => {
    const base = typeof m.color === "string" && m.color ? m.color : PALETTE[hashString(m.name) % PALETTE.length];
    // If already used, pick the next available in palette
    let color = base;
    if (used.has(color)) {
      const start = PALETTE.indexOf(base as any);
      for (let i = 1; i < PALETTE.length; i++) {
        const candidate = PALETTE[(start + i) % PALETTE.length];
        if (!used.has(candidate)) {
          color = candidate;
          break;
        }
      }
    }
    used.add(color);
    return { ...m, color };
  });
}

const CurrentMedicationsList = () => {
  const [medications, setMedications] = useState<Medication[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const base = (import.meta as any)?.env?.VITE_BACKEND_URL ?? "http://localhost:8000";

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

  const coloredMeds = useMemo(() => ensureUniqueColors(medications), [medications]);

  return (
    <Card className="animate-fade-in">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Current Medications</CardTitle>
      </CardHeader>
      <CardContent>
        {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {error && !loading && <p className="text-sm text-destructive">{error}</p>}
        {!loading && !error && coloredMeds.length === 0 ? (
          <p className="text-sm text-muted-foreground">No medications added yet</p>
        ) : (
          <div className="space-y-2">
            {coloredMeds.map((med) => (
              <div
                key={med.id}
                className="flex items-center gap-3 p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-all hover-scale cursor-pointer animate-scale-in"
              >
                <div
                  className="p-1.5 rounded-md"
                  style={{ backgroundColor: `hsl(var(--${med.color}) / 0.2)` }}
                >
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
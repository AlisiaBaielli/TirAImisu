import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Camera, Settings } from "lucide-react";
import ScanMedicationDialog, { NewMedicationPayload } from "./ScanMedicationDialog";
import InteractionsDialog from "./InteractionsDialog";
import { toast } from "sonner";

const ScanMedicationButton = () => {
  const [scanOpen, setScanOpen] = useState(false);
  const [interactionsOpen, setInteractionsOpen] = useState(false);

  const [newMed, setNewMed] = useState<string | undefined>();
  const [conflictWith, setConflictWith] = useState<string | undefined>();
  const [description, setDescription] = useState<string | undefined>();
  const [interactionFound, setInteractionFound] = useState<boolean>(false);

  // Top-center floating loading
  const [checking, setChecking] = useState(false);

  const base = (import.meta as any)?.env?.VITE_BACKEND_URL ?? "http://localhost";

  const handleScanConfirm = async (data: NewMedicationPayload) => {
    setScanOpen(false);
    setChecking(true); // show "Checking interactions..." banner

    const userId = localStorage.getItem("userId") || "1";

    // Build payload to persist into personal_medication.json
    const drugName = data.name.trim();
    const strength = data.dosage.trim();
    const quantity = data.numberOfPills ? parseInt(data.numberOfPills, 10) || 0 : 0;
    const schedule: any = {};
    if (data.frequency) {
      schedule.type = data.frequency;
      if (data.time) schedule.times = [data.time];
    }

    const medPayload: any = {
      drug_name: drugName,
      strength,
      quantity_left: quantity,
      schedule: Object.keys(schedule).length ? schedule : undefined,
      start_date: data.startDate || undefined,
      end_date: data.endDate || undefined,
    };

    try {
      // 1) persist medication
      const resAdd = await fetch(`${base}/api/users/${encodeURIComponent(userId)}/medications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(medPayload),
      });

      if (!resAdd.ok) {
        const txt = await resAdd.text().catch(() => `Status ${resAdd.status}`);
        throw new Error(`Failed to save medication: ${txt}`);
      }

      // update list
      window.dispatchEvent(new Event("medications:updated"));

      // 2) interactions (only send drug name)
      const res = await fetch(`${base}/api/drug-interactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, new_medication_name: drugName }),
      });

      if (!res.ok) {
        const txt = await res.text().catch(() => `Status ${res.status}`);
        throw new Error(`Interaction check failed: ${txt}`);
      }

      const json = await res.json();
      const interactions = Array.isArray(json?.interactions) ? json.interactions : [];

      setNewMed(drugName);

      if (interactions.length > 0) {
        const first = interactions[0];
        setConflictWith(first.existing_drug);
        setDescription(first.description || first.extended_description || "Potential interaction detected.");
        setInteractionFound(Boolean(first.interaction_found));
      } else {
        setConflictWith(undefined);
        setDescription("No interactions detected with current medications.");
        setInteractionFound(false);
      }
    } catch (e: any) {
      setNewMed(`${data.name}${data.dosage ? ` (${data.dosage})` : ""}`);
      setConflictWith(undefined);
      setDescription(e?.message ?? "Interaction check failed");
      setInteractionFound(false);
      toast.error(e?.message ?? "Error during save/check");
    } finally {
      setChecking(false); // hide banner
      setInteractionsOpen(true);
    }
  };

  return (
    <>
      {/* Floating top-center gear while checking */}
      {checking && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] pointer-events-none">
          <div className="bg-black/80 text-white px-4 py-2 rounded-full shadow-lg flex items-center gap-2">
            <Settings className="h-4 w-4 animate-spin" />
            <span className="text-sm font-medium">Checking interactions…</span>
          </div>
        </div>
      )}

      <Button
        size="lg"
        className="fixed bottom-8 left-1/2 -translate-x-1/2 shadow-lg gap-2 z-50"
        onClick={() => setScanOpen(true)}
      >
        <Camera className="h-5 w-5" />
        Add Medication
      </Button>

      <ScanMedicationDialog open={scanOpen} onOpenChange={setScanOpen} onConfirm={handleScanConfirm} />

      <InteractionsDialog
        open={interactionsOpen}
        onOpenChange={setInteractionsOpen}
        newMedicationName={newMed}
        conflictWith={conflictWith}
        description={description}
        interactionFound={interactionFound}
      />
    </>
  );
};

export default ScanMedicationButton;
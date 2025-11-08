import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Camera } from "lucide-react";
import ScanMedicationDialog, { NewMedicationPayload } from "./ScanMedicationDialog";
import InteractionsDialog, { InteractionSeverity } from "./InteractionsDialog";

// Demo list; mirrors CurrentMedicationsList
const existingMeds = ["Aspirin 100mg", "Vitamin D 2000IU", "Metformin 500mg"];

function evaluateInteraction(newMedName: string) {
  const n = newMedName.toLowerCase();
  if (n.includes("aspirin")) {
    return {
      conflictWith: "Metformin 500mg",
      severity: "high" as InteractionSeverity,
      description: "Increased risk of side effects. Consult your doctor.",
    };
  }
  if (n.includes("vitamin")) {
    return {
      conflictWith: "Metformin 500mg",
      severity: "low" as InteractionSeverity,
      description: "May affect absorption. Consider taking at different times.",
    };
  }
  return {
    conflictWith: existingMeds[0],
    severity: "low" as InteractionSeverity,
    description: "Minor interaction. Monitor for unusual symptoms.",
  };
}

const ScanMedicationButton = () => {
  const [scanOpen, setScanOpen] = useState(false);
  const [interactionsOpen, setInteractionsOpen] = useState(false);

  const [newMed, setNewMed] = useState<string | undefined>();
  const [conflictWith, setConflictWith] = useState<string | undefined>();
  const [severity, setSeverity] = useState<InteractionSeverity>("low");
  const [description, setDescription] = useState<string | undefined>();

  const handleScanConfirm = (data: NewMedicationPayload) => {
    setScanOpen(false);

    const evalRes = evaluateInteraction(data.name);
    setNewMed(`${data.name}${data.dosage ? ` (${data.dosage})` : ""}`);
    setConflictWith(evalRes.conflictWith);
    setSeverity(evalRes.severity);
    setDescription(evalRes.description);

    setInteractionsOpen(true);
  };

  return (
    <>
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
        severity={severity}
        description={description}
      />
    </>
  );
};

export default ScanMedicationButton;

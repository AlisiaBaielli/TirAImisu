import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Camera } from "lucide-react";
import ScanMedicationDialog from "./ScanMedicationDialog";
import InteractionsDialog from "./InteractionsDialog";

const ScanMedicationButton = () => {
  const [scanOpen, setScanOpen] = useState(false);
  const [interactionsOpen, setInteractionsOpen] = useState(false);

  const handleScanConfirm = () => {
    setScanOpen(false);
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
        Scan Medication
      </Button>

      <ScanMedicationDialog
        open={scanOpen}
        onOpenChange={setScanOpen}
        onConfirm={handleScanConfirm}
      />

      <InteractionsDialog
        open={interactionsOpen}
        onOpenChange={setInteractionsOpen}
      />
    </>
  );
};

export default ScanMedicationButton;

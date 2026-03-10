import { createContext, useContext, useState, type ReactNode } from "react";
import type { MedicineDraftItem } from "../types/medicine";

interface MedicationFlowContextValue {
  medicinesDraft: MedicineDraftItem[];
  addDraft: (item: MedicineDraftItem) => void;
  updateDraft: (index: number, item: MedicineDraftItem) => void;
  removeDraft: (indices: number[]) => void;
  clearDraft: () => void;
}

const MedicationFlowContext = createContext<MedicationFlowContextValue | null>(null);

export function MedicationFlowProvider({ children }: { children: ReactNode }) {
  const [medicinesDraft, setMedicinesDraft] = useState<MedicineDraftItem[]>([]);

  const addDraft = (item: MedicineDraftItem) =>
    setMedicinesDraft((prev) => [...prev, item]);

  const updateDraft = (index: number, item: MedicineDraftItem) =>
    setMedicinesDraft((prev) => prev.map((d, i) => (i === index ? item : d)));

  const removeDraft = (indices: number[]) =>
    setMedicinesDraft((prev) => prev.filter((_, i) => !indices.includes(i)));

  const clearDraft = () => setMedicinesDraft([]);

  return (
    <MedicationFlowContext.Provider
      value={{ medicinesDraft, addDraft, updateDraft, removeDraft, clearDraft }}
    >
      {children}
    </MedicationFlowContext.Provider>
  );
}

export function useMedicationFlow(): MedicationFlowContextValue {
  const ctx = useContext(MedicationFlowContext);
  if (!ctx) throw new Error("useMedicationFlow must be used within MedicationFlowProvider");
  return ctx;
}

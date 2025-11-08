from typing import List
from Backend.medications.medication import Medication


def get_current_medications() -> List[Medication]:
    """
    Return the current medications for the user.
    For now, this returns a static list matching the frontend's expected fields.
    """
    return [
        Medication(id="1", name="Aspirin 100mg", time=8, color="med-blue", hour_interval=24),
        Medication(id="2", name="Vitamin D 2000IU", time=12, color="med-green", hour_interval=24),
        Medication(id="3", name="Metformin 500mg", time=18, color="med-orange", hour_interval=24),
    ]



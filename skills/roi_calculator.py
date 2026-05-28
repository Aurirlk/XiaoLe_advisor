from typing import Dict


def calculate_roi(tuition_per_year: int, years: int, avg_start_salary: int) -> Dict[str, float]:
    total_cost = tuition_per_year * years
    if avg_start_salary <= 0:
        return {"roi_ratio": -1.0, "total_cost": float(total_cost)}
    return {"roi_ratio": round(total_cost / avg_start_salary, 2), "total_cost": float(total_cost)}

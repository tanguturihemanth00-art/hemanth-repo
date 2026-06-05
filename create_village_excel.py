import pandas as pd
from pathlib import Path

# Create some dummy data
data = {
    "Task ID": ["V-001", "V-002", "V-003"],
    "Action": ["Verify Report", "Download PDF", "Check Status"]
}
df = pd.DataFrame(data)

# The user requested the sheet name to hold the metadata: VillageName_Month_Year
sheet_name = "Springfield_August_2023"

out_path = Path("data/input/village_report.xlsx")
out_path.parent.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(out_path) as writer:
    df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Created {out_path} with sheet '{sheet_name}'")

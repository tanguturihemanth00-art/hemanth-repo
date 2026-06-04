import pandas as pd
from pathlib import Path

data = {
    "Task ID": ["T-001"],
    "Action": ["Verify Login"]
}
df = pd.DataFrame(data)
out_path = Path("data/input/demo.xlsx")
out_path.parent.mkdir(parents=True, exist_ok=True)
df.to_excel(out_path, index=False)
print(f"Created {out_path}")

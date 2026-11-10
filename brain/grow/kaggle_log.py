"""Print the end of the Kaggle training log, so a failed training explains itself in the run log.
The training script prints only counts, loss values and errors, never his lessons."""
import glob
import json
import sys

for path in glob.glob(sys.argv[1] + "/*.log"):
    raw = open(path, encoding="utf-8", errors="replace").read()
    try:   # Kaggle keeps the log as a list of {"stream_name", "time", "data"} pieces
        text = "".join(str(piece.get("data", "")) for piece in json.loads(raw))
    except (ValueError, AttributeError):
        text = raw
    for line in [l for l in text.splitlines() if l.strip()][-45:]:
        print("  | " + line[:300])

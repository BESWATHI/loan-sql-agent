"""
make_diagram.py - draws docs/workflow_diagram.png (the agent workflow).
Run from the project folder: python3 docs/make_diagram.py
Needs matplotlib: pip install matplotlib
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
plt.rcParams["font.family"] = "DejaVu Sans"

def box(x, y, w, h, title, body, face, edge):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.18",
                                facecolor=face, edgecolor=edge, linewidth=2))
    ax.text(x + w/2, y + h - 0.32, title, ha="center", va="top", fontsize=14, fontweight="bold", color="#1f2933")
    ax.text(x + w/2, y + h - 0.85, body, ha="center", va="top", fontsize=11.5, color="#323f4b", linespacing=1.45)

def arrow(x1, y1, x2, y2, label="", lx=0, ly=0, color="#3e4c59", rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=22,
                                 linewidth=2, color=color, connectionstyle="arc3,rad=%s" % rad))
    if label:
        ax.text((x1 + x2)/2 + lx, (y1 + y2)/2 + ly, label, ha="center", va="center",
                fontsize=11, color=color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none"))

ax.text(8, 8.65, "Loan Portfolio SQL Agent: workflow", ha="center", fontsize=20, fontweight="bold", color="#1f2933")

# 1 question
box(0.2, 5.6, 2.7, 1.7, "1. User question", "\"How many loans\nare in default?\"", "#f5f7fa", "#9aa5b1")
# 2 model
box(3.5, 5.3, 3.2, 2.3, "2. Model decides", "qwen3:8b via Ollama\npicks the next tool\nand gives a reason", "#e3f0ff", "#2f6fbf")
# 3 tools
box(8.3, 4.3, 3.4, 3.9, "3. Python runs the tool", "get_schema\nget_distinct_values\nrun_sql\n\n(the model chooses;\nPython only executes)", "#e6f6ec", "#2f8f4e")
# guard + db
box(12.5, 4.3, 3.2, 3.9, "Read-only guard", "SELECT only\napproved tables only\nrefuses values not\nin the data\n3 s limit, 200 rows\n\nSQLite loans.db\n300 borrowers, 600 loans", "#fff4e5", "#c77700")

arrow(2.9, 6.45, 3.5, 6.45)
arrow(6.7, 7.0, 8.3, 7.0, "tool call", ly=0.32, color="#2f6fbf")
arrow(8.3, 5.7, 6.7, 5.7, "4. result\nor error", ly=-0.5, color="#2f8f4e")
arrow(11.7, 6.6, 12.5, 6.6)
arrow(12.5, 5.6, 11.7, 5.6)
ax.text(10.0, 3.95, "Steps 2 to 4 repeat until the model calls submit_answer (max 10 steps)", ha="center", fontsize=11, style="italic", color="#52606d")

# 5 final answer
box(3.5, 1.0, 3.2, 2.3, "5. submit_answer", "status, answer,\nkey numbers, SQL used,\nassumptions", "#e3f0ff", "#2f6fbf")
arrow(5.1, 5.3, 5.1, 3.3, "model is done", lx=-1.05, color="#2f6fbf")
# 6 verify
box(8.3, 0.6, 3.4, 2.9, "6. verify.py", "checked by Python,\nnot by the model:\nmatches hand-checked values\nnumbers in real tool output\ndatabase file unchanged", "#f3ebff", "#7a4fc4")
arrow(6.7, 2.15, 8.3, 2.15)
# 7 record
box(12.5, 1.0, 3.2, 2.3, "7. Run record", "RUN_RECORD.md\ntrace.jsonl\nPASS / FAIL", "#f5f7fa", "#9aa5b1")
arrow(11.7, 2.15, 12.5, 2.15)

import os
OUT = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(OUT, "workflow_diagram.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.savefig(os.path.join(OUT, "workflow_diagram.svg"), bbox_inches="tight", facecolor="white")

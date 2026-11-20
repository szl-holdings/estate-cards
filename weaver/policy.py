"""HF repo -> canonical GitHub source mapping + card policy (estate-known pairs)."""

GH = "https://github.com/szl-holdings"

# explicit pairs (extend as sourcing closes the gaps)
MAP = {
    "SZLHOLDINGS/szl-khipu": GH + "/szl-khipu",
    "SZLHOLDINGS/salad-khipu-scholar-v1": GH + "/szl-khipu-scholar",
    "SZLHOLDINGS/khipu-scholar-runs": GH + "/szl-khipu-scholar",
    "SZLHOLDINGS/salad-flagship54-v2": GH + "/szl-frontier",
    "SZLHOLDINGS/salad-flagship54-v1": GH + "/szl-frontier",
    "SZLHOLDINGS/frontier-54-runs": GH + "/szl-frontier",
    "SZLHOLDINGS/salad-x402-frontier-v2": GH + "/szl-frontier",
    "SZLHOLDINGS/salad-x402-frontier-v1": GH + "/szl-frontier",
    "SZLHOLDINGS/frontier-54-doctrine-math-r1-candidate": GH + "/szl-frontier",
    "SZLHOLDINGS/proving-ground-54h-mesh": GH + "/szl-frontier",
    "SZLHOLDINGS/khipu-scholars-sft-v1": GH + "/szl-khipu-scholar",
    "SZLHOLDINGS/mesh-liveness": GH + "/szl-mesh",
    "SZLHOLDINGS/llm-router-live": GH + "/szl-router",
    "SZLHOLDINGS/david-leads": GH + "/david-leads",
    "SZLHOLDINGS/szl-second-brain": GH + "/szl-second-brain",
    "SZLHOLDINGS/a11oy": GH + "/a11oy",
    "SZLHOLDINGS/szl-command-lab": GH + "/szl-command-lab",
    "SZLHOLDINGS/counsel": GH + "/counsel",
    "SZLHOLDINGS/finance": GH + "/finance",
    "SZLHOLDINGS/terra": GH + "/terra",
    "SZLHOLDINGS/sentra": GH + "/sentra",
    "SZLHOLDINGS/khipu-scholar-4b-v1-checkpoints": GH + "/szl-khipu-scholar",
}

def source_for(repo_id):
    return MAP.get(repo_id, GH + " (org)")


# first wave: flagship repos get hand-tuned evidence-rich cards
FIRST_WAVE = [
    ("model", "SZLHOLDINGS/salad-khipu-scholar-v1"),
    ("model", "SZLHOLDINGS/salad-flagship54-v2"),
    ("model", "SZLHOLDINGS/salad-x402-frontier-v2"),
    ("model", "SZLHOLDINGS/SZL-Khipu-Yachay-Nano"),
    ("model", "SZLHOLDINGS/frontier-54-doctrine-math-r1-candidate"),
    ("dataset", "SZLHOLDINGS/khipu-scholar-runs"),
    ("dataset", "SZLHOLDINGS/frontier-54-runs"),
    ("dataset", "SZLHOLDINGS/proving-ground-54h-mesh"),
    ("dataset", "SZLHOLDINGS/khipu-scholars-sft-v1"),
    ("dataset", "SZLHOLDINGS/mesh-liveness"),
    ("space", "SZLHOLDINGS/a11oy"),
    ("space", "SZLHOLDINGS/szl-command-lab"),
    ("space", "SZLHOLDINGS/llm-router-live"),
]

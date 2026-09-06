
import os
import dotenv
import argparse
import json
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel
from typing import Literal

from LP.implementation import formulate_logic_program
from FOL.implementation import formulate_FOL_program
from CSP.implementation import formulate_CSP_program
from SAT.implementation import formulate_SAT_program


dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


FORMULATOR_SYSTEM_PROMPT = """
You are the Problem Formulator for a Logic-LM reasoning system.

Your job is to determine which symbolic reasoning approach is most
appropriate for solving a natural-language problem.

You DO NOT translate the problem into LP, FOL, CSP, Prolog, Python,
or any other symbolic representation.

You ONLY select the reasoning approach.

The available approaches are:

1. LP
2. FOL
3. CSP
4. SAT

============================================================
LP
============================================================

Choose LP when the problem is primarily about:

- Facts and rules
- Relationships between entities
- Forward or backward chaining
- Deriving conclusions from rules
- Recursive relationships
- Family relationships
- Classification from rules
- Knowledge-base style reasoning

Examples:

"Bob is kind. Kind people are friendly. Is Bob friendly?"

"John is the father of Alice. Alice is the mother of Bob. Who is Bob's
grandparent?"

"Anyone who studies hard passes. Alice studies hard. Does Alice pass?"

LP is appropriate when the problem can naturally be represented as
facts plus logical rules and queried through rule-based inference.

============================================================
FOL
============================================================

Choose FOL when the problem requires formal logical reasoning involving:

- Universal statements
- Existential statements
- Quantifiers
- Implication
- Negation
- Relationships between multiple entities
- Proving whether a proposition follows from premises
- First-order logical entailment
- Theorem-proving style questions

Examples:

"Every human is mortal. Socrates is human. Is Socrates mortal?"

"Every student who studies passes. Alice is a student. Alice does not
study. Can we conclude Alice passes?"

"Some student is intelligent. Everyone intelligent is successful.
Does there exist a successful student?"

FOL is especially appropriate when the natural-language problem is
expressed as premises and a conjecture that must be logically proven.

============================================================
CSP
============================================================

Choose CSP when the problem is primarily about:

- Assigning values to variables
- Scheduling
- Ordering
- Seating arrangements
- Timetables
- Resource allocation
- Matching
- Puzzles
- Numeric assignments
- Finite domains
- Constraints between possible assignments
- Finding one or all assignments satisfying constraints

Examples:

"Alice, Bob, and Charlie each have a number from 1 to 3. Everyone
must have a different number."

"Four students must be assigned to four different seats."

"John cannot work Monday. Sarah must work Tuesday. Each employee must
work exactly one day."

"Three numbers must add up to 15 and all numbers must be different."

CSP is appropriate when the central task is finding assignments that
satisfy a collection of constraints.

============================================================
SAT
============================================================

Choose SAT for analytical-reasoning problems with Boolean choices,
exactly/at-least/at-most conditions, and answer choices whose validity is
determined by satisfying the stated rules. AR-LSAT is the primary example.

============================================================
DECISION RULES
============================================================

Choose the approach based on the STRUCTURE of the problem, not isolated
words.

Do not choose CSP merely because numbers appear.

Do not choose FOL merely because words such as "every" or "all" appear.

Do not choose LP merely because the problem contains facts.

Ask:

1. Is this primarily a finite assignment/search problem?
   -> CSP

2. Is this primarily theorem proving with quantified logical statements?
   -> FOL

3. Is this primarily a knowledge base of facts and rules?
   -> LP

============================================================
IMPORTANT
============================================================

You are selecting a solver, not solving the problem.

Do not answer the user's question.

Do not translate the problem.

Do not create predicates.

Do not create rules.

Do not create variables.

Do not create domains.

Do not perform inference.

============================================================
OUTPUT
============================================================

Return exactly:

approach

The value must be exactly one of:

"LP"
"FOL"
"CSP"
"SAT"

Do not return explanations or additional fields.
"""


class FormulatorOutput(BaseModel):
    approach: Literal["LP", "FOL", "CSP", "SAT"]


# Select reasoner.
def select_reasoner(text):
    if client is None:
        raise RuntimeError(
            "An OpenAI API key is required for natural-language formulation. "
            "Set OPENAI_API_KEY or OPENAI_KEY."
        )
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": FORMULATOR_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": text
            }
        ],
        response_format=FormulatorOutput
    )

    result = response.choices[0].message.parsed

    if result is None:
        raise ValueError(
            "The problem formulator failed to select a reasoning approach."
        )

    return result.approach


# Solve.
def solve(text, announce=True):
    approach = select_reasoner(text)

    if announce:
        print("\n================ SELECTED REASONER ================\n")
        print(approach)

    if approach == "LP":
        return formulate_logic_program(text)

    if approach == "FOL":
        return formulate_FOL_program(text)

    if approach == "CSP":
        return formulate_CSP_program(text)

    if approach == "SAT":
        return formulate_SAT_program(text)

    raise ValueError(
        f"Unknown reasoning approach: {approach}"
    )

# Loadprontoqa.
def LoadProntoQA():
    import json
    with open("datasets/ProntoQA.json", "r") as file:
        data = file.read()

    data = json.loads(data)
    output=[]
    for item in data:
        individual = {}
        individual["context"] = item["context"]
        individual["question"] = item["question"] + " " + str(item["options"])
        individual["answer"] = item["answer"]
        individual["id"] = item["id"]
        output.append(individual)
    return output


REAL_DATA_ROOT = Path(__file__).resolve().parent / "datasets" / "real"
MERGED_DATASET_PATH = REAL_DATA_ROOT / "merged" / "all.jsonl"
REAL_DATASETS = (
    "prontoqa",
    "proofwriter",
    "folio",
    "logical_deduction",
    "ar_lsat",
)


#  read jsonl.
def _read_jsonl(path, limit=None):
    records = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
                if limit and len(records) >= limit:
                    break
    return records


# Load real dataset.
def load_real_dataset(dataset, split="test", limit=None):






    key = dataset.lower().replace("-", "_")
    aliases = {
        "prontoqa": "prontoqa",
        "proofwriter": "proofwriter",
        "folio": "folio",
        "logicaldeduction": "logical_deduction",
        "logical_deduction": "logical_deduction",
        "arlsat": "ar_lsat",
        "ar_lsat": "ar_lsat",
    }
    key = aliases.get(key, key)
    path = REAL_DATA_ROOT / key / f"{split}.jsonl"
    if key == "prontoqa":
        path = REAL_DATA_ROOT / key / f"{split}.json"

    source_split = split
    if not path.exists():
                                                                             
                                                                            
                                                                            
        fallback_splits = {
            "test": ["validation", "train"],
            "validation": ["train"],
        }
        for fallback in fallback_splits.get(split, []):
            candidate = REAL_DATA_ROOT / key / f"{fallback}.jsonl"
            if key == "prontoqa":
                candidate = REAL_DATA_ROOT / key / f"{fallback}.json"
            if candidate.exists():
                path = candidate
                source_split = fallback
                break
        else:
            raise FileNotFoundError(f"Downloaded split not found: {path}")

    if key == "prontoqa":
        raw = json.loads(path.read_text(encoding="utf-8"))
        records = []
        for group_id, group in raw.items():
            example = group.get("test_example") or group.get("in_context_example0")
            if not example:
                continue
            records.append({
                "id": group_id,
                "dataset": "PrOntoQA",
                "pipeline": "LP",
                "text": example["question"] + "\n" + example["query"],
                "expected": True,
                "requested_split": split,
                "source_split": source_split,
                "raw": example,
            })
            if limit and len(records) >= limit:
                break
        return records

    raw_records = _read_jsonl(path, limit)
    records = []
    for index, raw in enumerate(raw_records):
        if key == "folio":
            text = raw["premises"] + "\nConclusion: " + raw["conclusion"]
            expected = str(raw.get("label", "")).lower()
            pipeline = "FOL"
            record_id = raw.get("example_id", index)
        elif key == "logical_deduction":
            text = raw["context"] + "\n" + raw["question"] + "\n" + raw["options"]
            expected = raw.get("answer")
            pipeline = "CSP"
            record_id = raw.get("id", index)
        elif key == "ar_lsat":
            text = raw["context"] + "\n" + raw["question"] + "\n" + "\n".join(raw["answers"])
            expected = raw.get("label")
            pipeline = "SAT"
            record_id = raw.get("id_string", index)
        else:                                                               
            text = raw.get("translation", {}).get("en", "")
            expected = None
            pipeline = "LP"
            record_id = raw.get("id", index)
        records.append({
            "id": record_id,
            "dataset": dataset,
            "pipeline": pipeline,
            "text": text,
            "expected": expected,
            "requested_split": split,
            "source_split": source_split,
            "raw": raw,
        })
    return records


# Run real dataset.
def run_real_dataset(dataset, split="test", limit=1):

    records = load_real_dataset(dataset, split, limit)
    results = []
    for record in records:
        try:
            result = solve(record["text"])
            results.append({"id": record["id"], "expected": record["expected"], "result": result})
        except Exception as exc:
            results.append({"id": record["id"], "expected": record["expected"], "error": str(exc)})
    return results


# Merge real datasets.
def merge_real_datasets(output_path=None, limit_per_split=None):







    output_path = Path(output_path or MERGED_DATASET_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged = []
    split_counts = {}

    for dataset in REAL_DATASETS:
        dataset_dir = REAL_DATA_ROOT / dataset
        available = []
        for split in ("train", "validation", "test"):
            suffix = ".json" if dataset == "prontoqa" else ".jsonl"
            if (dataset_dir / f"{split}{suffix}").exists():
                available.append(split)

        for split in available:
            records = load_real_dataset(dataset, split, limit_per_split)
            split_counts[f"{dataset}:{split}"] = len(records)
            for record in records:
                record = dict(record)
                record["id"] = f"{dataset}:{split}:{record['id']}"
                record["merge_source"] = f"{dataset}/{split}"
                merged.append(record)

    with output_path.open("w", encoding="utf-8") as file:
        for record in merged:
            file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    return {
        "path": str(output_path),
        "records": len(merged),
        "splits": split_counts,
    }


# Validate merged dataset.
def validate_merged_dataset(path=None):

    path = Path(path or MERGED_DATASET_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Merged dataset not found: {path}")

    required = {"id", "dataset", "pipeline", "text", "requested_split", "source_split", "raw"}
    ids = set()
    pipeline_counts = {}
    records = 0
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            missing = required - set(record)
            if missing:
                raise ValueError(f"Merged record line {line_number} is missing {sorted(missing)}")
            if record["id"] in ids:
                raise ValueError(f"Duplicate merged record id: {record['id']}")
            if not record["text"].strip():
                raise ValueError(f"Merged record line {line_number} has empty text")
            if record["pipeline"] not in {"LP", "FOL", "CSP", "SAT"}:
                raise ValueError(f"Unknown pipeline on line {line_number}: {record['pipeline']}")
            ids.add(record["id"])
            pipeline_counts[record["pipeline"]] = pipeline_counts.get(record["pipeline"], 0) + 1
            records += 1

    return {"path": str(path), "records": records, "pipelines": pipeline_counts}


#  binary metrics.
def _binary_metrics(executed):
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    evaluated = 0
    for item in executed:
        expected = item.get("expected")
        actual = item.get("proved")
        if not isinstance(expected, bool) or not isinstance(actual, bool):
            continue
        evaluated += 1
        if expected and actual:
            counts["tp"] += 1
        elif not expected and not actual:
            counts["tn"] += 1
        elif actual:
            counts["fp"] += 1
        else:
            counts["fn"] += 1

    tp, tn, fp, fn = (counts[key] for key in ("tp", "tn", "fp", "fn"))
    accuracy = (tp + tn) / evaluated if evaluated else None
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "evaluated_binary_records": evaluated,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


# Test merged dataset.
def test_merged_dataset(path=None, execute=False, limit=None, metrics=False, progress=True):

    summary = validate_merged_dataset(path)
    if not execute:
        return summary
    if not limit or limit < 1:
        raise ValueError("--execute requires a positive --limit to bound API usage.")

    records = []
    with Path(path or MERGED_DATASET_PATH).open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
                if len(records) >= limit:
                    break

    execution = []
    total = len(records)
    for index, record in enumerate(records, 1):
        try:
            result = solve(record["text"], announce=False)
            execution.append({
                "id": record["id"],
                "dataset": record["dataset"],
                "expected": record["expected"],
                "proved": result[0] if isinstance(result, list) and result else None,
                "result": result,
            })
            if progress:
                print(
                    f"ROUND {index}/{total} | SUCCESS | "
                    f"{record['dataset']}:{record['id']} | "
                    f"pipeline={record['pipeline']} | proved={execution[-1]['proved']}",
                    flush=True,
                )
        except Exception as exc:
            execution.append({
                "id": record["id"],
                "dataset": record["dataset"],
                "expected": record["expected"],
                "error": str(exc),
            })
            if progress:
                print(
                    f"ROUND {index}/{total} | FAILURE | "
                    f"{record['dataset']}:{record['id']} | "
                    f"pipeline={record['pipeline']} | {exc}",
                    flush=True,
                )
    summary["completed"] = sum("error" not in item for item in execution)
    summary["errors"] = sum("error" in item for item in execution)
    if metrics:
        summary["metrics"] = _binary_metrics(execution)
    else:
        summary["executed"] = execution
    return summary



from concurrent.futures import ThreadPoolExecutor, as_completed


# Process item.
def process_item(item):
    try:
        output = formulate_logic_program(
            item["context"] + " " + item["question"]
        )

        proved = output[0]

        correct = (
            (proved and item["answer"] == "A")
            or
            (not proved and item["answer"] == "B")
        )

        return {
            "id": item["id"],
            "correct": correct,
            "proved": proved,
            "expected": item["answer"],
            "explanation": output[1],

        }

    except Exception as e:
        return {
            "id": item["id"],
            "correct": False,
            "proved": None,
            "expected": item["answer"],
            "explanation": f"ERROR: {e}",
        }



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Logic-LM pipeline.")
    parser.add_argument("--dataset", help="Downloaded dataset name, e.g. folio or ar_lsat")
    parser.add_argument("--split", default="test", choices=["train", "validation", "test"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--text", help="Solve one natural-language problem")
    parser.add_argument(
        "--merge-datasets",
        action="store_true",
        help="Merge every downloaded dataset split into datasets/real/merged/all.jsonl",
    )
    parser.add_argument(
        "--test-merged",
        action="store_true",
        help="Validate the complete merged JSONL dataset",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute a bounded sample from the merged dataset through the LLM pipeline",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Calculate accuracy, precision, recall, and F1 for compatible Boolean labels",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-record progress lines during merged execution",
    )
    parser.add_argument("--output", help="Custom merged JSONL output path")
    args = parser.parse_args()

    if args.merge_datasets:
        print(json.dumps(merge_real_datasets(args.output, args.limit), indent=2, default=str))
    elif args.test_merged:
        print(json.dumps(test_merged_dataset(
            args.output,
            args.execute,
            args.limit,
            args.metrics,
            progress=not args.quiet,
        ), indent=2, default=str))
    elif args.dataset:
        run_limit = args.limit if args.limit is not None else 1
        print(json.dumps(run_real_dataset(args.dataset, args.split, run_limit), indent=2, default=str))
    elif args.text:
        print(json.dumps(solve(args.text), indent=2, default=str))
    else:
        parser.error("Provide --dataset or --text")

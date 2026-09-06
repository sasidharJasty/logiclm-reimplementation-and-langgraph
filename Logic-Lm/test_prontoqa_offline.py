










import json
import re
import sys
import traceback

import logic_engine
from LP.implementation import process_output, LogicProgram, PredicateData, RuleData


PRED_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)$")


# Parse predicate.
def parse_predicate(text):
    text = text.strip()
    m = PRED_RE.match(text)
    if not m:
        raise ValueError(f"Could not parse predicate: {text!r}")
    name = m.group(1)
    args = [a.strip().lstrip("$") for a in m.group(2).split(",")]
    return PredicateData(name=name, args=args)


# Parse rule line.
def parse_rule_line(line):
                                                
    if ">>>" not in line:
        raise ValueError(f"Not a rule line: {line!r}")
    lhs, rhs = line.split(">>>")
                                                                    
                              
    antecedents = [parse_predicate(p) for p in lhs.split("&") if p.strip()]
    consequent = parse_predicate(rhs)
    return RuleData(antecedent=antecedents, consequent=consequent)


# Parse raw program.
def parse_raw_program(raw_text):
    facts_section = ""
    rules_section = ""
    query_section = ""

                                                               
    parts = re.split(r"\n(Facts:|Rules:|Query:|Predicates:)\n", "\n" + raw_text)

    current = None
    buf = []
    sections = {}
    for chunk in parts:
        if chunk in ("Facts:", "Rules:", "Query:", "Predicates:"):
            if current is not None:
                sections[current] = "\n".join(buf)
            current = chunk
            buf = []
        else:
            buf.append(chunk)
    if current is not None:
        sections[current] = "\n".join(buf)

    facts_section = sections.get("Facts:", "")
    rules_section = sections.get("Rules:", "")
    query_section = sections.get("Query:", "")

    facts = [
        parse_predicate(line)
        for line in facts_section.strip().splitlines()
        if line.strip()
    ]

    rules = [
        parse_rule_line(line)
        for line in rules_section.strip().splitlines()
        if line.strip()
    ]

    query_lines = [l for l in query_section.strip().splitlines() if l.strip()]
    if not query_lines:
        raise ValueError("No query found")
    query = parse_predicate(query_lines[0])

    return LogicProgram(facts=facts, rules=rules, query=query, type="first")


QUESTION_RE = re.compile(r"true or false\?\s*(.+?)\.?\s*$", re.IGNORECASE)


# Literal query polarity.
def literal_query_polarity(question):






    m = QUESTION_RE.search(question)
    stmt = m.group(1) if m else question
    return "False" if re.search(r"\bnot\b", stmt) else "True"


# Run item.
def run_item(item):
    raw = item["raw_logic_programs"][0]
    program = parse_raw_program(raw)

                                                                        
                                                                         
                                                                         
                                                                    
                           
    literal_query = logic_engine.Predicate(
        program.query.name,
        program.query.args[:-1] + [literal_query_polarity(item["question"])],
    )
    program.query = PredicateData(name=literal_query.name, args=literal_query.args)

    KB = logic_engine.KnowledgeBase()
    result = process_output(program, KB)

    proved = result["proved"]
    predicted = "A" if proved else "B"

    return predicted, item["answer"], result


# Main.
def main():
    with open("datasets/ProntoQA.json") as f:
        data = json.load(f)

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(data)

    n_correct = 0
    n_total = 0
    errors = []
    mismatches = []

    for item in data[:limit]:
        n_total += 1
        try:
            predicted, expected, result = run_item(item)
        except Exception as e:
            errors.append((item["id"], f"{type(e).__name__}: {e}"))
            continue

        if predicted == expected:
            n_correct += 1
        else:
            mismatches.append((item["id"], predicted, expected))

    print(f"Total examples run : {n_total}")
    print(f"Correct            : {n_correct}")
    print(f"Incorrect (logic)  : {len(mismatches)}")
    print(f"Errors (exceptions): {len(errors)}")
    print(f"Accuracy           : {n_correct / n_total:.2%}" if n_total else "n/a")

    if mismatches:
        print("\n--- First 20 logic mismatches ---")
        for id_, pred, exp in mismatches[:20]:
            print(f"  {id_}: predicted={pred} expected={exp}")

    if errors:
        print("\n--- First 20 errors ---")
        for id_, msg in errors[:20]:
            print(f"  {id_}: {msg}")

    return 0 if (not mismatches and not errors) else 1


if __name__ == "__main__":
    sys.exit(main())

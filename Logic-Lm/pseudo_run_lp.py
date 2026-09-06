













import json
import types
from types import SimpleNamespace

import LP.implementation as LP


PRONTOQA_1_TEXT = """Jompuses are not shy. Jompuses are yumpuses. Each yumpus is aggressive. \
Each yumpus is a dumpus. Dumpuses are not wooden. Dumpuses are wumpuses. Wumpuses are red. \
Every wumpus is an impus. Each impus is opaque. Impuses are tumpuses. Numpuses are sour. \
Tumpuses are not sour. Tumpuses are vumpuses. Vumpuses are earthy. Every vumpus is a zumpus. \
Zumpuses are small. Zumpuses are rompuses. Max is a yumpus. Is the following statement true \
or false? Max is sour."""


#  predicate data.
def _predicate_data(name, *args):
    return LP.PredicateData(name=name, args=list(args))


# Make gold formulator response.
def make_gold_formulator_response():






    facts = [_predicate_data("Yumpus", "Max", "True")]

    rule_defs = [
        (("Jompus", "x", "True"), ("Shy", "x", "False")),
        (("Jompus", "x", "True"), ("Yumpus", "x", "True")),
        (("Yumpus", "x", "True"), ("Aggressive", "x", "True")),
        (("Yumpus", "x", "True"), ("Dumpus", "x", "True")),
        (("Dumpus", "x", "True"), ("Wooden", "x", "False")),
        (("Dumpus", "x", "True"), ("Wumpus", "x", "True")),
        (("Wumpus", "x", "True"), ("Red", "x", "True")),
        (("Wumpus", "x", "True"), ("Impus", "x", "True")),
        (("Impus", "x", "True"), ("Opaque", "x", "True")),
        (("Impus", "x", "True"), ("Tumpus", "x", "True")),
        (("Numpus", "x", "True"), ("Sour", "x", "True")),
        (("Tumpus", "x", "True"), ("Sour", "x", "False")),
        (("Tumpus", "x", "True"), ("Vumpus", "x", "True")),
        (("Vumpus", "x", "True"), ("Earthy", "x", "True")),
        (("Vumpus", "x", "True"), ("Zumpus", "x", "True")),
        (("Zumpus", "x", "True"), ("Small", "x", "True")),
        (("Zumpus", "x", "True"), ("Rompus", "x", "True")),
    ]

    rules = [
        LP.RuleData(
            antecedent=[_predicate_data(*a)],
            consequent=_predicate_data(*c)
        )
        for a, c in rule_defs
    ]

    query = _predicate_data("Sour", "Max", "True")

    return LP.LogicProgram(facts=facts, rules=rules, query=query, type="first")


class FakeParsedMessage:
    # Initialize the object.
    def __init__(self, parsed):
        self.parsed = parsed


class FakeChoice:
    # Initialize the object.
    def __init__(self, parsed):
        self.message = FakeParsedMessage(parsed)


class FakeCompletion:
    # Initialize the object.
    def __init__(self, parsed):
        self.choices = [FakeChoice(parsed)]


# Install fake client.
def install_fake_client(interpreter_response_text, capture_box):







    call_count = {"n": 0}

    # Fake parse.
    def fake_parse(model, messages, response_format):
        call_count["n"] += 1
        if call_count["n"] == 1:
                             
            return FakeCompletion(make_gold_formulator_response())
        else:
                                                         
            user_msg = next(m["content"] for m in messages if m["role"] == "user")
            capture_box["interpreter_input"] = user_msg
            return FakeCompletion(LP.Output(explanation=interpreter_response_text))

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(parse=fake_parse)
            )
        )
    )
    LP.client = fake_client


# Run pseudo.
def run_pseudo(label, interpreter_response_text):
    print(f"\n{'=' * 70}\nPSEUDO RUN: {label}\n{'=' * 70}")
    capture_box = {}
    install_fake_client(interpreter_response_text, capture_box)

    proved, explanation, proof = LP.formulate_logic_program(PRONTOQA_1_TEXT)

    print(f"[symbolic engine] proved = {proved}   (expected: False — Sour(Max,True) is NOT derivable)")
    print(f"[symbolic engine] query  = {proof['query']}")

    print("\n--- what the interpreter LLM was actually shown (truncated) ---")
    shown = capture_box["interpreter_input"]
    print(shown[:1400] + ("... [truncated]" if len(shown) > 1400 else ""))

    print("\n--- scripted interpreter explanation ---")
    print(explanation)

                                                             
    checks = []
    checks.append(("'Numpus' does not appear in the trace JSON",
                    "Numpus" not in json.dumps(proof["result"])))
    checks.append(("entity whitelist in interpreter input includes 'Max'",
                    "Max" in shown.split("individuals that exist in this proof are:")[1].split("\n")[0]))
    checks.append(("deterministic proved-fact line present in interpreter input",
                    f"proved = {proved}" in shown))

    print("\n--- structural checks ---")
    for desc, ok in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {desc}")

    return proved, explanation


if __name__ == "__main__":
                                                                         
                                                                        
                  
    run_pseudo(
        "well-behaved interpreter",
        "No, Max is not sour. The proof establishes Yumpus(Max) as a "
        "given fact, then chains Dumpus, Wumpus, Impus, and Tumpus, at "
        "which point the rule 'tumpuses are not sour' directly gives "
        "Sour(Max, False). Since the query Sour(Max, True) could not be "
        "established, the statement 'Max is sour' is false."
    )

                                                                       
                                                                    
                                                                      
                                                                          
                                                                      
                                       
    proved, bad_explanation = run_pseudo(
        "reproducing the reported hallucination (for contrast)",
        "Yes, Max is sour. The knowledge base states that Sour(numpus) "
        "is true, and since we substituted 'numpus' with Max, it "
        "directly establishes that Sour(Max) is also true."
    )
    disagrees_with_proved = ("Yes" in bad_explanation) and (proved is False)
    print(f"\n[automated flag] explanation contradicts proved={proved}: "
          f"{disagrees_with_proved}  <- this is exactly the reported bug, "
          f"and it's now checkable/flaggable in an eval harness")

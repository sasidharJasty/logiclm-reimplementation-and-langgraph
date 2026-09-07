import json
from pathlib import Path
import unittest

import logic_engine
from CSP.implementation import (
    ConstraintData,
    VariableData,
    QueryData,
    CSPProgram,
    make_function_constraint,
    solve_csp,
)
from LP.implementation import (
    LogicProgram,
    PredicateData,
    RuleData,
    process_output,
)
import main
from SAT.implementation import SATProgram, solve_sat
from FOL.implementation import prove as prove_fol


# Test plural predicate aliases do not break inference.
def test_plural_predicate_aliases_do_not_break_inference():
    program = LogicProgram(
        facts=[PredicateData(name="Jompus", args=["Rex", "True"])],
        rules=[
            RuleData(
                antecedent=[PredicateData(name="Jompus", args=["x", "True"])],
                consequent=PredicateData(name="Impus", args=["x", "True"]),
            ),
            RuleData(
                antecedent=[PredicateData(name="Impuses", args=["x", "True"])],
                consequent=PredicateData(name="Wumpus", args=["x", "True"]),
            ),
            RuleData(
                antecedent=[PredicateData(name="Wumpuses", args=["x", "True"])],
                consequent=PredicateData(name="Metallic", args=["x", "False"]),
            ),
        ],
        query=PredicateData(name="Metallic", args=["Rex", "False"]),
        type="first",
    )

    result = process_output(program, logic_engine.KnowledgeBase())
    assert result["proved"] is True


# Test csp rejects undefined expression names.
def test_csp_rejects_undefined_expression_names():
    with unittest.TestCase().assertRaisesRegex(ValueError, "not listed"):
        make_function_constraint("Alice < Bob", ["Alice"])


# Test csp all results are projected and deduplicated.
def test_csp_all_results_are_projected_and_deduplicated():
    program = CSPProgram(
        variables=[
            VariableData(name="Alice", domain=[1, 2, 3]),
            VariableData(name="Bob", domain=[1, 2, 3]),
        ],
        constraints=[
            ConstraintData(
                type="function",
                variables=["Alice", "Bob"],
                expression="Alice < Bob",
            )
        ],
        query=QueryData(variables=["Alice"]),
        type="all",
    )

    result = solve_csp(program)
    assert result["proved"] is True
    assert {item["Alice"] for item in result["results"]} == {1, 2}


# Test pipeline example splits cover all requested pipelines.
def test_pipeline_example_splits_cover_all_requested_pipelines():
    root = Path(__file__).parents[1] / "datasets" / "pipeline_examples"
    expected = {"LP", "FOL", "CSP", "SAT"}
    seen = set()
    ids = set()

    for split in ("train", "validation", "test"):
        records = [json.loads(line) for line in (root / f"{split}.jsonl").read_text().splitlines()]
        assert records
        assert len({item["id"] for item in records}) == len(records)
        for item in records:
            assert item["pipeline"] in expected
            assert item["solver"]
            assert item["dataset"]
            seen.add(item["pipeline"])
            assert item["id"] not in ids
            ids.add(item["id"])

    assert seen == expected


# Test downloaded dataset adapters load real records.
def test_downloaded_dataset_adapters_load_real_records():
    for dataset in ("prontoqa", "proofwriter", "folio", "logical_deduction", "ar_lsat"):
        records = main.load_real_dataset(dataset, "test", limit=1)
        assert len(records) == 1
        assert records[0]["text"]
        assert records[0]["source_split"] in {"test", "validation", "train"}


# Test merged real dataset is valid.
def test_merged_real_dataset_is_valid():
    summary = main.test_merged_dataset()
    assert summary["records"] > 0
    assert set(summary["pipelines"]) == {"LP", "FOL", "CSP", "SAT"}


# Test z3 sat solves exactly three other technicians.
def test_z3_sat_solves_exactly_three_other_technicians():
    program = SATProgram(
        variables=["repairs_Xena", "repairs_Ada", "repairs_Ben", "repairs_Cal", "repairs_Dia"],
        constraints=[
            "repairs_Xena",
            "Exactly(3, repairs_Ada, repairs_Ben, repairs_Cal, repairs_Dia)",
        ],
    )
    result = solve_sat(program)
    assert result["proved"] is True
    assert result["model"]["repairs_Xena"] is True
    assert sum(result["model"][name] for name in program.variables[1:]) == 3


# Test z3 sat entailment and unsat.
def test_z3_sat_entailment_and_unsat():
    entailed = SATProgram(
        variables=["A", "B"],
        constraints=["A", "Implies(A, B)"],
        query="B",
        type="entails",
    )
    contradicted = SATProgram(
        variables=["A"],
        constraints=["A", "not A"],
    )
    assert solve_sat(entailed)["proved"] is True
    assert solve_sat(contradicted)["proved"] is False


def test_csp_boolean_expressions_short_circuit_and_support_bitwise_ops():
    from CSP.implementation import make_function_constraint

    assert make_function_constraint("False and (1 / 0)", [])() is False
    assert make_function_constraint("True or (1 / 0)", [])() is True
    assert make_function_constraint("A & B", ["A", "B"])(True, True) is True
    assert make_function_constraint("A | B", ["A", "B"])(False, True) is True


def test_fol_unknown_result_remains_nonfatal():
    assert prove_fol("unexpected prover output") is None

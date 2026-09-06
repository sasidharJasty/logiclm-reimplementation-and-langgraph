
import os
import json
import dotenv
import ast

from openai import OpenAI
from pydantic import BaseModel
from typing import Literal, Union

from constraint import (
    Problem,
    AllDifferentConstraint,
    ExactSumConstraint,
    MinSumConstraint,
    MaxSumConstraint,
)


dotenv.load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")

client = OpenAI(api_key=OPENAI_KEY)


FORMULATOR_SYSTEM_PROMPT = r"""
You are the CSP Problem Formulator for a Logic-LM reasoning system.

Your job is to translate a natural-language constraint satisfaction problem
into a symbolic CSP representation that will be executed by Python's
constraint package.

You are NOT the solver.

Do NOT solve the problem.

Do NOT determine which assignments satisfy the constraints.

Only translate the problem.

============================================================
CSP MODEL
============================================================

A Constraint Satisfaction Problem consists of:

1. Variables
2. Domains
3. Constraints
4. Query
5. Query type

============================================================
VARIABLES
============================================================

Each variable has:

name
domain

Example:

{
    "name": "Alice",
    "domain": [1, 2, 3]
}

Variable names must be strings.

============================================================
DOMAINS
============================================================

Domains must be explicit finite lists.

Valid values include:

integers
floating point numbers
strings
booleans

Examples:

[1, 2, 3]

["red", "blue", "green"]

["Monday", "Tuesday", "Wednesday"]

Do not use strings such as:

"1-5"

Instead use:

[1, 2, 3, 4, 5]

============================================================
CONSTRAINT TYPES
============================================================

Use exactly one of these constraint types:

function
all_different
exact_sum
min_sum
max_sum
exact_product
min_product
max_product

============================================================
FUNCTION
============================================================

Use function for comparisons and arithmetic relationships.

Example:

Alice < Bob

Represent:

{
    "type": "function",
    "variables": ["Alice", "Bob"],
    "expression": "Alice < Bob"
}

Other examples:

Alice != Bob

Alice + Bob == 10

Alice == Bob + 1

The expression must be valid Python.

Use only the variables listed in "variables".

============================================================
ALL DIFFERENT
============================================================

If every variable must have a different value:

{
    "type": "all_different",
    "variables": ["Alice", "Bob", "Charlie"]
}

============================================================
EXACT SUM
============================================================

If variables must sum to a specific value:

{
    "type": "exact_sum",
    "variables": ["A", "B", "C"],
    "value": 10
}

============================================================
MIN SUM
============================================================

If the sum must be at least a value:

{
    "type": "min_sum",
    "variables": ["A", "B"],
    "value": 10
}

============================================================
MAX SUM
============================================================

If the sum must be at most a value:

{
    "type": "max_sum",
    "variables": ["A", "B"],
    "value": 10
}

============================================================
EXACT PRODUCT
============================================================

If the product must equal a value:

{
    "type": "exact_product",
    "variables": ["A", "B"],
    "value": 12
}

============================================================
MIN PRODUCT
============================================================

If the product must be at least a value:

{
    "type": "min_product",
    "variables": ["A", "B"],
    "value": 12
}

============================================================
MAX PRODUCT
============================================================

If the product must be at most a value:

{
    "type": "max_product",
    "variables": ["A", "B"],
    "value": 12
}

============================================================
EXPLICIT ASSIGNMENTS
============================================================

If the problem states:

Alice has number 2.

Represent:

{
    "type": "function",
    "variables": ["Alice"],
    "expression": "Alice == 2"
}

============================================================
QUERY
============================================================

The query specifies what information the user wants from the CSP.

The query contains:

variables

The type is either:

"first"

or:

"all"

============================================================
TYPE FIRST
============================================================

Use "first" when the question requests one valid assignment or asks whether
a specific assignment is possible.

Examples:

"What is Alice's number?"

"Find one valid schedule."

"Can Alice be assigned 2?"

============================================================
TYPE ALL
============================================================

Use "all" when the question asks for every possible result.

Examples:

"What are all possible assignments?"

"What values can Alice have?"

"List every valid schedule."

"Which people can have number 2?"

============================================================
NO INFERENCE
============================================================

Do not solve the CSP.

Do not eliminate values.

Do not derive additional constraints.

Do not invent variables.

Do not invent domains.

Do not invent constraints.

Do not return solutions.

============================================================
OUTPUT
============================================================

Return exactly:

variables
constraints
query
type

Do not return Python code.

Do not return explanations.

Do not return solutions.
"""


INTERPRETER_SYSTEM_PROMPT = r"""
You are the Result Interpreter for a CSP Logic-LM reasoning system.

A deterministic CSP solver has already executed the problem.

Your job is to convert the solver's output into a natural-language answer.

You are NOT the solver.

The solver's output is authoritative.

============================================================
ABSOLUTE RULE
============================================================

Do not solve the CSP again.

Do not perform additional inference.

Do not invent solutions.

Do not remove solutions.

Do not add solutions.

Only describe the solver's actual output.

============================================================
FIRST
============================================================

If type is "first", report the returned valid assignment.

Example:

{
    "Alice": 1,
    "Bob": 2,
    "Charlie": 3
}

Answer:

"One valid solution is Alice = 1, Bob = 2, and Charlie = 3."

If no solution exists:

"No valid assignment satisfies all of the constraints."

============================================================
ALL
============================================================

If type is "all", report all requested results.

If the query asks about one variable:

Alice

and the solver produces:

Alice = 1
Alice = 2

say:

"Alice can be 1 or 2."

If the query asks for complete assignments, report the complete assignments.

============================================================
QUERY
============================================================

Only discuss variables requested by the query unless complete assignments
were explicitly requested.

============================================================
NO SOLUTION
============================================================

If there are no valid solutions:

"No valid assignment satisfies all of the given constraints."

Do not claim that the real-world problem is impossible.

============================================================
OUTPUT
============================================================

Return only the natural-language answer.

Do not output JSON.

Do not output Python.

Do not output solver syntax.

Do not output analysis.

Normally use 1-4 sentences.
"""


DomainValue = Union[str, int, float, bool]


class VariableData(BaseModel):
    name: str
    domain: list[DomainValue]


class ConstraintData(BaseModel):
    type: Literal[
        "function",
        "all_different",
        "exact_sum",
        "min_sum",
        "max_sum",
        "exact_product",
        "min_product",
        "max_product",
    ]

    variables: list[str]
    expression: str | None = None
    value: int | float | None = None


class QueryData(BaseModel):
    variables: list[str]


class CSPProgram(BaseModel):
    variables: list[VariableData]
    constraints: list[ConstraintData]
    query: QueryData
    type: Literal["first", "all"]


class Output(BaseModel):
    explanation: str


# Make function constraint.
def make_function_constraint(expression, variable_names):
    if not expression:
        raise ValueError("Function constraint requires an expression.")

    allowed_chars = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "_ +-*/%<>=!&|()."
    )

    if not set(expression) <= allowed_chars:
        raise ValueError(
            f"Unsafe characters found in expression: {expression}"
        )

    forbidden = [
        "__",
        "import",
        "exec",
        "eval",
        "open",
        "globals",
        "locals",
        "lambda",
        "os",
        "sys",
    ]

    lowered = expression.lower()

    for token in forbidden:
        if token in lowered:
            raise ValueError(
                f"Forbidden token in constraint: {token}"
            )

    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid constraint expression: {expression}") from exc

    referenced_names = {
        node.id for node in ast.walk(parsed) if isinstance(node, ast.Name)
    }
    unknown_names = referenced_names - set(variable_names)
    if unknown_names:
        raise ValueError(
            "Constraint references variables that are not listed: "
            + ", ".join(sorted(unknown_names))
        )

    # Constraint.
    def constraint(*values):
        environment = dict(zip(variable_names, values))

        return bool(
            eval(
                expression,
                {"__builtins__": {}},
                environment
            )
        )

    return constraint


# Make product constraint.
def make_product_constraint(variable_names, target, mode):
    # Constraint.
    def constraint(*values):
        product = 1

        for value in values:
            product *= value

        if mode == "exact":
            return product == target

        if mode == "min":
            return product >= target

        if mode == "max":
            return product <= target

        raise ValueError(
            f"Unknown product mode: {mode}"
        )

    return constraint


# Add constraint to problem.
def add_constraint_to_problem(problem, constraint):
    ctype = constraint.type
    variables = constraint.variables

    if not variables:
        raise ValueError(f"Constraint {ctype!r} must list at least one variable.")
    if len(set(variables)) != len(variables):
        raise ValueError(f"Constraint {ctype!r} contains duplicate variables.")

    if ctype == "function":
        function = make_function_constraint(
            constraint.expression,
            variables
        )

        problem.addConstraint(
            function,
            variables
        )

    elif ctype == "all_different":
        problem.addConstraint(
            AllDifferentConstraint(),
            variables
        )

    elif ctype == "exact_sum":
        if constraint.value is None:
            raise ValueError("exact_sum requires a numeric value.")
        problem.addConstraint(
            ExactSumConstraint(constraint.value),
            variables
        )

    elif ctype == "min_sum":
        if constraint.value is None:
            raise ValueError("min_sum requires a numeric value.")
        problem.addConstraint(
            MinSumConstraint(constraint.value),
            variables
        )

    elif ctype == "max_sum":
        if constraint.value is None:
            raise ValueError("max_sum requires a numeric value.")
        problem.addConstraint(
            MaxSumConstraint(constraint.value),
            variables
        )

    elif ctype == "exact_product":
        if constraint.value is None:
            raise ValueError("exact_product requires a numeric value.")
        problem.addConstraint(
            make_product_constraint(
                variables,
                constraint.value,
                "exact"
            ),
            variables
        )

    elif ctype == "min_product":
        if constraint.value is None:
            raise ValueError("min_product requires a numeric value.")
        problem.addConstraint(
            make_product_constraint(
                variables,
                constraint.value,
                "min"
            ),
            variables
        )

    elif ctype == "max_product":
        if constraint.value is None:
            raise ValueError("max_product requires a numeric value.")
        problem.addConstraint(
            make_product_constraint(
                variables,
                constraint.value,
                "max"
            ),
            variables
        )

    else:
        raise ValueError(
            f"Unknown constraint type: {ctype}"
        )


# Build problem.
def build_problem(program):
    problem = Problem()

    for variable in program.variables:
        problem.addVariable(
            variable.name,
            variable.domain
        )

    for constraint in program.constraints:
        add_constraint_to_problem(
            problem,
            constraint
        )

    return problem


# Project solution.
def project_solution(solution, query_variables):
    return {
        variable: solution[variable]
        for variable in query_variables
        if variable in solution
    }


# Solve csp.
def solve_csp(program):
    problem = build_problem(program)

    query_variables = program.query.variables

    if program.type == "first":
        solution = problem.getSolution()

        if solution is None:
            return {
                "type": "first",
                "proved": False,
                "query": query_variables,
                "result": None
            }

        return {
            "type": "first",
            "proved": True,
            "query": query_variables,
            "result": project_solution(
                solution,
                query_variables
            ),
            "complete_solution": solution
        }

    solutions = problem.getSolutions()

    projected = []

    for solution in solutions:
        result = project_solution(
            solution,
            query_variables
        )

        if result not in projected:
            projected.append(result)

    return {
        "type": "all",
        "proved": len(projected) > 0,
        "query": query_variables,
        "results": projected,
        "solution_count": len(projected)
    }


# Prepare interpreter input.
def prepare_interpreter_input(
    original_text,
    program,
    solver_result
):
    return {
        "question": original_text,
        "program": program.model_dump(),
        "solver_result": solver_result
    }


# Formulate csp.
def formulate_csp(text):
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
        response_format=CSPProgram,
    )

    program = response.choices[0].message.parsed

    if program is None:
        raise ValueError(
            "The model failed to produce a CSP program."
        )

    return program


# Interpret result.
def interpret_result(
    original_text,
    program,
    solver_result
):
    interpreter_input = prepare_interpreter_input(
        original_text,
        program,
        solver_result
    )

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": INTERPRETER_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": json.dumps(
                    interpreter_input,
                    indent=2,
                    default=str
                )
            }
        ],
        response_format=Output,
    )

    result = response.choices[0].message.parsed

    if result is None:
        raise ValueError(
            "The interpreter failed to produce an answer."
        )

    return result.explanation


# Formulate csp program.
def formulate_CSP_program(text):
    program = formulate_csp(text)

                                                               

           
                    
                                  
                      
                        
          
      

    solver_result = solve_csp(program)

                                                                 

           
                    
                           
                      
                        
          
      

    explanation = interpret_result(
        text,
        program,
        solver_result
    )

    return [
        solver_result["proved"],
        explanation
    ]


first_text = """
Alice, Bob, and Charlie each have a number from 1 to 3.

Each person must have a different number.
Alice's number is less than Bob's number.
Charlie has number 3.

What is Alice's number?
"""


all_text = """
Alice, Bob, and Charlie each have a number from 1 to 3.

Each person must have a different number.
Alice's number is less than Bob's number.
Charlie has number 3.

What are all possible assignments?
"""


sum_text = """
Three people, Alice, Bob, and Charlie, each choose a number from 1 to 5.

All three numbers must be different.
The three numbers must add up to 9.
Alice must have a smaller number than Bob.

What are all possible assignments?
"""


if __name__ == "__main__":
    print("\n\n========== FIRST TEST ==========\n")
    print(formulate_CSP_program(first_text))

    print("\n\n========== ALL TEST ==========\n")
    print(formulate_CSP_program(all_text))

    print("\n\n========== SUM TEST ==========\n")
    print(formulate_CSP_program(sum_text))

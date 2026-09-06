

import ast
import json
import os

import dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Literal
from z3 import (
    And,
    AtLeast,
    AtMost,
    Bool,
    BoolRef,
    If,
    Implies,
    Not,
    Or,
    Solver,
    Xor,
    is_true,
    sat,
)


dotenv.load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None


FORMULATOR_SYSTEM_PROMPT = """
Translate the analytical reasoning problem into a Boolean SAT program.
Return only the requested structured fields.

Variables are unique Boolean identifiers. Constraints must use only Python-like
Boolean expressions and these functions: Xor, Implies, Exactly, AtLeast,
AtMost, and If. Exactly/AtLeast/AtMost take an integer followed by Boolean
variables. If takes a Boolean condition and two numeric values.

Use type satisfiable when the question asks whether the constraints have a
solution. Use type entails when the question asks whether query follows from
the constraints.
"""


class SATProgram(BaseModel):
    variables: list[str]
    constraints: list[str] = Field(default_factory=list)
    query: str | None = None
    type: Literal["satisfiable", "entails"] = "satisfiable"


class _ExpressionCompiler(ast.NodeVisitor):
    # Initialize the object.
    def __init__(self, symbols):
        self.symbols = symbols

    # Compile.
    def compile(self, expression):
        tree = ast.parse(expression, mode="eval")
        return self.visit(tree.body)

    # Visit name.
    def visit_Name(self, node):
        if node.id not in self.symbols:
            raise ValueError(f"Unknown SAT variable: {node.id}")
        return self.symbols[node.id]

    # Visit constant.
    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            return node.value
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only Boolean and numeric constants are supported")

    # Visit unaryop.
    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            return Not(self.visit(node.operand))
        if isinstance(node.op, ast.USub):
            return -self.visit(node.operand)
        raise ValueError("Unsupported unary operator")

    # Visit boolop.
    def visit_BoolOp(self, node):
        values = [self.visit(value) for value in node.values]
        if isinstance(node.op, ast.And):
            return And(values)
        if isinstance(node.op, ast.Or):
            return Or(values)
        raise ValueError("Unsupported Boolean operator")

    # Visit binop.
    def visit_BinOp(self, node):
        if isinstance(node.op, ast.BitXor):
            return Xor(self.visit(node.left), self.visit(node.right))
        if isinstance(node.op, ast.Add):
            return self.visit(node.left) + self.visit(node.right)
        raise ValueError("Unsupported binary operator")

    # Visit compare.
    def visit_Compare(self, node):
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise ValueError("Only single comparisons are supported")
        left = self.visit(node.left)
        right = self.visit(node.comparators[0])
        operator = node.ops[0]
        if isinstance(operator, ast.Eq):
            return left == right
        if isinstance(operator, ast.NotEq):
            return left != right
        raise ValueError("Only equality and inequality are supported")

    # Visit call.
    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Unsupported SAT function")
        name = node.func.id
        args = [self.visit(arg) for arg in node.args]
        if name == "Xor":
            return Xor(*args)
        if name == "Implies" and len(args) == 2:
            return Implies(args[0], args[1])
        if name in {"Exactly", "AtLeast", "AtMost"}:
            if len(args) < 2 or not isinstance(args[0], int):
                raise ValueError(f"{name} requires a count and variables")
            count, values = args[0], args[1:]
            return {"Exactly": lambda: sum(If(v, 1, 0) for v in values) == count,
                    "AtLeast": lambda: AtLeast(*values, count),
                    "AtMost": lambda: AtMost(*values, count)}[name]()
        if name == "If" and len(args) == 3:
            return If(args[0], args[1], args[2])
        raise ValueError(f"Unsupported SAT function: {name}")

    # Generic visit.
    def generic_visit(self, node):
        raise ValueError(f"Unsupported SAT expression: {type(node).__name__}")


# Compile expression.
def compile_expression(expression, symbols):
    return _ExpressionCompiler(symbols).compile(expression)


# Solve sat.
def solve_sat(program: SATProgram):
    if len(set(program.variables)) != len(program.variables):
        raise ValueError("SAT variables must be unique")
    symbols = {name: Bool(name) for name in program.variables}
    solver = Solver()
    solver.add(*(compile_expression(item, symbols) for item in program.constraints))

    if program.type == "entails":
        if not program.query:
            raise ValueError("Entailment queries require query")
        query = compile_expression(program.query, symbols)
        solver.push()
        solver.add(Not(query))
        proved = solver.check() != sat
        solver.pop()
        if proved:
            solver.add(query)
    else:
        proved = solver.check() == sat

    if not proved:
        return {"proved": False, "status": "unsat", "model": None}

    if solver.check() != sat:
        return {"proved": False, "status": "unsat", "model": None}
    model = solver.model()
    return {
        "proved": True,
        "status": "sat",
        "model": {name: is_true(model.eval(symbols[name], model_completion=True)) for name in program.variables},
    }


# Formulate sat.
def formulate_sat(text):
    if client is None:
        raise RuntimeError("An OpenAI API key is required for SAT formulation.")
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": FORMULATOR_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format=SATProgram,
    )
    program = response.choices[0].message.parsed
    if program is None:
        raise ValueError("The SAT formulator returned no program")
    return program


# Formulate sat program.
def formulate_SAT_program(text):
    program = formulate_sat(text)
    result = solve_sat(program)
    return [result["proved"], json.dumps(result)]

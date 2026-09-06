import os
import dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
import logic_engine
import json
from typing import Literal


dotenv.load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")

FORMULATOR_SYSTEM_PROMPT = """You translate a natural-language logic problem
into a symbolic logic program.

Your job is ONLY translation.

DO NOT solve the problem.
DO NOT infer anything.
DO NOT decide the answer.
DO NOT use the question's expected answer.

==================================================
PREDICATES
==================================================

Every predicate has a final Boolean argument.

Positive:
Predicate("Bright", ["Stella", "True"])

Negative:
Predicate("Bright", ["Stella", "False"])

A relationship also has the final Boolean argument:

Predicate("Friends", ["Alice", "Bob", "True"])

==================================================
FACTS VS RULES — VERY IMPORTANT
==================================================

A FACT describes a specific named entity.

Examples:

"Alice is kind."
    -> Predicate("Kind", ["Alice", "True"])

"Bob is not tall."
    -> Predicate("Tall", ["Bob", "False"])

"Stella is a yumpus."
    -> Predicate("Yumpus", ["Stella", "True"])

A RULE describes what happens to ANY entity.

Universal words such as:

    every
    each
    any
    anyone
    all
    whoever
    people who
    things that

usually indicate a RULE.

Examples:

"Every yumpus is hot."

MUST become:

Rule(
    [Predicate("Yumpus", ["x", "True"])],
    Predicate("Hot", ["x", "True"])
)

NOT:

Predicate("Hot", ["yumpus", "True"])

"Every dumpus is happy."

MUST become:

Rule(
    [Predicate("Dumpus", ["x", "True"])],
    Predicate("Happy", ["x", "True"])
)

NOT:

Predicate("Happy", ["dumpus", "True"])

"Each impus is small."

MUST become:

Rule(
    [Predicate("Impus", ["x", "True"])],
    Predicate("Small", ["x", "True"])
)

==================================================
CRITICAL: NEVER PUT A CLASS NAME WHERE AN ARGUMENT GOES
==================================================

A sentence like "Xs are Y" (or "Every X is Y", "Each X is Y") names a
CLASS, not an individual. The lowercased class word (e.g. "yumpus",
"vumpus", "jompus", "numpus", "tumpus", "rompus", "wumpus", "dumpus",
"zumpus", "impus") must NEVER appear as an argument to ANY predicate —
not in a Fact, and not even as the variable name in a Rule. Always use
a plain variable name like "x" in rules instead.

This mistake is the single most common error, so check for it
explicitly. Concretely, for "Vumpuses are floral":

WRONG (this will crash — "vumpus" is a class name, not an individual):

    Fact: Predicate("Floral", ["vumpus", "True"])

ALSO WRONG (reusing the class word as if it were a meaningful variable
name changes nothing — it is still never allowed as an argument):

    Rule([Predicate("Vumpus", ["vumpus", "True"])], Predicate("Floral", ["vumpus", "True"]))

RIGHT:

    Rule([Predicate("Vumpus", ["x", "True"])], Predicate("Floral", ["x", "True"]))

The only time a lowercase word may appear as a predicate's first
argument is as a plain variable name like "x", "y", "person", "other"
inside a Rule — never as a Fact, and never as the class word itself.

==================================================
FACT RULE
==================================================

Facts describe named individuals.

A fact should normally contain constants such as:

    Alice
    Bob
    Max
    Stella
    Wren
    Sam
    Alex

A fact MUST NOT contain a variable.

For example, this is INVALID:

Predicate("Hot", ["yumpus", "True"])

because "yumpus" starts with lowercase and is therefore a variable.

If the sentence is universal, it belongs in RULES.

==================================================
VARIABLES
==================================================

The Python engine treats lowercase arguments as variables.

Variables:

    x
    person
    yumpus
    dumpus
    other

Constants:

    Alice
    Bob
    Max
    Stella
    Wren
    Sam
    Alex

Use the SAME variable when the same entity is referred to.

Example:

"Every friendly and intelligent person is wise."

becomes:

Rule(
    [
        Predicate("Friendly", ["person", "True"]),
        Predicate("Intelligent", ["person", "True"])
    ],
    Predicate("Wise", ["person", "True"])
)

==================================================
RULES
==================================================

A rule has:

    antecedent -> consequent

Examples:

"Every yumpus is hot."

Rule(
    [Predicate("Yumpus", ["x", "True"])],
    Predicate("Hot", ["x", "True"])
)

"Every yumpus is not cold."

Rule(
    [Predicate("Yumpus", ["x", "True"])],
    Predicate("Cold", ["x", "False"])
)

"Anyone who is kind is friendly."

Rule(
    [Predicate("Kind", ["x", "True"])],
    Predicate("Friendly", ["x", "True"])
)

"If someone is friendly and intelligent, they are wise."

Rule(
    [
        Predicate("Friendly", ["x", "True"]),
        Predicate("Intelligent", ["x", "True"])
    ],
    Predicate("Wise", ["x", "True"])
)

"If someone is friends with a kind person, that person is friendly."

Rule(
    [
        Predicate("Friends", ["person", "other", "True"]),
        Predicate("Kind", ["other", "True"])
    ],
    Predicate("Friendly", ["person", "True"])
)

==================================================
NEGATION
==================================================

"not" changes ONLY the final Boolean argument.

"Max is not sour."

Predicate("Sour", ["Max", "False"])

"Every tumpus is not sour."

Rule(
    [Predicate("Tumpus", ["x", "True"])],
    Predicate("Sour", ["x", "False"])
)

Do not turn negative statements into missing facts.

==================================================
QUERY
==================================================

The query represents the EXACT CLAIM being tested.

Never answer the query.

Never use the context to change the query.

"Is Max sour?"

-> Predicate("Sour", ["Max", "True"])

"Is Max not sour?"

-> Predicate("Sour", ["Max", "False"])

"Is Stella bright?"

-> Predicate("Bright", ["Stella", "True"])

"Is Stella not bright?"

-> Predicate("Bright", ["Stella", "False"])

The words "true or false" are only the benchmark's question format.

They do NOT determine the Boolean argument.

CRITICAL: when the query names a specific individual, spell that name
EXACTLY as it was capitalized in the facts (e.g. "Wren", not "wren").
A lowercase entity name is read by the engine as a variable, not the
individual you mean — it silently breaks the query. Named individuals
are always capitalized, in facts AND in the query.

==================================================
NO INFERENCE
==================================================

Do not create derived facts.

Example:

"Alice is kind.
Every kind person is friendly."

Output:

facts:
    Kind(Alice, True)

rules:
    Kind(x, True) -> Friendly(x, True)

Do NOT output:

    Friendly(Alice, True)

The reasoning engine will derive that.

==================================================
RELATIONSHIPS
==================================================

Preserve argument order.

"Bob is friends with Charlie."

-> Predicate("Friends", ["Bob", "Charlie", "True"])

"If someone is friends with another person who is kind..."

Keep the variables consistent:

Friends(person, other, True)
Kind(other, True)

NOT:

Friends(other, person, True)

==================================================
QUERY TYPE
==================================================

Use "first" when asking about one specific statement.

Examples:

"Is Alice kind?"
"Is Max sour?"
"Is Stella bright?"

Use "all" when asking for all matching entities.

Examples:

"Who is friendly?"
"Which people are kind?"

==================================================
FINAL CHECK
==================================================

Before returning the result, verify:

1. Every explicit named statement is a FACT.
2. Every universal statement is a RULE.
3. No FACT contains a lowercase variable.
4. No argument anywhere (Fact or Rule) is a lowercased class/predicate
   name (e.g. "vumpus", "jompus"). Rule variables must be plain names
   like "x", never the class word itself.
5. Every predicate has its final True/False argument.
6. The query exactly matches the claim in the question, and any named
   individual in it is capitalized exactly as in the facts.
7. No derived facts were added.
8. No inference was performed.
9. COMPLETENESS: go back through the input sentence by sentence. Every
   single sentence describing a class ("Xs are Y", "Every X is Y") or a
   named individual ("Name is Y", "Name is an X") must produce exactly
   one Fact or Rule. Count the qualifying sentences and count your
   Facts + Rules — they must match. A single dropped or merged sentence
   breaks the entire reasoning chain, even if every other sentence was
   translated correctly.

==================================================
OUTPUT
==================================================

Return exactly:

facts
rules
query
type

Do not return explanations.
Do not return answers.
Do not return proof traces.
Do not add fields.
"""
INTERPRETER_SYSTEM_PROMPT = """You are the Result Interpreter for a Logic-LM
reasoning system.

A deterministic symbolic logic engine has already executed a query.
Your job is to convert the engine's result and proof trace into a clear,
natural-language explanation.

The symbolic engine is authoritative.

You are NOT a reasoner. You are a VERBALIZER of an already-computed proof.

============================================================
INPUT
=====

You may receive:

* the original natural-language question
* the generated facts
* the generated rules
* the generated query
* the query type ("first" or "all")
* the symbolic result
* a proof trace

The proof trace consists of steps of two types:

FACT:
    A goal was matched directly against a fact in the knowledge base.

RULE:
    A goal was established by applying a rule whose antecedents were
    subsequently proven.

============================================================
ABSOLUTE RULE
=============

The symbolic result and proof trace are authoritative.

DO NOT perform additional inference.

DO NOT reconstruct a proof that is not explicitly represented in the
proof trace.

DO NOT use outside knowledge.

DO NOT invent facts.

DO NOT invent rules.

DO NOT assume relationships that are not shown in the proof.

DO NOT treat a rule itself as a fact.

DO NOT state that a predicate is true merely because it appears somewhere
in the knowledge base. It must be supported by the proof trace.

============================================================
UNDERSTANDING THE PROOF TRACE
=============================

The proof trace is ordered from the original query toward the supporting
facts.

A RULE step means:

    goal
    <- rule

The rule's antecedents are the conditions that must be established.

FACT steps establish those conditions.

For example:

Query:
    Wise(Alice)

Proof:

    RULE:
        Wise(Alice)
        [Friendly(person), Intelligent(person)] -> Wise(person)

    RULE:
        Friendly(Alice)
        [Friends(person, other), Kind(other)] -> Friendly(person)

    FACT:
        Friends(Alice, other)
        Friends(Alice, Bob)

    FACT:
        Kind(Bob)
        Kind(Bob)

    FACT:
        Intelligent(Alice)
        Intelligent(Alice)

The correct explanation is:

    Alice is wise because:
    1. Alice is friends with Bob.
    2. Bob is kind.
    3. Therefore Alice is friendly.
    4. Alice is intelligent.
    5. Friendly and intelligent people are wise.
    6. Therefore Alice is wise.

Notice that "Alice is friendly" is NOT a direct fact.
It is a derived conclusion.

============================================================
FACTS VS DERIVED CONCLUSIONS
=============================

Always distinguish between direct facts and derived conclusions.

If the trace contains:

    FACT:
        Kind(Bob)

say:

    "Bob is kind."

If the trace contains:

    RULE:
        Friendly(Alice)
        [Friends(person, other), Kind(other)] -> Friendly(person)

do NOT say:

    "Alice is friendly (fact)."

Instead say:

    "Alice is friendly because she is friends with Bob and Bob is kind."

If a conclusion requires multiple rules, explain the chain in the same
order represented by the proof trace.

============================================================
RULE APPLICATION
=================

When verbalizing a rule:

1. Identify the instantiated conclusion.
2. Identify the antecedents that were actually proven.
3. Explain how those proven antecedents support the conclusion.
4. Do not mention unused facts from the knowledge base.

Example:

Rule:

    [Friends(person, other), Kind(other)] -> Friendly(person)

With bindings:

    person = Alice
    other = Bob

and supporting facts:

    Friends(Alice, Bob)
    Kind(Bob)

should be verbalized as:

    "Alice is friendly because Alice is friends with Bob and Bob is kind."

Do NOT say:

    "Alice is friendly because Bob is friendly."

Do NOT reverse the relationship.

Do NOT change the arguments of a predicate.

============================================================
SUBSTITUTIONS
=============

Internal variable names such as:

    person__2
    person__9
    other__10

are implementation details.

Do NOT expose these names in the final answer.

Resolve them to their actual constants using the proof information.

For example:

    other__10 = Bob

should be verbalized as:

    "Bob"

not:

    "other__10".

Do not mention substitution dictionaries unless explicitly asked.

============================================================
TRUE / PROVEN QUERIES
=====================

If:

    proved = True

state that the query has been established.

For a specific query, directly answer the question first.

Example:

    Query: Wise(Alice)

Answer:

    "Yes, Alice is wise. Alice is intelligent, and she is friendly because
    she is friends with Bob and Bob is kind. The rule that friendly and
    intelligent people are wise then establishes that Alice is wise."

Only include reasoning steps supported by the proof trace.

============================================================
FALSE / UNPROVEN QUERIES
========================

If:

    proved = False

state that the knowledge base could not establish the queried statement.

Do NOT claim that the opposite is true.

For example:

Query:
    Orbits(Mars, Earth)

If the engine returns:

    proved = False

say:

    "The knowledge base does not establish that Mars orbits Earth."

Do NOT say:

    "Mars does not orbit Earth."

The system uses proof failure, not negation-as-failure.

============================================================
BOOLEAN / NEGATIVE PREDICATES
=============================

The logic engine represents positive and negative statements using a
Boolean argument.

For example:

    Sour(Max, True)

means:

    "Max is sour."

while:

    Sour(Max, False)

means:

    "Max is not sour."

Similarly:

    Bright(Stella, True)

means:

    "Stella is bright."

and:

    Bright(Stella, False)

means:

    "Stella is not bright."

CRITICAL:

`proved = True` means that the EXACT symbolic query was proven.

It does NOT mean that the English positive version of the statement
is true.

For example:

    Query:
        Sour(Max, False)

    proved:
        True

means:

    "Max is not sour."

It must NOT be verbalized as:

    "Max is sour."

Likewise:

    Query:
        Bright(Stella, True)

    proved:
        True

means:

    "Stella is bright."

Always inspect the final Boolean argument of the queried predicate when
verbalizing the answer.

============================================================
TYPE = "FIRST"
==============

For:

    type = "first"

the query asks for one specific proof.

If proved:

    Answer the specific question and briefly explain the successful proof.

If not proved:

    State that the query could not be established.

Even if multiple independent proofs exist, do not list every proof unless
the symbolic result explicitly provides them.

============================================================
TYPE = "ALL"
============

For:

    type = "all"

the query contains an open variable and asks for all matching bindings.

The symbolic engine may return multiple results.

Report the entities that are actually present in the returned bindings.

Example:

Query:
    InSystem(object, Sun)

Results:
    object = Earth
    object = Mars
    object = Moon

Answer:

    "Earth, Mars, and Moon are established to be in the system of the Sun."

Do not add entities that are not present in the symbolic results.

If no successful bindings exist:

    "No entities satisfying the query were established by the knowledge base."

============================================================
MULTIPLE RESULTS
=================

When type = "all", the engine may return multiple proof results.

Combine results that establish the same query binding rather than
repeating identical conclusions.

If different entities are established, list each entity.

If useful, briefly explain the proof for each entity.

Do not confuse multiple proofs of the same entity with multiple entities.

============================================================
NATURAL-LANGUAGE QUALITY
========================

Translate predicates into natural language when doing so is unambiguous.

Examples:

    Kind(Bob)
    -> "Bob is kind."

    Intelligent(Alice)
    -> "Alice is intelligent."

    Friends(Alice, Bob)
    -> "Alice is friends with Bob."

    Orbits(Earth, Sun)
    -> "Earth orbits the Sun."

    InSystem(Moon, Sun)
    -> "The Moon is in the Sun's system."

Preserve the direction and argument order of relationships.

Do not add information that is not represented by the predicate.

============================================================
EXPLANATION STRUCTURE
=====================

For a successful specific query, prefer this structure:

1. Direct answer.
2. Supporting facts.
3. Derived intermediate conclusions.
4. Final rule that establishes the query.

Example:

    "Yes, Alice is wise. Alice is intelligent. Alice is friendly because
    she is friends with Bob and Bob is kind. Since friendly and intelligent
    people are wise, the query is proven."

For a simple direct fact:

    "Yes, Bob is kind. This is directly stated as a fact in the knowledge
    base."

Do not unnecessarily explain unrelated facts.

============================================================
IMPORTANT: DO NOT OVER-INFER
============================

Only describe relationships explicitly represented in the proof.

For example, if the proof contains:

    Friends(Alice, Bob)
    Kind(Bob)

you may say:

    "Alice is friends with Bob, and Bob is kind."

You may NOT say:

    "Alice and Bob are both kind."

You may NOT say:

    "Bob is friendly."

unless the proof actually establishes Friendly(Bob).

You may NOT say:

    "Alice is kind."

unless the proof establishes Kind(Alice).

============================================================
OUTPUT
======

Return ONLY the final natural-language answer.

Do not output:

* JSON
* dictionaries
* substitutions
* predicate syntax
* rule syntax
* proof traces
* internal variable names
* analysis
* confidence scores
* explanations of the interpreter itself

Normally use 1-4 sentences.

For complex multi-step proofs, use enough sentences to accurately explain
the derivation, but remain concise.
"""



client = OpenAI(api_key=OPENAI_KEY)


class PredicateData(BaseModel):
    name: str
    args: list[str]


class RuleData(BaseModel):
    antecedent: list[PredicateData]
    consequent: PredicateData


class LogicProgram(BaseModel):
    facts: list[PredicateData]
    rules: list[RuleData]
    query: PredicateData
    type: Literal["first", "all"]

class Output(BaseModel):
    explanation: str


#  singular predicate name.
def _singular_predicate_name(name, names):









    if name.endswith("es") and name[:-2] in names:
        return name[:-2]
    return name


#  canonicalize predicate names.
def _canonicalize_predicate_names(output):

    names = {fact.name for fact in output.facts}
    names.update(rule.consequent.name for rule in output.rules)
    names.update(
        antecedent.name
        for rule in output.rules
        for antecedent in rule.antecedent
    )
    names.add(output.query.name)

    aliases = {name: _singular_predicate_name(name, names) for name in names}

    # Normalize.
    def normalize(predicate):
        return PredicateData(
            name=aliases[predicate.name],
            args=list(predicate.args),
        )

    output.facts = [normalize(fact) for fact in output.facts]
    output.rules = [
        RuleData(
            antecedent=[normalize(item) for item in rule.antecedent],
            consequent=normalize(rule.consequent),
        )
        for rule in output.rules
    ]
    output.query = normalize(output.query)
    return output


# Validate fact.
def validate_fact(fact):
    for arg in fact.args:
        if logic_engine.Predicate.is_variable(arg):
            raise ValueError(
                f"INVALID FACT: {fact}. "
                f"Facts cannot contain variables."
            )

# Proof to dict.
def proof_to_dict(proof):
    if proof is None:
        return None

    proof_steps = []

                                                                        
                                                                    
                                                                        
                                                                       
                                                 
    final_substitution = proof.substitution

    # Instantiate.
    def instantiate(predicate):
        return repr(logic_engine.apply_substitution(predicate, final_substitution))

    for step in proof.steps:

        if step.source_type == "FACT":
            proof_steps.append({
                "type": "fact",
                "goal": repr(step.goal),
                "fact": repr(step.source)
            })

        else:
            rule = step.source
            instantiated_antecedent = [
                instantiate(p) for p in rule.antecedent
            ]
            instantiated_consequent = instantiate(rule.consequent)

            proof_steps.append({
                "type": "rule",
                "goal": repr(step.goal),
                "rule": (
                    f"{instantiated_antecedent} -> {instantiated_consequent}"
                ),
            })

    return {
        "proof": proof_steps
    }
#  known class names.
def _known_class_names(output):









    names = set()
    for fact in output.facts:
        names.add(fact.name)
    for rule in output.rules:
        names.add(rule.consequent.name)
        for p in rule.antecedent:
            names.add(p.name)
    names.add(output.query.name)
    return names


#  repair misclassified fact.
def _repair_misclassified_fact(fact, known_class_names):






















    if not (
        len(fact.args) == 2
        and logic_engine.Predicate.is_variable(fact.args[0])
        and fact.args[1] in ("True", "False")
    ):
        return None, None

    capitalized = fact.args[0][0].upper() + fact.args[0][1:]

    if capitalized in known_class_names:
                                                              
        repaired_rule = RuleData(
            antecedent=[PredicateData(name=capitalized, args=["x", "True"])],
            consequent=PredicateData(name=fact.name, args=["x", fact.args[1]]),
        )
        return repaired_rule, None

                                                                        
    repaired_fact = PredicateData(name=fact.name, args=[capitalized, fact.args[1]])
    return None, repaired_fact


#  ground first query.
def _ground_first_query(query, facts):

















    known_entities = set()
    for fact in facts:
        for arg in fact.args:
            if not logic_engine.Predicate.is_variable(arg) and arg not in ("True", "False"):
                known_entities.add(arg)

    corrected_args = []
    for arg in query.args:
        if logic_engine.Predicate.is_variable(arg) and arg not in ("True", "False"):
            match = next((e for e in known_entities if e.lower() == arg.lower()), None)
            corrected_args.append(match if match else arg[0].upper() + arg[1:])
        else:
            corrected_args.append(arg)

    return PredicateData(name=query.name, args=corrected_args)


# Process output.
def process_output(output: LogicProgram, KB):

                                                                             
                                                                         
                                                               
    output = _canonicalize_predicate_names(output)

    known_class_names = _known_class_names(output)

    repaired_facts = []
    for fact in output.facts:
        try:
            validate_fact(fact)
        except ValueError:
            repaired_rule, repaired_fact = _repair_misclassified_fact(fact, known_class_names)
            if repaired_rule is not None:
                output.rules.append(repaired_rule)
                continue
            if repaired_fact is not None:
                fact = repaired_fact
                validate_fact(fact)                                           
            else:
                raise

        repaired_facts.append(fact)

    output.facts = repaired_facts

    if output.type == "first":
        output.query = _ground_first_query(output.query, output.facts)

    for fact in output.facts:
        KB.add_fact(
            logic_engine.Predicate(
                fact.name,
                fact.args
            )
        )

    for rule in output.rules:
        KB.add_rule(
            logic_engine.Rule(
                [
                    logic_engine.Predicate(
                        p.name,
                        p.args
                    )
                    for p in rule.antecedent
                ],
                logic_engine.Predicate(
                    rule.consequent.name,
                    rule.consequent.args
                )
            )
        )

    query = logic_engine.Predicate(
        output.query.name,
        output.query.args
    )

                                                              
           
                                                              

    if output.type == "first":

        result = logic_engine.Back_chain_with_trace(
            KB,
            query
        )

        if result is None:
            return {
                "type": "first",
                "proved": False,
                "query": repr(query),
                "result": None
            }

        return {
            "type": "first",
            "proved": True,
            "query": repr(query),
            "result": proof_to_dict(result)
        }

                                                              
         
                                                              

    elif output.type == "all":

        all_results = list(
            logic_engine.prove_with_trace(
                KB,
                query
            )
        )

        return {
            "type": "all",
            "proved": len(all_results) > 0,
            "query": repr(query),
            "results": [
                proof_to_dict(result)
                for result in all_results
            ]
        }

unstructured_text = """Alice is a student at Lincoln High School. Bob is also a student there. 
Alice is friends with Bob, and Bob is friends with Charlie. Bob is 
kind and Alice is intelligent. Anyone who is kind is considered friendly. 
Anyone who is friendly and intelligent is considered wise. If someone is 
friends with another person who is kind, then that person is friendly. 
Is Alice wise?"""

all_text = """Alice is a student at Lincoln High School. Bob is also a student there.
Charlie is a student at Lincoln High School. Alice is friends with Bob.
Bob is friends with Charlie. Charlie is friends with David. Bob is kind.
Charlie is kind. David is intelligent. Alice is intelligent.

Anyone who is kind is considered friendly.
Anyone who is friendly and intelligent is considered wise.
If someone is friends with another person who is kind, then that person is friendly.

Who is friendly?"""



#  entities in proof.
def _entities_in_proof(proof_dict, program=None):








    entities = set()

    # Scan repr.
    def scan_repr(text):
                                                                          
        inside = text[text.find("(") + 1 : text.rfind(")")]
        for arg in inside.split(","):
            arg = arg.strip().strip("[]'\"")
            if arg and not logic_engine.Predicate.is_variable(arg) and arg not in ("True", "False"):
                entities.add(arg)

    if proof_dict.get("result"):
        for step in proof_dict["result"].get("proof", []):
            scan_repr(step["goal"])
    if proof_dict.get("results"):
        for r in proof_dict["results"]:
            if r:
                for step in r.get("proof", []):
                    scan_repr(step["goal"])

                                                                  
    if proof_dict.get("query"):
        scan_repr(proof_dict["query"])

                                                                      
                                                                        
                                          
    if program is not None:
        for fact in program.facts:
            for arg in fact.args:
                if not logic_engine.Predicate.is_variable(arg) and arg not in ("True", "False"):
                    entities.add(arg)

    return sorted(entities)


# Formulate logic program.
def formulate_logic_program(text):
    formulator = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": FORMULATOR_SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        response_format=LogicProgram,
    )



    extracted_data = formulator.choices[0].message.parsed


    KB = logic_engine.KnowledgeBase()
    proof = process_output(extracted_data, KB)

    entities = _entities_in_proof(proof, extracted_data)

    interpreter_user_message = f"""Original problem:
{text}

Symbolic execution result (authoritative JSON — this is the ONLY source
of truth; do not use any fact, rule, or entity that does not literally
appear in it):
{json.dumps(proof, indent=2)}

DETERMINISTIC FACT (do not contradict this): proved = {proof["proved"]}.
Your answer's opening Yes/No (or "established"/"not established" for
type="all") MUST agree with this value exactly.

The ONLY individuals that exist in this proof are: {entities}.
Every other capitalized-looking word in the JSON above (e.g. predicate
names such as "Numpus", "Tumpus", "Yumpus") is a CLASS/PREDICATE NAME,
never an individual. Do not say any individual "refers to" or "is" a
predicate name, and do not introduce a predicate that does not appear
verbatim in the JSON above, even if it looks related.
"""

    explination = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": INTERPRETER_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": interpreter_user_message
            }
        ],
        response_format=Output,
    )



    extracted_data = explination.choices[0].message.parsed
    return [proof["proved"], extracted_data.explanation, proof]


if __name__ == "__main__":
    print(formulate_logic_program(all_text))

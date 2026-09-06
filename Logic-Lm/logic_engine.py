from copy import deepcopy


                                                              
           
                                                              

class Predicate:
    # Initialize the object.
    def __init__(self, name, args):
        self.name = name
        self.args = args

    # Handle the special operation.
    def __repr__(self):
        return f"{self.name}({', '.join(map(str, self.args))})"

    # Handle the special operation.
    def __eq__(self, other):
        return (
            isinstance(other, Predicate)
            and self.name == other.name
            and self.args == other.args
        )

    # Handle the special operation.
    def __hash__(self):
        return hash((self.name, tuple(self.args)))

    @staticmethod
    # Is variable.
    def is_variable(value):









        return (
            isinstance(value, str)
            and len(value) > 0
            and value[0].islower()
        )

    # Substitute.
    def substitute(self, substitution):












        new_args = []

        for arg in self.args:
            new_args.append(resolve(arg, substitution))

        return Predicate(self.name, new_args)


                                                              
      
                                                              

class Rule:
    # Initialize the object.
    def __init__(self, antecedent, consequent):
        if isinstance(antecedent, list):
            self.antecedent = antecedent
        else:
            self.antecedent = [antecedent]

        self.consequent = consequent

    # Handle the special operation.
    def __repr__(self):
        return (
            f"{self.antecedent} -> {self.consequent}"
        )

class ProofStep:
    # Initialize the object.
    def __init__(
        self,
        goal,
        source_type,
        source,
        substitution
    ):
        self.goal = goal
        self.source_type = source_type
        self.source = source
        self.substitution = substitution.copy()

    # Handle the special operation.
    def __repr__(self):
        if self.source_type == "FACT":
            return (
                f"{self.goal} "
                f"[FACT]"
            )

        return (
            f"{self.goal} "
            f"[RULE: {self.source}]"
        )

class ProofResult:
    # Initialize the object.
    def __init__(
        self,
        query,
        substitution,
        steps
    ):
        self.query = query
        self.substitution = substitution
        self.steps = steps

    @property
    # Success.
    def success(self):
        return True

    # Handle the special operation.
    def __repr__(self):
        lines = [
            f"Query: {self.query}",
            "Status: PROVED",
            f"Substitution: {self.substitution}",
            "Proof:"
        ]

        for i, step in enumerate(self.steps, 1):
            lines.append(
                f"  {i}. {step}"
            )

        return "\n".join(lines)

                                                              
                
                                                              

class KnowledgeBase:
    # Initialize the object.
    def __init__(self):
        self.rules = []
        self.facts = []

    # Add rule.
    def add_rule(self, rule):
        self.rules.append(rule)

    # Add fact.
    def add_fact(self, fact):
        self.facts.append(fact)

    # Handle the special operation.
    def __repr__(self):
        return (
            f"Rules: {self.rules}\n"
            f"Facts: {self.facts}"
        )


                                                              
                     
                                                              

# Resolve.
def resolve(term, substitution):














    visited = set()

    while (
        isinstance(term, str)
        and Predicate.is_variable(term)
        and term in substitution
        and term not in visited
    ):
        visited.add(term)
        term = substitution[term]

    return term


                                                              
             
                                                              

# Occurs check.
def occurs_check(variable, term, substitution):









    term = resolve(term, substitution)

    return term == variable


# Unify terms.
def unify_terms(a, b, substitution):








    a = resolve(a, substitution)
    b = resolve(b, substitution)

                       
    if a == b:
        return substitution

                     
    if Predicate.is_variable(a):

        if occurs_check(a, b, substitution):
            return None

        substitution[a] = b
        return substitution

                     
    if Predicate.is_variable(b):

        if occurs_check(b, a, substitution):
            return None

        substitution[b] = a
        return substitution

                                        
    return None


# Unify.
def unify(predicate_a, predicate_b, substitution=None):



















    if substitution is None:
        substitution = {}

    else:
        substitution = substitution.copy()

    if not isinstance(predicate_a, Predicate):
        return None

    if not isinstance(predicate_b, Predicate):
        return None

                                
    if predicate_a.name != predicate_b.name:
        return None

                                
    if len(predicate_a.args) != len(predicate_b.args):
        return None

    for a, b in zip(
        predicate_a.args,
        predicate_b.args
    ):
        result = unify_terms(
            a,
            b,
            substitution
        )

        if result is None:
            return None

        substitution = result

    return substitution


                                                              
                          
                                                              

_variable_counter = 0


# Fresh variable name.
def fresh_variable_name(name):















    global _variable_counter

    _variable_counter += 1

    return f"{name}__{_variable_counter}"


# Freshen predicate.
def freshen_predicate(predicate):





    variable_map = {}

    new_args = []

    for arg in predicate.args:

        if Predicate.is_variable(arg):

            if arg not in variable_map:
                variable_map[arg] = fresh_variable_name(arg)

            new_args.append(
                variable_map[arg]
            )

        else:
            new_args.append(arg)

    return Predicate(
        predicate.name,
        new_args
    ), variable_map


# Freshen rule.
def freshen_rule(rule):




    variable_map = {}

    # Rename predicate.
    def rename_predicate(predicate):

        new_args = []

        for arg in predicate.args:

            if Predicate.is_variable(arg):

                if arg not in variable_map:
                    variable_map[arg] = (
                        fresh_variable_name(arg)
                    )

                new_args.append(
                    variable_map[arg]
                )

            else:
                new_args.append(arg)

        return Predicate(
            predicate.name,
            new_args
        )

    new_antecedent = [
        rename_predicate(goal)
        for goal in rule.antecedent
    ]

    new_consequent = rename_predicate(
        rule.consequent
    )

    return Rule(
        new_antecedent,
        new_consequent
    )


                                                              
                    
                                                              

# Apply substitution.
def apply_substitution(predicate, substitution):




    return predicate.substitute(
        substitution
    )


                                                              
                   
                                                              

MAX_PROOF_DEPTH = 500


# Prove all.
def prove_all(KB, goals, substitution=None, _visited=None, _depth=0):
















    if substitution is None:
        substitution = {}

    if _visited is None:
        _visited = frozenset()

    if _depth > MAX_PROOF_DEPTH:
        return

                      
                                    
    if len(goals) == 0:
        yield substitution
        return

    current_goal = goals[0]

    remaining_goals = goals[1:]

                                        
    current_goal = apply_substitution(
        current_goal,
        substitution
    )

                                 
    for new_substitution in prove(
        KB,
        current_goal,
        substitution,
        _visited,
        _depth + 1
    ):

                                              
        yield from prove_all(
            KB,
            remaining_goals,
            new_substitution,
            _visited,
            _depth + 1
        )


# Prove.
def prove(KB, goal, substitution=None, _visited=None, _depth=0):











    if substitution is None:
        substitution = {}

    if _visited is None:
        _visited = frozenset()

    if _depth > MAX_PROOF_DEPTH:
        return

                                                                       
                                                                     
                                                               
    goal_key = repr(goal)

    if goal_key in _visited:
        return

                                                              
               
                                                              

    for fact in KB.facts:

        result = unify(
            goal,
            fact,
            substitution
        )

        if result is not None:
            yield result

                                                              
               
                                                              

    next_visited = _visited | {goal_key}

    for rule in KB.rules:

                                                    
        fresh_rule = freshen_rule(rule)

                                            
                                
        result = unify(
            goal,
            fresh_rule.consequent,
            substitution
        )

        if result is None:
            continue

                                                    
        new_goals = [
            apply_substitution(
                antecedent,
                result
            )
            for antecedent in fresh_rule.antecedent
        ]

                                         
        yield from prove_all(
            KB,
            new_goals,
            result,
            next_visited,
            _depth + 1
        )



# Prove with trace.
def prove_with_trace(
    KB,
    goal,
    substitution=None,
    trace=None,
    _visited=None,
    _depth=0
):










    if substitution is None:
        substitution = {}

    if trace is None:
        trace = []

    if _visited is None:
        _visited = frozenset()

    if _depth > MAX_PROOF_DEPTH:
        return

    goal_key = repr(goal)

    if goal_key in _visited:
        return

                                                              
               
                                                              

    for fact in KB.facts:

        result = unify(
            goal,
            fact,
            substitution
        )

        if result is not None:

            step = ProofStep(
                goal=goal,
                source_type="FACT",
                source=fact,
                substitution=result
            )

            yield ProofResult(
                query=goal,
                substitution=result,
                steps=trace + [step]
            )

                                                              
               
                                                              

    next_visited = _visited | {goal_key}

    for rule in KB.rules:

        fresh_rule = freshen_rule(rule)

        result = unify(
            goal,
            fresh_rule.consequent,
            substitution
        )

        if result is None:
            continue

        new_goals = [
            apply_substitution(
                antecedent,
                result
            )
            for antecedent in fresh_rule.antecedent
        ]

        rule_step = ProofStep(
            goal=goal,
            source_type="RULE",
            source=fresh_rule,
            substitution=result
        )

        yield from prove_goals_with_trace(
            KB,
            new_goals,
            result,
            trace + [rule_step],
            next_visited,
            _depth + 1
        )

# Prove goals with trace.
def prove_goals_with_trace(
    KB,
    goals,
    substitution,
    trace,
    _visited=None,
    _depth=0
):





    if _visited is None:
        _visited = frozenset()

    if _depth > MAX_PROOF_DEPTH:
        return

    if len(goals) == 0:

        yield ProofResult(
            query=None,
            substitution=substitution,
            steps=trace
        )

        return

    current_goal = apply_substitution(
        goals[0],
        substitution
    )

    remaining_goals = goals[1:]

    for proof in prove_with_trace(
        KB,
        current_goal,
        substitution,
        trace,
        _visited,
        _depth + 1
    ):

        yield from prove_goals_with_trace(
            KB,
            remaining_goals,
            proof.substitution,
            proof.steps,
            _visited,
            _depth + 1
        )


                                                              
                       
                                                              

# Back chain.
def Back_chain(KB, goal):










    for result in prove(KB, goal):

                                                       
                                               
        cleaned = {}

        for key, value in result.items():
            cleaned[key] = resolve(
                value,
                result
            )

        return cleaned

    return None

# Back chain with trace.
def Back_chain_with_trace(KB, goal):





    for proof in prove_with_trace(KB, goal):

        proof.query = goal

        return proof

    return None

if __name__ == "__main__":
        
                                                                  
                          
                                                                  

    KB = KnowledgeBase()


                                                                  
            
     
                          
         
                          
        
                          
                                                                  

    KB.add_rule(
        Rule(
            [
                Predicate(
                    "Orbits",
                    ["moon", "planet"]
                ),

                Predicate(
                    "Orbits",
                    ["planet", "star"]
                )
            ],

            Predicate(
                "InSystem",
                ["moon", "star"]
            )
        )
    )


                                                                  
            
     
                          
        
                            
                                                                  

    KB.add_rule(
        Rule(
            Predicate(
                "Orbits",
                ["planet", "star"]
            ),

            Predicate(
                "InSystem",
                ["planet", "star"]
            )
        )
    )


                                                                  
            
     
                            
         
                        
        
                             
                                                                  

    KB.add_rule(
        Rule(
            [
                Predicate(
                    "InSystem",
                    ["object", "star"]
                ),

                Predicate(
                    "MainSequence",
                    ["star"]
                )
            ],

            Predicate(
                "PlanetaryObject",
                ["object"]
            )
        )
    )


                                                                  
            
     
                            
         
                           
        
                                  
                                                                  

    KB.add_rule(
        Rule(
            [
                Predicate(
                    "HasLiquidWater",
                    ["planet"]
                ),

                Predicate(
                    "HabitableZone",
                    ["planet"]
                )
            ],

            Predicate(
                "PotentiallyHabitable",
                ["planet"]
            )
        )
    )


                                                                  
            
     
                          
         
                         
        
                                   
                                                                  

    KB.add_rule(
        Rule(
            [
                Predicate(
                    "Orbits",
                    ["planet", "star"]
                ),

                Predicate(
                    "StableOrbit",
                    ["planet"]
                )
            ],

            Predicate(
                "StablePlanetarySystem",
                ["planet"]
            )
        )
    )


                                                                  
            
     
                               
        
                         
                                                                  

    KB.add_rule(
        Rule(
            Predicate(
                "FartherFrom",
                ["planet", "star"]
            ),

            Predicate(
                "OuterPlanet",
                ["planet"]
            )
        )
    )


                                                                  
           
                                                                  

    KB.add_fact(
        Predicate(
            "Orbits",
            ["Earth", "Sun"]
        )
    )

    KB.add_fact(
        Predicate(
            "Orbits",
            ["Mars", "Sun"]
        )
    )

    KB.add_fact(
        Predicate(
            "Orbits",
            ["Jupiter", "Sun"]
        )
    )

    KB.add_fact(
        Predicate(
            "Orbits",
            ["Moon", "Earth"]
        )
    )

    KB.add_fact(
        Predicate(
            "Orbits",
            ["Europa", "Jupiter"]
        )
    )

    KB.add_fact(
        Predicate(
            "MainSequence",
            ["Sun"]
        )
    )

    KB.add_fact(
        Predicate(
            "HasLiquidWater",
            ["Earth"]
        )
    )

    KB.add_fact(
        Predicate(
            "HabitableZone",
            ["Earth"]
        )
    )

    KB.add_fact(
        Predicate(
            "StableOrbit",
            ["Earth"]
        )
    )

    KB.add_fact(
        Predicate(
            "StableOrbit",
            ["Mars"]
        )
    )

    KB.add_fact(
        Predicate(
            "FartherFrom",
            ["Jupiter", "Sun"]
        )
    )


                                                                  
           
                                                                  

    print("\n--- Space Knowledge Base Tests ---")


    tests = [

        (
            "InSystem(Earth,Sun)",
            Predicate(
                "InSystem",
                ["Earth", "Sun"]
            )
        ),

        (
            "InSystem(Moon,Sun)",
            Predicate(
                "InSystem",
                ["Moon", "Sun"]
            )
        ),

        (
            "InSystem(Europa,Sun)",
            Predicate(
                "InSystem",
                ["Europa", "Sun"]
            )
        ),

        (
            "PlanetaryObject(Earth)",
            Predicate(
                "PlanetaryObject",
                ["Earth"]
            )
        ),

        (
            "PlanetaryObject(Moon)",
            Predicate(
                "PlanetaryObject",
                ["Moon"]
            )
        ),

        (
            "PotentiallyHabitable(Earth)",
            Predicate(
                "PotentiallyHabitable",
                ["Earth"]
            )
        ),

        (
            "StablePlanetarySystem(Earth)",
            Predicate(
                "StablePlanetarySystem",
                ["Earth"]
            )
        ),

        (
            "OuterPlanet(Jupiter)",
            Predicate(
                "OuterPlanet",
                ["Jupiter"]
            )
        ),

        (
            "InSystem(Moon,Mars)",
            Predicate(
                "InSystem",
                ["Moon", "Mars"]
            )
        )
    ]


    for name, query in tests:

        result = Back_chain(
            KB,
            query
        )

        print(
            f"{name:<35}",
            "=>",
            result is not None,
            result
        )


                                                                  
                                 
                                                                  

    print("\n--- Multiple Proof Test ---")

    query = Predicate(
        "InSystem",
        ["x", "Sun"]
    )

    all_results = list(
        prove(KB, query)
    )

    for result in all_results:

        resolved = {
            key: resolve(value, result)
            for key, value in result.items()
        }

        print(
            "InSystem(x,Sun)",
            "=>",
            resolved
        )


                                                                  
                              
                                                                  

    print("\n--- Direct Query ---")

    query = Predicate(
        "PotentiallyHabitable",
        ["Earth"]
    )

    result = Back_chain(
        KB,
        query
    )

    print(
        "PotentiallyHabitable(Earth)",
        "=>",
        result is not None,
        result
    )

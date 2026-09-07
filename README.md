# Logic Reasoning Projects

This workspace contains two related projects:

- `Logic-Lm/`: the dataset-backed Logic-LM symbolic reasoning pipeline.
- `LangGraph_Proj/`: a conversational LangGraph agent using a local astronomy knowledge base.

## Setup

From the workspace root:

```bash
source env/bin/activate
```

For Logic-LM, install the dependencies:

```bash
cd Logic-Lm
pip install -r requirements.txt
```

Set the OpenAI and Gemini key in `Logic-Lm/.env`:

```env
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

For the LangGraph agent, install its dependencies:

```bash
cd ../LangGraph_Proj
pip install langchain langchain-core langchain-community langgraph \
  langchain-google-genai faiss-cpu typing-extensions
```

Set the Google key:

```bash
export GOOGLE_API_KEY=your_key_here
```

## Logic-LM

Logic-LM converts natural language into symbolic programs and runs local
solvers:

- LP: backward-chaining engine in `logic_engine.py`.
- FOL: Prover9 in `FOL/implementation.py`.
- CSP: finite-domain constraints in `CSP/implementation.py`.
- SAT: Boolean constraints with Z3 in `SAT/implementation.py`.

Run one problem:

```bash
cd /Users/sasidharjasty/Logic-Lm/Logic-Lm
python main.py --text "Every human is mortal. Socrates is human. Is Socrates mortal?"
```

Run downloaded datasets:

```bash
python main.py --dataset prontoqa --split test --limit 5
python main.py --dataset proofwriter --split test --limit 5
python main.py --dataset folio --split validation --limit 5
python main.py --dataset logical_deduction --split train --limit 5
python main.py --dataset ar_lsat --split test --limit 5
```

Merge and validate all downloaded records:

```bash
python main.py --merge-datasets
python main.py --test-merged
```

Run the full OpenAI-backed evaluation with progress and metrics:

```bash
python main.py --test-merged --execute --metrics --limit 63970
```

This makes one model-backed call per record and may be expensive. Each round
prints `SUCCESS` or `FAILURE`. Use `--quiet` to suppress progress lines.

Run offline checks:

```bash
python -m py_compile main.py SAT/implementation.py
python test_prontoqa_offline.py
```

## LangGraph agent

The executable is `LangGraph_Proj/mainpy`. It builds an astronomy knowledge
base, creates a FAISS retrieval index, and uses LangGraph tool calls with
Google Gemini.

Run it as a standalone program:

```bash
cd /Users/sasidharjasty/Logic-Lm/LangGraph_Proj
python mainpy
```

The agent supports these tools:

- `search_knowledge_base`: retrieve relevant facts and rules.
- `identify_goal`: convert a specific claim to a symbolic predicate.
- `logic_reasoner`: prove a grounded predicate with backward chaining.
- `find_entities`: find entities matching a predicate.

Example question:

```text
Does Venus orbit Earth?
```

Enter `exit` to stop the interactive session. The current LangGraph knowledge
base is the astronomy example embedded in `mainpy`; it is separate from the
downloaded benchmark datasets used by Logic-LM.

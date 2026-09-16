# LiveCodeBench — the prompt every model receives

One turn, no tools, no examples beyond what the problem statement contains. Adopted
from LiveCodeBench's own generic template (`lcb_runner/prompts/code_generation.py`)
so scores stay comparable to the public leaderboard. Two variants, chosen by whether
the problem ships starter code.

## System message

```
You are an expert Python programmer. You will be given a question (problem specification) and will generate a correct Python program that matches the specification and passes all tests.
```

## User message — problems WITH starter code (LeetCode-style: complete the given class/function)

```
### Question:
{question_content}

### Format: You will use the following starter code to write the solution to the problem and enclose your code within delimiters.
```python
{starter_code}
```

### Answer: (use the provided format with backticks)

```

## User message — problems WITHOUT starter code (stdin/stdout)

```
### Question:
{question_content}

### Format: Read the inputs from stdin solve the problem and write the answer to stdout (do not directly test on the sample inputs). Enclose your code within delimiters as follows. Ensure that when the python program runs, it reads the inputs, runs the algorithm and writes output to STDOUT.
```python
# YOUR CODE HERE
```

### Answer: (use the provided format with backticks)

```

## What is extracted

The first ```python fenced block in the reply is the program. Everything else the model
writes — its reasoning, explanation, alternatives — stays in the trace and is what the
judge reads; only the block is executed.

## Settings

Temperature 0. Reasoning off, matching models-1 on HoVer. One sample per problem.

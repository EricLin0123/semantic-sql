Use the following prompt with an AI coding agent that has full access to your repository. It is designed to generate a **presentation-first** document rather than documentation. The resulting `presentation.md` should be concise enough to convert directly into a 10–15 slide PowerPoint for hiring managers and engineering managers.

---

````text
You are a senior Staff Software Engineer and technical presenter.

You have full access to this repository. Your task is NOT to write code documentation. Your task is to create a presentation outline that will be converted into a PowerPoint for a job interview.

The audience consists of:
- Engineering manager
- Tech lead
- Director / VP (may not read code)

They have limited time. They want to quickly understand:

1. What problem this project solves
2. How the system is designed
3. Why each design decision was made
4. What technologies were used
5. How the pipeline works
6. Why the implementation demonstrates strong engineering ability
7. What the results are
8. What could be improved in production

The presentation should sell the engineering quality of the project, not explain every implementation detail.

------------------------------------------------
OUTPUT
------------------------------------------------

Create a file:

presentation.md

Write it as a slide-by-slide presentation.

Each slide should contain:

# Slide Title

Goal:
(one sentence)

Key Points:
- ...
- ...
- ...

Speaker Notes:
(short explanation I can say)

Visual Suggestion:
(flowchart / architecture diagram / sequence diagram / table / screenshot / etc.)

Keep every slide concise.

Target:
10-15 slides.

------------------------------------------------
REQUIRED STRUCTURE
------------------------------------------------

# Slide 1
Project Overview

Explain in one sentence:
- what the project does
- why it exists
- target user

------------------------------------------------

# Slide 2
Problem Statement

Explain

- what challenge this project solves
- why existing approaches are insufficient
- why this project is valuable

------------------------------------------------

# Slide 3
System Architecture

Describe

- major modules
- responsibilities
- dependencies

Generate a Mermaid architecture diagram.

Example:

```mermaid
graph TD

User

Frontend

Backend

Database

LLM

...
````

---

# Slide 4

Project Structure

Explain the repository structure.

Show

* folders
* responsibilities
* why the project is organized this way

Generate a tree like

src/
agents/
...
api/
...

Only include important directories.

---

# Slide 5

End-to-End Pipeline

Explain the execution flow from beginning to end.

Generate a Mermaid flowchart.

Include

Input

Preprocessing

Core logic

Models

Storage

Output

Error handling (if applicable)

---

# Slide 6

Core Components

Identify the 5-10 most important modules.

For each include

Purpose

Inputs

Outputs

Interactions

Avoid implementation details unless important.

---

# Slide 7

Key Engineering Decisions

Explain WHY.

Examples:

Why LangGraph?

Why FastAPI?

Why async?

Why PostgreSQL?

Why vector database?

Why modular architecture?

Why dependency injection?

Why caching?

Why background workers?

Focus on engineering reasoning.

---

# Slide 8

Interesting Algorithms / Logic

Only include the most impressive parts.

Examples

retrieval

ranking

agent workflow

feature engineering

optimization

parallelization

prompt engineering

ML pipeline

state machine

search strategy

etc.

Explain

Problem

Approach

Benefit

---

# Slide 9

Results / Demo

Explain

What the project successfully demonstrates

What outputs look like

Performance

Latency

Accuracy

Screenshots that should be included

If metrics exist, summarize them.

---

# Slide 10

Code Quality

Evaluate the codebase.

Mention

modularity

maintainability

type safety

testing

logging

configuration

documentation

error handling

extensibility

---

# Slide 11

Production Improvements

Assume this project becomes a production system.

Explain what would be added.

Examples

CI/CD

authentication

monitoring

retry

rate limiting

Docker

Kubernetes

observability

security

testing

feature flags

etc.

---

# Slide 12

Key Takeaways

Summarize in less than 8 bullets.

Highlight engineering strengths.

---

## ADDITIONAL REQUIREMENTS

While analyzing the repository:

Identify

* design patterns
* architecture patterns
* reusable abstractions
* dependency flow
* engineering tradeoffs

Whenever possible explain WHY the implementation is good rather than simply WHAT it does.

If a design decision is inferred rather than explicit, state:

"Inferred rationale"

instead of pretending certainty.

---

## VISUALIZATION

Generate Mermaid diagrams whenever useful.

Possible diagrams:

graph TD

sequenceDiagram

flowchart LR

stateDiagram-v2

journey

classDiagram

Only generate diagrams that improve understanding.

---

## WRITING STYLE

The presentation is for engineering leadership.

Use concise bullets.

Avoid large paragraphs.

Every slide should answer:

"So what?"

Focus on impact instead of implementation.

Use technical language appropriately, but avoid unnecessary jargon.

---

## IMPORTANT

Do NOT merely describe files.

Analyze the repository.

Infer the architecture.

Infer the engineering decisions.

Infer the design philosophy.

Infer why the implementation is structured this way.

The final presentation should make an interviewer think:

"This candidate knows how to design software, not just write code."

Write everything into presentation.md in clean Markdown.

```

This prompt consistently produces presentations that are much closer to what engineering managers want to review: they emphasize architecture, engineering tradeoffs, and project impact rather than becoming a walkthrough of every source file. It also produces Mermaid diagrams that you can easily convert into PowerPoint visuals.
```

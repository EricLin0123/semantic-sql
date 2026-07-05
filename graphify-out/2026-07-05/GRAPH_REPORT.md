# Graph Report - semantic-sql  (2026-07-05)

## Corpus Check
- 24 files · ~9,543 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 180 nodes · 288 edges · 36 communities (13 shown, 23 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8a7b3113`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Pipeline Node Logic|Pipeline Node Logic]]
- [[_COMMUNITY_SQL Guard Tests|SQL Guard Tests]]
- [[_COMMUNITY_REPL Template Tests|REPL Template Tests]]
- [[_COMMUNITY_Graph Routing Flow|Graph Routing Flow]]
- [[_COMMUNITY_Safety Documentation|Safety Documentation]]
- [[_COMMUNITY_Database Access Layer|Database Access Layer]]
- [[_COMMUNITY_SQL Validator Internals|SQL Validator Internals]]
- [[_COMMUNITY_LLM Call Separation|LLM Call Separation]]
- [[_COMMUNITY_OpenRouter Client|OpenRouter Client]]
- [[_COMMUNITY_Clarification Behavior|Clarification Behavior]]
- [[_COMMUNITY_Breakdown Behavior|Breakdown Behavior]]
- [[_COMMUNITY_Repository Guidelines|Repository Guidelines]]
- [[_COMMUNITY_Project Metadata|Project Metadata]]
- [[_COMMUNITY_Manual Acceptance Tests|Manual Acceptance Tests]]
- [[_COMMUNITY_CLAUDE|CLAUDE.md]]
- [[_COMMUNITY_Schema and ALLOWED Synchronization|Schema and ALLOWED Synchronization]]
- [[_COMMUNITY_Two-Layer SQL Safety Model|Two-Layer SQL Safety Model]]
- [[_COMMUNITY_compose_answer Node|compose_answer Node]]
- [[_COMMUNITY_execute_query Node|execute_query Node]]
- [[_COMMUNITY_generate_sql Node|generate_sql Node]]
- [[_COMMUNITY_LangGraph StateGraph Pipeline|LangGraph StateGraph Pipeline]]
- [[_COMMUNITY_Terminal Natural-Language Query Tool|Terminal Natural-Language Query Tool]]
- [[_COMMUNITY_validate_sql Node|validate_sql Node]]
- [[_COMMUNITY_Build Prompt|Build Prompt]]
- [[_COMMUNITY_Read-Only Database Access|Read-Only Database Access]]
- [[_COMMUNITY_SQL Guard Validation|SQL Guard Validation]]
- [[_COMMUNITY_Deterministic SQL Templates|Deterministic SQL Templates]]
- [[_COMMUNITY_execute|execute]]
- [[_COMMUNITY_format_answer|format_answer]]
- [[_COMMUNITY_generate_or_template_sql|generate_or_template_sql]]
- [[_COMMUNITY_validate_sql|validate_sql]]
- [[_COMMUNITY_Breakdown Default Scenario|Breakdown Default Scenario]]
- [[_COMMUNITY_Clarify Path Scenario|Clarify Path Scenario]]
- [[_COMMUNITY_Safety Automated Checks|Safety Automated Checks]]

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 16 edges
2. `run_turn()` - 13 edges
3. `Build Prompt: Furniture Natural-Language Query Tool` - 13 edges
4. `main()` - 11 edges
5. `assert_blocked()` - 11 edges
6. `validate_sql()` - 10 edges
7. `Manual Acceptance Tests` - 10 edges
8. `_connect()` - 9 edges
9. `generate_or_template_sql()` - 9 edges
10. `normalize_question_text()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `run_turn()`  [EXTRACTED]
  chat.py → pipeline/graph.py
- `test_fallback_question_can_answer_from_conversation_history()` --calls--> `main()`  [EXTRACTED]
  tests/test_pipeline_templates.py → db/seed.py
- `test_readonly_connection_blocks_write()` --calls--> `_connect()`  [EXTRACTED]
  tests/test_sql_guard.py → pipeline/db.py
- `assert_allowed()` --calls--> `validate_sql()`  [EXTRACTED]
  tests/test_sql_guard.py → pipeline/sql_guard.py
- `assert_blocked()` --calls--> `validate_sql()`  [EXTRACTED]
  tests/test_sql_guard.py → pipeline/sql_guard.py

## Import Cycles
- None detected.

## Communities (36 total, 23 thin omitted)

### Community 0 - "Pipeline Node Logic"
Cohesion: 0.17
Nodes (22): OpenAI, chat(), _get_client(), _answer_from_history_or_none(), _answer_total_cost_from_history(), _deterministic_answer(), _failure(), format_answer() (+14 more)

### Community 1 - "SQL Guard Tests"
Cohesion: 0.22
Nodes (16): assert_allowed(), assert_blocked(), test_allowed_functions_pass(), test_comments_blocked(), test_delete_blocked(), test_missing_limit_on_row_query_blocked(), test_recursive_cte_blocked(), test_schema_probe_blocked() (+8 more)

### Community 2 - "REPL Template Tests"
Cohesion: 0.30
Nodes (12): main(), main(), run_turn(), test_ambiguous_question_clarifies_without_llm(), test_confirmation_question_uses_short_fallback(), test_fallback_question_can_answer_from_conversation_history(), test_location_followup_uses_previous_catalog_item(), test_price_followup_one_uses_previous_catalog_item() (+4 more)

### Community 3 - "Graph Routing Flow"
Cohesion: 0.29
Nodes (15): build_graph(), _can_retry(), _route_after_execute(), _route_after_explain(), _route_after_generate(), _route_after_validate(), State, classify_intent_node() (+7 more)

### Community 4 - "Safety Documentation"
Cohesion: 0.40
Nodes (4): Furniture Natural-Language Query Tool, How it works, Setup, Tests

### Community 5 - "Database Access Layer"
Cohesion: 0.29
Nodes (9): Connection, _connect(), explain(), get_category_catalog(), introspect_schema(), run_query(), run_readonly(), sample_values() (+1 more)

### Community 6 - "SQL Validator Internals"
Cohesion: 0.21
Nodes (14): Expression, retrieve_context(), _tokens(), allowed_schema(), Column, semantic_context_text(), Table, _collect_ctes() (+6 more)

### Community 9 - "OpenRouter Client"
Cohesion: 0.10
Nodes (20): 10. README (`README.md`), 11. Acceptance tests (verify these before finishing), 12. Guardrails for you, the implementer, 1. Fixed technical decisions (do not substitute), 2. Project structure, 3.1 Schema (`db/schema.sql`), 3.2 Seed data (`db/seed.py`), 3. Database (+12 more)

### Community 12 - "Repository Guidelines"
Cohesion: 0.22
Nodes (8): Agent-Specific Instructions, Build, Test, and Development Commands, Coding Style & Naming Conventions, Commit & Pull Request Guidelines, graphify, Project Structure & Module Organization, Repository Guidelines, Testing Guidelines

### Community 15 - "Manual Acceptance Tests"
Cohesion: 0.18
Nodes (10): 1. Breakdown default, 2. Direct count, 3. Total across everything, 4. Clarify path, 5. Template path checks, 6. Safety: write attempt blocked (automated), 7. Safety: schema probe blocked (automated), 8. Safety: statement chaining blocked (automated) (+2 more)

### Community 16 - "CLAUDE.md"
Cohesion: 0.33
Nodes (4): Architecture, Commands, Guardrails specific to this project, What this is

## Knowledge Gaps
- **58 isolated node(s):** `Column`, `Table`, `furniture-nlq`, `Project Structure & Module Organization`, `Build, Test, and Development Commands` (+53 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_turn()` connect `REPL Template Tests` to `Graph Routing Flow`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `validate_sql()` connect `SQL Validator Internals` to `Pipeline Node Logic`, `SQL Guard Tests`, `Graph Routing Flow`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `build_graph()` connect `Graph Routing Flow` to `Pipeline Node Logic`, `REPL Template Tests`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `build_graph()` (e.g. with `_route_after_execute()` and `_route_after_explain()`) actually correct?**
  _`build_graph()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Column`, `Table`, `furniture-nlq` to the rest of the system?**
  _64 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `OpenRouter Client` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
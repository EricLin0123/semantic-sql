# Graph Report - .  (2026-07-05)

## Corpus Check
- Corpus is ~8,806 words - fits in a single context window. You may not need a graph.

## Summary
- 126 nodes · 251 edges · 16 communities (11 shown, 5 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Pipeline Node Logic|Pipeline Node Logic]]
- [[_COMMUNITY_SQL Guard Tests|SQL Guard Tests]]
- [[_COMMUNITY_REPL Template Tests|REPL Template Tests]]
- [[_COMMUNITY_Graph Routing Flow|Graph Routing Flow]]
- [[_COMMUNITY_Safety Documentation|Safety Documentation]]
- [[_COMMUNITY_Database Access Layer|Database Access Layer]]
- [[_COMMUNITY_SQL Validator Internals|SQL Validator Internals]]
- [[_COMMUNITY_Retrieval Semantic Context|Retrieval Semantic Context]]
- [[_COMMUNITY_LLM Call Separation|LLM Call Separation]]
- [[_COMMUNITY_OpenRouter Client|OpenRouter Client]]
- [[_COMMUNITY_Clarification Behavior|Clarification Behavior]]
- [[_COMMUNITY_Breakdown Behavior|Breakdown Behavior]]
- [[_COMMUNITY_Repository Guidelines|Repository Guidelines]]
- [[_COMMUNITY_Project Metadata|Project Metadata]]
- [[_COMMUNITY_Manual Acceptance Tests|Manual Acceptance Tests]]

## God Nodes (most connected - your core abstractions)
1. `build_graph()` - 16 edges
2. `run_turn()` - 13 edges
3. `assert_blocked()` - 11 edges
4. `main()` - 10 edges
5. `validate_sql()` - 10 edges
6. `_connect()` - 9 edges
7. `State` - 8 edges
8. `generate_or_template_sql()` - 8 edges
9. `normalize_question_text()` - 8 edges
10. `assert_allowed()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Furniture Natural-Language Query Tool` --semantically_similar_to--> `Terminal Natural-Language Query Tool`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `Two-Layer SQL Safety Model` --semantically_similar_to--> `Read-Only Database Access`  [INFERRED] [semantically similar]
  AGENTS.md → docs/plan.md
- `Safety Automated Checks` --semantically_similar_to--> `Two-Layer SQL Safety Model`  [INFERRED] [semantically similar]
  tests/test_manual.md → AGENTS.md
- `validate_sql` --semantically_similar_to--> `SQL Guard Validation`  [INFERRED] [semantically similar]
  README.md → docs/plan.md
- `Breakdown Default Scenario` --semantically_similar_to--> `Default Breakdown Behavior`  [INFERRED] [semantically similar]
  tests/test_manual.md → docs/plan.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Two-Layer SQL Safety Across Docs** — agents_two_layer_sql_safety_model, docs_plan_read_only_database_access, docs_plan_sql_guard_validation, readme_validate_sql, tests_test_manual_safety_automated_checks [INFERRED 0.95]
- **Query Pipeline Flow Across Docs** — claude_langgraph_stategraph_pipeline, readme_generate_or_template_sql, readme_validate_sql, readme_execute, readme_format_answer [INFERRED 0.85]
- **Acceptance Tests Validate Documented Behavior** — tests_test_manual_breakdown_default, tests_test_manual_clarify_path, docs_plan_default_breakdown_behavior, docs_plan_clarify_when_ambiguous, readme_deterministic_templates [INFERRED 0.85]

## Communities (16 total, 5 thin omitted)

### Community 0 - "Pipeline Node Logic"
Cohesion: 0.20
Nodes (18): classify_intent_node(), _deterministic_answer(), _failure(), _format_money(), generate_or_template_sql(), normalize_question(), _parse_json_response(), record_trace() (+10 more)

### Community 1 - "SQL Guard Tests"
Cohesion: 0.22
Nodes (16): assert_allowed(), assert_blocked(), test_allowed_functions_pass(), test_comments_blocked(), test_delete_blocked(), test_missing_limit_on_row_query_blocked(), test_recursive_cte_blocked(), test_schema_probe_blocked() (+8 more)

### Community 2 - "REPL Template Tests"
Cohesion: 0.33
Nodes (11): main(), main(), run_turn(), test_ambiguous_question_clarifies_without_llm(), test_confirmation_question_uses_short_fallback(), test_location_followup_uses_previous_catalog_item(), test_price_followup_one_uses_previous_catalog_item(), test_price_question_returns_unit_price_not_quantity() (+3 more)

### Community 3 - "Graph Routing Flow"
Cohesion: 0.34
Nodes (13): build_graph(), _can_retry(), _route_after_execute(), _route_after_explain(), _route_after_generate(), _route_after_validate(), State, dry_run_explain() (+5 more)

### Community 4 - "Safety Documentation"
Cohesion: 0.15
Nodes (13): Schema and ALLOWED Synchronization, Two-Layer SQL Safety Model, Terminal Natural-Language Query Tool, Build Prompt, Read-Only Database Access, SQL Guard Validation, Deterministic SQL Templates, execute (+5 more)

### Community 5 - "Database Access Layer"
Cohesion: 0.29
Nodes (9): Connection, _connect(), explain(), get_category_catalog(), introspect_schema(), run_query(), run_readonly(), sample_values() (+1 more)

### Community 6 - "SQL Validator Internals"
Cohesion: 0.44
Nodes (8): Expression, _collect_ctes(), _function_name(), _has_limit(), _projection_is_aggregate_or_literal(), _returns_single_aggregate_row(), validate_sql(), Select

### Community 7 - "Retrieval Semantic Context"
Cohesion: 0.36
Nodes (6): retrieve_context(), _tokens(), allowed_schema(), Column, semantic_context_text(), Table

### Community 8 - "LLM Call Separation"
Cohesion: 0.53
Nodes (6): Separate SQL Generation and Answer Composition Calls, compose_answer Node, execute_query Node, generate_sql Node, LangGraph StateGraph Pipeline, validate_sql Node

### Community 9 - "OpenRouter Client"
Cohesion: 0.83
Nodes (3): OpenAI, chat(), _get_client()

## Knowledge Gaps
- **12 isolated node(s):** `Column`, `Table`, `furniture-nlq`, `Repository Guidelines`, `Terminal Natural-Language Query Tool` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_turn()` connect `REPL Template Tests` to `Graph Routing Flow`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `validate_sql()` connect `SQL Validator Internals` to `Pipeline Node Logic`, `SQL Guard Tests`, `Graph Routing Flow`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `build_graph()` connect `Graph Routing Flow` to `Pipeline Node Logic`, `REPL Template Tests`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `build_graph()` (e.g. with `_route_after_execute()` and `_route_after_explain()`) actually correct?**
  _`build_graph()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Column`, `Table`, `furniture-nlq` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._
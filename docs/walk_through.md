# Chatbot Code Walkthrough

This document traces what happens when a user asks a question in the terminal chatbot, from the prompt typed at `you>` to the final `bot>` response.

## High-Level Shape

The application is a terminal natural-language query assistant for a SQLite furniture inventory database.

The main runtime path is:

1. `chat.py::main()`
2. `pipeline.graph::run_turn(question, conversation)`
3. LangGraph nodes in `pipeline.nodes`
4. SQL validation in `pipeline.sql_guard`
5. Read-only SQLite access in `pipeline.db`
6. Answer formatting in `pipeline.nodes`
7. Back to `chat.py::main()` for terminal output

The important design point is that SQL generation and answer composition are separate operations. The system first decides what SQL to run, validates that SQL, executes it read-only, and only then formats an answer from the returned rows.

## Startup

When you run:

```bash
uv run python chat.py
```

Python executes `chat.py`.

### `chat.py::main()`

`main()` performs these startup steps:

1. `load_dotenv()` runs at import time, loading environment variables from `.env`.
2. `main()` checks `os.environ.get("OPENROUTER_API_KEY")`.
3. If the key is missing, it prints an error and exits with `sys.exit(1)`.
4. If the key exists, it imports `run_turn` from `pipeline.graph`.
5. It prints the startup banner.
6. It initializes `conversation = []`.
7. It enters an infinite REPL loop.

The `run_turn` import is intentionally inside `main()` after the API key check. Importing `pipeline.graph` eventually imports `pipeline.nodes`, which initializes catalog/sample data from the database.

## User Prompt Entry

Inside the REPL loop:

```python
question = console.input("[bold green]you>[/bold green] ")
```

Then:

1. Empty input is ignored with `continue`.
2. `exit` or `quit` breaks the loop.
3. Any other question is handled inside a Rich status spinner:

```python
result = run_turn(question, conversation)
```

If `run_turn()` raises, `chat.py` catches the exception, prints a generic error, and does not update conversation history for that failed turn.

## Graph Construction

### `pipeline.graph::run_turn(question, conversation)`

`run_turn()` owns the per-turn LangGraph execution.

On the first call:

1. It sees `_compiled_graph is None`.
2. It calls `build_graph()`.
3. It stores the compiled graph in the module global `_compiled_graph`.

On later turns, the already compiled graph is reused.

### `pipeline.graph::build_graph()`

`build_graph()` creates a `StateGraph(State)` where `State` is a `TypedDict` with fields such as:

- `question`
- `normalized_question`
- `conversation`
- `intent`
- `context`
- `sql`
- `sql_source`
- `last_error`
- `failure_type`
- `attempts`
- `rows`
- `answer`
- `clarify`
- `explain`
- `memory_hit`
- `trace`

It registers these node functions:

1. `normalize_question`
2. `classify_intent_node`
3. `retrieve_context_node`
4. `generate_or_template_sql`
5. `validate_sql_node`
6. `dry_run_explain`
7. `execute_query`
8. `format_answer`
9. `record_trace`

The graph entry point is `normalize_question`.

The normal edge order is:

```text
normalize_question
-> classify_intent
-> retrieve_context
-> generate_or_template_sql
-> validate_sql
-> dry_run_explain
-> execute
-> format_answer
-> record_trace
-> END
```

There are conditional edges after SQL generation, validation, explain, and execute. These route to retry, answer formatting, clarification, or the end.

## Initial State

Back in `run_turn()`, before graph invocation, it builds this initial state:

```python
initial_state = {
    "question": question,
    "normalized_question": None,
    "conversation": conversation,
    "intent": None,
    "context": None,
    "sql": None,
    "sql_source": None,
    "last_error": None,
    "failure_type": None,
    "attempts": 0,
    "rows": None,
    "answer": None,
    "clarify": None,
    "explain": None,
    "memory_hit": None,
    "trace": [],
}
```

Then it calls:

```python
result = _compiled_graph.invoke(initial_state)
```

From this point, LangGraph calls the node functions.

## Node 1: Normalize Question

### `pipeline.nodes::normalize_question(state)`

This node calls:

```python
_resolve_followup_question(state["question"], state.get("conversation", []))
```

It stores the return value in:

```python
state["normalized_question"]
```

It also appends a trace item:

```python
{"node": "normalize_question"}
```

### `pipeline.nodes::_resolve_followup_question(question, conversation)`

This helper resolves simple follow-up questions like "what about those?" by borrowing the most recent category or subtype from prior conversation.

It calls:

```python
normalize_question_text(question)
```

### `pipeline.retrieval::normalize_question_text(question)`

This function:

1. Strips whitespace.
2. Lowercases the text.
3. Collapses repeated whitespace.
4. Replaces business synonyms from `pipeline.semantic_layer.BUSINESS_SYNONYMS`.

Examples:

- `sofa` becomes `couch`
- `bookcase` becomes `bookshelf`
- `bedframe` becomes `bed frame`

Back in `_resolve_followup_question()`:

1. It calls `find_catalog_match(normalized, _SAMPLES["categories"], _SAMPLES["subtypes"])`.
2. If the current question already names a known category or subtype, it returns the normalized question unchanged.
3. If the question does not contain pronouns such as `it`, `they`, `that`, or `those`, it returns the normalized question unchanged.
4. Otherwise, it scans the recent `conversation` backward.
5. For each previous message, it normalizes the content and calls `find_catalog_match(...)`.
6. If it finds a prior category or subtype, it appends that matched value to the current normalized question.

So a follow-up like:

```text
Where are they?
```

can become something like:

```text
where are they office chair
```

if `office chair` was the last catalog item mentioned.

## Node 2: Classify Intent

### `pipeline.nodes::classify_intent_node(state)`

This node first checks the in-memory query cache:

```python
memory_hit = lookup(state["normalized_question"])
```

### `pipeline.query_memory::lookup(question)`

`lookup()`:

1. Normalizes the question again with `normalize_question_text(question)`.
2. Iterates over the process-local `_MEMORY` list.
3. Skips entries whose `schema_version` is not `SCHEMA_VERSION`.
4. Uses `difflib.SequenceMatcher` to compare the new normalized question to cached questions.
5. Returns the best entry if the similarity score is at least `0.92`.
6. Returns `None` if there is no close match.

Back in `classify_intent_node()`:

If there is a memory hit:

```python
state["memory_hit"] = memory_hit
state["intent"] = memory_hit.get("intent") or {"kind": "cache"}
```

If there is no memory hit, it calls:

```python
classify_intent(
    state["normalized_question"],
    _SAMPLES["categories"],
    _SAMPLES["subtypes"],
)
```

### `pipeline.templates::classify_intent(question, categories, subtypes)`

This is a rule-based classifier for common inventory questions.

It normalizes the question and checks for these broad cases:

1. Confirmation phrases such as `are you sure` return a fallback answer.
2. Thanks return a fallback answer.
3. Vague overview requests like `tell me about furniture` return `{"kind": "ambiguous"}`.
4. Price/cost questions return template intents such as `subtype_price` or `category_price_breakdown`.
5. Value/worth questions return `total_inventory_value` or `category_inventory_value`.
6. Location questions return `subtype_location`, `category_location_breakdown`, or `location_breakdown`.
7. Category listing questions return `category_list`.
8. Quantity/count/stock questions return `subtype_quantity`, `category_quantity_breakdown`, or `total_quantity`.
9. Anything else returns a fallback answer explaining the assistant's supported domain.

To identify categories and subtypes, it calls:

```python
find_catalog_match(normalized, categories, subtypes)
```

### `pipeline.templates::find_catalog_match(question, categories, subtypes)`

This function checks known subtypes first, then known categories, using word-boundary regex matching. It sorts by length descending so longer catalog terms win before shorter terms.

It returns:

```python
("subtype", subtype)
```

or:

```python
("category", category)
```

or `None`.

Back in `classify_intent_node()`, the node appends a trace entry:

```python
{"node": "classify_intent", "intent": state["intent"]}
```

## Node 3: Retrieve Context

### `pipeline.nodes::retrieve_context_node(state)`

This node calls:

```python
retrieve_context(state["normalized_question"], _CATALOG, _SAMPLES)
```

and stores the result in:

```python
state["context"]
```

Then it appends:

```python
{"node": "retrieve_context"}
```

### `pipeline.retrieval::retrieve_context(question, catalog, samples)`

This function builds the schema/business context used by the SQL-generation LLM path.

It starts with:

```python
semantic_context_text()
```

### `pipeline.semantic_layer::semantic_context_text()`

This function describes:

- approved tables
- table synonyms
- columns
- column synonyms
- approved join paths
- approved query templates

The semantic layer defines two tables:

- `furniture_category`
- `furniture_item`

It also defines the approved join:

```text
furniture_item.category_id = furniture_category.id
```

Back in `retrieve_context()`, the function:

1. Tokenizes the normalized question.
2. Adds relevant table and column descriptions if their names, synonyms, or descriptions match question tokens.
3. Adds known categories when the question references category terms.
4. Adds known locations when the question references location terms.
5. Always appends the full category-to-subtype catalog.
6. Always appends approved join paths.

This context is only needed if the graph later reaches the LLM SQL generation branch. Template and cache paths can avoid LLM SQL generation, but the graph still retrieves context before that decision.

## Node 4: Generate or Template SQL

### `pipeline.nodes::generate_or_template_sql(state)`

This is the main routing node. It decides whether the turn needs clarification, a fallback answer, a cached SQL query, a deterministic template SQL query, or a new LLM-generated SQL query.

It starts with:

```python
intent = state.get("intent") or {"kind": "llm"}
```

### Branch A: Ambiguous Intent

If:

```python
intent.get("kind") == "ambiguous"
```

the node sets:

```python
state["clarify"] = "What would you like to know: quantity, inventory value, or location?"
state["sql"] = None
state["sql_source"] = "clarify"
```

Then it returns.

The graph calls `_route_after_generate(state)`, sees `state["clarify"]`, and routes directly to `END`.

### Branch B: Fallback Intent

If:

```python
intent.get("kind") == "fallback"
```

the node attempts to answer from conversation history before using the generic fallback.

It calls:

```python
_answer_from_history_or_none(state)
```

#### `pipeline.nodes::_answer_from_history_or_none(state)`

This helper:

1. Reads the last eight conversation messages.
2. Appends the current user question.
3. Calls:

```python
chat(HISTORY_FALLBACK_PROMPT, messages)
```

#### `pipeline.llm::chat(system, messages)`

`chat()`:

1. Calls `_get_client()`.
2. Prepends the system message to the message list.
3. Calls OpenRouter through the OpenAI-compatible SDK:

```python
client.chat.completions.create(model=MODEL, messages=full_messages)
```

4. Returns:

```python
response.choices[0].message.content
```

#### `pipeline.llm::_get_client()`

`_get_client()` lazily creates a global OpenAI client:

```python
OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
```

The configured model is:

```python
nvidia/nemotron-3-ultra-550b-a55b:free
```

Back in `_answer_from_history_or_none()`:

1. It parses the LLM output with `_parse_json_response(raw)`.
2. If the JSON is `{"action": "answer", "answer": "..."}`, it returns that answer.
3. Otherwise it falls back to `_answer_total_cost_from_history(...)`.

#### `pipeline.nodes::_answer_total_cost_from_history(question, conversation)`

This is a deterministic fallback for questions like "what is the total cost?" after a prior answer included a quantity and unit price.

It:

1. Normalizes the question.
2. Requires words like `total` and `cost`/`price`/`value`/`amount`.
3. Searches recent assistant messages for a quantity phrase.
4. Searches recent assistant messages for a matching unit price phrase.
5. Calls `_format_history_total_cost(quantity, unit_price)`.

#### `pipeline.nodes::_format_history_total_cost(quantity, unit_price)`

This returns a sentence such as:

```text
The total cost is 4 * $250.00 = $1,000.00.
```

Back in the fallback branch of `generate_or_template_sql()`:

```python
state["answer"] = history_answer or fallback_answer
state["sql"] = None
state["sql_source"] = "history_fallback" if history_answer else "fallback"
```

The graph routes to `END` because `_route_after_generate()` sees `state["answer"]`.

### Branch C: Memory Hit

If `classify_intent_node()` found a cached query:

```python
if state.get("memory_hit"):
```

then:

```python
state["sql"] = state["memory_hit"]["sql"]
state["sql_source"] = "cache"
state["attempts"] += 1
```

The graph continues to SQL validation. Cached SQL is still validated and executed again.

### Branch D: Template Intent

If:

```python
intent.get("kind") == "template"
```

the node calls:

```python
sql_for_intent(intent)
```

### `pipeline.templates::sql_for_intent(intent)`

This maps rule-based intents to fixed SQL strings.

Examples:

- `total_quantity` -> `SELECT SUM(quantity) AS quantity FROM furniture_item`
- `subtype_price` -> a `SELECT subtype, unit_price ... LIMIT 100`
- `category_inventory_value` -> a join with `ROUND(SUM(quantity * unit_price), 2)`
- `category_list` -> `SELECT name AS category FROM furniture_category ORDER BY name LIMIT 100`

Template SQL strings quote user-facing catalog values through `_quote(value)`, which doubles single quotes for SQLite string literals.

Back in `generate_or_template_sql()`:

```python
state["sql"] = sql_for_intent(intent)
state["sql_source"] = "template"
state["attempts"] += 1
```

The graph continues to SQL validation.

### Branch E: LLM SQL Generation

If none of the earlier branches applies, the node asks the LLM to produce SQL.

It builds messages from prior conversation:

```python
messages = list(state.get("conversation", []))
```

If this is a retry after an earlier SQL failure, it appends the error to the user question:

```python
Your previous SQL failed with <failure_type>: <last_error>. Produce a corrected SELECT only.
```

Then it appends the current user message and calls:

```python
raw = chat(sql_generation_prompt(state["context"]), messages)
```

#### `pipeline.prompts::sql_generation_prompt(context)`

This formats `SQL_GENERATION_PROMPT_TEMPLATE` with the retrieved schema/business context.

The SQL prompt tells the model to output exactly one JSON object:

```json
{"action": "query", "sql": "<a single SELECT statement>"}
```

or:

```json
{"action": "clarify", "question": "<one short clarifying question>"}
```

or:

```json
{"action": "not_found", "item": "<the item/category the user asked about>"}
```

The prompt also instructs the model to:

- generate only SQLite `SELECT`
- avoid schema probing
- use only retrieved tables, columns, joins, values, and business terms
- never use `SELECT *`
- add `LIMIT 100` to row-returning queries
- use only approved functions

Back in `generate_or_template_sql()`, after the LLM call:

1. It increments `state["attempts"]`.
2. It sets `state["sql_source"] = "llm"`.
3. It parses the raw output with `_parse_json_response(raw)`.

#### `pipeline.nodes::_parse_json_response(raw)`

This helper:

1. Strips whitespace.
2. Removes a surrounding Markdown code fence if present.
3. Calls `json.loads(text)`.
4. Requires the parsed value to be a dict.
5. Returns the dict or `None`.

If parsing fails, `generate_or_template_sql()` calls:

```python
_failure(state, f"response was not valid JSON: {raw[:200]}", "parse_failure")
```

#### `pipeline.nodes::_failure(state, reason, failure_type)`

This sets:

```python
state["last_error"] = reason
state["failure_type"] = failure_type
state["sql"] = None
```

If parsing succeeds:

- `action == "clarify"` sets `state["clarify"]`.
- `action == "query"` sets `state["sql"]`.
- `action == "not_found"` sets a direct `state["answer"]` listing current inventory categories.
- Any other action becomes a parse failure.

For `query`, the node also prints generated SQL to stderr through Rich:

```python
_console.print(f"[dim]\\[debug] generated SQL: {state['sql']}[/dim]")
```

## Route After SQL Generation

### `pipeline.graph::_route_after_generate(state)`

This function returns:

```python
"end"
```

if either `state["clarify"]` or `state["answer"]` is set.

Otherwise it returns:

```python
"validate"
```

So only states with SQL continue to `validate_sql_node`.

## Node 5: Validate SQL

### `pipeline.nodes::validate_sql_node(state)`

This node first checks whether SQL exists.

If no SQL exists, it sets:

```python
state["last_error"] = "no SQL was produced"
state["failure_type"] = "parse_failure"
```

If SQL exists, it calls:

```python
is_valid, reason = validate_sql(sql, ALLOWED)
```

### `pipeline.sql_guard::validate_sql(sql, allowed)`

This is the first layer of the two-layer SQL safety model.

It enforces:

1. No SQL comments.
2. No `sqlite_master`, `sqlite_schema`, `pragma`, or `attach`.
3. SQL must parse with `sqlglot.parse(sql, read="sqlite")`.
4. There must be exactly one statement.
5. The statement must be a `SELECT`.
6. Disallowed expression types such as `ALTER`, `CREATE`, `DELETE`, `DROP`, `INSERT`, `UPDATE`, and `PRAGMA` are rejected.
7. CTEs must be non-recursive and contain only `SELECT`.
8. `SELECT *` is rejected.
9. Tables must be in `ALLOWED`.
10. Columns must exist in the allowed schema.
11. Functions must be in `APPROVED_FUNCTIONS` and not in `DENYLIST_FUNCTIONS`.
12. Row-returning queries must include `LIMIT`.
13. Single aggregate-row queries may omit `LIMIT`.

Important helpers inside `validate_sql()`:

- `_collect_ctes(stmt)` validates CTEs and returns CTE names.
- `_function_name(func)` normalizes function names.
- `_returns_single_aggregate_row(stmt)` detects aggregate-only projections without `GROUP BY`.
- `_has_limit(stmt)` checks for a `LIMIT` clause.

`ALLOWED` comes from:

```python
pipeline.semantic_layer::allowed_schema()
```

which returns allowed table names and column names based on the semantic layer's `TABLES`.

Back in `validate_sql_node()`:

If valid:

```python
state["last_error"] = None
state["failure_type"] = None
```

If invalid:

```python
state["last_error"] = reason
state["failure_type"] = "policy_failure"
state["sql"] = None
```

Then it appends:

```python
{"node": "validate_sql", "valid": is_valid}
```

## Route After Validation

### `pipeline.graph::_route_after_validate(state)`

If there is no `last_error`, validation succeeded and the graph routes to:

```text
dry_run_explain
```

If validation failed, the graph calls:

```python
_can_retry(state)
```

### `pipeline.graph::_can_retry(state)`

This returns true only when:

```python
state.get("sql_source") == "llm"
and state.get("attempts", 0) < MAX_ATTEMPTS
```

`MAX_ATTEMPTS` is `2`.

So only LLM-generated SQL can retry. Template and cache SQL do not retry through generation.

If retry is allowed, the graph routes back to:

```text
generate_or_template_sql
```

On retry, `generate_or_template_sql()` includes the previous error in the prompt and asks the model for corrected SQL.

If retry is not allowed, the graph routes to:

```text
format_answer
```

## Node 6: Dry-Run Explain

### `pipeline.nodes::dry_run_explain(state)`

This node checks whether SQLite can prepare a query plan before actually executing the query.

It calls:

```python
explain(state["sql"])
```

### `pipeline.db::explain(sql)`

`explain()`:

1. Opens a database connection with `_connect()`.
2. Executes:

```python
EXPLAIN QUERY PLAN <sql>
```

3. Converts all returned rows to dictionaries.
4. Closes the connection in `finally`.

### `pipeline.db::_connect()`

This is the second layer of the two-layer SQL safety model.

It opens SQLite in read-only mode:

```python
sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
```

It also sets:

```python
conn.row_factory = sqlite3.Row
```

so rows can be converted cleanly to dictionaries.

Back in `dry_run_explain()`:

If explain succeeds:

```python
state["explain"] = explain_result
state["last_error"] = None
state["failure_type"] = None
```

If explain fails:

```python
state["last_error"] = f"database explain error: {e}"
state["failure_type"] = "execution_error"
state["sql"] = None
```

Then it appends:

```python
{"node": "dry_run_explain"}
```

## Route After Explain

### `pipeline.graph::_route_after_explain(state)`

If there is no `last_error`, the graph routes to:

```text
execute
```

If explain failed and `_can_retry(state)` is true, the graph routes back to:

```text
generate_or_template_sql
```

Otherwise it routes to:

```text
format_answer
```

## Node 7: Execute Query

### `pipeline.nodes::execute_query(state)`

This node calls:

```python
rows = run_readonly(state["sql"])
```

### `pipeline.db::run_readonly(sql)`

This is a wrapper:

```python
return run_query(sql)
```

### `pipeline.db::run_query(sql)`

`run_query()`:

1. Opens the database through `_connect()`, which uses `mode=ro`.
2. Installs a SQLite progress handler:

```python
conn.set_progress_handler(lambda: 1, MAX_SQLITE_STEPS)
```

`MAX_SQLITE_STEPS` is `100_000`. Returning `1` from the handler interrupts execution once the step threshold is reached.

3. Executes the SQL:

```python
cur = conn.execute(sql)
```

4. Fetches up to `MAX_ROWS` rows:

```python
rows = cur.fetchmany(MAX_ROWS)
```

`MAX_ROWS` is `500`.

5. Converts rows to dictionaries:

```python
[dict(row) for row in rows]
```

6. Clears the progress handler and closes the connection in `finally`.

Back in `execute_query()`:

If execution succeeds:

```python
state["rows"] = rows
state["last_error"] = None
state["failure_type"] = "empty_result" if rows == [] else None
```

If execution fails:

```python
state["last_error"] = f"database error: {e}"
state["failure_type"] = "execution_error"
state["rows"] = None
state["sql"] = None
```

Then it appends:

```python
{"node": "execute", "rows": len(state.get("rows") or [])}
```

## Route After Execute

### `pipeline.graph::_route_after_execute(state)`

If there is no `last_error`, the graph routes to:

```text
format_answer
```

If the failure type is `empty_result`, it also routes to `format_answer`.

If execution failed and `_can_retry(state)` is true, it routes back to:

```text
generate_or_template_sql
```

Otherwise it routes to:

```text
format_answer
```

## Node 8: Format Answer

### `pipeline.nodes::format_answer(state)`

This node produces the final assistant answer for states that reached answer formatting.

First, if there are no rows and there is a last error:

```python
if rows is None and state.get("last_error"):
```

it returns:

```text
I could not build a valid query for that. Could you rephrase?
```

Next it tries deterministic formatting:

```python
deterministic = _deterministic_answer(state)
```

### `pipeline.nodes::_deterministic_answer(state)`

This helper only handles:

```python
state["sql_source"] in {"template", "cache"}
```

It does not handle LLM SQL. That keeps template/cache answers predictable and avoids a second LLM call for common questions.

It formats known templates directly:

- `total_quantity`
- `category_quantity_breakdown`
- `subtype_quantity`
- `subtype_price`
- `category_price_breakdown`
- `subtype_location`
- `category_location_breakdown`
- `location_breakdown`
- `total_inventory_value`
- `category_inventory_value`
- `category_list`

Money values are formatted through:

```python
_format_money(value)
```

If deterministic formatting returns a string, `format_answer()` sets:

```python
state["answer"] = deterministic
```

and returns.

### LLM Answer Composition Branch

If no deterministic answer is available, `format_answer()` builds a small JSON payload:

```python
payload = json.dumps({"question": question, "rows": rows if rows is not None else []})
```

Then it calls:

```python
answer = chat(ANSWER_COMPOSITION_PROMPT, [{"role": "user", "content": payload}])
```

`ANSWER_COMPOSITION_PROMPT` instructs the model to:

- answer only from the provided rows
- state breakdowns and totals when appropriate
- say no matching items were found for empty rows
- not output SQL
- not mention database mechanics

If the answer LLM call fails, `format_answer()` uses:

```text
I found matching inventory data, but could not format a detailed answer right now.
```

Finally it sets:

```python
state["answer"] = answer
```

## Node 9: Record Trace and Cache Query

### `pipeline.nodes::record_trace(state)`

This node remembers successful SQL turns in process memory.

It only calls `remember()` if all of these are true:

```python
state.get("sql")
state.get("rows") is not None
not state.get("last_error")
```

Then it calls:

```python
remember(
    state["normalized_question"],
    state["sql"],
    state["rows"],
    state.get("sql_source", "unknown"),
    state.get("intent"),
)
```

### `pipeline.query_memory::remember(question, sql, rows, source, intent)`

`remember()`:

1. Normalizes the question.
2. Avoids duplicate entries with the same normalized question and SQL.
3. Appends a dict to `_MEMORY` containing:
   - `question`
   - `sql`
   - `result_shape`
   - `schema_version`
   - `source`
   - `intent`

This cache is in memory only. It disappears when the Python process exits.

Back in `record_trace()`, it appends:

```python
{"node": "record_trace", "source": state.get("sql_source")}
```

Then the graph reaches `END`.

## Returning to `run_turn()`

After:

```python
result = _compiled_graph.invoke(initial_state)
```

`run_turn()` converts the final graph state into a small response object for `chat.py`.

If the graph state has `clarify`:

```python
return {"type": "clarify", "question": result["clarify"]}
```

Otherwise:

```python
return {"type": "answer", "answer": result.get("answer", "")}
```

## Returning to the Terminal

Back in `chat.py::main()`:

If `result["type"] == "clarify"`:

1. It prints:

```python
console.print(f"[bold magenta]bot>[/bold magenta] {result['question']}")
```

2. It appends the user question to `conversation`.
3. It appends the assistant clarifying question to `conversation`.

Otherwise:

1. It prints:

```python
console.print(f"[bold magenta]bot>[/bold magenta] {result['answer']}")
```

2. It appends the user question to `conversation`.
3. It appends the assistant answer to `conversation`.

That updated `conversation` list is passed into the next `run_turn()` call, enabling follow-up resolution and history fallback.

## Normal Successful Template Example

For a question like:

```text
How many office chairs do we have?
```

the likely function-level path is:

1. `chat.py::main()`
2. `pipeline.graph::run_turn(question, conversation)`
3. `_compiled_graph.invoke(initial_state)`
4. `pipeline.nodes::normalize_question(state)`
5. `pipeline.nodes::_resolve_followup_question(question, conversation)`
6. `pipeline.retrieval::normalize_question_text(question)`
7. `pipeline.templates::find_catalog_match(...)`
8. `pipeline.nodes::classify_intent_node(state)`
9. `pipeline.query_memory::lookup(normalized_question)`
10. `pipeline.retrieval::normalize_question_text(question)`
11. `pipeline.templates::classify_intent(normalized_question, categories, subtypes)`
12. `pipeline.templates::find_catalog_match(...)`
13. `pipeline.nodes::retrieve_context_node(state)`
14. `pipeline.retrieval::retrieve_context(normalized_question, catalog, samples)`
15. `pipeline.semantic_layer::semantic_context_text()`
16. `pipeline.nodes::generate_or_template_sql(state)`
17. `pipeline.templates::sql_for_intent(intent)`
18. `pipeline.graph::_route_after_generate(state)`
19. `pipeline.nodes::validate_sql_node(state)`
20. `pipeline.sql_guard::validate_sql(sql, ALLOWED)`
21. `pipeline.sql_guard::_collect_ctes(stmt)`
22. `pipeline.sql_guard::_returns_single_aggregate_row(stmt)`
23. `pipeline.sql_guard::_has_limit(stmt)`
24. `pipeline.graph::_route_after_validate(state)`
25. `pipeline.nodes::dry_run_explain(state)`
26. `pipeline.db::explain(sql)`
27. `pipeline.db::_connect()`
28. `pipeline.graph::_route_after_explain(state)`
29. `pipeline.nodes::execute_query(state)`
30. `pipeline.db::run_readonly(sql)`
31. `pipeline.db::run_query(sql)`
32. `pipeline.db::_connect()`
33. `pipeline.graph::_route_after_execute(state)`
34. `pipeline.nodes::format_answer(state)`
35. `pipeline.nodes::_deterministic_answer(state)`
36. `pipeline.nodes::_format_money(value)` if the template involves money
37. `pipeline.nodes::record_trace(state)`
38. `pipeline.query_memory::remember(...)`
39. `pipeline.retrieval::normalize_question_text(question)`
40. `pipeline.graph::run_turn()` returns `{"type": "answer", "answer": "..."}`
41. `chat.py::main()` prints `bot> ...`
42. `chat.py::main()` appends the user and assistant messages to `conversation`

This path usually uses no LLM calls because the rule-based template system can classify, generate SQL, and format the answer deterministically.

## LLM SQL Example Path

For a question that is not covered by templates but is still answerable from the schema, the path differs at `generate_or_template_sql()`.

The function-level path is:

1. `generate_or_template_sql(state)`
2. `sql_generation_prompt(state["context"])`
3. `chat(system_prompt, messages)`
4. `_get_client()`
5. `client.chat.completions.create(...)`
6. `_parse_json_response(raw)`
7. If `action == "query"`, store `state["sql"]`
8. `validate_sql_node(state)`
9. `validate_sql(sql, ALLOWED)`
10. `dry_run_explain(state)`
11. `explain(sql)`
12. `execute_query(state)`
13. `run_readonly(sql)`
14. `format_answer(state)`
15. `chat(ANSWER_COMPOSITION_PROMPT, [{"role": "user", "content": payload}])`
16. `record_trace(state)`

This path uses two separate LLM calls:

1. One LLM call to generate SQL JSON.
2. One LLM call to compose the natural-language answer from returned rows.

The SQL is validated and executed between those two calls.

## Retry Path

Retries only apply to SQL whose source is `llm`.

If LLM SQL fails validation, dry-run explain, or execution:

1. The failing node sets `state["last_error"]`.
2. It sets `state["failure_type"]`.
3. It clears `state["sql"]`.
4. The route function calls `_can_retry(state)`.
5. `_can_retry(state)` checks `sql_source == "llm"` and `attempts < MAX_ATTEMPTS`.
6. If true, the graph routes back to `generate_or_template_sql`.
7. `generate_or_template_sql()` appends the prior failure details to the user question.
8. The LLM gets one chance to produce corrected SQL.

Because `MAX_ATTEMPTS = 2`, the first LLM SQL attempt plus one correction attempt is the maximum.

If retry is not possible or the retry also fails, the graph routes to `format_answer()`, which produces:

```text
I could not build a valid query for that. Could you rephrase?
```

## Clarification Path

Clarification can happen in two places.

First, rule-based classification can return:

```python
{"kind": "ambiguous", "reason": "missing requested metric"}
```

Then `generate_or_template_sql()` sets:

```text
What would you like to know: quantity, inventory value, or location?
```

Second, the SQL-generation LLM can return:

```json
{"action": "clarify", "question": "..."}
```

In both cases:

1. `state["clarify"]` is set.
2. `_route_after_generate()` routes to `END`.
3. `run_turn()` returns `{"type": "clarify", "question": ...}`.
4. `chat.py` prints the clarification.
5. The clarification is stored in `conversation`.

The next user answer can then use conversation context to resolve the request.

## Fallback Path

For unsupported questions, greetings, thanks, or unrelated input:

1. `classify_intent()` returns `{"kind": "fallback", "answer": "..."}`
2. `generate_or_template_sql()` calls `_answer_from_history_or_none(state)`.
3. `_answer_from_history_or_none()` may call the LLM with `HISTORY_FALLBACK_PROMPT`.
4. If the LLM cannot answer from history, `_answer_total_cost_from_history()` tries deterministic arithmetic.
5. If neither history path works, the rule-based fallback answer is used.
6. `_route_after_generate()` ends the graph immediately because `state["answer"]` is set.

No SQL is generated or executed in this path.

## Safety Model

The code has two safety layers.

Layer 1 is `pipeline.sql_guard::validate_sql()`:

- only one statement
- only `SELECT`
- no comments
- no schema probing
- no write operations
- no `SELECT *`
- only approved tables and columns
- only approved functions
- `LIMIT` required for row-returning queries

Layer 2 is `pipeline.db::_connect()`:

```python
sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
```

Even if unsafe SQL somehow passed the guard, SQLite is opened read-only.

Execution also has practical limits:

- `MAX_ROWS = 500`
- `MAX_SQLITE_STEPS = 100_000`

## Import-Time Data Loading

When `pipeline.nodes` is imported, it initializes:

```python
_CATALOG = get_category_catalog()
_SAMPLES = sample_values()
```

### `pipeline.db::sample_values()`

This reads:

- category names from `furniture_category`
- subtypes from `furniture_item`
- distinct locations from `furniture_item`

These values power template classification and prompt context.

### `pipeline.db::get_category_catalog()`

This joins `furniture_category` and `furniture_item`, groups subtypes by category in Python, and returns text like:

```text
- chair: office chair, dining chair
- table: coffee table, square table
```

This catalog is inserted into retrieved context for the SQL-generation prompt.

## What To Emphasize In An Interview

The core explanation is:

1. The terminal REPL captures the user question and calls `run_turn()`.
2. `run_turn()` invokes a compiled LangGraph state machine.
3. The graph normalizes the question, classifies intent, retrieves schema context, and chooses between clarification, fallback, cache, template SQL, or LLM SQL.
4. Any SQL, including cached and templated SQL, must pass `validate_sql()`.
5. SQLite is opened read-only through `mode=ro`.
6. The query is dry-run with `EXPLAIN QUERY PLAN` before execution.
7. Results are formatted deterministically for template/cache paths or by a separate answer-composition LLM call for LLM SQL paths.
8. Successful queries are remembered in process-local memory for near-duplicate future questions.
9. `run_turn()` returns a small dict to `chat.py`, and `chat.py` prints the final answer or clarification and updates conversation history.

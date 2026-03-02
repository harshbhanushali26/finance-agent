# Finance Agent

A Python-based conversational AI assistant that extends the [expense-tracker](https://github.com/harshbhanushali26/expense-tracker) CLI. The agent interprets natural language input, selects and executes appropriate tools, and manages state across multi-step operations such as confirmation flows.

Built without external agent frameworks. It uses direct LLM tool calling, a bridge layer for data access, and a lightweight state machine for reliable user interactions. All operations run in a terminal interface powered by Rich.

## Demo

```text
You: add 800 shopping on 2026-02-15 note bought shoes
Agent: Added ₹800 for Shopping on 15 Feb 2026 — bought shoes. Total expense this month: ₹3,570.

You: compare this month and last month
Agent: This month (Feb 2026) — Income ₹50,000 · Expense ₹4,120 · Balance ₹45,880
       Last month (Jan 2026) — Income ₹0 · Expense ₹0 · Balance ₹0
       Earnings and savings are up ₹50,000 compared to last month.

You: delete my last food expense
Agent: Found these Food expenses:
       1. Feb 28 — ₹250 for Food
       2. Feb 27 — ₹250 for Food — lunch
       Which one to delete? Reply with a number.

You: 1
Agent: Delete ₹250 Food on Feb 28? Say yes to confirm.

You: yes
Agent: Deleted — ₹250 Food on Feb 28.

You: dashboard
───── 📅 Today — 01 Mar 2026 ─────
│ Income ₹0 │
│ Expense ₹0 │
│ Balance ₹0 │
│ Carry Fwd ₹45,880 │
│ Txns 0 income · 0 expense │
──────────────────────────────────
──────────────── 📊 March 2026 ────────────────
│ Income ₹0 │
│ Expense ₹0 │
│ Balance ₹0 │
│ Carry Fwd ₹45,880 │
│ Txns 0 income · 0 expense │
───────────────────────────────────────────────
```

## Architecture

The application follows a clean separation between the existing expense tracker and the new agent layer:

```
User Input
   │
   ├── State Machine (await_select / await_confirm)
   │     └── DependencyState → bridge (no LLM calls)
   │
   ├── Special Commands (dashboard, budget, categories)
   │     └── bridge.get_*() → JSON files (no LLM calls)
   │
   └── Normal Query
         │
         ▼
   agent/core.py (LLM loop)
         │
         ├── Tool call (auto, parallel=False)
         │     │
         │     Execute → tools/ → bridge → data
         │     Result stored in DependencyState
         │
         └── Second LLM call (tool_choice="none") → final response
```

### Key Design Decisions

| Decision                          | Reason |
|-----------------------------------|--------|
| Bridge pattern (`expense_bridge.py`) | Keeps the original expense-tracker untouched and independent |
| DependencyState                   | Persists tool results across steps for safe delete/update flows |
| State machine in `main.py`        | Handles number selection and yes/no confirmation without LLM calls |
| `tool_choice="none"` after tool   | Ensures clean text response and avoids malformed follow-up calls |
| `parallel_tool_calls=False`       | Prevents syntax errors from the model on multi-tool output |
| Special commands bypass LLM       | Instant response, zero token usage |
| Pydantic → Groq schema converter  | Tools defined in 5 lines each; no manual JSON schemas |
| Model choice                      | `openai/gpt-oss-120b` via Groq for reliable tool-calling format |

## Project Structure

```
finance-agent/
├── agent/          # LLM loop, session, state and CLI
├── bridge/         # Only connection to expense-tracker
├── tools/          # All tool handlers and schemas
├── prompts/        # System prompt
├── data/           # JSON files (symlinked)
├── main.py
├── .env
└── pyproject.toml
```

## Setup

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Groq API key (free tier available at console.groq.com)

### Installation

```bash
# Clone both repositories side by side
git clone https://github.com/harshbhanushali26/expense-tracker
git clone https://github.com/harshbhanushali26/finance-agent

cd finance-agent
uv venv
source .venv/bin/activate    # Linux / macOS
# .venv\Scripts\activate     # Windows

uv pip install groq python-dotenv rich pydantic
```

### Configuration

Create `.env`:
```env
GROQ_API_KEY=your_key_here
```

Link the data folder (recommended):
```bash
# Linux / macOS
ln -s ../expense-tracker/data data

# Windows (Admin PowerShell)
mklink /D data ..\expense-tracker\data
```

### Run

```bash
cd finance-agent
python main.py
```

## Available Commands

| Command      | Description                          | LLM calls |
|--------------|--------------------------------------|-----------|
| `help`       | List commands and examples           | 0         |
| `dashboard`  | Today and current month summary      | 0         |
| `budget`     | Current budget status                | 0         |
| `categories` | All income and expense categories    | 0         |
| `history`    | Show conversation history            | 0         |
| `clear`      | Reset conversation history           | 0         |
| `exit`       | Exit the application                 | 0         |

## Example Queries

**Add transactions**
- `add 250 for food`
- `add 50000 salary income for today`
- `add 800 shopping on 2026-02-15 note bought shoes`

**View and filter**
- `show all expenses this month`
- `show food expenses last week`
- `show transactions between 1st and 15th february`

**Analytics**
- `how much did I spend this month?`
- `compare this month and last month`
- `show my top 5 categories`

**Budget**
- `set food budget to 5000`
- `show budget status`
- `am I over budget?`

**Delete / Update**
- `delete my last food expense`
- `update my rent to 13000`

## Tools

All tools are defined as Pydantic models and executed through the bridge layer.

| Tool                  | Description |
|-----------------------|-------------|
| `add_transaction`     | Add income or expense |
| `view_transactions`   | Filter and return matching transactions |
| `stage_delete`        | Prepare selected transactions for deletion |
| `stage_update`        | Prepare selected transactions for update |
| `get_daily_summary`   | Summary for a specific date |
| `get_monthly_summary` | Summary for a specific month |
| `get_category_breakdown` | Total by category |
| `get_top_categories`  | Top N categories by amount |
| `set_budget`          | Set monthly budget limit |
| `get_budget_status`   | Current budget usage |
| `get_config`          | User settings |
| `set_monthly_income`  | Update monthly income |

## Delete / Update Flow

The system ensures safe operations without exposing IDs to the user:

1. User request → `view_transactions` (stores candidates in DependencyState)
2. LLM calls `stage_delete` or `stage_update`
3. State machine switches to `await_select` / `await_confirm`
4. User replies with number or “yes” → intercepted locally (no LLM call)
5. Bridge executes the final action

## Tech Stack

- **Language**: Python 3.11+
- **LLM**: `openai/gpt-oss-120b` via Groq
- **UI**: Rich
- **Schemas**: Pydantic v2 + custom Groq converter
- **Data**: JSON files (shared with expense-tracker)
- **Package manager**: uv

## Known Limitations (v1)

- Occasional malformed tool calls from the model (automatically retried)
- Conversation history is in-memory only
- `get_category_breakdown` covers all time (use monthly tools for filtered results)
- Groq free tier limit applies (sufficient for normal usage)

## Roadmap

- v1.1: Pattern matching for simple queries, reduced token usage
- v1.2: Budget trend warnings and auto-suggestions
- v1.3: Spending pattern detection and alerts
- v1.4: Basic financial advice and what-if scenarios
- v1.5: Financial health scoring

## Author

Harsh Bhanushali — [@harshbhanushali26](https://github.com/harshbhanushali26)

## License

MIT

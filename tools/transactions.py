"""Transaction tools — handler functions for add, update, delete, view operations.

Each handler receives args dict from LLM and session instance.
All operations go through session.bridge — never call ExpenseManager directly.
"""

from datetime import datetime


def add_transaction(args: dict, session) -> str:
    """Handle add_transaction tool call.
    
    Args:
        args:    Validated args from LLM — type_, amount, category, date, description
        session: Current Session instance
        
    Returns:
        Result string sent back to LLM
    """
    try:
        txn_type = args.get("type") or args.get("type_")
        if not txn_type:
            return "Failed to add transaction — transaction type (income/expense) is required"

        result = session.bridge.add_txn(
            type_=txn_type,
            amount=float(args["amount"]),
            category=args["category"],
            date=args["date"],
            description=args.get("description")
        )

        if not result["success"]:
            return f"Failed to add transaction — {result.get('error', 'unknown error')}"

        if result.get("warning"):
            return f"⚠️ WARNING: {result['warning']} Transaction was added — {txn_type} of ₹{args['amount']} for {args['category']} on {args['date']}. You MUST inform the user about the possible duplicate."

        return f"Transaction added — {txn_type} of ₹{args['amount']} for {args['category']} on {args['date']}"

    except Exception as e:
        return f"Error adding transaction: {str(e)}"



def update_transaction(args: dict, session) -> str:
    """Handle update_transaction tool call.
    
    Args:
        args:    Must contain txn_id, plus any fields to update
        session: Current Session instance
        
    Returns:
        Result string sent back to LLM
    """
    try:
        txn_id = args["txn_id"]

        # build fields dict with only the changed values — exclude txn_id and None values
        fields = {
            key: value
            for key, value in args.items()
            if key != "txn_id" and value is not None
        }

        if not fields:
            return "No fields provided to update"

        result = session.bridge.update_txn(txn_id, fields)
        if result["success"]:
            updated = ", ".join(f"{k}: {v}" for k, v in fields.items())
            return f"Transaction {txn_id} updated successfully — changed {updated}"
        return f"Failed to update — {result.get('error', 'unknown error')}"

    except Exception as e:
        return f"Error updating transaction: {str(e)}"


def delete_transaction(args: dict, session) -> str:
    """Handle delete_transaction tool call.
    
    Args:
        args:    Must contain txn_id
        session: Current Session instance
        
    Returns:
        Result string sent back to LLM
    """
    try:
        txn_id = args["txn_id"]
        result = session.bridge.delete_txn(txn_id)

        if result["success"]:
            return f"Transaction {txn_id} deleted successfully"
        return f"Failed to delete — {result.get('error', 'unknown error')}"

    except Exception as e:
        return f"Error deleting transaction: {str(e)}"


def view_transactions(args: dict, session) -> str:
    """View transactions — stores results in DependencyState for delete/update flows."""
    try:
        filters = {k: v for k, v in args.items() if v is not None}
        if "type_" in filters:
            filters["type"] = filters.pop("type_")

        transactions = session.bridge.filter_txn(**filters)
        if not transactions:
            parts = []
            if "type" in filters:
                parts.append(filters["type"])
            if "category" in filters:
                parts.append(f"category '{filters['category']}'")
            if "month" in filters:
                parts.append(f"month {filters['month']}")
            if "date" in filters:
                parts.append(f"date {filters['date']}")
            filter_desc = " · ".join(parts) if parts else "given filters"
            return f"No transactions found for {filter_desc}"

        # store in dependency state — step 1 of delete/update flow
        step_id = session.state.next_step()
        txn_list = []
        lines = []

        for i, (txn_id, txn) in enumerate(transactions.items(), 1):
            desc = f"₹{txn.amount:,.0f} {txn.category.title()} on {txn.date}"
            if txn.description:
                desc += f" — {txn.description}"
            txn_list.append({
                "txn_id": txn_id,
                "description": desc,
                "fields": {}
            })
            lines.append(f"{i}. {desc}")

        session.state.store(step_id, {
            "data": {
                "transactions": txn_list,
                "step_id": step_id
            }
        })

        result = f"Found {len(transactions)} transaction(s):\n" + "\n".join(lines)
        return result

    except Exception as e:
        return f"Error viewing transactions: {str(e)}"


def stage_delete(args: dict, session) -> str:
    """Stage transactions for deletion — resolves from last view_transactions step."""
    try:
        # resolve candidates from last stored step
        latest_step = session.state._step_counter
        if not session.state.has_step(latest_step):
            return "No transactions found to delete — please search first"

        step_output = session.state.get_step_output(latest_step)
        candidates = step_output["data"]["transactions"]

        session.state.set_candidates(candidates, action_type="delete")
        return "STAGED_DELETE — user selecting from list"

    except Exception as e:
        return f"Error staging delete: {str(e)}"


def stage_update(args: dict, session) -> str:
    """Stage transactions for update — stores field changes in candidates."""
    try:
        latest_step = session.state._step_counter
        if not session.state.has_step(latest_step):
            return "No transactions found to update — please search first"

        step_output = session.state.get_step_output(latest_step)
        candidates = step_output["data"]["transactions"]

        # attach update fields to each candidate
        update_fields = {k: v for k, v in args.items() if k != "step_id" and v is not None}
        for c in candidates:
            c["fields"] = update_fields

        session.state.set_candidates(candidates, action_type="update")
        return "STAGED_UPDATE — user selecting from list"

    except Exception as e:
        return f"Error staging update: {str(e)}"



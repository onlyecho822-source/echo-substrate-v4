"""
ORGAN #6: METABOLISM
Tracks the cost of every action and enforces resource budgets.
Prevents resource exhaustion and self-inflicted DDoS.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from .models import CostLedger, AgentBudget, EventLog


class BudgetExceeded(Exception):
    """Raised when an agent attempts an action that would exceed its budget."""
    pass


class Metabolism:
    """
    The Metabolism organ manages the energy economy of the system.
    Every action has a cost. No budget, no action.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def allocate_budget(
        self,
        agent_id: str,
        total_budget: float,
        window_hours: int = 24
    ) -> None:
        """
        Allocate a budget to an agent for a specific time window.
        
        Args:
            agent_id: Unique identifier for the agent
            total_budget: Total budget tokens allocated
            window_hours: Duration of the budget window in hours
        """
        # Check if budget already exists
        existing = self.db.query(AgentBudget).filter(
            AgentBudget.agent_id == agent_id
        ).first()
        
        if existing:
            # Update existing budget
            existing.total_budget = total_budget
            existing.spent_budget = 0.0
            existing.budget_window_start = datetime.utcnow()
            existing.budget_window_end = datetime.utcnow() + timedelta(hours=window_hours)
        else:
            # Create new budget
            budget = AgentBudget(
                agent_id=agent_id,
                total_budget=total_budget,
                spent_budget=0.0,
                budget_window_start=datetime.utcnow(),
                budget_window_end=datetime.utcnow() + timedelta(hours=window_hours)
            )
            self.db.add(budget)
        
        # Log to event log
        event = EventLog(
            event_type="budget_allocated",
            actor="metabolism",
            payload={
                "agent_id": agent_id,
                "total_budget": total_budget,
                "window_hours": window_hours
            }
        )
        self.db.add(event)
        self.db.commit()
    
    def check_budget(self, agent_id: str, required_cost: float) -> bool:
        """
        Check if an agent has sufficient budget for an action.
        
        Args:
            agent_id: Unique identifier for the agent
            required_cost: Cost of the proposed action
        
        Returns:
            True if the agent has sufficient budget, False otherwise
        """
        budget = self.db.query(AgentBudget).filter(
            AgentBudget.agent_id == agent_id
        ).first()
        
        if not budget:
            return False
        
        # Check if budget window has expired
        if datetime.utcnow() > budget.budget_window_end:
            return False
        
        # Check if sufficient budget remains
        remaining = budget.total_budget - budget.spent_budget
        return remaining >= required_cost
    
    def charge_cost(
        self,
        agent_id: str,
        cost_type: str,
        cost_amount: float,
        action_id: Optional[int] = None
    ) -> None:
        """
        Charge a cost to an agent's budget.
        
        Args:
            agent_id: Unique identifier for the agent
            cost_type: Type of cost (e.g., "compute", "api_call", "reputation")
            cost_amount: Amount to charge
            action_id: Optional reference to the action that incurred this cost
        
        Raises:
            BudgetExceeded: If the agent doesn't have sufficient budget
        """
        # Check budget first
        if not self.check_budget(agent_id, cost_amount):
            raise BudgetExceeded(
                f"Agent {agent_id} has insufficient budget for cost {cost_amount}"
            )
        
        # Record the cost in the ledger
        ledger_entry = CostLedger(
            agent_id=agent_id,
            action_id=action_id,
            cost_type=cost_type,
            cost_amount=cost_amount
        )
        self.db.add(ledger_entry)
        
        # Update the agent's spent budget
        budget = self.db.query(AgentBudget).filter(
            AgentBudget.agent_id == agent_id
        ).first()
        
        if budget:
            budget.spent_budget += cost_amount
        
        # Log to event log
        event = EventLog(
            event_type="cost_charged",
            actor="metabolism",
            payload={
                "agent_id": agent_id,
                "cost_type": cost_type,
                "cost_amount": cost_amount,
                "action_id": action_id
            }
        )
        self.db.add(event)
        self.db.commit()
    
    def get_remaining_budget(self, agent_id: str) -> float:
        """
        Get the remaining budget for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
        
        Returns:
            Remaining budget tokens, or 0.0 if no budget exists or window expired
        """
        budget = self.db.query(AgentBudget).filter(
            AgentBudget.agent_id == agent_id
        ).first()
        
        if not budget:
            return 0.0
        
        # Check if budget window has expired
        if datetime.utcnow() > budget.budget_window_end:
            return 0.0
        
        return budget.total_budget - budget.spent_budget
    
    def get_total_cost(self, agent_id: str, cost_type: Optional[str] = None) -> float:
        """
        Get the total cost incurred by an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            cost_type: Optional filter by cost type
        
        Returns:
            Total cost incurred
        """
        query = self.db.query(CostLedger).filter(CostLedger.agent_id == agent_id)
        
        if cost_type:
            query = query.filter(CostLedger.cost_type == cost_type)
        
        total = sum(entry.cost_amount for entry in query.all())
        return total

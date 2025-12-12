"""
Base Agent Class
All agents in the Apex system inherit from this class, which enforces the universal constraints.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from ..organs.metabolism import Metabolism, BudgetExceeded
from ..organs.immune_system import ImmuneSystem
from ..organs.models import EventLog, ActuatorAction


class AgentConstraintViolation(Exception):
    """Raised when an agent violates a universal constraint."""
    pass


class BaseAgent(ABC):
    """
    Base class for all agents in the Apex system.
    
    Universal Constraints (enforced by this class):
    1. No Action Without Budget
    2. No Action Without Provenance
    3. No Escalation Without Arbitration
    4. Subject to Immune System
    """
    
    def __init__(self, agent_id: str, db: Session):
        self.agent_id = agent_id
        self.db = db
        self.metabolism = Metabolism(db)
        self.immune = ImmuneSystem(db)
        
        # Check if quarantined on initialization
        if self.immune.is_quarantined(self.agent_id):
            raise AgentConstraintViolation(
                f"Agent {self.agent_id} is quarantined and cannot be initialized"
            )
    
    def execute_action(
        self,
        action_type: str,
        action_payload: Dict[str, Any],
        cost: float
    ) -> Dict[str, Any]:
        """
        Execute an action with full constraint enforcement.
        
        This is the ONLY way an agent can perform an action.
        It enforces all four universal constraints.
        
        Args:
            action_type: Type of action (e.g., "api_call", "shell_command")
            action_payload: Payload for the action
            cost: Metabolic cost of the action
        
        Returns:
            Result of the action
        
        Raises:
            AgentConstraintViolation: If any constraint is violated
            BudgetExceeded: If the agent has insufficient budget
        """
        # CONSTRAINT #4: Subject to Immune System
        if self.immune.is_quarantined(self.agent_id):
            raise AgentConstraintViolation(
                f"Agent {self.agent_id} is quarantined and cannot perform actions"
            )
        
        # CONSTRAINT #1: No Action Without Budget
        if not self.metabolism.check_budget(self.agent_id, cost):
            # Trigger immune response for budget violation
            self.immune.quarantine_agent(
                self.agent_id,
                f"Attempted action without sufficient budget (required: {cost})"
            )
            raise BudgetExceeded(
                f"Agent {self.agent_id} has insufficient budget for action (cost: {cost})"
            )
        
        # CONSTRAINT #2: No Action Without Provenance (Part 1: Pre-action logging)
        event = EventLog(
            event_type="agent_action_initiated",
            actor=self.agent_id,
            payload={
                "action_type": action_type,
                "action_payload": action_payload,
                "cost": cost
            }
        )
        self.db.add(event)
        self.db.commit()
        
        # Create action record
        action = ActuatorAction(
            agent_id=self.agent_id,
            action_type=action_type,
            action_payload=action_payload,
            cost=cost,
            status="pending"
        )
        self.db.add(action)
        self.db.commit()
        
        # Charge the cost BEFORE executing (fail-safe)
        try:
            self.metabolism.charge_cost(
                agent_id=self.agent_id,
                cost_type=action_type,
                cost_amount=cost,
                action_id=action.id
            )
        except BudgetExceeded as e:
            action.status = "failed"
            action.result = {"error": str(e)}
            self.db.commit()
            raise
        
        # Execute the actual action
        try:
            result = self._perform_action(action_type, action_payload)
            action.status = "success"
            action.result = result
        except Exception as e:
            action.status = "failed"
            action.result = {"error": str(e)}
            
            # Trigger immune response for action failure
            self.immune.quarantine_agent(
                self.agent_id,
                f"Action failed with error: {str(e)}"
            )
            raise
        finally:
            # CONSTRAINT #2: No Action Without Provenance (Part 2: Post-action logging)
            completion_event = EventLog(
                event_type="agent_action_completed",
                actor=self.agent_id,
                payload={
                    "action_id": action.id,
                    "status": action.status,
                    "result": action.result
                },
                previous_event_id=event.id
            )
            self.db.add(completion_event)
            self.db.commit()
        
        return result
    
    @abstractmethod
    def _perform_action(self, action_type: str, action_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform the actual action.
        This method must be implemented by subclasses.
        
        Args:
            action_type: Type of action
            action_payload: Payload for the action
        
        Returns:
            Result of the action
        """
        pass
    
    def request_escalation(self, to_state: str, trigger: str) -> bool:
        """
        Request a system state escalation.
        
        CONSTRAINT #3: No Escalation Without Arbitration
        
        Agents cannot directly change the system state.
        They can only REQUEST an escalation, which must be approved by the Arbiter.
        
        Args:
            to_state: Desired system state
            trigger: Reason for the escalation request
        
        Returns:
            False (always). Agents cannot escalate directly.
        """
        # Log the escalation request
        event = EventLog(
            event_type="escalation_request",
            actor=self.agent_id,
            payload={
                "to_state": to_state,
                "trigger": trigger
            }
        )
        self.db.add(event)
        self.db.commit()
        
        # In a real implementation, this would notify the Arbiter
        # For now, we just log it and return False
        return False
    
    def get_remaining_budget(self) -> float:
        """Get the agent's remaining budget."""
        return self.metabolism.get_remaining_budget(self.agent_id)
    
    def is_quarantined(self) -> bool:
        """Check if the agent is quarantined."""
        return self.immune.is_quarantined(self.agent_id)

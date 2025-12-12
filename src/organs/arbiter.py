"""
ORGAN #3: THE ARBITER
The central decision-making engine. Manages system state transitions and conflict resolution.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from .models import SystemState, SystemStateLog, ConflictResolution, EventLog


class StateTransitionDenied(Exception):
    """Raised when a state transition is not permitted."""
    pass


class Arbiter:
    """
    The Arbiter is the brain of the Apex system.
    It manages the state machine and resolves conflicts between agents/signals.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._current_state = self._load_current_state()
    
    def _load_current_state(self) -> SystemState:
        """Load the current system state from the database."""
        latest = self.db.query(SystemStateLog).order_by(
            SystemStateLog.timestamp.desc()
        ).first()
        
        if latest:
            return SystemState(latest.to_state)
        return SystemState.OBSERVE  # Default state
    
    @property
    def current_state(self) -> SystemState:
        """Get the current system state."""
        return self._current_state
    
    def request_transition(
        self,
        to_state: SystemState,
        trigger: str,
        authorized_by: Optional[str] = None
    ) -> bool:
        """
        Request a state transition.
        
        Args:
            to_state: The desired target state
            trigger: Description of what triggered this request
            authorized_by: Human role or agent ID requesting the transition
        
        Returns:
            True if transition was allowed, False otherwise
        
        Raises:
            StateTransitionDenied: If the transition violates the state machine rules
        """
        # Validate the transition
        if not self._is_valid_transition(self._current_state, to_state):
            raise StateTransitionDenied(
                f"Cannot transition from {self._current_state.value} to {to_state.value}"
            )
        
        # Check authorization requirements
        if to_state == SystemState.DEFEND and not self._is_authorized_for_defend(authorized_by):
            raise StateTransitionDenied(
                f"DEFEND mode requires Intent Architect authorization. Got: {authorized_by}"
            )
        
        # Log the transition to the event log (provenance)
        event = EventLog(
            event_type="state_transition",
            actor=authorized_by or "system",
            payload={
                "from": self._current_state.value,
                "to": to_state.value,
                "trigger": trigger
            }
        )
        self.db.add(event)
        
        # Log the transition to the state log
        transition = SystemStateLog(
            from_state=self._current_state.value,
            to_state=to_state.value,
            trigger=trigger,
            authorized_by=authorized_by
        )
        self.db.add(transition)
        self.db.commit()
        
        # Update internal state
        self._current_state = to_state
        
        return True
    
    def _is_valid_transition(self, from_state: SystemState, to_state: SystemState) -> bool:
        """
        Check if a state transition is valid according to the state machine.
        
        Valid transitions:
        - OBSERVE -> ALERT (anomaly detected)
        - ALERT -> ACT (threat confirmed, action authorized)
        - ALERT -> OBSERVE (false positive)
        - ACT -> OBSERVE (action completed)
        - Any state -> DEFEND (exceptional circumstances, requires high authorization)
        - DEFEND -> OBSERVE (de-escalation after defense)
        """
        valid_transitions = {
            SystemState.OBSERVE: [SystemState.ALERT, SystemState.DEFEND],
            SystemState.ALERT: [SystemState.ACT, SystemState.OBSERVE, SystemState.DEFEND],
            SystemState.ACT: [SystemState.OBSERVE, SystemState.DEFEND],
            SystemState.DEFEND: [SystemState.OBSERVE],
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def _is_authorized_for_defend(self, authorized_by: Optional[str]) -> bool:
        """
        Check if the actor is authorized to escalate to DEFEND mode.
        Only the Intent Architect or Arbiter roles can authorize this.
        """
        if not authorized_by:
            return False
        
        # In production, this would check against a role database
        # For now, we check for specific role prefixes
        authorized_roles = ["intent_architect:", "arbiter:"]
        return any(authorized_by.startswith(role) for role in authorized_roles)
    
    def resolve_conflict(
        self,
        conflict_type: str,
        conflicting_agents: List[str],
        resolution: str,
        resolved_by: str
    ) -> int:
        """
        Record a conflict resolution.
        
        Args:
            conflict_type: Type of conflict (e.g., "action_disagreement")
            conflicting_agents: List of agent IDs involved
            resolution: Description of how the conflict was resolved
            resolved_by: Human role who made the decision
        
        Returns:
            The ID of the conflict resolution record
        """
        # Log to event log for provenance
        event = EventLog(
            event_type="conflict_resolution",
            actor=resolved_by,
            payload={
                "conflict_type": conflict_type,
                "agents": conflicting_agents,
                "resolution": resolution
            }
        )
        self.db.add(event)
        
        # Record the resolution
        conflict = ConflictResolution(
            conflict_type=conflict_type,
            conflicting_agents=conflicting_agents,
            resolution=resolution,
            resolved_by=resolved_by
        )
        self.db.add(conflict)
        self.db.commit()
        
        return conflict.id

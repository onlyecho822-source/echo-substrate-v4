"""
ORGAN #5: IMMUNE SYSTEM
Protects against internal threats like runaway processes or corrupted modules.
Provides quarantine, kill switches, and rollback capabilities.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from .models import QuarantinedAgent, RollbackCheckpoint, EventLog, AgentBudget


class ImmuneSystem:
    """
    The Immune System monitors internal behavior and neutralizes threats
    originating from within the Substrate itself.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def quarantine_agent(self, agent_id: str, reason: str) -> None:
        """
        Quarantine a misbehaving agent.
        
        This immediately cuts off the agent's access to:
        - Actuators (cannot perform actions)
        - Memory writes (cannot modify state)
        - Budget (cannot spend resources)
        
        Args:
            agent_id: Unique identifier for the agent
            reason: Explanation of why the agent was quarantined
        """
        # Check if already quarantined
        existing = self.db.query(QuarantinedAgent).filter(
            QuarantinedAgent.agent_id == agent_id,
            QuarantinedAgent.released_at.is_(None)
        ).first()
        
        if existing:
            # Already quarantined, update reason
            existing.reason = f"{existing.reason}; {reason}"
        else:
            # Create new quarantine record
            quarantine = QuarantinedAgent(
                agent_id=agent_id,
                reason=reason
            )
            self.db.add(quarantine)
        
        # Revoke the agent's budget
        budget = self.db.query(AgentBudget).filter(
            AgentBudget.agent_id == agent_id
        ).first()
        
        if budget:
            budget.spent_budget = budget.total_budget  # Zero out remaining budget
        
        # Log to event log
        event = EventLog(
            event_type="agent_quarantined",
            actor="immune_system",
            payload={
                "agent_id": agent_id,
                "reason": reason
            }
        )
        self.db.add(event)
        self.db.commit()
    
    def release_agent(self, agent_id: str, released_by: str) -> None:
        """
        Release an agent from quarantine.
        
        Args:
            agent_id: Unique identifier for the agent
            released_by: Human role authorizing the release
        """
        quarantine = self.db.query(QuarantinedAgent).filter(
            QuarantinedAgent.agent_id == agent_id,
            QuarantinedAgent.released_at.is_(None)
        ).first()
        
        if not quarantine:
            raise ValueError(f"Agent {agent_id} is not currently quarantined")
        
        quarantine.released_at = datetime.utcnow()
        
        # Log to event log
        event = EventLog(
            event_type="agent_released",
            actor=released_by,
            payload={
                "agent_id": agent_id,
                "quarantine_reason": quarantine.reason
            }
        )
        self.db.add(event)
        self.db.commit()
    
    def is_quarantined(self, agent_id: str) -> bool:
        """
        Check if an agent is currently quarantined.
        
        Args:
            agent_id: Unique identifier for the agent
        
        Returns:
            True if the agent is quarantined, False otherwise
        """
        quarantine = self.db.query(QuarantinedAgent).filter(
            QuarantinedAgent.agent_id == agent_id,
            QuarantinedAgent.released_at.is_(None)
        ).first()
        
        return quarantine is not None
    
    def create_checkpoint(self, checkpoint_name: str, state_snapshot: Dict[str, Any]) -> int:
        """
        Create a rollback checkpoint.
        
        Args:
            checkpoint_name: Human-readable name for the checkpoint
            state_snapshot: Full system state to save
        
        Returns:
            The ID of the created checkpoint
        """
        checkpoint = RollbackCheckpoint(
            checkpoint_name=checkpoint_name,
            state_snapshot=state_snapshot
        )
        self.db.add(checkpoint)
        
        # Log to event log
        event = EventLog(
            event_type="checkpoint_created",
            actor="immune_system",
            payload={
                "checkpoint_name": checkpoint_name
            }
        )
        self.db.add(event)
        self.db.commit()
        
        return checkpoint.id
    
    def rollback_to_checkpoint(self, checkpoint_id: int, authorized_by: str) -> Dict[str, Any]:
        """
        Rollback the system to a previous checkpoint.
        
        This is a critical operation that should only be performed
        when the system is in an unrecoverable state.
        
        Args:
            checkpoint_id: ID of the checkpoint to restore
            authorized_by: Human role authorizing the rollback
        
        Returns:
            The state snapshot that was restored
        
        Raises:
            ValueError: If the checkpoint doesn't exist
        """
        checkpoint = self.db.query(RollbackCheckpoint).filter(
            RollbackCheckpoint.id == checkpoint_id
        ).first()
        
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        # Log to event log
        event = EventLog(
            event_type="system_rollback",
            actor=authorized_by,
            payload={
                "checkpoint_id": checkpoint_id,
                "checkpoint_name": checkpoint.checkpoint_name
            }
        )
        self.db.add(event)
        self.db.commit()
        
        return checkpoint.state_snapshot
    
    def apoptosis(self, agent_id: str, reason: str) -> None:
        """
        Terminate an agent (kill switch).
        
        This is the most severe action the Immune System can take.
        It permanently removes an agent from the system.
        
        Args:
            agent_id: Unique identifier for the agent
            reason: Explanation of why the agent was terminated
        """
        # First quarantine the agent
        self.quarantine_agent(agent_id, f"TERMINATED: {reason}")
        
        # Log the termination
        event = EventLog(
            event_type="agent_terminated",
            actor="immune_system",
            payload={
                "agent_id": agent_id,
                "reason": reason
            }
        )
        self.db.add(event)
        self.db.commit()
        
        # In a real implementation, this would also:
        # 1. Kill the agent's process
        # 2. Revoke all credentials
        # 3. Remove from agent registry
        # 4. Archive all agent data

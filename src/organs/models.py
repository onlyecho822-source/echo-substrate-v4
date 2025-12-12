"""
Database models for the 8-organ Echo Substrate architecture.
All state is persisted to PostgreSQL for production resilience.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SystemState(str, Enum):
    """The four operational modes of the Apex system."""
    OBSERVE = "observe"
    ALERT = "alert"
    ACT = "act"
    DEFEND = "defend"


# =============================================================================
# ORGAN #1: SENSORS (Perception & Data Ingestion)
# =============================================================================

class SensorNode(Base):
    """A registered sensor that feeds data into the system."""
    __tablename__ = "sensor_nodes"

    id = Column(Integer, primary_key=True)
    node_id = Column(String(255), unique=True, nullable=False, index=True)
    node_type = Column(String(100), nullable=False)  # e.g., "log_monitor", "api_listener"
    source_uri = Column(String(500), nullable=False)
    status = Column(String(50), default="active")
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to events
    events = relationship("SensorEvent", back_populates="sensor")


class SensorEvent(Base):
    """Raw events captured by sensors."""
    __tablename__ = "sensor_events"

    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensor_nodes.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    processed = Column(Boolean, default=False)
    
    sensor = relationship("SensorNode", back_populates="events")


# =============================================================================
# ORGAN #2: INTERPRETER (Sense-Making & Anomaly Detection)
# =============================================================================

class Anomaly(Base):
    """Detected anomalies flagged by the Interpreter."""
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("sensor_events.id"), nullable=False)
    anomaly_type = Column(String(100), nullable=False)  # e.g., "entropy_spike", "pattern_break"
    severity = Column(Float, nullable=False)  # 0.0 to 1.0
    description = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# =============================================================================
# ORGAN #3: ARBITER (Decision & State Management)
# =============================================================================

class SystemStateLog(Base):
    """Audit log of all system state transitions."""
    __tablename__ = "system_state_log"

    id = Column(Integer, primary_key=True)
    from_state = Column(String(50), nullable=False)
    to_state = Column(String(50), nullable=False)
    trigger = Column(String(255), nullable=False)  # What caused the transition
    authorized_by = Column(String(255), nullable=True)  # Human role or agent ID
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class ConflictResolution(Base):
    """Record of conflicts between agents/signals and their resolution."""
    __tablename__ = "conflict_resolutions"

    id = Column(Integer, primary_key=True)
    conflict_type = Column(String(100), nullable=False)
    conflicting_agents = Column(JSON, nullable=False)  # List of agent IDs
    resolution = Column(Text, nullable=False)
    resolved_by = Column(String(255), nullable=False)  # Arbiter role
    timestamp = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# ORGAN #4: ACTUATORS (Action & Environmental Interaction)
# =============================================================================

class ActuatorAction(Base):
    """Log of all actions executed by actuators."""
    __tablename__ = "actuator_actions"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(255), nullable=False)
    action_type = Column(String(100), nullable=False)  # e.g., "api_call", "shell_command"
    action_payload = Column(JSON, nullable=False)
    cost = Column(Float, nullable=False)  # Metabolic cost
    status = Column(String(50), default="pending")  # pending, success, failed
    result = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# =============================================================================
# ORGAN #5: IMMUNE SYSTEM (Internal Regulation & Safety)
# =============================================================================

class QuarantinedAgent(Base):
    """Agents that have been quarantined by the Immune System."""
    __tablename__ = "quarantined_agents"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(255), nullable=False, unique=True)
    reason = Column(Text, nullable=False)
    quarantined_at = Column(DateTime, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)


class RollbackCheckpoint(Base):
    """Checkpoints for system rollback."""
    __tablename__ = "rollback_checkpoints"

    id = Column(Integer, primary_key=True)
    checkpoint_name = Column(String(255), nullable=False)
    state_snapshot = Column(JSON, nullable=False)  # Full system state
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# =============================================================================
# ORGAN #6: METABOLISM (Resource & Cost Management)
# =============================================================================

class CostLedger(Base):
    """Ledger of all costs incurred by agents."""
    __tablename__ = "cost_ledger"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(255), nullable=False, index=True)
    action_id = Column(Integer, ForeignKey("actuator_actions.id"), nullable=True)
    cost_type = Column(String(100), nullable=False)  # e.g., "compute", "api_call", "reputation"
    cost_amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class AgentBudget(Base):
    """Budget allocations for agents."""
    __tablename__ = "agent_budgets"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(255), nullable=False, unique=True, index=True)
    total_budget = Column(Float, nullable=False)
    spent_budget = Column(Float, default=0.0)
    budget_window_start = Column(DateTime, default=datetime.utcnow)
    budget_window_end = Column(DateTime, nullable=False)


# =============================================================================
# ORGAN #7: MEMORY (State & Provenance)
# =============================================================================

class EventLog(Base):
    """Immutable, append-only event sourcing log. Ground truth for all actions."""
    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(100), nullable=False, index=True)
    actor = Column(String(255), nullable=False)  # Agent ID or human role
    payload = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    # Provenance chain
    previous_event_id = Column(Integer, ForeignKey("event_log.id"), nullable=True)


# =============================================================================
# ORGAN #8: EVOLUTION (Adaptation & Experimentation)
# =============================================================================

class Experiment(Base):
    """A/B tests and controlled mutations."""
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True)
    experiment_name = Column(String(255), nullable=False)
    hypothesis = Column(Text, nullable=False)
    variant_a = Column(JSON, nullable=False)
    variant_b = Column(JSON, nullable=False)
    status = Column(String(50), default="running")  # running, completed, aborted
    fitness_a = Column(Float, nullable=True)
    fitness_b = Column(Float, nullable=True)
    winner = Column(String(10), nullable=True)  # "A", "B", or "tie"
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

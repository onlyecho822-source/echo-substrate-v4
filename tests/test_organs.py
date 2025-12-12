"""
Real Functional Tests for Echo Substrate v4
These tests execute actual code and validate functionality, not keyword counts.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.organs.models import Base, SystemState
from src.organs.arbiter import Arbiter, StateTransitionDenied
from src.organs.metabolism import Metabolism, BudgetExceeded
from src.organs.immune_system import ImmuneSystem
from src.agents.base_agent import BaseAgent, AgentConstraintViolation
from src.agents.example_agents import SensorAgent, TaskAgent, ReflexAgent


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# =============================================================================
# Arbiter Tests
# =============================================================================

def test_arbiter_initial_state(db_session):
    """Test that the Arbiter starts in OBSERVE mode."""
    arbiter = Arbiter(db_session)
    assert arbiter.current_state == SystemState.OBSERVE


def test_arbiter_valid_transition(db_session):
    """Test a valid state transition."""
    arbiter = Arbiter(db_session)
    
    # OBSERVE -> ALERT is valid
    success = arbiter.request_transition(
        to_state=SystemState.ALERT,
        trigger="Anomaly detected",
        authorized_by="operator:test_user"
    )
    
    assert success is True
    assert arbiter.current_state == SystemState.ALERT


def test_arbiter_invalid_transition(db_session):
    """Test that invalid transitions are blocked."""
    arbiter = Arbiter(db_session)
    
    # OBSERVE -> ACT is invalid (must go through ALERT first)
    with pytest.raises(StateTransitionDenied):
        arbiter.request_transition(
            to_state=SystemState.ACT,
            trigger="Direct action attempt",
            authorized_by="operator:test_user"
        )


def test_arbiter_defend_requires_authorization(db_session):
    """Test that DEFEND mode requires high-level authorization."""
    arbiter = Arbiter(db_session)
    
    # Transition to ALERT first
    arbiter.request_transition(
        to_state=SystemState.ALERT,
        trigger="Test",
        authorized_by="operator:test_user"
    )
    
    # ALERT -> DEFEND without proper authorization should fail
    with pytest.raises(StateTransitionDenied):
        arbiter.request_transition(
            to_state=SystemState.DEFEND,
            trigger="Defense needed",
            authorized_by="operator:test_user"  # Operator is not authorized
        )
    
    # ALERT -> DEFEND with proper authorization should succeed
    success = arbiter.request_transition(
        to_state=SystemState.DEFEND,
        trigger="Defense needed",
        authorized_by="intent_architect:admin"  # Intent Architect is authorized
    )
    
    assert success is True
    assert arbiter.current_state == SystemState.DEFEND


# =============================================================================
# Metabolism Tests
# =============================================================================

def test_metabolism_allocate_budget(db_session):
    """Test budget allocation."""
    metabolism = Metabolism(db_session)
    
    metabolism.allocate_budget(
        agent_id="test_agent",
        total_budget=100.0,
        window_hours=24
    )
    
    remaining = metabolism.get_remaining_budget("test_agent")
    assert remaining == 100.0


def test_metabolism_charge_cost(db_session):
    """Test charging a cost."""
    metabolism = Metabolism(db_session)
    
    # Allocate budget
    metabolism.allocate_budget(
        agent_id="test_agent",
        total_budget=100.0,
        window_hours=24
    )
    
    # Charge a cost
    metabolism.charge_cost(
        agent_id="test_agent",
        cost_type="api_call",
        cost_amount=25.0
    )
    
    remaining = metabolism.get_remaining_budget("test_agent")
    assert remaining == 75.0


def test_metabolism_budget_exceeded(db_session):
    """Test that exceeding budget raises an exception."""
    metabolism = Metabolism(db_session)
    
    # Allocate a small budget
    metabolism.allocate_budget(
        agent_id="test_agent",
        total_budget=10.0,
        window_hours=24
    )
    
    # Attempt to charge more than the budget
    with pytest.raises(BudgetExceeded):
        metabolism.charge_cost(
            agent_id="test_agent",
            cost_type="expensive_operation",
            cost_amount=50.0
        )


def test_metabolism_no_budget(db_session):
    """Test that agents without budgets cannot perform actions."""
    metabolism = Metabolism(db_session)
    
    # Check budget for non-existent agent
    remaining = metabolism.get_remaining_budget("nonexistent_agent")
    assert remaining == 0.0
    
    # Attempt to charge cost without budget
    with pytest.raises(BudgetExceeded):
        metabolism.charge_cost(
            agent_id="nonexistent_agent",
            cost_type="api_call",
            cost_amount=1.0
        )


# =============================================================================
# Immune System Tests
# =============================================================================

def test_immune_quarantine_agent(db_session):
    """Test quarantining an agent."""
    immune = ImmuneSystem(db_session)
    
    # Quarantine an agent
    immune.quarantine_agent(
        agent_id="bad_agent",
        reason="Exceeded budget multiple times"
    )
    
    # Check quarantine status
    assert immune.is_quarantined("bad_agent") is True


def test_immune_release_agent(db_session):
    """Test releasing an agent from quarantine."""
    immune = ImmuneSystem(db_session)
    
    # Quarantine and then release
    immune.quarantine_agent(
        agent_id="bad_agent",
        reason="Test quarantine"
    )
    
    immune.release_agent(
        agent_id="bad_agent",
        released_by="arbiter:admin"
    )
    
    # Check that agent is no longer quarantined
    assert immune.is_quarantined("bad_agent") is False


def test_immune_checkpoint_and_rollback(db_session):
    """Test creating a checkpoint and rolling back."""
    immune = ImmuneSystem(db_session)
    
    # Create a checkpoint
    state_snapshot = {"system_state": "OBSERVE", "agents": ["agent1", "agent2"]}
    checkpoint_id = immune.create_checkpoint(
        checkpoint_name="pre_deployment",
        state_snapshot=state_snapshot
    )
    
    # Rollback to the checkpoint
    restored_state = immune.rollback_to_checkpoint(
        checkpoint_id=checkpoint_id,
        authorized_by="intent_architect:admin"
    )
    
    assert restored_state == state_snapshot


# =============================================================================
# Agent Tests
# =============================================================================

def test_agent_cannot_act_without_budget(db_session):
    """Test that agents cannot perform actions without budget."""
    agent = TaskAgent(agent_id="test_task_agent", db=db_session)
    
    # Attempt action without budget
    with pytest.raises(BudgetExceeded):
        agent.execute_action(
            action_type="analyze_data",
            action_payload={"data": [1, 2, 3]},
            cost=10.0
        )


def test_agent_with_budget_can_act(db_session):
    """Test that agents with budget can perform actions."""
    metabolism = Metabolism(db_session)
    agent = TaskAgent(agent_id="test_task_agent", db=db_session)
    
    # Allocate budget
    metabolism.allocate_budget(
        agent_id="test_task_agent",
        total_budget=100.0,
        window_hours=24
    )
    
    # Perform action
    result = agent.execute_action(
        action_type="analyze_data",
        action_payload={"data": [1, 2, 3, 4, 5]},
        cost=10.0
    )
    
    assert result["analysis"] == "mean"
    assert result["result"] == 3.0
    assert result["data_points"] == 5


def test_quarantined_agent_cannot_act(db_session):
    """Test that quarantined agents cannot perform actions."""
    metabolism = Metabolism(db_session)
    immune = ImmuneSystem(db_session)
    agent = TaskAgent(agent_id="test_task_agent", db=db_session)
    
    # Allocate budget
    metabolism.allocate_budget(
        agent_id="test_task_agent",
        total_budget=100.0,
        window_hours=24
    )
    
    # Quarantine the agent
    immune.quarantine_agent(
        agent_id="test_task_agent",
        reason="Test quarantine"
    )
    
    # Attempt action while quarantined
    with pytest.raises(AgentConstraintViolation):
        agent.execute_action(
            action_type="analyze_data",
            action_payload={"data": [1, 2, 3]},
            cost=10.0
        )


def test_agent_cannot_escalate_directly(db_session):
    """Test that agents cannot escalate system state directly."""
    metabolism = Metabolism(db_session)
    agent = TaskAgent(agent_id="test_task_agent", db=db_session)
    
    # Allocate budget
    metabolism.allocate_budget(
        agent_id="test_task_agent",
        total_budget=100.0,
        window_hours=24
    )
    
    # Attempt escalation
    result = agent.request_escalation(
        to_state="DEFEND",
        trigger="Perceived threat"
    )
    
    # Escalation should be logged but not executed
    assert result is False


# =============================================================================
# Integration Tests
# =============================================================================

def test_full_workflow(db_session):
    """Test a complete workflow from sensor to action."""
    # Setup
    metabolism = Metabolism(db_session)
    arbiter = Arbiter(db_session)
    
    # Create agents
    sensor = SensorAgent(agent_id="sensor_1", db=db_session, source_uri="http://example.com/data")
    task_agent = TaskAgent(agent_id="task_1", db=db_session)
    
    # Allocate budgets
    metabolism.allocate_budget(agent_id="sensor_1", total_budget=50.0, window_hours=24)
    metabolism.allocate_budget(agent_id="task_1", total_budget=100.0, window_hours=24)
    
    # Step 1: Sensor reads data
    sensor_result = sensor.execute_action(
        action_type="read_data",
        action_payload={},
        cost=5.0
    )
    
    assert sensor_result["source"] == "http://example.com/data"
    
    # Step 2: Sensor reports anomaly
    anomaly_result = sensor.execute_action(
        action_type="report_anomaly",
        action_payload={
            "event_id": 1,
            "anomaly_type": "entropy_spike",
            "severity": 0.8,
            "description": "Unusual pattern detected"
        },
        cost=2.0
    )
    
    assert anomaly_result["reported"] is True
    
    # Step 3: Arbiter escalates to ALERT
    arbiter.request_transition(
        to_state=SystemState.ALERT,
        trigger="Anomaly detected by sensor_1",
        authorized_by="operator:system"
    )
    
    assert arbiter.current_state == SystemState.ALERT
    
    # Step 4: Arbiter escalates to ACT
    arbiter.request_transition(
        to_state=SystemState.ACT,
        trigger="Action authorized",
        authorized_by="arbiter:admin"
    )
    
    assert arbiter.current_state == SystemState.ACT
    
    # Step 5: Task agent performs analysis
    analysis_result = task_agent.execute_action(
        action_type="analyze_data",
        action_payload={"data": [10, 20, 30, 40, 50]},
        cost=15.0
    )
    
    assert analysis_result["result"] == 30.0
    
    # Step 6: De-escalate to OBSERVE
    arbiter.request_transition(
        to_state=SystemState.OBSERVE,
        trigger="Action completed successfully",
        authorized_by="operator:system"
    )
    
    assert arbiter.current_state == SystemState.OBSERVE
    
    # Verify budgets were charged
    assert metabolism.get_remaining_budget("sensor_1") == 43.0  # 50 - 5 - 2
    assert metabolism.get_remaining_budget("task_1") == 85.0  # 100 - 15

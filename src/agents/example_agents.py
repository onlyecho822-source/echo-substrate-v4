"""
Example Agent Implementations
Demonstrates how to build agents that comply with the Apex constraints.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
import httpx

from .base_agent import BaseAgent


class SensorAgent(BaseAgent):
    """
    A sensor agent that reads data from an external source.
    
    Constraints:
    - Cannot modify data
    - Cannot act on data directly (only reports to Interpreter)
    """
    
    def __init__(self, agent_id: str, db: Session, source_uri: str):
        super().__init__(agent_id, db)
        self.source_uri = source_uri
    
    def _perform_action(self, action_type: str, action_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform sensor actions.
        
        Allowed actions:
        - read_data: Read data from the source
        - report_anomaly: Report an anomaly to the Interpreter
        """
        if action_type == "read_data":
            return self._read_data()
        elif action_type == "report_anomaly":
            return self._report_anomaly(action_payload)
        else:
            raise ValueError(f"Unknown action type for SensorAgent: {action_type}")
    
    def _read_data(self) -> Dict[str, Any]:
        """Read data from the source."""
        try:
            # In a real implementation, this would read from the actual source
            # For now, we simulate it
            return {
                "source": self.source_uri,
                "data": {"status": "ok", "value": 42},
                "timestamp": "2025-12-12T00:00:00Z"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _report_anomaly(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Report an anomaly to the Interpreter."""
        # This would typically create an Anomaly record in the database
        from ..organs.models import Anomaly
        
        anomaly = Anomaly(
            event_id=payload.get("event_id"),
            anomaly_type=payload.get("anomaly_type", "unknown"),
            severity=payload.get("severity", 0.5),
            description=payload.get("description", "")
        )
        self.db.add(anomaly)
        self.db.commit()
        
        return {"anomaly_id": anomaly.id, "reported": True}


class TaskAgent(BaseAgent):
    """
    A task agent that performs bounded, delegated tasks.
    
    Constraints:
    - Cannot define its own tasks
    - Cannot persist outside its sandbox
    - Operates within a strict metabolic budget
    """
    
    def __init__(self, agent_id: str, db: Session):
        super().__init__(agent_id, db)
    
    def _perform_action(self, action_type: str, action_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform task actions.
        
        Allowed actions:
        - analyze_data: Analyze provided data
        - generate_report: Generate a report
        - api_call: Make an external API call
        """
        if action_type == "analyze_data":
            return self._analyze_data(action_payload)
        elif action_type == "generate_report":
            return self._generate_report(action_payload)
        elif action_type == "api_call":
            return self._make_api_call(action_payload)
        else:
            raise ValueError(f"Unknown action type for TaskAgent: {action_type}")
    
    def _analyze_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data."""
        data = payload.get("data", [])
        
        # Simple analysis: compute mean
        if isinstance(data, list) and all(isinstance(x, (int, float)) for x in data):
            mean = sum(data) / len(data) if data else 0
            return {
                "analysis": "mean",
                "result": mean,
                "data_points": len(data)
            }
        else:
            return {"error": "Invalid data format for analysis"}
    
    def _generate_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a report."""
        report_type = payload.get("report_type", "summary")
        data = payload.get("data", {})
        
        report = {
            "report_type": report_type,
            "generated_at": "2025-12-12T00:00:00Z",
            "summary": f"Report on {len(data)} data points",
            "data": data
        }
        
        return report
    
    def _make_api_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make an external API call."""
        url = payload.get("url")
        method = payload.get("method", "GET")
        
        if not url:
            return {"error": "No URL provided"}
        
        try:
            # Use httpx for async-safe HTTP calls
            with httpx.Client() as client:
                if method == "GET":
                    response = client.get(url, timeout=5.0)
                elif method == "POST":
                    response = client.post(url, json=payload.get("body", {}), timeout=5.0)
                else:
                    return {"error": f"Unsupported method: {method}"}
                
                return {
                    "status_code": response.status_code,
                    "body": response.text[:500],  # Limit response size
                    "headers": dict(response.headers)
                }
        except Exception as e:
            return {"error": str(e)}


class ReflexAgent(BaseAgent):
    """
    A reflex agent that executes pre-approved, low-cost actions.
    
    Constraints:
    - Cannot escalate system state
    - Cannot perform complex analysis
    - Actions must be simple and fast
    """
    
    def __init__(self, agent_id: str, db: Session):
        super().__init__(agent_id, db)
    
    def _perform_action(self, action_type: str, action_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform reflex actions.
        
        Allowed actions:
        - block_ip: Block a known-bad IP
        - purge_cache: Purge temporary files
        - send_alert: Send a low-priority alert
        """
        if action_type == "block_ip":
            return self._block_ip(action_payload)
        elif action_type == "purge_cache":
            return self._purge_cache(action_payload)
        elif action_type == "send_alert":
            return self._send_alert(action_payload)
        else:
            raise ValueError(f"Unknown action type for ReflexAgent: {action_type}")
    
    def _block_ip(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Block an IP address."""
        ip = payload.get("ip")
        
        if not ip:
            return {"error": "No IP provided"}
        
        # In a real implementation, this would update firewall rules
        # For now, we simulate it
        return {
            "action": "block_ip",
            "ip": ip,
            "blocked": True
        }
    
    def _purge_cache(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Purge temporary files."""
        cache_type = payload.get("cache_type", "all")
        
        # In a real implementation, this would delete files
        # For now, we simulate it
        return {
            "action": "purge_cache",
            "cache_type": cache_type,
            "purged": True,
            "files_deleted": 42
        }
    
    def _send_alert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a low-priority alert."""
        message = payload.get("message", "Alert")
        
        # In a real implementation, this would send a notification
        # For now, we simulate it
        return {
            "action": "send_alert",
            "message": message,
            "sent": True
        }

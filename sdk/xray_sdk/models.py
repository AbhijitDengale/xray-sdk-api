from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel
from datetime import datetime
import uuid


class StepData(BaseModel):
    """Represents a single step in a pipeline with decision context."""
    step_name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    reasoning: str
    timestamp: datetime
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = {}


class CandidateData(BaseModel):
    """Represents candidate filtering/selection data."""
    step_name: str
    input_count: int
    output_count: int
    filters_applied: List[str]
    sample_rejections: Dict[str, Union[int, str]] = {}
    sample_accepted: List[Dict[str, Any]] = []
    sample_rejected: List[Dict[str, Any]] = []
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class PipelineData(BaseModel):
    """Complete pipeline execution data."""
    pipeline_id: str
    pipeline_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    final_result: Any = None
    steps: List[StepData] = []
    candidates: List[CandidateData] = []
    status: str = "running"  # running, completed, failed
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    def add_step(self, step: StepData):
        """Add a step to the pipeline."""
        self.steps.append(step)
    
    def add_candidates(self, candidates: CandidateData):
        """Add candidate data to the pipeline."""
        self.candidates.append(candidates)
    
    def complete(self, final_result: Any):
        """Mark pipeline as completed."""
        self.final_result = final_result
        self.end_time = datetime.utcnow()
        self.status = "completed"
    
    def fail(self, error_message: str):
        """Mark pipeline as failed."""
        self.error_message = error_message
        self.end_time = datetime.utcnow()
        self.status = "failed"
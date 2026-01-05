from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Union
from datetime import datetime


class StepCreate(BaseModel):
    step_name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    reasoning: str
    timestamp: datetime
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = {}


class StepResponse(StepCreate):
    id: str
    
    class Config:
        from_attributes = True


class CandidateCreate(BaseModel):
    step_name: str
    input_count: int
    output_count: int
    filters_applied: List[str]
    sample_rejections: Dict[str, Union[int, str]] = {}
    sample_accepted: List[Dict[str, Any]] = []
    sample_rejected: List[Dict[str, Any]] = []
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class CandidateResponse(CandidateCreate):
    id: str
    elimination_rate: float
    
    class Config:
        from_attributes = True


class PipelineCreate(BaseModel):
    pipeline_id: str
    pipeline_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    final_result: Any = None
    steps: List[StepCreate] = []
    candidates: List[CandidateCreate] = []
    status: str = "running"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PipelineResponse(BaseModel):
    id: str
    pipeline_id: str
    pipeline_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    final_result: Any = None
    status: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    steps: List[StepResponse] = []
    candidates: List[CandidateResponse] = []
    created_at: datetime
    
    @classmethod
    def from_db_model(cls, db_pipeline):
        """Create response from database model."""
        return cls(
            id=db_pipeline.id,
            pipeline_id=db_pipeline.pipeline_id,
            pipeline_type=db_pipeline.pipeline_type,
            start_time=db_pipeline.start_time,
            end_time=db_pipeline.end_time,
            final_result=db_pipeline.final_result,
            status=db_pipeline.status,
            error_message=db_pipeline.error_message,
            metadata=db_pipeline.pipeline_metadata or {},
            steps=[StepResponse.from_db_model(step) for step in db_pipeline.steps],
            candidates=[CandidateResponse.from_db_model(candidate) for candidate in db_pipeline.candidates],
            created_at=db_pipeline.created_at
        )
    
    class Config:
        from_attributes = True


class StepResponse(StepCreate):
    id: str
    
    @classmethod
    def from_db_model(cls, db_step):
        """Create response from database model."""
        return cls(
            id=db_step.id,
            step_name=db_step.step_name,
            inputs=db_step.inputs,
            outputs=db_step.outputs,
            reasoning=db_step.reasoning,
            timestamp=db_step.timestamp,
            execution_time_ms=db_step.execution_time_ms,
            metadata=db_step.step_metadata or {}
        )
    
    class Config:
        from_attributes = True


class CandidateResponse(CandidateCreate):
    id: str
    elimination_rate: float
    
    @classmethod
    def from_db_model(cls, db_candidate):
        """Create response from database model."""
        elimination_rate = 0.0
        if db_candidate.input_count > 0:
            elimination_rate = ((db_candidate.input_count - db_candidate.output_count) / db_candidate.input_count) * 100
        
        return cls(
            id=db_candidate.id,
            step_name=db_candidate.step_name,
            input_count=db_candidate.input_count,
            output_count=db_candidate.output_count,
            filters_applied=db_candidate.filters_applied,
            sample_rejections=db_candidate.sample_rejections or {},
            sample_accepted=db_candidate.sample_accepted or [],
            sample_rejected=db_candidate.sample_rejected or [],
            timestamp=db_candidate.timestamp,
            metadata=db_candidate.candidate_metadata or {},
            elimination_rate=elimination_rate
        )
    
    class Config:
        from_attributes = True


class PipelineSearchQuery(BaseModel):
    pipeline_type: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    step_name: Optional[str] = None
    min_elimination_rate: Optional[float] = None
    limit: int = 100
    offset: int = 0


class StepAnalysisQuery(BaseModel):
    step_name: Optional[str] = None
    pipeline_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_execution_time: Optional[float] = None
    limit: int = 100


class StepAnalysisResponse(BaseModel):
    step_name: str
    pipeline_type: str
    avg_execution_time_ms: float
    total_executions: int
    success_rate: float
    common_reasoning_patterns: List[str]
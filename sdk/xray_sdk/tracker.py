import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import requests
import json
from .models import StepData, CandidateData, PipelineData


class XRayTracker:
    """
    Main SDK class for tracking multi-step algorithmic decisions.
    
    Provides lightweight instrumentation for capturing decision context,
    candidate filtering, and reasoning at each step of a pipeline.
    """
    
    def __init__(
        self, 
        pipeline_type: str, 
        pipeline_id: Optional[str] = None,
        api_base_url: str = "http://localhost:8000/api/v1",
        auto_send: bool = True,
        batch_size: int = 10
    ):
        """
        Initialize X-Ray tracker for a pipeline.
        
        Args:
            pipeline_type: Type of pipeline (e.g., "competitor_selection")
            pipeline_id: Unique identifier for this pipeline run
            api_base_url: Base URL for X-Ray API
            auto_send: Whether to automatically send data to API
            batch_size: Number of steps to batch before sending
        """
        self.pipeline_id = pipeline_id or str(uuid.uuid4())
        self.pipeline_type = pipeline_type
        self.api_base_url = api_base_url.rstrip('/')
        self.auto_send = auto_send
        self.batch_size = batch_size
        
        self.pipeline_data = PipelineData(
            pipeline_id=self.pipeline_id,
            pipeline_type=pipeline_type,
            start_time=datetime.utcnow()
        )
        
        self._step_count = 0
        self._last_step_time = time.time()
    
    def capture_step(
        self,
        step_name: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        reasoning: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Capture a decision step in the pipeline.
        
        Args:
            step_name: Name/identifier for this step
            inputs: Input data for this step
            outputs: Output data from this step
            reasoning: Explanation of why this decision was made
            metadata: Additional context data
        """
        current_time = time.time()
        execution_time = (current_time - self._last_step_time) * 1000  # Convert to ms
        
        step_data = StepData(
            step_name=step_name,
            inputs=inputs,
            outputs=outputs,
            reasoning=reasoning,
            timestamp=datetime.utcnow(),
            execution_time_ms=execution_time,
            metadata=metadata or {}
        )
        
        self.pipeline_data.add_step(step_data)
        self._step_count += 1
        self._last_step_time = current_time
        
        # Auto-send if batch size reached
        if self.auto_send and self._step_count % self.batch_size == 0:
            self._send_batch_update()
    
    def capture_candidates(
        self,
        step_name: str,
        input_count: int,
        output_count: int,
        filters_applied: List[str],
        sample_rejections: Dict[str, Union[int, str]] = None,
        sample_accepted: List[Dict[str, Any]] = None,
        sample_rejected: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Capture candidate filtering/selection data.
        
        Args:
            step_name: Name of the filtering step
            input_count: Number of candidates before filtering
            output_count: Number of candidates after filtering
            filters_applied: List of filter names applied
            sample_rejections: Summary of rejection reasons with counts
            sample_accepted: Sample of accepted candidates (for large datasets)
            sample_rejected: Sample of rejected candidates (for large datasets)
            metadata: Additional context data
        """
        candidate_data = CandidateData(
            step_name=step_name,
            input_count=input_count,
            output_count=output_count,
            filters_applied=filters_applied,
            sample_rejections=sample_rejections or {},
            sample_accepted=sample_accepted or [],
            sample_rejected=sample_rejected or [],
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.pipeline_data.add_candidates(candidate_data)
        
        # Auto-send if batch size reached
        if self.auto_send and len(self.pipeline_data.candidates) % self.batch_size == 0:
            self._send_batch_update()
    
    def capture_reasoning(
        self,
        step_name: str,
        decision: str,
        reasoning: str,
        confidence: Optional[float] = None,
        alternatives_considered: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Capture detailed reasoning for a decision (especially useful for LLM steps).
        
        Args:
            step_name: Name of the decision step
            decision: The decision that was made
            reasoning: Detailed explanation of why
            confidence: Confidence score (0-1) if available
            alternatives_considered: Other options that were considered
            metadata: Additional context data
        """
        reasoning_data = {
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "alternatives_considered": alternatives_considered or []
        }
        
        self.capture_step(
            step_name=f"{step_name}_reasoning",
            inputs={"alternatives": alternatives_considered or []},
            outputs={"decision": decision, "confidence": confidence},
            reasoning=reasoning,
            metadata={**(metadata or {}), "reasoning_data": reasoning_data}
        )
    
    def end_pipeline(self, final_result: Any = None, error_message: str = None) -> None:
        """
        Complete the pipeline tracking.
        
        Args:
            final_result: The final output of the pipeline
            error_message: Error message if pipeline failed
        """
        if error_message:
            self.pipeline_data.fail(error_message)
        else:
            self.pipeline_data.complete(final_result)
        
        # Send final data to API
        if self.auto_send:
            self.send_to_api()
    
    def send_to_api(self) -> bool:
        """
        Send complete pipeline data to X-Ray API.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.api_base_url}/pipelines",
                json=self.pipeline_data.model_dump(),
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            # Graceful degradation - don't break the main pipeline
            print(f"Warning: Failed to send X-Ray data to API: {e}")
            return False
    
    def _send_batch_update(self) -> None:
        """Send incremental update to API (for long-running pipelines)."""
        try:
            response = requests.put(
                f"{self.api_base_url}/pipelines/{self.pipeline_id}",
                json=self.pipeline_data.model_dump(),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to send X-Ray batch update: {e}")
    
    def get_pipeline_data(self) -> PipelineData:
        """Get the current pipeline data."""
        return self.pipeline_data
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set pipeline-level metadata."""
        self.pipeline_data.metadata[key] = value
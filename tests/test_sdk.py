import pytest
from datetime import datetime
from xray_sdk import XRayTracker, StepData, CandidateData, PipelineData


def test_xray_tracker_initialization():
    """Test basic tracker initialization."""
    tracker = XRayTracker("test_pipeline", auto_send=False)
    
    assert tracker.pipeline_type == "test_pipeline"
    assert tracker.auto_send == False
    assert tracker.pipeline_data.pipeline_type == "test_pipeline"
    assert tracker.pipeline_data.status == "running"


def test_capture_step():
    """Test step capture functionality."""
    tracker = XRayTracker("test_pipeline", auto_send=False)
    
    tracker.capture_step(
        step_name="test_step",
        inputs={"input_key": "input_value"},
        outputs={"output_key": "output_value"},
        reasoning="Test reasoning"
    )
    
    assert len(tracker.pipeline_data.steps) == 1
    step = tracker.pipeline_data.steps[0]
    assert step.step_name == "test_step"
    assert step.inputs["input_key"] == "input_value"
    assert step.outputs["output_key"] == "output_value"
    assert step.reasoning == "Test reasoning"


def test_capture_candidates():
    """Test candidate capture functionality."""
    tracker = XRayTracker("test_pipeline", auto_send=False)
    
    tracker.capture_candidates(
        step_name="filtering_step",
        input_count=1000,
        output_count=50,
        filters_applied=["price_filter", "rating_filter"],
        sample_rejections={"price_too_high": 500, "low_rating": 450}
    )
    
    assert len(tracker.pipeline_data.candidates) == 1
    candidate = tracker.pipeline_data.candidates[0]
    assert candidate.step_name == "filtering_step"
    assert candidate.input_count == 1000
    assert candidate.output_count == 50
    assert candidate.filters_applied == ["price_filter", "rating_filter"]
    assert candidate.sample_rejections["price_too_high"] == 500


def test_capture_reasoning():
    """Test reasoning capture functionality."""
    tracker = XRayTracker("test_pipeline", auto_send=False)
    
    tracker.capture_reasoning(
        step_name="decision_step",
        decision="Selected option A",
        reasoning="Option A had the highest score",
        confidence=0.95,
        alternatives_considered=[{"option": "B", "score": 0.8}]
    )
    
    assert len(tracker.pipeline_data.steps) == 1
    step = tracker.pipeline_data.steps[0]
    assert step.step_name == "decision_step_reasoning"
    assert step.outputs["decision"] == "Selected option A"
    assert step.outputs["confidence"] == 0.95


def test_end_pipeline_success():
    """Test successful pipeline completion."""
    tracker = XRayTracker("test_pipeline", auto_send=False)
    
    tracker.capture_step("step1", {}, {}, "test")
    tracker.end_pipeline(final_result="success_result")
    
    assert tracker.pipeline_data.status == "completed"
    assert tracker.pipeline_data.final_result == "success_result"
    assert tracker.pipeline_data.end_time is not None


def test_end_pipeline_failure():
    """Test pipeline failure handling."""
    tracker = XRayTracker("test_pipeline", auto_send=False)
    
    tracker.capture_step("step1", {}, {}, "test")
    tracker.end_pipeline(error_message="Something went wrong")
    
    assert tracker.pipeline_data.status == "failed"
    assert tracker.pipeline_data.error_message == "Something went wrong"
    assert tracker.pipeline_data.end_time is not None


def test_pipeline_metadata():
    """Test pipeline metadata functionality."""
    tracker = XRayTracker("test_pipeline", auto_send=False)
    
    tracker.set_metadata("user_id", "test_user")
    tracker.set_metadata("experiment_id", "exp_123")
    
    assert tracker.pipeline_data.metadata["user_id"] == "test_user"
    assert tracker.pipeline_data.metadata["experiment_id"] == "exp_123"


def test_step_data_model():
    """Test StepData model validation."""
    step = StepData(
        step_name="test_step",
        inputs={"key": "value"},
        outputs={"result": "output"},
        reasoning="Test reasoning",
        timestamp=datetime.utcnow()
    )
    
    assert step.step_name == "test_step"
    assert step.inputs["key"] == "value"
    assert step.outputs["result"] == "output"
    assert step.reasoning == "Test reasoning"


def test_candidate_data_model():
    """Test CandidateData model validation."""
    candidate = CandidateData(
        step_name="filtering",
        input_count=100,
        output_count=10,
        filters_applied=["filter1", "filter2"],
        timestamp=datetime.utcnow()
    )
    
    assert candidate.step_name == "filtering"
    assert candidate.input_count == 100
    assert candidate.output_count == 10
    assert candidate.filters_applied == ["filter1", "filter2"]


def test_pipeline_data_model():
    """Test PipelineData model functionality."""
    pipeline = PipelineData(
        pipeline_id="test_123",
        pipeline_type="test_type",
        start_time=datetime.utcnow()
    )
    
    # Test adding steps
    step = StepData(
        step_name="test_step",
        inputs={},
        outputs={},
        reasoning="test",
        timestamp=datetime.utcnow()
    )
    pipeline.add_step(step)
    assert len(pipeline.steps) == 1
    
    # Test adding candidates
    candidate = CandidateData(
        step_name="test_filtering",
        input_count=100,
        output_count=10,
        filters_applied=["test_filter"],
        timestamp=datetime.utcnow()
    )
    pipeline.add_candidates(candidate)
    assert len(pipeline.candidates) == 1
    
    # Test completion
    pipeline.complete("final_result")
    assert pipeline.status == "completed"
    assert pipeline.final_result == "final_result"
    assert pipeline.end_time is not None
    
    # Test failure
    pipeline.fail("error message")
    assert pipeline.status == "failed"
    assert pipeline.error_message == "error message"


if __name__ == "__main__":
    pytest.main([__file__])
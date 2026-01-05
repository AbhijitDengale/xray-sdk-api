import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from api.main import app
from api.database import get_db, create_tables
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models import Base

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_health_check():
    """Test the root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "X-Ray API is running"


def test_create_pipeline():
    """Test creating a new pipeline."""
    pipeline_data = {
        "pipeline_id": "test_pipeline_123",
        "pipeline_type": "test_type",
        "start_time": datetime.utcnow().isoformat(),
        "status": "running",
        "steps": [
            {
                "step_name": "test_step",
                "inputs": {"key": "value"},
                "outputs": {"result": "output"},
                "reasoning": "Test reasoning",
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "candidates": [
            {
                "step_name": "test_filtering",
                "input_count": 100,
                "output_count": 10,
                "filters_applied": ["filter1", "filter2"],
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "metadata": {"test_key": "test_value"}
    }
    
    response = client.post("/api/v1/pipelines", json=pipeline_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["pipeline_id"] == "test_pipeline_123"
    assert result["pipeline_type"] == "test_type"
    assert len(result["steps"]) == 1
    assert len(result["candidates"]) == 1


def test_get_pipeline():
    """Test retrieving a specific pipeline."""
    # First create a pipeline
    pipeline_data = {
        "pipeline_id": "test_get_pipeline",
        "pipeline_type": "test_type",
        "start_time": datetime.utcnow().isoformat(),
        "status": "completed",
        "final_result": "test_result",
        "steps": [],
        "candidates": [],
        "metadata": {}
    }
    
    create_response = client.post("/api/v1/pipelines", json=pipeline_data)
    assert create_response.status_code == 200
    
    # Then retrieve it
    response = client.get("/api/v1/pipelines/test_get_pipeline")
    assert response.status_code == 200
    
    result = response.json()
    assert result["pipeline_id"] == "test_get_pipeline"
    assert result["final_result"] == "test_result"


def test_get_nonexistent_pipeline():
    """Test retrieving a pipeline that doesn't exist."""
    response = client.get("/api/v1/pipelines/nonexistent_pipeline")
    assert response.status_code == 404


def test_search_pipelines():
    """Test searching pipelines with various filters."""
    # Create test pipelines
    for i in range(3):
        pipeline_data = {
            "pipeline_id": f"search_test_{i}",
            "pipeline_type": "search_test_type",
            "start_time": datetime.utcnow().isoformat(),
            "status": "completed" if i % 2 == 0 else "failed",
            "steps": [],
            "candidates": [],
            "metadata": {}
        }
        client.post("/api/v1/pipelines", json=pipeline_data)
    
    # Test search by pipeline type
    response = client.get("/api/v1/pipelines/search?pipeline_type=search_test_type")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 3
    
    # Test search by status
    response = client.get("/api/v1/pipelines/search?status=completed")
    assert response.status_code == 200
    results = response.json()
    assert all(r["status"] == "completed" for r in results)


def test_analyze_steps():
    """Test step analysis endpoint."""
    # Create a pipeline with steps
    pipeline_data = {
        "pipeline_id": "analysis_test",
        "pipeline_type": "analysis_type",
        "start_time": datetime.utcnow().isoformat(),
        "status": "completed",
        "steps": [
            {
                "step_name": "analysis_step",
                "inputs": {"key": "value"},
                "outputs": {"result": "output"},
                "reasoning": "Analysis test reasoning",
                "timestamp": datetime.utcnow().isoformat(),
                "execution_time_ms": 150.0
            }
        ],
        "candidates": [],
        "metadata": {}
    }
    
    client.post("/api/v1/pipelines", json=pipeline_data)
    
    # Test step analysis
    response = client.get("/api/v1/steps/analyze?step_name=analysis_step")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert results[0]["step_name"] == "analysis_step"


def test_high_elimination_candidates():
    """Test high elimination rate endpoint."""
    # Create a pipeline with high elimination
    pipeline_data = {
        "pipeline_id": "elimination_test",
        "pipeline_type": "elimination_type",
        "start_time": datetime.utcnow().isoformat(),
        "status": "completed",
        "steps": [],
        "candidates": [
            {
                "step_name": "high_elimination_filter",
                "input_count": 1000,
                "output_count": 5,  # 99.5% elimination
                "filters_applied": ["strict_filter"],
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "metadata": {}
    }
    
    client.post("/api/v1/pipelines", json=pipeline_data)
    
    # Test high elimination endpoint
    response = client.get("/api/v1/candidates/high-elimination?min_rate=95.0")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert results[0]["step_name"] == "high_elimination_filter"


def test_debug_pipeline():
    """Test the debug endpoint."""
    # Create a pipeline for debugging
    pipeline_data = {
        "pipeline_id": "debug_test",
        "pipeline_type": "debug_type",
        "start_time": datetime.utcnow().isoformat(),
        "status": "completed",
        "final_result": "debug_result",
        "steps": [
            {
                "step_name": "debug_step",
                "inputs": {"input": "test"},
                "outputs": {"output": "result"},
                "reasoning": "Debug step reasoning",
                "timestamp": datetime.utcnow().isoformat(),
                "execution_time_ms": 6000.0  # Long execution time
            }
        ],
        "candidates": [
            {
                "step_name": "debug_filtering",
                "input_count": 100,
                "output_count": 2,  # 98% elimination
                "filters_applied": ["debug_filter"],
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "metadata": {}
    }
    
    client.post("/api/v1/pipelines", json=pipeline_data)
    
    # Test debug endpoint
    response = client.get("/api/v1/debug/pipeline/debug_test")
    assert response.status_code == 200
    
    result = response.json()
    assert result["pipeline_id"] == "debug_test"
    assert "execution_summary" in result
    assert "filtering_analysis" in result
    assert len(result["execution_summary"]) == 1
    assert len(result["filtering_analysis"]) == 1
    
    # Check for detected issues
    step_summary = result["execution_summary"][0]
    assert "Long execution time" in step_summary["potential_issues"]
    
    filter_analysis = result["filtering_analysis"][0]
    assert "Very high elimination rate" in filter_analysis["potential_issues"][0]


def test_update_pipeline():
    """Test updating an existing pipeline."""
    # Create initial pipeline
    initial_data = {
        "pipeline_id": "update_test",
        "pipeline_type": "update_type",
        "start_time": datetime.utcnow().isoformat(),
        "status": "running",
        "steps": [],
        "candidates": [],
        "metadata": {}
    }
    
    client.post("/api/v1/pipelines", json=initial_data)
    
    # Update with new data
    updated_data = {
        "pipeline_id": "update_test",
        "pipeline_type": "update_type",
        "start_time": initial_data["start_time"],
        "end_time": datetime.utcnow().isoformat(),
        "status": "completed",
        "final_result": "updated_result",
        "steps": [
            {
                "step_name": "new_step",
                "inputs": {"key": "value"},
                "outputs": {"result": "output"},
                "reasoning": "New step added",
                "timestamp": datetime.utcnow().isoformat()
            }
        ],
        "candidates": [],
        "metadata": {"updated": True}
    }
    
    response = client.put("/api/v1/pipelines/update_test", json=updated_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["status"] == "completed"
    assert result["final_result"] == "updated_result"
    assert len(result["steps"]) == 1


if __name__ == "__main__":
    pytest.main([__file__])
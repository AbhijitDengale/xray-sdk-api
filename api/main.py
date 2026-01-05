from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from . import crud, models, schemas
from .database import SessionLocal, engine, get_db, create_tables

# Create tables on startup
create_tables()

app = FastAPI(
    title="X-Ray API",
    description="API for debugging non-deterministic, multi-step algorithmic systems",
    version="1.0.0"
)


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"message": "X-Ray API is running", "version": "1.0.0"}


@app.post("/api/v1/pipelines", response_model=schemas.PipelineResponse)
def create_pipeline(
    pipeline: schemas.PipelineCreate,
    db: Session = Depends(get_db)
):
    """
    Ingest pipeline data from X-Ray SDK.
    
    Creates a new pipeline execution record with all steps and candidate data.
    """
    try:
        db_pipeline = crud.create_pipeline(db=db, pipeline=pipeline)
        return schemas.PipelineResponse.from_db_model(db_pipeline)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create pipeline: {str(e)}")


@app.put("/api/v1/pipelines/{pipeline_id}", response_model=schemas.PipelineResponse)
def update_pipeline(
    pipeline_id: str,
    pipeline: schemas.PipelineCreate,
    db: Session = Depends(get_db)
):
    """
    Update existing pipeline (for batch updates during long-running pipelines).
    """
    db_pipeline = crud.update_pipeline(db=db, pipeline_id=pipeline_id, pipeline=pipeline)
    if db_pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return schemas.PipelineResponse.from_db_model(db_pipeline)


@app.get("/api/v1/pipelines/{pipeline_id}", response_model=schemas.PipelineResponse)
def get_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    Get specific pipeline by ID.
    
    Returns complete pipeline data including all steps and candidate filtering information.
    """
    db_pipeline = crud.get_pipeline(db=db, pipeline_id=pipeline_id)
    if db_pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return schemas.PipelineResponse.from_db_model(db_pipeline)


@app.get("/api/v1/pipelines/search", response_model=List[schemas.PipelineResponse])
def search_pipelines(
    pipeline_type: Optional[str] = Query(None, description="Filter by pipeline type"),
    status: Optional[str] = Query(None, description="Filter by status (running, completed, failed)"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    step_name: Optional[str] = Query(None, description="Filter by step name"),
    min_elimination_rate: Optional[float] = Query(None, description="Minimum elimination rate percentage"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Search pipelines across different criteria.
    
    Supports filtering by:
    - Pipeline type (e.g., "competitor_selection", "categorization")
    - Status (running, completed, failed)
    - Date range
    - Specific step names
    - Minimum elimination rate (for finding aggressive filtering)
    
    Example: Find all runs where filtering eliminated more than 90% of candidates
    """
    query = schemas.PipelineSearchQuery(
        pipeline_type=pipeline_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        step_name=step_name,
        min_elimination_rate=min_elimination_rate,
        limit=limit,
        offset=offset
    )
    
    pipelines = crud.search_pipelines(db=db, query=query)
    return [schemas.PipelineResponse.from_db_model(pipeline) for pipeline in pipelines]


@app.get("/api/v1/steps/analyze", response_model=List[schemas.StepAnalysisResponse])
def analyze_steps(
    step_name: Optional[str] = Query(None, description="Filter by step name"),
    pipeline_type: Optional[str] = Query(None, description="Filter by pipeline type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    min_execution_time: Optional[float] = Query(None, description="Minimum execution time in ms"),
    limit: int = Query(100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Analyze step performance across pipelines.
    
    Returns aggregated statistics including:
    - Average execution time
    - Success rates
    - Common reasoning patterns
    - Total executions
    """
    query = schemas.StepAnalysisQuery(
        step_name=step_name,
        pipeline_type=pipeline_type,
        start_date=start_date,
        end_date=end_date,
        min_execution_time=min_execution_time,
        limit=limit
    )
    
    return crud.analyze_steps(db=db, query=query)


@app.get("/api/v1/candidates/high-elimination", response_model=List[schemas.CandidateResponse])
def get_high_elimination_steps(
    min_rate: float = Query(90.0, description="Minimum elimination rate percentage"),
    db: Session = Depends(get_db)
):
    """
    Get all filtering steps that eliminated more than the specified percentage of candidates.
    
    Useful for finding overly aggressive filters or identifying bottlenecks in pipelines.
    """
    candidates = crud.get_high_elimination_steps(db=db, min_rate=min_rate)
    return [schemas.CandidateResponse.from_db_model(candidate) for candidate in candidates]


@app.get("/api/v1/debug/pipeline/{pipeline_id}")
def debug_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    Debug-focused endpoint that provides a walkthrough of pipeline decisions.
    
    Returns structured debugging information to help identify where things went wrong.
    """
    pipeline = crud.get_pipeline(db=db, pipeline_id=pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Build debug walkthrough
    debug_info = {
        "pipeline_id": pipeline.pipeline_id,
        "pipeline_type": pipeline.pipeline_type,
        "status": pipeline.status,
        "final_result": pipeline.final_result,
        "total_steps": len(pipeline.steps),
        "total_filtering_steps": len(pipeline.candidates),
        "execution_summary": []
    }
    
    # Add step-by-step breakdown
    for i, step in enumerate(pipeline.steps):
        step_info = {
            "step_number": i + 1,
            "step_name": step.step_name,
            "execution_time_ms": step.execution_time_ms,
            "inputs_summary": {k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                             for k, v in (step.inputs or {}).items()},
            "outputs_summary": {k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                              for k, v in (step.outputs or {}).items()},
            "reasoning": step.reasoning,
            "potential_issues": []
        }
        
        # Add potential issue detection
        if step.execution_time_ms and step.execution_time_ms > 5000:  # > 5 seconds
            step_info["potential_issues"].append("Long execution time")
        
        if "error" in step.reasoning.lower() or "fail" in step.reasoning.lower():
            step_info["potential_issues"].append("Error mentioned in reasoning")
        
        debug_info["execution_summary"].append(step_info)
    
    # Add candidate filtering analysis
    debug_info["filtering_analysis"] = []
    for candidate in pipeline.candidates:
        elimination_rate = candidate.elimination_rate
        filter_info = {
            "step_name": candidate.step_name,
            "input_count": candidate.input_count,
            "output_count": candidate.output_count,
            "elimination_rate": round(elimination_rate, 2),
            "filters_applied": candidate.filters_applied,
            "rejection_summary": candidate.sample_rejections,
            "potential_issues": []
        }
        
        if elimination_rate > 95:
            filter_info["potential_issues"].append("Very high elimination rate - filters may be too strict")
        elif elimination_rate < 10:
            filter_info["potential_issues"].append("Very low elimination rate - filters may be too loose")
        
        debug_info["filtering_analysis"].append(filter_info)
    
    return debug_info


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
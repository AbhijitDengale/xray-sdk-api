from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime

from . import models, schemas


def create_pipeline(db: Session, pipeline: schemas.PipelineCreate) -> models.Pipeline:
    """Create a new pipeline with steps and candidates."""
    
    # Create pipeline
    db_pipeline = models.Pipeline(
        pipeline_id=pipeline.pipeline_id,
        pipeline_type=pipeline.pipeline_type,
        start_time=pipeline.start_time,
        end_time=pipeline.end_time,
        final_result=pipeline.final_result,
        status=pipeline.status,
        error_message=pipeline.error_message,
        pipeline_metadata=pipeline.metadata
    )
    db.add(db_pipeline)
    db.flush()  # Get the ID
    
    # Create steps
    for step_data in pipeline.steps:
        db_step = models.Step(
            pipeline_db_id=db_pipeline.id,
            step_name=step_data.step_name,
            inputs=step_data.inputs,
            outputs=step_data.outputs,
            reasoning=step_data.reasoning,
            timestamp=step_data.timestamp,
            execution_time_ms=step_data.execution_time_ms,
            step_metadata=step_data.metadata
        )
        db.add(db_step)
    
    # Create candidates
    for candidate_data in pipeline.candidates:
        db_candidate = models.Candidate(
            pipeline_db_id=db_pipeline.id,
            step_name=candidate_data.step_name,
            input_count=candidate_data.input_count,
            output_count=candidate_data.output_count,
            filters_applied=candidate_data.filters_applied,
            sample_rejections=candidate_data.sample_rejections,
            sample_accepted=candidate_data.sample_accepted,
            sample_rejected=candidate_data.sample_rejected,
            timestamp=candidate_data.timestamp,
            candidate_metadata=candidate_data.metadata
        )
        db.add(db_candidate)
    
    db.commit()
    db.refresh(db_pipeline)
    return db_pipeline


def get_pipeline(db: Session, pipeline_id: str) -> Optional[models.Pipeline]:
    """Get a pipeline by its pipeline_id."""
    return db.query(models.Pipeline).filter(
        models.Pipeline.pipeline_id == pipeline_id
    ).first()


def update_pipeline(db: Session, pipeline_id: str, pipeline: schemas.PipelineCreate) -> Optional[models.Pipeline]:
    """Update an existing pipeline (for batch updates)."""
    db_pipeline = get_pipeline(db, pipeline_id)
    if not db_pipeline:
        return None
    
    # Update pipeline fields
    db_pipeline.end_time = pipeline.end_time
    db_pipeline.final_result = pipeline.final_result
    db_pipeline.status = pipeline.status
    db_pipeline.error_message = pipeline.error_message
    db_pipeline.pipeline_metadata = pipeline.metadata
    
    # Add new steps (avoid duplicates by checking timestamp)
    existing_step_timestamps = {step.timestamp for step in db_pipeline.steps}
    for step_data in pipeline.steps:
        if step_data.timestamp not in existing_step_timestamps:
            db_step = models.Step(
                pipeline_db_id=db_pipeline.id,
                step_name=step_data.step_name,
                inputs=step_data.inputs,
                outputs=step_data.outputs,
                reasoning=step_data.reasoning,
                timestamp=step_data.timestamp,
                execution_time_ms=step_data.execution_time_ms,
                step_metadata=step_data.metadata
            )
            db.add(db_step)
    
    # Add new candidates
    existing_candidate_timestamps = {candidate.timestamp for candidate in db_pipeline.candidates}
    for candidate_data in pipeline.candidates:
        if candidate_data.timestamp not in existing_candidate_timestamps:
            db_candidate = models.Candidate(
                pipeline_db_id=db_pipeline.id,
                step_name=candidate_data.step_name,
                input_count=candidate_data.input_count,
                output_count=candidate_data.output_count,
                filters_applied=candidate_data.filters_applied,
                sample_rejections=candidate_data.sample_rejections,
                sample_accepted=candidate_data.sample_accepted,
                sample_rejected=candidate_data.sample_rejected,
                timestamp=candidate_data.timestamp,
                candidate_metadata=candidate_data.metadata
            )
            db.add(db_candidate)
    
    db.commit()
    db.refresh(db_pipeline)
    return db_pipeline


def search_pipelines(db: Session, query: schemas.PipelineSearchQuery) -> List[models.Pipeline]:
    """Search pipelines based on various criteria."""
    db_query = db.query(models.Pipeline)
    
    # Apply filters
    if query.pipeline_type:
        db_query = db_query.filter(models.Pipeline.pipeline_type == query.pipeline_type)
    
    if query.status:
        db_query = db_query.filter(models.Pipeline.status == query.status)
    
    if query.start_date:
        db_query = db_query.filter(models.Pipeline.start_time >= query.start_date)
    
    if query.end_date:
        db_query = db_query.filter(models.Pipeline.start_time <= query.end_date)
    
    # Filter by step name (join with steps table)
    if query.step_name:
        db_query = db_query.join(models.Step).filter(
            models.Step.step_name == query.step_name
        )
    
    # Filter by elimination rate (join with candidates table)
    if query.min_elimination_rate is not None:
        db_query = db_query.join(models.Candidate).filter(
            ((models.Candidate.input_count - models.Candidate.output_count) / 
             models.Candidate.input_count * 100) >= query.min_elimination_rate
        )
    
    # Apply pagination and ordering
    db_query = db_query.order_by(desc(models.Pipeline.start_time))
    db_query = db_query.offset(query.offset).limit(query.limit)
    
    return db_query.all()


def analyze_steps(db: Session, query: schemas.StepAnalysisQuery) -> List[schemas.StepAnalysisResponse]:
    """Analyze step performance across pipelines."""
    db_query = db.query(
        models.Step.step_name,
        models.Pipeline.pipeline_type,
        func.avg(models.Step.execution_time_ms).label('avg_execution_time'),
        func.count(models.Step.id).label('total_executions'),
        func.count(
            func.case([(models.Pipeline.status == 'completed', 1)])
        ).label('successful_executions')
    ).join(models.Pipeline)
    
    # Apply filters
    if query.step_name:
        db_query = db_query.filter(models.Step.step_name == query.step_name)
    
    if query.pipeline_type:
        db_query = db_query.filter(models.Pipeline.pipeline_type == query.pipeline_type)
    
    if query.start_date:
        db_query = db_query.filter(models.Step.timestamp >= query.start_date)
    
    if query.end_date:
        db_query = db_query.filter(models.Step.timestamp <= query.end_date)
    
    if query.min_execution_time:
        db_query = db_query.filter(models.Step.execution_time_ms >= query.min_execution_time)
    
    # Group by step name and pipeline type
    db_query = db_query.group_by(models.Step.step_name, models.Pipeline.pipeline_type)
    db_query = db_query.limit(query.limit)
    
    results = db_query.all()
    
    # Convert to response format
    analysis_results = []
    for result in results:
        success_rate = (result.successful_executions / result.total_executions * 100) if result.total_executions > 0 else 0
        
        # Get common reasoning patterns (simplified - could be more sophisticated)
        reasoning_query = db.query(models.Step.reasoning).filter(
            and_(
                models.Step.step_name == result.step_name,
                models.Pipeline.pipeline_type == result.pipeline_type
            )
        ).join(models.Pipeline).limit(10)
        
        reasoning_patterns = [r.reasoning[:100] + "..." if len(r.reasoning) > 100 else r.reasoning 
                            for r in reasoning_query.all()]
        
        analysis_results.append(schemas.StepAnalysisResponse(
            step_name=result.step_name,
            pipeline_type=result.pipeline_type,
            avg_execution_time_ms=result.avg_execution_time or 0,
            total_executions=result.total_executions,
            success_rate=success_rate,
            common_reasoning_patterns=reasoning_patterns[:5]  # Top 5 patterns
        ))
    
    return analysis_results


def get_high_elimination_steps(db: Session, min_rate: float = 90.0) -> List[models.Candidate]:
    """Get all steps where filtering eliminated more than specified percentage of candidates."""
    return db.query(models.Candidate).filter(
        ((models.Candidate.input_count - models.Candidate.output_count) / 
         models.Candidate.input_count * 100) >= min_rate
    ).all()
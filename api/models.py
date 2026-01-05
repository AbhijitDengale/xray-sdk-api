from sqlalchemy import Column, String, DateTime, Integer, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Pipeline(Base):
    """Database model for pipeline executions."""
    __tablename__ = "pipelines"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(String, unique=True, nullable=False, index=True)
    pipeline_type = Column(String, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    final_result = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="running", index=True)
    error_message = Column(Text, nullable=True)
    pipeline_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    steps = relationship("Step", back_populates="pipeline", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="pipeline", cascade="all, delete-orphan")


class Step(Base):
    """Database model for pipeline steps."""
    __tablename__ = "steps"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_db_id = Column(String, ForeignKey("pipelines.id"), nullable=False)
    step_name = Column(String, nullable=False, index=True)
    inputs = Column(JSON, nullable=False)
    outputs = Column(JSON, nullable=False)
    reasoning = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    execution_time_ms = Column(Float, nullable=True)
    step_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata'
    
    # Relationships
    pipeline = relationship("Pipeline", back_populates="steps")


class Candidate(Base):
    """Database model for candidate filtering data."""
    __tablename__ = "candidates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_db_id = Column(String, ForeignKey("pipelines.id"), nullable=False)
    step_name = Column(String, nullable=False, index=True)
    input_count = Column(Integer, nullable=False)
    output_count = Column(Integer, nullable=False)
    filters_applied = Column(JSON, nullable=False)  # List of filter names
    sample_rejections = Column(JSON, nullable=True)  # Dict of rejection reasons
    sample_accepted = Column(JSON, nullable=True)  # List of accepted samples
    sample_rejected = Column(JSON, nullable=True)  # List of rejected samples
    timestamp = Column(DateTime, nullable=False)
    candidate_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata'
    
    # Relationships
    pipeline = relationship("Pipeline", back_populates="candidates")
    
    @property
    def elimination_rate(self) -> float:
        """Calculate the percentage of candidates eliminated."""
        if self.input_count == 0:
            return 0.0
        return ((self.input_count - self.output_count) / self.input_count) * 100
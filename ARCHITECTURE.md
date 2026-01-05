# X-Ray System Architecture

## System Overview

X-Ray provides transparency into multi-step, non-deterministic algorithmic processes by capturing decision context at each step. Unlike traditional tracing that focuses on performance, X-Ray answers "why did the system make this decision?"

```
Developer Code → X-Ray SDK → X-Ray API → Database → Query Interface
```

## Data Model Rationale

**Core Design**: Three-entity model separating concerns while maintaining queryability.

```sql
Pipeline (1) ──── (N) Steps
Pipeline (1) ──── (N) Candidates
```

**Why this structure?**
- **Steps**: Capture individual decisions (inputs, outputs, reasoning)
- **Candidates**: Track filtering operations (5000 → 30 scenario)
- **Pipeline**: Group related operations with metadata

**Alternatives considered:**
- Single JSON blob: Poor queryability, can't analyze across pipelines
- Event sourcing: Too complex for debugging use case
- Step-centric only: Loses pipeline context for cross-step analysis

**What would break with different choices:**
- Without separate Candidates table: Can't efficiently query "filtering steps with >90% elimination"
- Without standardized step names: Cross-pipeline analysis impossible
- Single table approach: Performance degrades with large datasets

## Debugging Walkthrough: Phone Case vs Laptop Stand

**Problem**: Competitor selection returns phone case for laptop stand query.

**Investigation workflow:**
1. **Find the pipeline**: `GET /api/v1/pipelines/search?final_result=phone_case_123`
2. **Examine decision flow**: `GET /api/v1/debug/pipeline/{pipeline_id}`

**What they'd see:**
```json
{
  "steps": [
    {
      "step_name": "keyword_generation",
      "inputs": {"product_title": "Adjustable Laptop Stand"},
      "outputs": {"keywords": ["laptop", "stand", "phone"]},
      "reasoning": "LLM generated 'phone' due to training bias",
      "issue_detected": "Unexpected keyword contamination"
    }
  ],
  "filtering_analysis": [
    {
      "step_name": "category_filtering",
      "elimination_rate": 76.0,
      "issue": "High elimination but phone cases still present"
    }
  ]
}
```

**Root cause identified**: LLM keyword generation added "phone", contaminating entire pipeline.

## Queryability

**Cross-pipeline query support:**
```sql
-- "Show filtering steps with >90% elimination across all pipelines"
SELECT pipeline_type, step_name, AVG(elimination_rate)
FROM candidates c JOIN pipelines p ON c.pipeline_id = p.id
WHERE elimination_rate > 90
GROUP BY pipeline_type, step_name;
```

**Developer conventions required:**
- **Standardized step names**: `keyword_generation`, `candidate_filtering`, `relevance_scoring`
- **Consistent filter naming**: `price_range`, `category_match`, `rating_threshold`
- **Structured metadata**: Common fields in JSON for extensibility

**Handling variability**: Core schema supports common patterns, pipeline-specific data goes in metadata JSON fields.

## Performance & Scale

**5,000 → 30 candidates challenge:**

**Solution**: Configurable sampling with summary statistics.
```python
tracker.capture_candidates(
    input_count=5000, output_count=30,
    sample_rejections={"price_too_high": 2000},  # Summary counts
    sample_rejected=candidates[:100],  # First 100 for analysis
    sample_accepted=candidates  # All 30 accepted
)
```

**Trade-offs:**
| Approach | Completeness | Performance | Storage | Debug Value |
|----------|-------------|-------------|---------|-------------|
| Full capture | 100% | Poor | High | Maximum |
| Smart sampling | 80% | Good | Medium | High |
| Summary only | 40% | Excellent | Low | Medium |

**Who decides**: Developer controls via SDK configuration (`sampling_strategy="smart"`, `max_sample_size=100`).

## Developer Experience

**Minimal instrumentation** (4 lines):
```python
tracker = XRayTracker("competitor_selection")
tracker.capture_step("keyword_gen", inputs, outputs, reasoning)
tracker.capture_candidates("filtering", 5000, 30, filters)
tracker.end_pipeline(result)
```

**Full instrumentation**: Add detailed reasoning, metadata, confidence scores, alternatives considered.

**Backend unavailable**: SDK fails gracefully with local logging fallback, never breaks main pipeline.

## Real-World Application

**E-commerce recommendation engine** I worked on had 5-step pipeline: user profiling → candidate generation → content matching → business rules → ranking. When recommendations had 15% lower CTR, debugging took weeks.

**X-Ray would have shown**: Business rule filtering eliminated 97.6% of relevant products due to overly strict margin thresholds. Root cause identified in minutes instead of weeks.

**Retrofit approach**: Start with ranking step (highest impact), add candidate tracking to filtering (biggest bottleneck), gradually instrument upstream.

## API Specification

**Core endpoints:**
- `POST /api/v1/pipelines` - Ingest pipeline data
- `GET /api/v1/pipelines/search?pipeline_type=X&min_elimination_rate=90` - Cross-pipeline queries
- `GET /api/v1/debug/pipeline/{id}` - Structured debugging walkthrough
- `GET /api/v1/steps/analyze?step_name=filtering` - Step performance analysis

**Request/Response shapes:**
```json
// POST /api/v1/pipelines
{
  "pipeline_id": "string", "pipeline_type": "string",
  "steps": [{"step_name": "string", "inputs": {}, "outputs": {}, "reasoning": "string"}],
  "candidates": [{"input_count": 5000, "output_count": 30, "filters_applied": []}]
}
```

## What Next?

**Production priorities:**
1. **Multi-language SDKs** (JavaScript, Java, Go)
2. **Real-time streaming** for live debugging
3. **Anomaly detection** for decision pattern changes
4. **Natural language queries** ("show me failed runs this week")
5. **Integration ecosystem** (Datadog, New Relic, Grafana)

**Technical improvements:**
- ClickHouse backend for analytics workloads
- GraphQL API for complex queries
- Automatic instrumentation via decorators
- PII detection and masking for compliance
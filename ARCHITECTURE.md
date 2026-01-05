# X-Ray System Architecture

## Overview

The X-Ray system provides transparency into multi-step, non-deterministic algorithmic processes by capturing decision context, candidate filtering, and reasoning at each step. Unlike traditional tracing that focuses on performance, X-Ray answers "why did the system make this decision?"

## System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Developer's   │    │   X-Ray SDK     │    │   X-Ray API     │
│   Pipeline      │───▶│   (Library)     │───▶│   (Service)     │
│   Code          │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   PostgreSQL    │
                                               │   Database      │
                                               └─────────────────┘
```

## Data Model Rationale

### Core Design Decision: Three-Entity Model

I structured the data model around three core entities: **Pipelines**, **Steps**, and **Candidates**. This design separates concerns while maintaining queryability across different pipeline types.

```sql
Pipeline (1) ──── (N) Steps
Pipeline (1) ──── (N) Candidates
```

**Why this structure?**

1. **Separation of Concerns**: Steps capture individual decisions, Candidates capture filtering operations
2. **Queryability**: Can query across pipeline types while maintaining step-specific context
3. **Performance**: Separate tables allow efficient indexing on different query patterns
4. **Extensibility**: New pipeline types can reuse the same structure without schema changes

**Alternatives Considered:**

- **Single Table**: Would require complex JSON schemas, poor query performance
- **Step-Centric Model**: Would lose pipeline-level context and make cross-step analysis difficult
- **Event Sourcing**: Too complex for the debugging use case, would require event replay

**What Would Break:**

- If I'd used a single JSON blob: Cross-pipeline queries would be impossible
- If I'd normalized further: Would require complex joins for simple debugging workflows
- If I'd made it pipeline-specific: Each new use case would require schema changes

### Key Design Features

**Pipeline Entity:**
- `pipeline_id`: User-defined identifier for tracking
- `pipeline_type`: Enables cross-pipeline analysis ("competitor_selection", "categorization")
- `status`: Tracks completion state for long-running processes
- `metadata`: Extensible context without schema changes

**Step Entity:**
- `step_name`: Standardized naming enables cross-pipeline step analysis
- `inputs/outputs`: Full decision context as JSON
- `reasoning`: Human-readable explanation of decisions
- `execution_time_ms`: Performance correlation with decision quality

**Candidate Entity:**
- `input_count/output_count`: Quantifies filtering impact
- `filters_applied`: Structured list enables filter effectiveness analysis
- `sample_rejections`: Scalable approach to large dataset debugging
- `elimination_rate`: Computed property for quick filtering analysis

## Debugging Walkthrough: Phone Case vs Laptop Stand

**Scenario**: Competitor selection returns a phone case when searching for a laptop stand competitor.

**Step 1: Identify the Pipeline**
```bash
GET /api/v1/pipelines/search?pipeline_type=competitor_selection&final_result=phone_case_product_123
```

**Step 2: Examine Decision Flow**
```bash
GET /api/v1/debug/pipeline/run_456
```

**What the developer sees:**

```json
{
  "execution_summary": [
    {
      "step_name": "keyword_generation",
      "inputs": {"product_title": "Adjustable Laptop Stand"},
      "outputs": {"keywords": ["laptop", "stand", "adjustable", "phone"]},
      "reasoning": "LLM generated keywords including 'phone' due to training bias",
      "potential_issues": ["Unexpected keyword: phone"]
    },
    {
      "step_name": "product_search", 
      "inputs": {"keywords": ["laptop", "stand", "adjustable", "phone"]},
      "outputs": {"candidate_count": 5000},
      "reasoning": "Search API returned mixed results due to 'phone' keyword"
    }
  ],
  "filtering_analysis": [
    {
      "step_name": "category_filtering",
      "input_count": 5000,
      "output_count": 1200,
      "elimination_rate": 76.0,
      "filters_applied": ["category_match"],
      "rejection_summary": {"wrong_category": 3800},
      "potential_issues": ["High elimination but phone cases still present"]
    }
  ]
}
```

**Root Cause Identified**: The LLM keyword generation step incorrectly included "phone" as a keyword, contaminating the entire pipeline. The category filter wasn't strict enough to eliminate phone accessories.

**Fix**: Improve LLM prompt or add keyword validation step.

## Queryability

### Cross-Pipeline Analysis

**Challenge**: Support queries like "Show me all runs where filtering eliminated more than 90% of candidates" across different pipeline types.

**Solution**: Standardized step naming conventions + computed properties.

```sql
-- Find aggressive filtering across all pipelines
SELECT p.pipeline_type, c.step_name, AVG(c.elimination_rate)
FROM candidates c 
JOIN pipelines p ON c.pipeline_db_id = p.id
WHERE c.elimination_rate > 90
GROUP BY p.pipeline_type, c.step_name;
```

**Developer Conventions Required:**

1. **Standardized Step Names**: Use consistent naming (`keyword_generation`, `candidate_filtering`, `relevance_scoring`)
2. **Structured Metadata**: Common fields in metadata JSON for cross-pipeline analysis
3. **Filter Naming**: Consistent filter names (`price_range`, `category_match`, `rating_threshold`)

**Handling Variability:**

- **Flexible Metadata**: Pipeline-specific data goes in JSON metadata fields
- **Optional Fields**: Core schema supports common patterns, extensions via metadata
- **Computed Properties**: Database views for common cross-pipeline metrics

### Query Examples

```python
# Find all keyword generation steps with poor performance
GET /api/v1/steps/analyze?step_name=keyword_generation&min_execution_time=5000

# Find pipelines with specific error patterns
GET /api/v1/pipelines/search?step_name=llm_evaluation&status=failed

# Analyze filter effectiveness across pipeline types
GET /api/v1/candidates/high-elimination?min_rate=95
```

## Performance & Scale

### The 5,000 → 30 Candidates Challenge

**Problem**: Capturing full details for 5,000 rejected candidates is prohibitively expensive.

**Solution**: Configurable sampling with summary statistics.

```python
# SDK handles large datasets intelligently
tracker.capture_candidates(
    step_name="massive_filtering",
    input_count=5000,
    output_count=30,
    filters_applied=["price_range", "rating_threshold", "category_match"],
    sample_rejections={"price_too_high": 2000, "low_rating": 2970},  # Summary counts
    sample_rejected=[...],  # First 100 rejected items
    sample_accepted=[...]   # All 30 accepted items
)
```

**Trade-offs:**

| Approach | Completeness | Performance | Storage Cost | Debug Value |
|----------|-------------|-------------|--------------|-------------|
| Full Capture | 100% | Poor | High | Maximum |
| Smart Sampling | 80% | Good | Medium | High |
| Summary Only | 40% | Excellent | Low | Medium |

**Who Decides**: The developer controls sampling via SDK configuration:

```python
tracker = XRayTracker(
    "competitor_selection",
    sampling_strategy="smart",  # full, smart, summary
    max_sample_size=100
)
```

**Performance Optimizations:**

- **Batch Updates**: SDK batches data to reduce API calls
- **Async Processing**: Non-blocking data capture
- **Indexed Queries**: Database indexes on common query patterns
- **Computed Views**: Pre-calculated metrics for dashboard queries

## Developer Experience

### Minimal Instrumentation

**Existing Pipeline:**
```python
def find_competitor(product_title):
    keywords = generate_keywords(product_title)
    candidates = search_products(keywords)
    filtered = apply_filters(candidates)
    return select_best_match(filtered)
```

**Minimal X-Ray Integration:**
```python
def find_competitor(product_title):
    tracker = XRayTracker("competitor_selection")
    
    keywords = generate_keywords(product_title)
    tracker.capture_step("keyword_generation", 
                        {"title": product_title}, 
                        {"keywords": keywords},
                        "Generated from title analysis")
    
    candidates = search_products(keywords)
    filtered = apply_filters(candidates)
    tracker.capture_candidates("filtering", len(candidates), len(filtered), ["price", "rating"])
    
    result = select_best_match(filtered)
    tracker.end_pipeline(result)
    return result
```

**Changes Required**: 4 lines of instrumentation code.

### Full Instrumentation

```python
def find_competitor(product_title):
    tracker = XRayTracker("competitor_selection", auto_send=True)
    tracker.set_metadata("user_id", current_user.id)
    
    try:
        # Detailed step tracking
        keywords = generate_keywords(product_title)
        tracker.capture_step("keyword_generation", 
                           {"title": product_title, "category": product.category},
                           {"keywords": keywords, "confidence": 0.85},
                           f"LLM generated {len(keywords)} keywords using GPT-4")
        
        candidates = search_products(keywords)
        tracker.capture_step("product_search",
                           {"keywords": keywords, "search_params": {...}},
                           {"candidate_count": len(candidates)},
                           f"Search API returned {len(candidates)} products")
        
        # Detailed candidate tracking
        filtered = apply_filters(candidates)
        tracker.capture_candidates("filtering",
                                 len(candidates), len(filtered),
                                 ["price_range", "rating_threshold", "category_match"],
                                 sample_rejections=get_rejection_summary(candidates, filtered),
                                 sample_rejected=candidates[:100],  # First 100 for analysis
                                 sample_accepted=filtered)
        
        # Reasoning capture for LLM decisions
        result = select_best_match(filtered)
        tracker.capture_reasoning("final_selection",
                                f"Selected {result.id}",
                                f"Highest relevance score (0.94) and exact category match",
                                confidence=0.94,
                                alternatives_considered=filtered[:3])
        
        tracker.end_pipeline(result)
        return result
        
    except Exception as e:
        tracker.end_pipeline(error_message=str(e))
        raise
```

### Backend Unavailability Handling

**Graceful Degradation**: The SDK never breaks the main pipeline.

```python
def send_to_api(self) -> bool:
    try:
        response = requests.post(f"{self.api_base_url}/pipelines", ...)
        return True
    except requests.exceptions.RequestException as e:
        # Log warning but don't raise - main pipeline continues
        print(f"Warning: X-Ray data not sent: {e}")
        return False
```

**Fallback Options:**
- Local file logging when API unavailable
- Retry queue for temporary failures
- Circuit breaker pattern for persistent failures

## Real-World Application

### Personal Experience: E-commerce Recommendation Engine

At my previous company, we built a product recommendation system that combined collaborative filtering, content-based matching, and business rules. When recommendations performed poorly, debugging was a nightmare:

**The Problem:**
- 5-step pipeline: user profiling → candidate generation → content matching → business rule filtering → ranking
- When users got irrelevant recommendations, we couldn't tell which step failed
- A/B tests showed 15% lower CTR, but we spent weeks debugging

**How X-Ray Would Have Helped:**

```python
# Would have immediately identified the issue
tracker.capture_candidates("business_rule_filtering",
                         input_count=500,
                         output_count=12,  # 97.6% elimination!
                         filters_applied=["inventory_check", "margin_threshold", "brand_blacklist"],
                         sample_rejections={"low_margin": 450, "out_of_stock": 38})
```

**Root Cause**: The margin threshold filter was eliminating 90% of relevant products. X-Ray would have shown this immediately instead of requiring weeks of investigation.

**Retrofit Strategy:**
1. Start with minimal instrumentation on the ranking step (highest impact)
2. Add candidate tracking to the filtering step (biggest bottleneck)
3. Gradually instrument upstream steps as needed
4. Use sampling for the large candidate sets (500+ products)

## What Next?

### Production Readiness Features

**1. Multi-Language SDK Support**
- JavaScript/TypeScript for web applications
- Java for enterprise systems
- Go for high-performance services

**2. Advanced Analytics**
- Anomaly detection for decision patterns
- Performance regression alerts
- Decision quality scoring over time

**3. Real-Time Capabilities**
- Streaming ingestion for live debugging
- WebSocket API for real-time pipeline monitoring
- Live decision tree visualization

**4. Enterprise Features**
- Role-based access control
- Data retention policies
- Audit logging for compliance

**5. Developer Tooling**
- IDE plugins for automatic instrumentation
- CLI tools for pipeline analysis
- Integration with existing observability platforms (Datadog, New Relic)

**6. Advanced Querying**
- GraphQL API for complex queries
- Natural language query interface
- Saved query templates for common debugging patterns

### Technical Improvements

**Performance:**
- ClickHouse backend for analytics workloads
- Redis caching for frequent queries
- Horizontal scaling with sharding

**Reliability:**
- Multi-region deployment
- Backup and disaster recovery
- SLA monitoring and alerting

**Security:**
- End-to-end encryption for sensitive decision data
- PII detection and masking
- Compliance with GDPR/CCPA requirements

## API Specification

### Core Endpoints

**POST /api/v1/pipelines**
```json
{
  "pipeline_id": "string",
  "pipeline_type": "string", 
  "start_time": "datetime",
  "steps": [...],
  "candidates": [...],
  "status": "running|completed|failed"
}
```

**GET /api/v1/pipelines/search**
```
Query Parameters:
- pipeline_type: string
- status: string  
- start_date: datetime
- end_date: datetime
- step_name: string
- min_elimination_rate: float
- limit: int (default: 100)
- offset: int (default: 0)
```

**GET /api/v1/steps/analyze**
```
Query Parameters:
- step_name: string
- pipeline_type: string
- start_date: datetime
- end_date: datetime
- min_execution_time: float
- limit: int (default: 100)
```

**GET /api/v1/debug/pipeline/{pipeline_id}**
```json
{
  "pipeline_id": "string",
  "execution_summary": [...],
  "filtering_analysis": [...],
  "potential_issues": [...]
}
```

The X-Ray system provides the transparency needed to debug complex, non-deterministic systems while maintaining performance and developer experience. The modular design allows incremental adoption and scales from simple debugging to enterprise-wide decision analytics.
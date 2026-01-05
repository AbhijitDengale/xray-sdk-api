# X-Ray SDK and API

A debugging system for non-deterministic, multi-step algorithmic processes.

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python -m uvicorn api.main:app --reload --port 8000

# Install SDK locally
pip install -e ./sdk
```

### Basic Usage

```python
from xray_sdk import XRayTracker

# Initialize tracker
tracker = XRayTracker("competitor_selection", pipeline_id="run_123")

# Capture decision steps
tracker.capture_step(
    step_name="keyword_generation",
    inputs={"product_title": "Wireless Phone Charger"},
    outputs={"keywords": ["wireless", "charger", "phone"]},
    reasoning="Generated keywords from product title analysis"
)

# Track candidate filtering
tracker.capture_candidates(
    step_name="product_filtering", 
    input_count=5000,
    output_count=30,
    filters_applied=["price_range", "rating_threshold"],
    sample_rejections={"price_too_high": 2000, "low_rating": 2970}
)

# Complete pipeline
tracker.end_pipeline(final_result="competitor_product_67890")
```

### API Endpoints

- `POST /api/v1/pipelines` - Ingest pipeline data
- `GET /api/v1/pipelines/{pipeline_id}` - Get specific pipeline
- `GET /api/v1/pipelines/search` - Query across pipelines
- `GET /api/v1/steps/analyze` - Analyze step performance

## Architecture

See `ARCHITECTURE.md` for detailed system design and rationale.

## Known Limitations

- Currently supports Python only
- Requires manual instrumentation
- Basic query capabilities (can be extended)

## Future Improvements

- Multi-language SDK support
- Advanced analytics dashboard
- Automatic instrumentation via decorators
- Real-time streaming capabilities
#!/usr/bin/env python3
"""
X-Ray System Demo Script

This script demonstrates the X-Ray SDK in action with a realistic
competitor selection pipeline that shows both successful and problematic scenarios.
"""

import time
import random
from datetime import datetime
from xray_sdk import XRayTracker


def simulate_llm_keyword_generation(product_title: str, introduce_error: bool = False):
    """Simulate LLM-based keyword generation with potential errors."""
    time.sleep(0.1)  # Simulate API call
    
    base_keywords = product_title.lower().split()
    
    if introduce_error:
        # Simulate LLM hallucination - adds irrelevant keyword
        base_keywords.append("phone")  # Wrong keyword for laptop stand
        
    return {
        "keywords": base_keywords,
        "confidence": 0.85 if not introduce_error else 0.72,
        "model_used": "gpt-4"
    }


def simulate_product_search(keywords: list):
    """Simulate product search API."""
    time.sleep(0.2)  # Simulate API call
    
    # More results if "phone" keyword is present (contamination)
    base_count = 1000
    if "phone" in keywords:
        base_count = 5000  # Contaminated search results
        
    return {
        "candidates": [
            {"id": f"prod_{i}", "title": f"Product {i}", "category": "electronics", 
             "price": random.randint(10, 200), "rating": random.uniform(3.0, 5.0)}
            for i in range(base_count)
        ]
    }


def simulate_filtering(candidates: list, strict_mode: bool = False):
    """Simulate product filtering with configurable strictness."""
    time.sleep(0.3)  # Simulate processing
    
    # Simulate different filter outcomes
    if strict_mode:
        # Very strict filtering - eliminates too many
        filtered = candidates[:10]  # Keep only 10 out of many
        rejection_reasons = {
            "price_too_high": len(candidates) * 0.6,
            "low_rating": len(candidates) * 0.3,
            "wrong_category": len(candidates) * 0.1
        }
    else:
        # Normal filtering
        filtered = candidates[:50]  # Keep 50
        rejection_reasons = {
            "price_too_high": len(candidates) * 0.4,
            "low_rating": len(candidates) * 0.2,
            "wrong_category": len(candidates) * 0.4
        }
    
    return filtered, rejection_reasons


def simulate_llm_ranking(candidates: list, introduce_error: bool = False):
    """Simulate LLM-based relevance ranking."""
    time.sleep(0.4)  # Simulate LLM call
    
    if introduce_error:
        # Simulate poor ranking - picks wrong product
        best_match = candidates[-1]  # Pick last (worst) instead of first
        reasoning = "Selected based on price similarity, but missed category mismatch"
        confidence = 0.65
    else:
        # Good ranking
        best_match = candidates[0]  # Pick best match
        reasoning = "Selected based on high title similarity (0.94) and exact category match"
        confidence = 0.94
    
    return {
        "selected_product": best_match,
        "reasoning": reasoning,
        "confidence": confidence,
        "alternatives_considered": candidates[:3]
    }


def run_competitor_selection_demo(scenario: str = "success"):
    """
    Run a complete competitor selection pipeline with X-Ray tracking.
    
    Args:
        scenario: "success", "bad_keywords", "strict_filtering", or "poor_ranking"
    """
    print(f"\n🔍 Running Competitor Selection Demo - Scenario: {scenario}")
    print("=" * 60)
    
    # Initialize X-Ray tracker
    tracker = XRayTracker(
        pipeline_type="competitor_selection",
        pipeline_id=f"demo_{scenario}_{int(time.time())}",
        auto_send=False  # Don't send to API for demo
    )
    
    # Set pipeline metadata
    tracker.set_metadata("demo_scenario", scenario)
    tracker.set_metadata("user_id", "demo_user")
    
    try:
        # Input product
        product_title = "Adjustable Laptop Stand"
        print(f"📱 Input Product: {product_title}")
        
        # Step 1: Keyword Generation
        print("\n🔤 Step 1: Keyword Generation")
        introduce_keyword_error = scenario == "bad_keywords"
        
        start_time = time.time()
        keyword_result = simulate_llm_keyword_generation(product_title, introduce_keyword_error)
        
        tracker.capture_step(
            step_name="keyword_generation",
            inputs={"product_title": product_title, "category": "electronics"},
            outputs=keyword_result,
            reasoning=f"LLM generated {len(keyword_result['keywords'])} keywords using {keyword_result['model_used']}. "
                     f"Confidence: {keyword_result['confidence']}"
        )
        
        print(f"   Keywords: {keyword_result['keywords']}")
        print(f"   Confidence: {keyword_result['confidence']}")
        if introduce_keyword_error:
            print("   ⚠️  Warning: Unexpected 'phone' keyword detected!")
        
        # Step 2: Product Search
        print("\n🔍 Step 2: Product Search")
        search_result = simulate_product_search(keyword_result['keywords'])
        
        tracker.capture_step(
            step_name="product_search",
            inputs={"keywords": keyword_result['keywords'], "search_api": "internal"},
            outputs={"candidate_count": len(search_result['candidates'])},
            reasoning=f"Search API returned {len(search_result['candidates'])} products using keyword matching"
        )
        
        print(f"   Found: {len(search_result['candidates'])} candidate products")
        
        # Step 3: Filtering
        print("\n🔧 Step 3: Product Filtering")
        strict_filtering = scenario == "strict_filtering"
        
        filtered_products, rejection_reasons = simulate_filtering(
            search_result['candidates'], 
            strict_mode=strict_filtering
        )
        
        tracker.capture_candidates(
            step_name="product_filtering",
            input_count=len(search_result['candidates']),
            output_count=len(filtered_products),
            filters_applied=["price_range", "rating_threshold", "category_match"],
            sample_rejections=rejection_reasons,
            sample_accepted=filtered_products[:5],  # Sample of accepted
            sample_rejected=search_result['candidates'][-5:]  # Sample of rejected
        )
        
        elimination_rate = ((len(search_result['candidates']) - len(filtered_products)) / 
                          len(search_result['candidates'])) * 100
        
        print(f"   Input: {len(search_result['candidates'])} products")
        print(f"   Output: {len(filtered_products)} products")
        print(f"   Elimination Rate: {elimination_rate:.1f}%")
        print(f"   Rejection Reasons: {rejection_reasons}")
        
        if elimination_rate > 95:
            print("   ⚠️  Warning: Very high elimination rate - filters may be too strict!")
        
        # Step 4: LLM Ranking & Selection
        print("\n🎯 Step 4: Final Selection")
        introduce_ranking_error = scenario == "poor_ranking"
        
        ranking_result = simulate_llm_ranking(filtered_products, introduce_ranking_error)
        
        tracker.capture_reasoning(
            step_name="final_selection",
            decision=f"Selected product {ranking_result['selected_product']['id']}",
            reasoning=ranking_result['reasoning'],
            confidence=ranking_result['confidence'],
            alternatives_considered=ranking_result['alternatives_considered']
        )
        
        final_result = ranking_result['selected_product']
        
        print(f"   Selected: {final_result['id']} - {final_result['title']}")
        print(f"   Reasoning: {ranking_result['reasoning']}")
        print(f"   Confidence: {ranking_result['confidence']}")
        
        if ranking_result['confidence'] < 0.7:
            print("   ⚠️  Warning: Low confidence in final selection!")
        
        # Complete pipeline
        tracker.end_pipeline(final_result=final_result)
        
        print(f"\n✅ Pipeline completed successfully!")
        print(f"   Final Result: {final_result['title']}")
        print(f"   Total Steps: {len(tracker.get_pipeline_data().steps)}")
        print(f"   Total Filtering Operations: {len(tracker.get_pipeline_data().candidates)}")
        
    except Exception as e:
        tracker.end_pipeline(error_message=str(e))
        print(f"\n❌ Pipeline failed: {e}")
        raise
    
    return tracker.get_pipeline_data()


def demonstrate_debugging_workflow():
    """Show how to debug a problematic pipeline using X-Ray data."""
    print("\n🐛 Debugging Workflow Demonstration")
    print("=" * 60)
    
    # Run a problematic scenario
    pipeline_data = run_competitor_selection_demo("bad_keywords")
    
    print("\n🔍 Debugging Analysis:")
    print("-" * 30)
    
    # Analyze steps for issues
    print("\n📊 Step Analysis:")
    for i, step in enumerate(pipeline_data.steps):
        print(f"\n   Step {i+1}: {step.step_name}")
        print(f"   Execution Time: {step.execution_time_ms:.1f}ms")
        print(f"   Reasoning: {step.reasoning}")
        
        # Check for potential issues
        if step.step_name == "keyword_generation":
            keywords = step.outputs.get("keywords", [])
            if "phone" in keywords and "laptop" in keywords:
                print("   🚨 ISSUE DETECTED: Conflicting keywords ('phone' + 'laptop')")
                print("   💡 RECOMMENDATION: Review LLM prompt or add keyword validation")
    
    # Analyze filtering steps
    print("\n📈 Filtering Analysis:")
    for candidate in pipeline_data.candidates:
        elimination_rate = ((candidate.input_count - candidate.output_count) / 
                          candidate.input_count) * 100
        print(f"\n   Step: {candidate.step_name}")
        print(f"   Elimination Rate: {elimination_rate:.1f}%")
        print(f"   Filters Applied: {candidate.filters_applied}")
        
        if elimination_rate > 95:
            print("   🚨 ISSUE DETECTED: Excessive elimination rate")
            print("   💡 RECOMMENDATION: Review filter thresholds")
    
    print("\n🎯 Root Cause Analysis:")
    print("   The 'phone' keyword contaminated the search results,")
    print("   leading to irrelevant candidates and poor final selection.")
    print("   Fix: Improve LLM keyword generation or add validation step.")


def run_all_scenarios():
    """Run all demo scenarios to show different types of issues."""
    scenarios = ["success", "bad_keywords", "strict_filtering", "poor_ranking"]
    
    print("🚀 X-Ray System Complete Demo")
    print("=" * 60)
    print("This demo shows how X-Ray captures decision context in")
    print("multi-step algorithmic pipelines and helps debug issues.")
    
    results = {}
    
    for scenario in scenarios:
        pipeline_data = run_competitor_selection_demo(scenario)
        results[scenario] = pipeline_data
        time.sleep(1)  # Brief pause between scenarios
    
    # Summary analysis
    print("\n📋 Demo Summary")
    print("=" * 60)
    
    for scenario, data in results.items():
        print(f"\n{scenario.upper()}:")
        print(f"   Steps: {len(data.steps)}")
        print(f"   Status: {data.status}")
        print(f"   Duration: {(data.end_time - data.start_time).total_seconds():.1f}s")
        
        # Calculate total elimination rate
        total_input = sum(c.input_count for c in data.candidates)
        total_output = sum(c.output_count for c in data.candidates)
        if total_input > 0:
            total_elimination = ((total_input - total_output) / total_input) * 100
            print(f"   Total Elimination Rate: {total_elimination:.1f}%")
    
    return results


if __name__ == "__main__":
    print("🔬 X-Ray SDK Demo Script")
    print("This script demonstrates the X-Ray system with realistic scenarios.")
    print("\nChoose a demo:")
    print("1. Single scenario (success)")
    print("2. Single scenario (with issues)")
    print("3. All scenarios")
    print("4. Debugging workflow")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        run_competitor_selection_demo("success")
    elif choice == "2":
        run_competitor_selection_demo("bad_keywords")
    elif choice == "3":
        run_all_scenarios()
    elif choice == "4":
        demonstrate_debugging_workflow()
    else:
        print("Running default demo...")
        run_all_scenarios()
    
    print("\n🎉 Demo completed!")
    print("\nTo run the API server:")
    print("   python -m uvicorn api.main:app --reload --port 8000")
    print("\nTo test API endpoints:")
    print("   curl http://localhost:8000/api/v1/pipelines/search")
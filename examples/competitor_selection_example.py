#!/usr/bin/env python3
"""
Competitor Selection Example - Demonstrates X-Ray SDK usage

This example shows how to instrument a competitor selection pipeline
that matches the scenario described in the job posting.
"""

import time
import random
from typing import List, Dict, Any
from xray_sdk import XRayTracker


class Product:
    """Simple product representation."""
    def __init__(self, id: str, title: str, category: str, price: float, rating: float):
        self.id = id
        self.title = title
        self.category = category
        self.price = price
        self.rating = rating
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "price": self.price,
            "rating": self.rating
        }


class CompetitorSelectionPipeline:
    """
    Competitor selection pipeline with X-Ray instrumentation.
    
    This demonstrates the exact scenario from the job posting:
    Given a seller's product, find the most relevant competitor product.
    """
    
    def __init__(self, api_base_url: str = "http://localhost:8000/api/v1"):
        self.api_base_url = api_base_url
    
    def find_competitor(self, seller_product: Product) -> Product:
        """
        Main pipeline: Find the best competitor for a given product.
        
        Steps:
        1. Generate search keywords from product title and category
        2. Search and retrieve candidate competitor products  
        3. Apply filters (price range, rating threshold, category match)
        4. Use ranking to evaluate relevance and eliminate false positives
        5. Select the single best competitor
        """
        
        # Initialize X-Ray tracking
        tracker = XRayTracker(
            pipeline_type="competitor_selection",
            api_base_url=self.api_base_url,
            auto_send=True  # Send data to API automatically
        )
        
        # Set pipeline metadata
        tracker.set_metadata("seller_product_id", seller_product.id)
        tracker.set_metadata("seller_category", seller_product.category)
        
        try:
            print(f"🔍 Finding competitor for: {seller_product.title}")
            
            # Step 1: Generate Keywords
            keywords = self._generate_keywords(tracker, seller_product)
            
            # Step 2: Search Products
            candidates = self._search_products(tracker, keywords)
            
            # Step 3: Apply Filters
            filtered_candidates = self._apply_filters(tracker, candidates, seller_product)
            
            # Step 4: Rank and Select
            best_competitor = self._rank_and_select(tracker, filtered_candidates, seller_product)
            
            # Complete pipeline
            tracker.end_pipeline(final_result=best_competitor.to_dict())
            
            print(f"✅ Selected competitor: {best_competitor.title}")
            return best_competitor
            
        except Exception as e:
            tracker.end_pipeline(error_message=str(e))
            print(f"❌ Pipeline failed: {e}")
            raise
    
    def _generate_keywords(self, tracker: XRayTracker, product: Product) -> List[str]:
        """Step 1: Generate search keywords (simulates LLM call)."""
        print("  📝 Generating keywords...")
        
        start_time = time.time()
        
        # Simulate LLM processing time
        time.sleep(0.1)
        
        # Extract keywords from title and category
        title_words = product.title.lower().split()
        category_words = product.category.lower().split()
        
        # Simulate LLM keyword generation with potential issues
        keywords = []
        for word in title_words + category_words:
            if len(word) > 3:  # Skip short words
                keywords.append(word)
        
        # Simulate LLM hallucination (adds wrong keyword sometimes)
        if random.random() < 0.2:  # 20% chance of error
            keywords.append("phone")  # Wrong keyword for laptop stand
        
        execution_time = (time.time() - start_time) * 1000
        
        tracker.capture_step(
            step_name="keyword_generation",
            inputs={
                "product_title": product.title,
                "product_category": product.category,
                "llm_model": "gpt-4"
            },
            outputs={
                "keywords": keywords,
                "keyword_count": len(keywords),
                "confidence": 0.85
            },
            reasoning=f"LLM extracted {len(keywords)} keywords from product title and category. "
                     f"Used GPT-4 with product categorization prompt.",
            metadata={"execution_time_ms": execution_time}
        )
        
        print(f"    Generated keywords: {keywords}")
        return keywords
    
    def _search_products(self, tracker: XRayTracker, keywords: List[str]) -> List[Product]:
        """Step 2: Search for candidate products."""
        print("  🔍 Searching for candidates...")
        
        start_time = time.time()
        
        # Simulate API call delay
        time.sleep(0.2)
        
        # Generate mock candidates (more if contaminated with wrong keywords)
        base_count = 1000
        if "phone" in keywords:
            base_count = 5000  # Contaminated search returns more irrelevant results
        
        candidates = []
        categories = ["electronics", "accessories", "office", "mobile"]
        
        for i in range(base_count):
            # Simulate search results with varying relevance
            if "phone" in keywords and i < 2000:
                # Phone-related products (contamination)
                category = "mobile"
                title = f"Phone Case {i}" if i < 1000 else f"Phone Charger {i}"
            else:
                # Relevant products
                category = "electronics" if i % 2 == 0 else "office"
                title = f"Laptop Stand {i}" if i % 3 == 0 else f"Monitor Stand {i}"
            
            product = Product(
                id=f"candidate_{i}",
                title=title,
                category=category,
                price=random.uniform(10, 200),
                rating=random.uniform(2.0, 5.0)
            )
            candidates.append(product)
        
        execution_time = (time.time() - start_time) * 1000
        
        tracker.capture_step(
            step_name="product_search",
            inputs={
                "keywords": keywords,
                "search_api": "internal_catalog",
                "search_params": {"limit": 10000, "include_variants": True}
            },
            outputs={
                "candidate_count": len(candidates),
                "search_time_ms": execution_time
            },
            reasoning=f"Search API returned {len(candidates)} products using keyword matching. "
                     f"Higher count indicates potential keyword contamination.",
            metadata={"api_endpoint": "/search/products", "cache_hit": False}
        )
        
        print(f"    Found {len(candidates)} candidates")
        return candidates
    
    def _apply_filters(self, tracker: XRayTracker, candidates: List[Product], 
                      seller_product: Product) -> List[Product]:
        """Step 3: Apply filtering logic."""
        print("  🔧 Applying filters...")
        
        start_time = time.time()
        
        # Simulate processing time
        time.sleep(0.3)
        
        original_count = len(candidates)
        
        # Filter 1: Price range (within 50% of seller price)
        price_min = seller_product.price * 0.5
        price_max = seller_product.price * 1.5
        candidates = [c for c in candidates if price_min <= c.price <= price_max]
        after_price = len(candidates)
        
        # Filter 2: Rating threshold (>= 3.5)
        candidates = [c for c in candidates if c.rating >= 3.5]
        after_rating = len(candidates)
        
        # Filter 3: Category match (same category or compatible)
        compatible_categories = {
            "electronics": ["electronics", "office"],
            "office": ["office", "electronics"],
            "mobile": ["mobile", "accessories"],
            "accessories": ["accessories", "mobile"]
        }
        
        allowed_categories = compatible_categories.get(seller_product.category, [seller_product.category])
        candidates = [c for c in candidates if c.category in allowed_categories]
        after_category = len(candidates)
        
        execution_time = (time.time() - start_time) * 1000
        
        # Calculate rejection reasons
        price_rejected = original_count - after_price
        rating_rejected = after_price - after_rating  
        category_rejected = after_rating - after_category
        
        tracker.capture_candidates(
            step_name="product_filtering",
            input_count=original_count,
            output_count=len(candidates),
            filters_applied=["price_range", "rating_threshold", "category_match"],
            sample_rejections={
                "price_out_of_range": price_rejected,
                "low_rating": rating_rejected,
                "category_mismatch": category_rejected
            },
            sample_accepted=[c.to_dict() for c in candidates[:10]],  # First 10 accepted
            sample_rejected=[c.to_dict() for c in candidates[-5:]] if candidates else [],  # Last 5 for analysis
            metadata={
                "price_range": f"${price_min:.2f} - ${price_max:.2f}",
                "rating_threshold": 3.5,
                "allowed_categories": allowed_categories,
                "execution_time_ms": execution_time
            }
        )
        
        elimination_rate = ((original_count - len(candidates)) / original_count) * 100
        print(f"    Filtered {original_count} → {len(candidates)} ({elimination_rate:.1f}% eliminated)")
        
        return candidates
    
    def _rank_and_select(self, tracker: XRayTracker, candidates: List[Product], 
                        seller_product: Product) -> Product:
        """Step 4: Rank candidates and select the best match."""
        print("  🎯 Ranking and selecting...")
        
        if not candidates:
            raise ValueError("No candidates remaining after filtering")
        
        start_time = time.time()
        
        # Simulate LLM ranking time
        time.sleep(0.4)
        
        # Simple ranking algorithm (in real system, this might be an LLM)
        scored_candidates = []
        
        for candidate in candidates:
            # Calculate relevance score based on multiple factors
            title_similarity = self._calculate_title_similarity(seller_product.title, candidate.title)
            category_bonus = 0.2 if candidate.category == seller_product.category else 0.0
            price_similarity = 1.0 - abs(candidate.price - seller_product.price) / seller_product.price
            rating_bonus = (candidate.rating - 3.0) / 2.0  # Normalize rating to 0-1
            
            total_score = (title_similarity * 0.4 + 
                          category_bonus * 0.3 + 
                          price_similarity * 0.2 + 
                          rating_bonus * 0.1)
            
            scored_candidates.append((candidate, total_score))
        
        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Select best candidate
        best_candidate, best_score = scored_candidates[0]
        
        execution_time = (time.time() - start_time) * 1000
        
        # Prepare alternatives for reasoning
        alternatives = [
            {
                "product_id": candidate.id,
                "title": candidate.title,
                "score": score,
                "reason": f"Score: {score:.3f}"
            }
            for candidate, score in scored_candidates[:5]  # Top 5
        ]
        
        tracker.capture_reasoning(
            step_name="final_selection",
            decision=f"Selected {best_candidate.id}: {best_candidate.title}",
            reasoning=f"Highest relevance score ({best_score:.3f}) based on title similarity, "
                     f"category match, price similarity, and rating. "
                     f"Title similarity: {self._calculate_title_similarity(seller_product.title, best_candidate.title):.3f}",
            confidence=min(best_score, 1.0),
            alternatives_considered=alternatives,
            metadata={
                "ranking_algorithm": "weighted_similarity",
                "total_candidates_ranked": len(candidates),
                "execution_time_ms": execution_time
            }
        )
        
        print(f"    Selected: {best_candidate.title} (score: {best_score:.3f})")
        return best_candidate
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Simple title similarity calculation."""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)  # Jaccard similarity


def main():
    """Run the competitor selection example."""
    print("🚀 Competitor Selection Pipeline Example")
    print("=" * 50)
    
    # Create pipeline
    pipeline = CompetitorSelectionPipeline()
    
    # Example seller product
    seller_product = Product(
        id="seller_123",
        title="Adjustable Laptop Stand",
        category="electronics",
        price=45.99,
        rating=4.2
    )
    
    print(f"Seller Product: {seller_product.title}")
    print(f"Category: {seller_product.category}")
    print(f"Price: ${seller_product.price}")
    print()
    
    try:
        # Run the pipeline
        competitor = pipeline.find_competitor(seller_product)
        
        print("\n📊 Results:")
        print(f"Competitor: {competitor.title}")
        print(f"Category: {competitor.category}")
        print(f"Price: ${competitor.price}")
        print(f"Rating: {competitor.rating}")
        
        print("\n💡 To debug this pipeline:")
        print("1. Start the X-Ray API: python -m uvicorn api.main:app --reload")
        print("2. Check the pipeline data at: http://localhost:8000/api/v1/pipelines/search")
        print("3. Use the debug endpoint for detailed analysis")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")


if __name__ == "__main__":
    main()
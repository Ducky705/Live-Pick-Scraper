import json
import os
import sys
import asyncio
from typing import Any

# Setup
sys.path.insert(0, os.path.abspath("."))
from src.extraction_pipeline import ExtractionPipeline

# Mocking the pipeline run since it's hard to import everything cleanly in a script sometimes
# But we should rely on the actual pipeline if possible. 
# Depending on previous learnings, ExtractionPipeline.run is the entry point.

def generate_labels():
    input_path = "benchmark/dataset/golden_set_v3_candidates.json"
    output_path = "benchmark/dataset/golden_set_v3_draft.json"
    
    with open(input_path, "r") as f:
        candidates = json.load(f)
        
    print(f"Generating labels for {len(candidates)} candidates...")
    
    # We transform candidates into the format expected by pipeline
    # The pipeline expects a list of dicts.
    # We will process them.
    
    # Run pipeline
    # We use 'groq' strategy for speed/quality balance
    try:
        results = ExtractionPipeline.run(
            messages=candidates, 
            target_date="2026-02-05", 
            batch_size=5,
            strategy="groq"
        )
        
        # Map results back to candidates
        # Result items should have 'message_id' corresponding to candidate 'id'
        # But 'results' is a list of picks. We need to group picks by message_id.
        
        picks_map = {}
        for r in results:
            mid = str(r.get("message_id"))
            if mid not in picks_map:
                picks_map[mid] = []
            
            # Format pick for "expected_picks"
            # We want the "selection" string primarily, maybe "odds" too?
            # For simplicity, let's keep the full object for now or a simplified string
            # Benchmark usually expects a list of strings "Team -110" or dicts.
            # v2 benchmark used dicts: {"pick": "..."}
            
            p_clean = {
                "pick": r.get("pick"),
                "odds": r.get("odds"),
                "units": r.get("units"),
                "type": r.get("type")
            }
            picks_map[mid].append(p_clean)
            
        # Reconstruct the Golden Set
        golden_set = []
        for cand in candidates:
            mid = str(cand.get("id"))
            picks = picks_map.get(mid, [])
            
            cand["expected_picks"] = picks
            # Add metadata about how this was generated
            cand["label_source"] = "hybrid_pipeline_v1"
            golden_set.append(cand)
            
        with open(output_path, "w") as f:
            json.dump(golden_set, f, indent=2)
            
        print(f"Saved populated dataset to {output_path}")
        
    except Exception as e:
        print(f"Error generating labels: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_labels()

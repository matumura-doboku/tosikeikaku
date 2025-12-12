import os
import sys
import threading
import time

# Mock Flask app context if needed or just test the logic directly
# We will test by importing app and calling the function logic directly 
# because running a full flask server in test script might be complex in this environment.

# Add path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import app
    # Mocking Flask globals/requests if needed, but we can verify initialize_simulator
    
    print("Test 1: Initialize Simulator")
    app.initialize_simulator()
    
    if app.SIM_GRAPH is None:
        print("FAIL: SIM_GRAPH is None. Check data files.")
        # Create dummy data if missing for test?
        # The code mocks data in advanced_city_simulator if file missing? 
        # acs.py line 48: except: masters["line_type"] = dummy...
        # But calculate_zone_demand imports from CSV.
        # Let's see if it fails.
    else:
        print(f"SUCCESS: SIM_GRAPH initialized with {len(app.SIM_GRAPH.nodes)} nodes.")

    print("\nTest 2: Run Simulation (Direct Call)")
    # Mock parameters? default is used.
    
    # We call underlying logic to avoid request context issues
    import advanced_city_simulator as acs
    
    if app.SIM_GRAPH:
        stats = acs.run_simulation_logit(app.SIM_GRAPH, app.SIM_DEMAND, app.SIM_PARAMS)
        print(f"SUCCESS: Simulation returned stats for {len(stats)} zones.")
        
        # Check output structure
        sample_zone = list(stats.keys())[0] if stats else None
        if sample_zone:
            print(f"Sample Zone {sample_zone} stats: {stats[sample_zone]}")
    
except Exception as e:
    print(f"TEST FAILED: {e}")

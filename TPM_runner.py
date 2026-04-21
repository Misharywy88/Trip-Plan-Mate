import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from Hotels.travel_hotels_pipeline import run_hotels
from Flights.travel_flights_pipeline import run_flights
from Activities.travel_things_pipeline import run_tripadvisor

def run_TPM(from_city, to_city, travelers, dates, activities_percentages,
            run_hotels_flag=True, run_flights_flag=True, run_tripadvisor_flag=True,
            ):
    
    start = time.perf_counter()

    # Construct user_text for hotels/flights
    user_text = f"Book a trip from {from_city} to {to_city} for {travelers} traveler(s) from {dates}"
    
    futures = {}
    results = {}

    # Counters
    pipeline_counters = {
        "hotels": {"success": 0, "failed": 0},
        "flights": {"success": 0, "failed": 0},
        "tripadvisor": {"success": 0, "failed": 0},
    }

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=3) as executor:
        if run_hotels_flag:
            futures[executor.submit(run_hotels, user_text)] = "hotels"

        if run_flights_flag:
            futures[executor.submit(run_flights, user_text)] = "flights"

        if run_tripadvisor_flag:
            futures[executor.submit(run_tripadvisor, to_city, activities_percentages)] = "tripadvisor"

        for future in as_completed(futures):
            key = futures[future]

            try:
                results[key] = future.result()
                pipeline_counters[key]["success"] += 1

            except Exception as e:
                print(f"❌ Error in {key} pipeline: {e}")
                results[key] = None
                pipeline_counters[key]["failed"] += 1


    time_taken = time.perf_counter() - start
    print(f"\nTotal time taken to run TPM pipelines: {time_taken:.2f} seconds")

    # Print counters summary
    # print("\nPipeline Summary:")
    # for k, v in pipeline_counters.items():
    #     print(f"{k.upper()} → ✅ Success: {v['success']} | ❌ Failed: {v['failed']}")
        
        
        
    
    return results



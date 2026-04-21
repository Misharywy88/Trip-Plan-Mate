import datetime
import time
import streamlit as st
from streamlit_option_menu import option_menu
from TPM_runner import run_TPM


# -------------------------------
# Initialize session state
# -------------------------------
if "show_results" not in st.session_state:
    st.session_state.show_results = False
if "last_search_results" not in st.session_state:
    st.session_state.last_search_results = {}
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None

# -------------------------------
# Page UI
# -------------------------------
st.set_page_config(page_title="Travel Planner Mate", layout="centered", page_icon="✈️")
st.title("✈️ Travel Planner Mate (MVP)")

today = datetime.date.today()
six_months = today + datetime.timedelta(days=30 * 6)
default_start = today
default_end = today + datetime.timedelta(days=7)

# -------------------------------
# Top container: Inputs
# -------------------------------
with st.container():
    st.subheader("Trip Inputs")

    col1, col2 = st.columns(2)

    with col1:
        departure = st.text_input("Departure Location", placeholder="City or Airport code...")
        date_range = st.date_input(
            "Trip dates",
            value=(default_start, default_end),
            min_value=today,
            max_value=six_months,
            format="DD.MM.YYYY"
        )

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        elif isinstance(date_range, tuple) and len(date_range) == 1:
            start_date = end_date = date_range[0]
        else:
            start_date = end_date = date_range

        travelers_num = st.number_input("Travelers Number:", min_value=1, value=1)
        flights_checked = st.checkbox("Include Flights", value=False)
        hotels_checked = st.checkbox("Include Hotels", value=False)
        activities_checked = st.checkbox("Include Activities & Restaurants", value=False)

    with col2:
        destination = st.text_input("Destination", placeholder="Molly, Almaty, Vinna")
        budget_min = st.number_input("Stay Budget Min per Night (SAR)", min_value=0, value=200)
        budget_max = st.number_input("Stay Budget Max per Night (SAR)", min_value=0, value=2000)
        description = st.text_area("Stay Imagination (optional)", placeholder="Describe your stay ideas...\n Beach access, city center, quiet area..")

# -------------------------------
# Second container: Sliders row
# -------------------------------
with st.container():
    st.subheader("Experiences Preferences")
    col1, col2 = st.columns(2)

    with col1:
        nature = st.slider("Human-built <-----------------------------------------------> Natural ", 0, 100, 50)
        human_built = 100 - nature

    with col2:
        historical = st.slider("Modern <--------------------------------------------------> Historical ", 0, 100, 50)
        modern = 100 - historical

    preferences = {
        "Nature": nature,
        "Human-built": human_built,
        "Historical": historical,
        "Modern": modern
    }

# -------------------------------
# Search button
# -------------------------------
if st.button("Search", type="primary"):

    errors = []

    # ---------------------------
    # Flights validation
    # ---------------------------
    if flights_checked:
        if not departure:
            errors.append("✈️ Departure location is required for flights.")
        if not destination:
            errors.append("✈️ Destination is required for flights.")
        if not start_date or not end_date:
            errors.append("✈️ Trip dates are required for flights.")
        if travelers_num < 1:
            errors.append("✈️ Number of travelers is required for flights.")

    # ---------------------------
    # Hotels validation
    # ---------------------------
    if hotels_checked:
        if not destination:
            errors.append("🏨 Destination is required for hotels.")
        if not start_date or not end_date:
            errors.append("🏨 Trip dates are required for hotels.")
        if travelers_num < 1:
            errors.append("🏨 Number of travelers is required for hotels.")

    # ---------------------------
    # Activities validation
    # ---------------------------
    if activities_checked:
        if not destination:
            errors.append("🎯 Destination is required for activities.")

    # ---------------------------
    # No checkbox selected
    # ---------------------------
    if not (flights_checked or hotels_checked or activities_checked):
        errors.append("Please select at least one option: Flights, Hotels, or Activities.")

    # ---------------------------
    # Show errors OR run search
    # ---------------------------
    if errors:
        for err in errors:
            st.toast(err, icon="⚠️")   # popup-style alert
        st.stop()

    # ---------------------------
    # All good → run TPM
    # ---------------------------
    st.session_state.show_results = True
    
    start_time = time.time()
    with st.spinner("Running search..."):
        st.session_state.last_search_results = run_TPM(
            from_city=departure,
            to_city=destination,
            travelers=travelers_num,
            dates=f"{start_date} to {end_date}",
            activities_percentages=preferences,
            run_hotels_flag=hotels_checked,
            run_flights_flag=flights_checked,
            run_tripadvisor_flag=activities_checked,
        )

    elapsed = time.time() - start_time
    elapsed_rounded = round(elapsed, 1)

    # -----------------------
    # Color-coded result
    # -----------------------
    if elapsed < 30:
        st.success(f"⏱ Search completed in {elapsed_rounded} seconds")
    elif elapsed <= 40:
        st.warning(f"⏱ Search completed in {elapsed_rounded} seconds")
    else:
        st.error(f"⏱ Search completed in {elapsed_rounded} seconds")

# -------------------------------
# Display results with horizontal menu (cards)
# -------------------------------
if st.session_state.show_results and st.session_state.last_search_results:

    # Get each type of data
    trip_data = st.session_state.last_search_results.get("tripadvisor", {})
    hotels_data = st.session_state.last_search_results.get("hotels", [])
    flights_data = st.session_state.last_search_results.get("flights", [])

    # Build menu options dynamically based on available results
    available_categories = []

    if trip_data:
        available_categories.extend([key.capitalize() for key, val in trip_data.items() if val])
    if hotels_data:
        available_categories.append("Hotels")
    if flights_data:
        available_categories.append("Flights")

    if available_categories:
        st.subheader("Search Results")
        selected = option_menu(
            menu_title=None,
            options=available_categories,
            default_index=0,
            orientation="horizontal"
        )

        # Save selected category in session_state
        st.session_state.selected_category = selected
        category_key = selected.lower()

        # Determine which results to show
        if category_key in ["activities", "restaurants"]:
            results = trip_data.get(category_key, [])
        elif category_key == "hotels":
            results = hotels_data
        elif category_key == "flights":
            results = flights_data
        else:
            results = []


        if results:
            # 1️⃣ Activities → show as boxed cards
            if category_key == "activities":
                for act in results:
                    with st.container():
                        st.markdown(
                            f"""
                            <div style="
                                display: flex;
                                border: 1px solid #ddd;
                                border-radius: 12px;
                                padding: 10px;
                                margin-bottom: 15px;
                                background-color: #f9f9f9;
                                color: #111;
                                box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
                            ">
                                <div style="flex: 1; min-width: 120px;">
                                    <img src="{act.get('thumbnail', '')}" style="width: 100%; border-radius: 10px;">
                                </div>
                                <div style="flex: 2; padding-left: 15px;">
                                    <h4 style="color: #111;">{act.get('title', 'No title')}</h4>
                                    <p><b>Location:</b> {act.get('location', 'N/A')}</p>
                                    <p><b>Rating:</b> {act.get('rating', 'N/A')} ⭐ | <b>Reviews:</b> {act.get('reviews', 'N/A')}</p>
                                    <p>{act.get('description', '')[:200]}{'...' if len(act.get('description', ''))>200 else ''}</p>
                                    <p><a href="{act.get('link', '#')}" target="_blank">View More</a></p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            # 2️⃣ Restaurants → show as boxed cards
            elif category_key == "restaurants":
                for res in results:
                    with st.container():
                        st.markdown(
                            f"""
                            <div style="
                                display: flex;
                                border: 1px solid #ddd;
                                border-radius: 12px;
                                padding: 10px;
                                margin-bottom: 15px;
                                background-color: #fefefe;
                                color: #111;
                                box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
                            ">
                                <div style="flex: 1; min-width: 120px;">
                                    <img src="{res.get('thumbnail', '')}" style="width: 100%; border-radius: 10px;">
                                </div>
                                <div style="flex: 2; padding-left: 15px;">
                                    <h4 style="color: #111;">{res.get('title', 'No title')}</h4>
                                    <p><b>Location:</b> {res.get('location', 'N/A')}</p>
                                    <p><b>Rating:</b> {res.get('rating', 'N/A')} ⭐ | <b>Reviews:</b> {res.get('reviews', 'N/A')}</p>
                                    <p>{res.get('description', '')[:200]}{'...' if len(res.get('description', ''))>200 else ''}</p>
                                    <p><a href="{res.get('link', '#')}" target="_blank">View More</a></p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

            
            
        # 3️⃣ Hotels → show as boxed cards with gallery & expander
            elif category_key == "hotels":
                for hotel in results:
                    with st.container():
                        # Extract first 3 images for gallery preview
                        images = hotel.get("images", [])[:3]
                        gallery_html = "".join(
                            f'<img src="{img.get("thumbnail", "")}" style="width:32%; margin-right:2%; border-radius:8px;">'
                            for img in images
                        )

                        # Get pricing info
                        rate = hotel.get("rate_per_night", {})
                        total_rate = hotel.get("total_rate", {})
                        per_night = rate.get("lowest", "N/A")
                        total = total_rate.get("lowest", "N/A")

                        # Main hotel card
                        st.markdown(
                            f"""
                            <div style="
                                display: flex;
                                flex-direction: column;
                                border: 1px solid #ddd;
                                border-radius: 12px;
                                padding: 12px;
                                margin-bottom: 20px;
                                background-color: #1e1e1e;
                                color: #f1f1f1;
                                box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
                            ">
                                <h3 style="color:#f1f1f1;">{hotel.get('name', 'No name')}</h3>
                                <p><b>Hotel Class:</b> {hotel.get('hotel_class', 'N/A')} | <b>Rating:</b> {hotel.get('overall_rating', 'N/A')} ⭐ ({hotel.get('reviews', '0')} reviews)</p>
                                <p><b>Price per night:</b> {per_night} | <b>Total for stay:</b> {total}</p>
                                <div style="display:flex; margin-bottom:10px;">{gallery_html}</div>
                                <p>{hotel.get('description', '')[:200]}{'...' if len(hotel.get('description', ''))>200 else ''}</p>
                                <p><a href="{hotel.get('link', '#')}" target="_blank">Visit Hotel Site</a></p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # Expander for more details
                        with st.expander("More Details"):
                            # Amenities
                            amenities = hotel.get("amenities", [])
                            amenities_str = ", ".join(amenities) if amenities else "N/A"

                            # Check-in/out
                            check_in = hotel.get("check_in_time", "N/A")
                            check_out = hotel.get("check_out_time", "N/A")

                            # Nearby places
                            nearby_places = hotel.get("nearby_places", [])
                            nearby_html = ""
                            for place in nearby_places:
                                name = place.get("name", "")
                                transports = place.get("transportations", [])
                                transport_str = ", ".join(f'{t.get("type")}: {t.get("duration")}' for t in transports)
                                nearby_html += f"<li>{name} ({transport_str})</li>"

                            # Ratings breakdown
                            ratings_breakdown = hotel.get("reviews_breakdown", [])
                            ratings_html = ""
                            for r in ratings_breakdown:
                                ratings_html += f"<li>{r.get('name')}: {r.get('positive', 0)}👍 / {r.get('negative', 0)}👎 / {r.get('neutral', 0)}😐</li>"

                            st.markdown(
                                f"""
                                <p><b>Amenities:</b> {amenities_str}</p>
                                <p><b>Check-in:</b> {check_in} | <b>Check-out:</b> {check_out}</p>
                                <p><b>Nearby Places:</b></p>
                                <ul>{nearby_html}</ul>
                                <p><b>Review Breakdown:</b></p>
                                <ul>{ratings_html}</ul>
                                """,
                                unsafe_allow_html=True
                            )


            elif category_key == "flights":
                selected_flights = results.get("selected_flights", [])

                for i, selected in enumerate(selected_flights):
                    with st.container():
                        st.write("---")  # separator between flight options

                        # Determine trip type
                        trip_label = "Outbound" if i == 0 else "Return"

                        # Main container for this flight option
                        flight_type = selected.get("type", "N/A")
                        total_duration = selected.get("total_duration", "N/A")
                        airline_logo = selected.get("airline_logo", "")

                        # Flight option card with top logo + trip label
                        st.markdown(
                            f"""
                            <div style="
                                border: 2px solid #444;
                                border-radius: 16px;
                                padding: 12px;
                                margin-bottom: 20px;
                                background-color: #1e1e1e;
                                box-shadow: 3px 3px 8px rgba(0,0,0,0.5);
                            ">
                                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
                                    <div style="display:flex; align-items:center;">
                                        <img src="{airline_logo}" width="70" style="border-radius:8px; margin-right:12px;">
                                        <h4 style="margin:0; color:#f1f1f1;">{trip_label} | Total Duration: {total_duration/60:.1f} hours</h4>
                                    </div>
                                    <a href="{results.get('search_metadata', {}).get('google_flights_url', '#')}" target="_blank" style="background-color:#ff4b2b; color:white; padding:8px 16px; border-radius:8px; text-decoration:none;">View on Google Flights</a>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # Iterate each leg of the flight
                        flights = selected.get("flights", [])
                        for idx, leg in enumerate(flights, 1):
                            dep = leg.get("departure_airport", {})
                            arr = leg.get("arrival_airport", {})

                            st.markdown(
                                f"""
                                <div style="
                                    border: 1px solid #555;
                                    border-radius: 12px;
                                    padding: 12px;
                                    margin-bottom: 12px;
                                    background-color: #2a2a2a;
                                    color: #f1f1f1;
                                    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
                                    position:relative;
                                ">
                                    <div style="position:absolute; top:12px; left:12px; display:flex; align-items:center;">
                                        <img src="{leg.get('airline_logo', '')}" width="40" style="border-radius:6px; margin-right:6px;">
                                        <b>{leg.get('flight_number', 'N/A')}</b>
                                    </div>
                                    <p style="margin-top:36px;"><b>From:</b> {dep.get('name', 'N/A')} ({dep.get('id', '')}) at {dep.get('time', '')}</p>
                                    <p><b>To:</b> {arr.get('name', 'N/A')} ({arr.get('id', '')}) at {arr.get('time', '')}</p>
                                    <p>⏱️ Duration: {leg.get('duration', 'N/A')/60:.1f} hours | ✈️ Airplane: {leg.get('airplane', 'N/A')} <br> 🎫 Class: {leg.get('travel_class', 'N/A')} | 🦵 Legroom: {leg.get('legroom', 'N/A')}</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            # Extras / extensions
                            extensions = leg.get("extensions", [])
                            if extensions:
                                with st.expander(f"Extras for {leg.get('flight_number', 'N/A')}"):
                                    for ext in extensions:
                                        st.write(f"- {ext}")

                        # Layovers
                        layovers = selected.get("layovers", [])
                        if layovers:
                            with st.expander("Layovers"):
                                for stop in layovers:
                                    st.write(f"- {stop.get('name', 'N/A')} ({stop.get('duration', 'N/A')/60:.1f} hours)")

                       
# ✈️ Trip Plan Mate

An AI-powered travel planning platform that fetches real-time data for flights, hotels, and activities — all in one place.

---

## Overview

Trip Plan Mate eliminates the need to visit multiple travel sites by aggregating live data from Google Flights, Google Hotels, and TripAdvisor into a single Streamlit dashboard. Users input their trip details and preferences, and the app returns personalized, AI-analyzed results in seconds.

Built as a team MVP project at Imam Abdulrahman Bin Faisal University.

---

## Features

- **Flight Search** — Real-time outbound and return flights via Google Flights, with leg-by-leg breakdowns, layover info, and direct links to book
- **Hotel Search** — Available hotels with pricing, ratings, amenities, check-in/out times, and nearby places
- **Activities & Restaurants** — Top-rated attractions and dining options pulled from TripAdvisor
- **Experience Preferences** — Sliders to personalize results by nature vs. human-built and historical vs. modern preferences
- **AI-Powered Analysis** — Anthropic API used to analyze and summarize results intelligently
- **Interactive Dashboard** — Clean Streamlit UI with horizontal navigation between result categories

---

## Tech Stack

| Category | Technology |
|---|---|
| Frontend | Streamlit |
| Backend / AI | Anthropic API |
| Data Sources | SerpAPI (Google Flights, Google Hotels, TripAdvisor) |
| Language | Python |
| Data Handling | JSON |

---

## Project Structure

```
Trip-Plan-Mate/
├── main.py                     # Streamlit UI and app entry point
├── TPM_runner.py               # Orchestrates all pipelines
├── requirements.txt            # Dependencies
├── Flights/
│   ├── travel_flights_pipeline.py
│   ├── JSONs/                  # Sample flight data
│   └── prompts/                # AI prompt templates
├── Hotels/
│   └── travel_hotels_pipeline.py
├── hotels/
│   ├── JSONs/                  # Sample hotel data
│   └── prompts/                # AI prompt templates
└── Activities/
    ├── travel_things_pipeline.py
    └── prompts/                # AI prompt templates
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- A [SerpAPI](https://serpapi.com/) key
- An [Anthropic](https://www.anthropic.com/) API key

### Installation

```bash
# Clone the repository
git clone https://github.com/Misharywy88/Trip-Plan-Mate.git
cd Trip-Plan-Mate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the root directory and add your API keys:

```
SERPAPI_KEY=your_serpapi_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### Run the App

```bash
streamlit run main.py
```

---

## Team

Built by a 6-person team as part of a university software engineering course.

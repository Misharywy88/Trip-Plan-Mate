# ✈️ Trip Plan Mate

A travel planning app built by a 6-person university team. Instead of jumping between Google Flights, Google Hotels, and TripAdvisor, you search once and get everything in one place.

---

## What it does

You enter your destination, travel dates, budget, and number of travelers. The app fetches live flight options, available hotels, and top activities/restaurants for that location — then uses AI to analyze and surface the best matches based on your preferences.

There's also a preferences slider where you can tune results toward natural vs. human-built attractions, or historical vs. modern experiences.

---

## Tech used

- **Streamlit** — for the UI
- **SerpAPI** — to pull real-time data from Google Flights, Google Hotels, and TripAdvisor
- **Anthropic API** — for AI-powered analysis and recommendations
- **Python** — everything is Python

---

## Project structure

```
Trip-Plan-Mate/
├── main.py              # UI and app entry point
├── TPM_runner.py        # Ties all the pipelines together
├── requirements.txt
├── Flights/             # Flight search pipeline + prompts
├── hotels/              # Hotel search pipeline + prompts
└── Activities/          # Activities/restaurants pipeline + prompts
```

---

## Running it locally

You'll need a SerpAPI key and an Anthropic API key.

```bash
git clone https://github.com/Misharywy88/Trip-Plan-Mate.git
cd Trip-Plan-Mate
pip install -r requirements.txt
```

Create a `.env` file:
```
SERPAPI_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

Then run:
```bash
streamlit run main.py
```

---

Built as part of a university software engineering course at Imam Abdulrahman Bin Faisal University.

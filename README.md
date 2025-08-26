
# Trading Room Game (Streamlit)

This is a minimal Streamlit app to run your 5-stock, 5-round trading game in the trading room.

## Files
- `app.py` — the Streamlit app
- `game_config.csv` — your scenario configuration (rounds, headlines, and per-stock returns in %)
- `submissions.csv` — (created at runtime) a log of all participant submissions and scores

## How scoring works
For each stock in a round:
- **Buy** → payoff = +return
- **Sell** → payoff = −return
- **Hold** → payoff = 0

Round score is the sum across the five stocks. Cumulative score is the sum across rounds.

> Example: If CEN=+2 and you **Buy** CEN, you get +2. If you **Sell**, you get −2. If you **Hold**, you get 0.

## Edit your scenario
Open `game_config.csv` and update the `headline` and per-stock return columns (`CEN`, `FBU`, `AIR`, `FPH`, `WHS`) for each round.
- Returns are percentage points (integers or decimals are fine).
- You can add or remove rounds. Keep the same column names.
- If you change stock tickers, update the `STOCKS` list in `app.py` to match.

## Run locally
```bash
pip install streamlit pandas
streamlit run app.py
```

## In the app
1. Enter a participant name (this becomes their ID).
2. Click **Start / Continue** to load the current round.
3. Choose **Buy/Sell/Hold** for each stock and submit.
4. You’ll see per-round and cumulative performance.
5. Use **Reset current player** to start the same participant again; **Reset EVERYTHING** wipes the whole session, including the submissions log.

## Multi-participant logging
Each submission is appended to `submissions.csv` with timestamp, participant, choices, round score, and cumulative score. You can open this CSV in Excel later for a leaderboard.

## Tips
- Put this on a big display, and run the app on a laptop connected to the trading room screens.
- If you want mobile access (kiosk-style), deploy to Streamlit Community Cloud or your own server.
- To keep participants from peeking ahead, choices are locked after submission for each round.

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# ---- CONFIG ----
CONFIG_PATH = "game_config.csv"
SUBMISSIONS_PATH = "submissions.csv"
STOCKS = ["CEN", "FBU", "AIR", "FPH", "WHS"]

# ---- HELPERS ----
@st.cache_data
def load_config(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    req_cols = {"round", "headline"} | set(STOCKS)
    missing = req_cols - set(df.columns)
    if missing:
        raise ValueError(f"Config missing columns: {missing}")
    return df.sort_values("round").reset_index(drop=True)

def init_state(cfg: pd.DataFrame):
    if "cfg" not in st.session_state: st.session_state.cfg = cfg
    if "round_idx" not in st.session_state: st.session_state.round_idx = 0
    if "choices" not in st.session_state: st.session_state.choices = {}
    if "scores" not in st.session_state: st.session_state.scores = []
    if "participant" not in st.session_state: st.session_state.participant = ""
    if "locked_rounds" not in st.session_state: st.session_state.locked_rounds = set()

def action_to_sign(action: str) -> int:
    return {"Buy": 1, "Sell": -1, "Hold": 0}[action]

def calc_round_score(cfg: pd.DataFrame, r_idx: int, choices: dict) -> float:
    row = cfg.iloc[r_idx]
    return sum(action_to_sign(choices.get(s, "Hold")) * float(row[s]) for s in STOCKS)

def save_submission(cfg: pd.DataFrame, r_idx: int, score: float, participant: str, choices: dict):
    row = cfg.iloc[r_idx]
    ts = datetime.now().isoformat(timespec="seconds")
    data = {
        "timestamp": ts,
        "participant": participant,
        "round": int(row["round"]),
        "headline": row["headline"],
        **{f"choice_{s}": choices.get(s, "Hold") for s in STOCKS},
        **{f"return_{s}": float(row[s]) for s in STOCKS},
        "round_score": score,
    }
    try:
        df = pd.read_csv(SUBMISSIONS_PATH)
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    except Exception:
        df = pd.DataFrame([data])
    df["cum_score_after"] = df.groupby("participant")["round_score"].cumsum()
    df.to_csv(SUBMISSIONS_PATH, index=False)

def load_submissions() -> pd.DataFrame:
    if not Path(SUBMISSIONS_PATH).exists(): return pd.DataFrame()
    return pd.read_csv(SUBMISSIONS_PATH)

def compute_leaderboard(sub: pd.DataFrame) -> pd.DataFrame:
    if sub.empty: return pd.DataFrame(columns=["participant","latest_round","latest_score","cum_score"])
    latest = sub.sort_values(["participant","timestamp"]).groupby("participant").tail(1)
    board = latest[["participant","round","cum_score_after"]].rename(
        columns={"round":"latest_round","cum_score_after":"cum_score"}
    )
    last_scores = latest[["participant","round_score"]].rename(columns={"round_score":"latest_score"})
    board = board.merge(last_scores, on="participant")
    return board.sort_values("cum_score", ascending=False).reset_index(drop=True)

# ---- APP ----
st.set_page_config(page_title="Trading Room Game", page_icon="📈", layout="wide")
cfg = load_config(CONFIG_PATH)

# Check for spectator mode
params = st.query_params
spectator_mode = str(params.get("mode", [""])[0]).lower() in {"spectator","leaderboard"}

if spectator_mode:
    st.title("🏆 Live Leaderboard (Spectator Mode)")
    st.caption("🔄 Refresh the page (Ctrl+R / Cmd+R) to update the leaderboard.")
    sub = load_submissions()
    board = compute_leaderboard(sub)
    if board.empty:
        st.info("No submissions yet.")
    else:
        st.dataframe(board.rename(columns={
            "participant":"Participant",
            "latest_round":"Latest Round",
            "latest_score":"Last Round Score",
            "cum_score":"Cumulative Score"
        }), hide_index=True, use_container_width=True)
        st.bar_chart(board.set_index("participant")["cum_score"])
else:
    tabs = st.tabs(["🎮 Play","🏆 Leaderboard","⚙️ Admin"])

    # --- Play tab ---
    with tabs[0]:
        st.title("📈 Trading Room Game")
        init_state(cfg)

        with st.sidebar:
            st.text_input("Participant name", key="participant", placeholder="Team A")
            if st.button("Reset current player"):
                for k in ["round_idx","choices","scores","locked_rounds"]: st.session_state[k] = {} if k=="choices" else [] if k=="scores" else 0 if k=="round_idx" else set()

        if not st.session_state.participant: st.stop()
        r_idx = st.session_state.round_idx
        row = cfg.iloc[r_idx]
        st.subheader(f"Round {int(row['round'])}")
        st.write(f"**Headline:** {row['headline']}")

        locked = r_idx in st.session_state.locked_rounds
        cols = st.columns(3)
        for i,s in enumerate(STOCKS):
            default = st.session_state.choices.get(r_idx,{}).get(s,"Hold")
            with cols[i%3]:
                st.selectbox(f"{s} action",["Buy","Sell","Hold"],
                    index=["Buy","Sell","Hold"].index(default),disabled=locked,key=f"{r_idx}_{s}")

        if not locked and st.button("Submit choices",type="primary"):
            st.session_state.choices[r_idx] = {s:st.session_state[f"{r_idx}_{s}"] for s in STOCKS}
            score = calc_round_score(cfg,r_idx,st.session_state.choices[r_idx])
            st.session_state.scores.append(score)
            st.session_state.locked_rounds.add(r_idx)
            save_submission(cfg,r_idx,score,st.session_state.participant,st.session_state.choices[r_idx])
            st.success(f"Round {row['round']} submitted. Score {score:+.1f}")

    # --- Leaderboard tab ---
    with tabs[1]:
        st.title("🏆 Live Leaderboard")
        st.caption("🔄 Refresh the page (Ctrl+R / Cmd+R) to update the leaderboard.")
        sub = load_submissions()
        board = compute_leaderboard(sub)
        if board.empty:
            st.info("No submissions yet.")
        else:
            st.dataframe(board.rename(columns={
                "participant":"Participant",
                "latest_round":"Latest Round",
                "latest_score":"Last Round Score",
                "cum_score":"Cumulative Score"
            }), hide_index=True, use_container_width=True)
            st.bar_chart(board.set_index("participant")["cum_score"])

    # --- Admin tab ---
    with tabs[2]:
        st.write("⚙️ Admin tools here")
        if st.button("Clear submissions.csv"):
            Path(SUBMISSIONS_PATH).unlink(missing_ok=True)
            st.success("Cleared.")

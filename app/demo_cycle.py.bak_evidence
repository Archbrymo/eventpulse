import json
import os
import time
from datetime import datetime

import streamlit as st


DEMO_STATE_FILE = ".eventpulse_demo_state.json"

DEMO_STEPS = [
    ("UNIVERSE", "1,173 Reality assets discovered"),
    ("SCREEN", "50 candidates passed fast screen"),
    ("RESEARCH", "10 candidates moved to evidence research"),
    ("QWEN", "Investment Council evaluating catalysts, valuation and market"),
    ("RISK", "Deterministic risk gate reviewing proposed actions"),
    ("EXECUTION", "Paper execution simulation ready"),
    ("THESIS", "Thesis tracking updated"),
]


def _load_demo_state():
    """Restore the last demo checkpoint from disk."""

    if not os.path.exists(DEMO_STATE_FILE):
        return {
            "session_id": "",
            "status": "NEW",
            "completed_step": 0,
            "events": [],
            "updated_at": "",
        }

    try:
        with open(DEMO_STATE_FILE, "r") as file:
            state = json.load(file)

        if not isinstance(state, dict):
            raise ValueError("Invalid demo state")

        state.setdefault("session_id", "")
        state.setdefault("status", "NEW")
        state.setdefault("completed_step", 0)
        state.setdefault("events", [])
        state.setdefault("updated_at", "")

        return state

    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "session_id": "",
            "status": "NEW",
            "completed_step": 0,
            "events": [],
            "updated_at": "",
        }


def _save_demo_state(state):
    """Atomically persist the current demo checkpoint."""

    state["updated_at"] = datetime.now().isoformat()

    temporary_file = DEMO_STATE_FILE + ".tmp"

    with open(temporary_file, "w") as file:
        json.dump(
            state,
            file,
            indent=2,
        )

    os.replace(
        temporary_file,
        DEMO_STATE_FILE,
    )


def _new_session_id():
    return datetime.now().strftime(
        "demo-%Y%m%d-%H%M%S"
    )


def _restore_into_session():
    """Load disk checkpoint into Streamlit session state."""

    if st.session_state.get("demo_state_loaded"):
        return

    state = _load_demo_state()

    st.session_state.demo_state = state
    st.session_state.demo_events = state.get(
        "events",
        [],
    )
    st.session_state.demo_running = False
    st.session_state.demo_state_loaded = True


def _render_demo_panel(placeholder, events, complete=False):
    """Render the terminal-style demo progress panel."""

    with placeholder.container():

        if complete:
            st.markdown(
                """
                <div class="ep-demo-panel ep-demo-complete">
                    <div class="ep-section-title">
                        DEMO CYCLE COMPLETE
                    </div>

                    <div class="ep-section-subtitle">
                        EVENTPULSE AUTONOMOUS PIPELINE · PAPER
                    </div>

                    <div class="ep-demo-result">
                        <span>1,173</span> Reality
                        →
                        <span>50</span> Screen
                        →
                        <span>10</span> Evidence
                        →
                        <span>QWEN</span>
                        →
                        <span>RISK</span>
                        →
                        <span>PAPER</span>
                    </div>

                    <div class="ep-demo-safe">
                        NO LIVE ORDERS · NO PORTFOLIO CHANGES
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            return

        st.markdown(
            """
            <div class="ep-demo-panel">
                <div class="ep-section-title">
                    AUTONOMOUS DEMO CYCLE
                </div>

                <div class="ep-section-subtitle">
                    PAPER · SIMULATION · NO ORDERS PLACED
                </div>
            """,
            unsafe_allow_html=True,
        )

        for index, event in enumerate(events, start=1):

            current = index == len(events)

            status = (
                "RUNNING"
                if current
                else "COMPLETE"
            )

            st.markdown(
                f"""
                <div class="ep-demo-row">
                    <span class="ep-demo-index">
                        {index:02d}
                    </span>

                    <span class="ep-demo-stage">
                        {event["stage"]}
                    </span>

                    <span class="ep-demo-message">
                        {event["message"]}
                    </span>

                    <span class="ep-demo-status">
                        {status}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )


def run_demo_cycle():
    """
    Safe hackathon demonstration.

    This function does NOT:
    - place live orders
    - modify the portfolio
    - write trades
    - modify the trading database

    It only advances and persists the demonstration pipeline.
    """

    if st.session_state.get(
        "demo_running",
        False,
    ):
        return

    _restore_into_session()

    st.session_state.demo_running = True

    state = st.session_state.demo_state

    # Resume an existing interrupted session.
    completed_step = int(
        state.get(
            "completed_step",
            0,
        )
    )

    events = list(
        state.get(
            "events",
            [],
        )
    )

    # If there is no session, create one.
    if not state.get("session_id"):
        state["session_id"] = _new_session_id()
        state["status"] = "RUNNING"

    placeholder = st.empty()

    try:
        # Continue from the first unfinished stage.
        for index in range(
            completed_step,
            len(DEMO_STEPS),
        ):
            stage, message = DEMO_STEPS[index]

            timestamp = datetime.now().strftime(
                "%H:%M:%S"
            )

            event = {
                "time": timestamp,
                "stage": stage,
                "message": message,
                "status": "ACTIVE",
            }

            events.append(event)

            state["events"] = events
            state["status"] = "RUNNING"

            # Save BEFORE displaying the active stage.
            _save_demo_state(state)

            _render_demo_panel(
                placeholder,
                events,
            )

            time.sleep(0.65)

            # Mark this stage permanently complete.
            events[-1]["status"] = "COMPLETE"

            state["events"] = events
            state["completed_step"] = index + 1

            _save_demo_state(state)

            _render_demo_panel(
                placeholder,
                events,
            )

        # Entire pipeline completed.
        state["status"] = "COMPLETE"
        state["completed_step"] = len(
            DEMO_STEPS
        )
        state["events"] = events

        _save_demo_state(state)

        _render_demo_panel(
            placeholder,
            events,
            complete=True,
        )

    finally:
        st.session_state.demo_running = False


def reset_demo_cycle():
    """Start a completely fresh demonstration session."""

    state = {
        "session_id": _new_session_id(),
        "status": "NEW",
        "completed_step": 0,
        "events": [],
        "updated_at": "",
    }

    _save_demo_state(state)

    st.session_state.demo_state = state
    st.session_state.demo_events = []
    st.session_state.demo_running = False


def demo_button():
    _restore_into_session()

    state = st.session_state.demo_state

    status = state.get(
        "status",
        "NEW",
    )

    completed_step = int(
        state.get(
            "completed_step",
            0,
        )
    )

    running = st.session_state.get(
        "demo_running",
        False,
    )

    # Completed sessions get a new-run button.
    if status == "COMPLETE" or completed_step >= len(DEMO_STEPS):

        if st.button(
            "↻ RUN DEMO AGAIN",
            key="run_demo_again",
            use_container_width=True,
            disabled=running,
        ):
            reset_demo_cycle()
            st.rerun()

        return

    # Existing checkpoint = resume.
    if completed_step > 0:

        button_label = "▶ CONTINUE DEMO CYCLE"

    else:

        button_label = "▶ RUN DEMO CYCLE"

    if st.button(
        button_label,
        key="run_demo_cycle",
        use_container_width=True,
        disabled=running,
    ):
        run_demo_cycle()
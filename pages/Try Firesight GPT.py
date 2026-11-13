import random

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import assistant
import scenarios
from storage import _setting, load_user_profile

st.set_page_config(page_title="FIRESight GPT", page_icon="💬", layout="wide")


def net_worth_figure(series, start_age, title):
    fig = go.Figure()
    for label, results, color in series:
        bands = scenarios.net_worth_bands(results, (10, 50, 90))
        ages = start_age + (np.arange(len(bands[50])) + 1) / 12
        fig.add_trace(go.Scatter(x=ages, y=bands[90], line_color="rgba(0,0,0,0)", showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=ages, y=bands[10], fill="tonexty", fillcolor=color.replace("1)", "0.15)"),
                                 line_color="rgba(0,0,0,0)", name=f"{label} 10th-90th pct"))
        fig.add_trace(go.Scatter(x=ages, y=bands[50], line=dict(color=color, width=3), name=f"{label} median"))
    fig.update_layout(title=title, xaxis_title="Age", yaxis_title="Net Worth ($)", hovermode="x unified")
    return fig


def build_figures(payload, profile):
    """Turn a tool result into the charts Claude asked for."""
    start_age = profile.get("age", 0)
    figures = []
    charts = set(payload.get("charts", []))
    if payload["kind"] == "run":
        summary = payload["summary"]
        if "net_worth" in charts:
            figures.append(net_worth_figure([("Plan", payload["results"], "rgba(255, 107, 107, 1)")], start_age,
                                            "Net Worth Projection"))
        if "retirement_age_distribution" in charts and summary["retirement_ages"]:
            fig = px.histogram(x=summary["retirement_ages"], nbins=20)
            fig.update_layout(title="Retirement Age Distribution", xaxis_title="Retirement Age", yaxis_title="Count")
            figures.append(fig)
        if "budget_breakdown" in charts and profile.get("budget_items"):
            per_month = {"monthly": 1, "weekly": 4.33, "annual": 1 / 12}
            budget = pd.DataFrame([{"item": b.get("name") or b.get("type"),
                                    "monthly": b.get("value", 0) * per_month.get(b.get("frequency", "monthly"), 1)}
                                   for b in profile["budget_items"]])
            figures.append(px.pie(budget, values="monthly", names="item", title="Monthly Budget Breakdown"))
        if "investment_allocation" in charts:
            alloc = pd.DataFrame([{"vehicle": name, "ratio": profile.get(key, 0)}
                                  for name, key in scenarios.ALLOCATION_KEYS.items() if profile.get(key, 0)])
            if not alloc.empty:
                figures.append(px.pie(alloc, values="ratio", names="vehicle", title="Investment Allocation"))
    else:
        if "net_worth_comparison" in charts:
            figures.append(net_worth_figure([("Current", payload["baseline_results"], "rgba(99, 110, 250, 1)"),
                                             ("Scenario", payload["scenario_results"], "rgba(255, 107, 107, 1)")],
                                            start_age, "Net Worth Comparison"))
        if "retirement_age_comparison" in charts:
            fig = go.Figure()
            for label, summary in (("Current", payload["baseline"]), ("Scenario", payload["scenario"])):
                if summary["retirement_ages"]:
                    fig.add_trace(go.Histogram(x=summary["retirement_ages"], name=label, opacity=0.7))
            fig.update_layout(title="Retirement Age Distribution", barmode="overlay",
                              xaxis_title="Retirement Age", yaxis_title="Count")
            figures.append(fig)
    return figures


def clear_conversation():
    st.session_state.pop("gpt_messages", None)
    st.session_state.pop("gpt_display", None)


def main():
    st.title("FIRESight GPT")

    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not logged in.")
        st.page_link("pages/Create Account and Log in.py", label="Log in or try a demo profile", icon="🔐")
        return

    user_data = load_user_profile(user_id)
    if not user_data:
        st.error("Failed to load user profile.")
        return

    if not (_setting("ANTHROPIC_API_KEY") or (_setting("FIRESIGHT_LLM_PROVIDER") or "").lower() == "bedrock"):
        st.info("FIRESight GPT needs Claude. Add `ANTHROPIC_API_KEY` to `.streamlit/secrets.toml` (or set "
                "`FIRESIGHT_LLM_PROVIDER = \"bedrock\"` to use Amazon Bedrock), then reload this page.")
        return

    st.caption("Ask about your plan in plain English. FIRESight GPT runs the simulator to answer, "
               "e.g. *\"What if I cut dining out in half and put 10% more into index funds?\"*")

    # The API conversation (with tool calls) and what we show on screen are kept separately
    st.session_state.setdefault("gpt_messages", [])
    st.session_state.setdefault("gpt_display", [])
    st.session_state.setdefault("gpt_seed", random.randrange(2**31))

    if st.button("Clear Conversation"):
        clear_conversation()
        st.rerun()

    for entry in st.session_state.gpt_display:
        with st.chat_message(entry["role"]):
            st.markdown(entry["text"].replace("$", "\\$"))
            for fig in entry.get("figures", []):
                st.plotly_chart(fig, width="stretch")

    if prompt := st.chat_input("What would you like to know about your FIRE journey?"):
        st.session_state.gpt_display.append({"role": "user", "text": prompt})
        st.session_state.gpt_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt.replace("$", "\\$"))

        with st.chat_message("assistant"):
            figures = []

            def show(payload):
                for fig in build_figures(payload, user_data):
                    figures.append(fig)
                    st.plotly_chart(fig, width="stretch")

            history_length = len(st.session_state.gpt_messages) - 1
            try:
                with st.spinner("Thinking..."):
                    create = assistant.make_create(_setting, user_data)
                    reply = assistant.run_turn(create, st.session_state.gpt_messages, user_data,
                                               on_tool_result=show, seed=st.session_state.gpt_seed)
            except Exception as e:
                # roll the conversation back to before this question so it can be retried
                del st.session_state.gpt_messages[history_length:]
                st.session_state.gpt_display.pop()
                st.error(f"Couldn't reach Claude: {e}")
                return
            st.markdown(reply.replace("$", "\\$"))
        st.session_state.gpt_display.append({"role": "assistant", "text": reply, "figures": figures})


if __name__ == "__main__":
    main()

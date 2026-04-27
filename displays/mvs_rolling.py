import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from computations.mvs_rolling import (
    compute_performance_with_rolling_window,
)

from tools.data_management import get_sp500_data


def display_rolling_window_performance():
    st.header("Performance Analysis with Rolling Window")
    st.info(
        "Analyze portfolio performance over time using a rolling window approach and compare it with the S&P 500."
    )

    if "final_combined_weights" not in st.session_state:
        st.warning(
            "Make sure you have completed the previous steps named : Weights with only Min Var before analyzing the performance."
        )
        return

    slider_risk_free_value = st.session_state.get(
        "mvs_rolling_risk_free_rate", 0.04
    )
    slider_risk_aversion_value = st.session_state.get(
        "mvs_rolling_risk_aversion", 3.0
    )

    risk_free_rate = st.slider(
        "Adjust Risk-Free Rate ",
        0.0,
        0.09,
        slider_risk_free_value,
        0.01,
    )
    risk_aversion = st.slider(
        "Select Risk Aversion ",
        1.00,
        5.0,
        slider_risk_aversion_value,
        1.0,
    )

    if st.button("Confirm and Compute"):
        # Update session state with slider values
        st.session_state["mvs_rolling_risk_free_rate"] = risk_free_rate
        st.session_state["mvs_rolling_risk_aversion"] = risk_aversion

        with st.spinner("Computing rolling window performance..."):
            # Perform computation
            (
                portfolio_with_risk_free_df,
                cumulative_returns_yearly,
                annualized_returns_yearly,
            ) = compute_performance_with_rolling_window(risk_free_rate, risk_aversion)

            # Store the results in session state
            st.session_state["portfolio_with_risk_free_df"] = (
                portfolio_with_risk_free_df
            )
            st.session_state["cumulative_returns_yearly"] = cumulative_returns_yearly
            st.session_state["annualized_returns_yearly"] = annualized_returns_yearly

        st.success("Computation completed!")

    if (
        "portfolio_with_risk_free_df" not in st.session_state
        or "cumulative_returns_yearly" not in st.session_state
        or "annualized_returns_yearly" not in st.session_state
    ):
        st.warning(
            "Please confirm the slider values to compute the portfolio performance."
        )
        return

    portfolio_with_risk_free_df = st.session_state["portfolio_with_risk_free_df"]
    cumulative_returns_yearly = st.session_state["cumulative_returns_yearly"]
    annualized_returns_yearly = st.session_state["annualized_returns_yearly"]

    sp500_data = get_sp500_data(
        portfolio_with_risk_free_df.index[0], portfolio_with_risk_free_df.index[-1]
    )

    # === Graph 1: Portfolio Cumulative Returns ===
    st.subheader("1. Portfolio Cumulative Returns")
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    ax3.plot(
        portfolio_with_risk_free_df.index,
        cumulative_returns_yearly,
        label="Portfolio Cumulative Return",
        color="blue",
    )
    ax3.set_title("Portfolio Cumulative Returns")
    ax3.set_xlabel("Date")
    ax3.set_ylabel("Cumulative Return")
    ax3.legend()
    ax3.grid()
    st.pyplot(fig3)

    # === Graph 2: Pie Chart for Portfolio Weights at a Specific Date ===
    st.subheader("2. Portfolio Allocation on Selected Date")

    # Assuming portfolio_with_risk_free_df is already loaded and contains pre-computed weights
    portfolio_with_risk_free_df.index = pd.to_datetime(
        portfolio_with_risk_free_df.index
    )

    # Resample the data to quarterly frequency for fewer slider options
    # Ensure that the latest date (2024-10-31) is the last date in the slider
    quarterly_data = portfolio_with_risk_free_df.resample("QE").last()
    latest_date = pd.Timestamp("2024-10-31")
    if latest_date not in quarterly_data.index:
        # Include the latest date manually if it's missing from the resampled data
        quarterly_data.loc[latest_date] = portfolio_with_risk_free_df.loc[latest_date]

    # Sort the data to maintain chronological order
    quarterly_data = quarterly_data.sort_index()

    # Define colors for the assets
    color_map = {
        "gold": "#FFDDC1",
        "oil": "#FFABAB",
        "gas": "#FFC3A0",
        "copper": "#D5AAFF",
        "aluminium": "#85E3FF",
        "wheat": "#FFFFB5",
        "sugar": "#FF9CEE",
        "Risk-Free Asset": "#B9FBC0",
    }

    # Filter function to remove values below 0.01%
    def filter_small_allocations(data):
        return data[data >= 0.0001]

    # Initialize the Plotly figure
    fig = go.Figure()

    # Create a list of frames for the slider (one per date)
    frames = []
    for date in quarterly_data.index:
        weights = filter_small_allocations(quarterly_data.loc[date].dropna())
        frames.append(
            go.Frame(
                data=[
                    go.Pie(
                        labels=weights.index,
                        values=weights.values,
                        hole=0.4,  # Donut chart effect
                        marker=dict(
                            colors=[color_map[asset] for asset in weights.index]
                        ),
                    )
                ],
                name=str(date.date()),
            )
        )

    # Add the first frame (initial state) to the figure
    initial_date = quarterly_data.index[0]
    initial_weights = filter_small_allocations(
        quarterly_data.loc[initial_date].dropna()
    )
    fig.add_trace(
        go.Pie(
            labels=initial_weights.index,
            values=initial_weights.values,
            hole=0.4,
            marker=dict(colors=[color_map[asset] for asset in initial_weights.index]),
        )
    )

    # Set up the layout for the figure
    fig.update_layout(
        title="Portfolio Allocation Over Time (Quarterly Data, Filtered)",
        annotations=[
            dict(text="Portfolio", x=0.5, y=0.5, font_size=20, showarrow=False)
        ],
        sliders=[
            {
                "active": 0,
                "currentvalue": {
                    "prefix": "Date: ",
                    "xanchor": "center",
                    "font": {"size": 14},
                },
                "pad": {"t": 20},  # Slight padding between chart and slider
                "len": 1.0,  # Slider spans the full figure width
                "x": 0,  # Align slider to the left
                "steps": [
                    {
                        "method": "animate",
                        "args": [
                            [str(date.date())],
                            {
                                "frame": {"duration": 500, "redraw": True},
                                "mode": "immediate",
                            },
                        ],
                        "label": str(date.date()),
                    }
                    for date in quarterly_data.index
                ],
            }
        ],
    )

    # Add frames to the figure for the slider
    fig.frames = frames

    # Adjust layout for better alignment and a smaller chart size
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=50),  # Reduce margins to avoid excessive spacing
        height=400,  # Smaller chart height
        showlegend=True,
        template="plotly_white",
    )

    # Display the Plotly chart in Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # === Graph 2: Annualized Returns ===
    st.subheader("3. Annualized Portfolio Returns by Year")
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    annualized_returns_yearly.plot(
        kind="bar", ax=ax2, color="blue", alpha=0.7, label="Portfolio"
    )
    ax2.set_title("Annualized Returns by Year")
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Annualized Return")
    ax2.legend()
    ax2.grid(axis="y")
    st.pyplot(fig2)

    # === Graph 4: Comparison of Cumulative Returns ===
    st.subheader("4. Portfolio vs S&P 500 Cumulative Returns")
    fig4, ax4 = plt.subplots(figsize=(12, 6))
    ax4.plot(
        portfolio_with_risk_free_df.index,
        cumulative_returns_yearly,
        label="Portfolio Cumulative Return",
        color="blue",
    )
    ax4.plot(
        sp500_data.index,
        sp500_data["Cumulative_Return"],
        label="S&P 500 Cumulative Return",
        color="orange",
    )
    ax4.set_title("Portfolio vs S&P 500 Cumulative Returns")
    ax4.set_xlabel("Date")
    ax4.set_ylabel("Cumulative Return")
    ax4.legend()
    ax4.grid()
    st.pyplot(fig4)
    st.session_state["portfolio_with_risk_free_df"] = portfolio_with_risk_free_df

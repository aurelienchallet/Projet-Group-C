import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from computations.black_litterman import compute_black_litterman_portfolio
from tools.data_management import get_sp500_data


def display_black_litterman_performance():
    st.header("Black-litterman Performance Analysis ")
    st.info(
        "Analyze Black-litterman portfolio performance over time and compare it with the S&P 500."
    )

    if "final_combined_weights" not in st.session_state:
        st.warning(
            "Make sure you have completed the 2 previous steps before analyzing the performance."
        )
        return

    slider_risk_free_value = st.session_state.get("bl_risk_free_rate", 0.04)
    slider_risk_aversion_value = st.session_state.get("bl_risk_aversion", 3.0)

    risk_free_rate = st.slider(
        "Adjust Risk-Free Rate ", 0.0, 0.09, slider_risk_free_value, 0.01
    )
    risk_aversion = st.slider(
        "Select Risk Aversion ", 1.00, 5.0, slider_risk_aversion_value, 1.0
    )

    if st.button("Confirm and Compute"):
        # Update session state with slider values
        st.session_state["bl_risk_free_rate"] = risk_free_rate
        st.session_state["bl_risk_aversion"] = risk_aversion

        with st.spinner("Computing rolling window performance..."):
            # Perform computation
            (
                portfolio_with_risk_free_df_bl,
                cumulative_returns,
                annualized_returns_df,
            ) = compute_black_litterman_portfolio(risk_free_rate, risk_aversion)

            # Store the results in session state
            st.session_state["portfolio_with_risk_free_df_bl"] = (
                portfolio_with_risk_free_df_bl
            )
            st.session_state["cumulative_returns"] = cumulative_returns
            st.session_state["annualized_returns_df"] = annualized_returns_df

        st.success("Computation completed!")

    if (
        "portfolio_with_risk_free_df_bl" not in st.session_state
        or "cumulative_returns" not in st.session_state
        or "annualized_returns_df" not in st.session_state
    ):
        st.warning(
            "Please confirm the slider values to compute the portfolio performance."
        )
        return

    portfolio_with_risk_free_df_bl = st.session_state["portfolio_with_risk_free_df_bl"]
    cumulative_returns = st.session_state["cumulative_returns"]
    annualized_returns_df = st.session_state["annualized_returns_df"]

    sp500_data = get_sp500_data(
        portfolio_with_risk_free_df_bl.index[0],
        portfolio_with_risk_free_df_bl.index[-1],
    )

    st.subheader("1.Portfolio Cumulative Returns")

    # Create a single plot
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot S&P 500 cumulative returns

    ax.plot(cumulative_returns, label="Black-litterman portfolio", color="green")
    # Set titles and labels
    ax.set_title("Black-litterman portfolio ")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Returns")
    ax.legend()
    ax.grid()

    # Display the plot in Streamlit
    st.pyplot(fig)

    # === Graph 2: Pie Chart for Portfolio Weights at a Specific Date ===
    st.subheader("2. Portfolio Allocation on Selected Date")

    # Assuming portfolio_with_risk_free_df is already loaded and contains pre-computed weights
    portfolio_with_risk_free_df_bl.index = pd.to_datetime(
        portfolio_with_risk_free_df_bl.index
    )

    # Resample the data to quarterly frequency for fewer slider options
    quarterly_data = portfolio_with_risk_free_df_bl.resample("QE").last()

    # Clean column names by removing "Price_" prefix
    quarterly_data.columns = [
        col.replace("Price_", "") for col in quarterly_data.columns
    ]

    # Define colors for the assets
    color_map = {
        "gold": "#FFDDC1",  # Soft peach
        "oil": "#FFABAB",  # Light coral
        "gas": "#FFC3A0",  # Pastel orange
        "copper": "#D5AAFF",  # Lavender
        "aluminium": "#85E3FF",  # Light sky blue
        "wheat": "#FFFFB5",  # Mint green
        "sugar": "#FF9CEE",  # Light pink
        "Risk-Free Asset": "#B9FBC0",  # Soft yellow
    }

    # Filter function to remove values below 0.01%
    def filter_small_allocations(data):
        return data[data >= 0.0001]

    # Initialize the Plotly figure
    fig = go.Figure()

    # Create a list of frames for the slider (one per date)
    frames = []
    for date in quarterly_data.index:
        weights = filter_small_allocations(quarterly_data.loc[date])
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
    initial_weights = filter_small_allocations(quarterly_data.loc[initial_date])
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

    # === Graph 3: Annualized Returns ===
    st.subheader("3. Annualized Portfolio Returns by Year")
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    annualized_returns_df.plot(
        kind="bar", ax=ax2, color="green", alpha=0.7, label="Portfolio"
    )
    ax2.set_title("Annualized Returns by Year")
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Annualized Return")
    ax2.legend()
    ax2.grid(axis="y")
    st.pyplot(fig2)

    st.subheader("4.Portfolio vs S&P 500 Cumulative Returns")

    # Create a single plot
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot S&P 500 cumulative returns
    ax.plot(
        sp500_data.index,
        sp500_data["Cumulative_Return"],
        label="S&P 500 ",
        color="orange",
    )
    ax.plot(cumulative_returns, label="Black-litterman portfolio", color="green")
    # Set titles and labels
    ax.set_title("Black-litterman portfolio vs S&P 500")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Returns")
    ax.legend()
    ax.grid()

    # Display the plot in Streamlit
    st.pyplot(fig)

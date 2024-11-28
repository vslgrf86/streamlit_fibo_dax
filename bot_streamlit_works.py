import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Function to calculate Fibonacci levels
def calculate_fibonacci_levels(high, low):
    retracement_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
    extension_ratios = [1.0, 1.236, 1.382, 1.5, 1.618, 1.786, 2.0, 2.618]

    retracement_levels = {
        f"Retracement {int(ratio * 100)}%": low + (high - low) * ratio
        for ratio in retracement_ratios
    }
    extension_levels = {
        f"Extension {int(ratio * 100)}%": high + (high - low) * (ratio - 1)
        for ratio in extension_ratios
    }
    return {**retracement_levels, **extension_levels}

# Function to search for a value within a tolerance
def search_value_in_columns(data, value, tolerance, cols_to_search):
    condition = None
    
    for col in cols_to_search:
        if pd.api.types.is_numeric_dtype(data[col]):  # If column is numeric
            col_condition = (data[col] >= value - tolerance) & (data[col] <= value + tolerance)
        else:
            continue  # Skip non-numeric columns

        condition = col_condition if condition is None else condition | col_condition  # Combine conditions

    return data[condition] if condition is not None else pd.DataFrame()

# Streamlit app
def main():
    st.title("Fibonacci Levels Calculator")
    st.write("Fetch stock data and calculate Fibonacci retracement and extension levels.")

    # Input ticker and fetch data
    ticker = st.text_input("Enter the stock ticker (e.g., ^GDAXI for DAX):", value="^GDAXI")
    period = st.selectbox("Select data period", options=["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    interval = st.selectbox("Select data interval", options=["1d", "1wk", "1mo"], index=0)

    if ticker:
        try:
            # Fetch data
            stock_data = yf.download(ticker, period=period, interval=interval)

            if stock_data.empty:
                st.error("No data available for the given ticker.")
                return

            # Reset index and clean data
            stock_data.reset_index(inplace=True)
            stock_data['Date'] = stock_data['Date'].dt.date  # Remove timestamp from date
            
            # Calculate percentage change for Close
            stock_data['% Difference'] = stock_data['Close'].pct_change() * 100
            
            # Add Price Difference (High - Low) with two decimals
            stock_data['Price Difference'] = (stock_data['High'] - stock_data['Low']).round(2)
            
            # Calculate Volume Difference in millions (absolute volume difference in millions)
            stock_data['Volume Difference'] = (stock_data['Volume'].diff() / 1e6).round(2)  # Difference in millions
            stock_data['% Volume Difference'] = stock_data['Volume'].pct_change() * 100
            stock_data['% Volume Difference'] = stock_data['% Volume Difference'].round(2)
            
            # Format all numeric columns to two decimal places
            for col in stock_data.select_dtypes(include='number').columns:
                stock_data[col] = stock_data[col].round(2)

            # Display data preview with dynamic width
            st.subheader("Data Preview")
            
            # Format percentage difference columns for display
            if '% Difference' in stock_data.columns:
                stock_data['% Difference'] = stock_data['% Difference'].map(lambda x: f"{x:.2f}%")
            if '% Volume Difference' in stock_data.columns:
                stock_data['% Volume Difference'] = stock_data['% Volume Difference'].map(lambda x: f"{x:.2f}%")
            
            # Display the dataframe with dynamic width (fits to container)
            st.dataframe(stock_data, use_container_width=True)

            # Get numeric columns (High, Low, Close, Volume)
            available_cols = [col for col in stock_data.columns if pd.api.types.is_numeric_dtype(stock_data[col])]
            
            # Add "All" option to column selection
            cols_to_search = st.multiselect(
                "Select columns to search in",
                options=["All"] + available_cols,
                default=["All"] + available_cols
            )

            # If "All" is selected, use all numeric columns
            if "All" in cols_to_search:
                cols_to_search = available_cols

            if not cols_to_search:
                st.error("Please select at least one column.")
                st.stop()

            # Enter value and tolerance
            value_to_search = st.number_input("Enter the value to search for (daily High or Low):")
            tolerance = st.slider(
                "Select the tolerance:", 
                min_value=0.0, 
                max_value=50.0, 
                value=10.0, 
                step=5.0
            )

            # Search for matches
            result = search_value_in_columns(stock_data, value_to_search, tolerance, cols_to_search)
            st.subheader("Search Results")
            if result.empty:
                st.write("No matches found.")
            else:
                # Display the search result dataframe with dynamic width
                st.dataframe(result, use_container_width=True)

                # Select a row for Fibonacci calculation
                row_index = st.selectbox("Select the row index for Fibonacci calculation", options=result.index)
                selected_row = result.loc[row_index]

                # Extract scalar values for high and low prices
                high_price = selected_row['High']
                low_price = selected_row['Low']

                if isinstance(high_price, pd.Series):
                    high_price = high_price.iloc[0]

                if isinstance(low_price, pd.Series):
                    low_price = low_price.iloc[0]

                # Calculate Fibonacci levels
                fib_levels = calculate_fibonacci_levels(high_price, low_price)

                # Format Fibonacci levels to two decimal places
                formatted_fib_levels = {key: f"{value:.2f}" for key, value in fib_levels.items()}
                fib_df = pd.DataFrame(formatted_fib_levels.items(), columns=["Level", "Price"])

                # Display Fibonacci levels dataframe with dynamic width
                st.subheader("Fibonacci Levels")
                st.write("Note: Golden ratio 61.8")
                st.dataframe(fib_df, use_container_width=True)

                # Plotting the stock data with Fibonacci levels
                fig = go.Figure()

                # Plot stock's closing price
                fig.add_trace(go.Candlestick(
                    x=stock_data['Date'],
                    open=stock_data['Open'],
                    high=stock_data['High'],
                    low=stock_data['Low'],
                    close=stock_data['Close'],
                    name='Candlestick'
                ))

                # Add Fibonacci lines
                for level, price in fib_levels.items():
                    fig.add_hline(y=price, line_dash="dash", annotation_text=level, annotation_position="top right")

                fig.update_layout(title=f'{ticker} Fibonacci Levels',
                                  xaxis_title='Date',
                                  yaxis_title='Price',
                                  template='plotly_white')

                st.plotly_chart(fig)

        except ValueError as ve:
            st.error(f"Invalid value entered: {ve}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()

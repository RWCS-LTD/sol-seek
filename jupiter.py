import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Function to get the top tokens from CoinGecko (pagination to get top 1000)
def get_top_tokens():
    tokens = []
    for page in range(1, 5):  # Fetch 250 tokens per page, 4 pages = 1000 tokens
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 250,
            "page": page,
            "sparkline": False,
            "price_change_percentage": "7d,30d"  # Fetch 7-day and 30-day price change
        }
        response = requests.get("https://api.coingecko.com/api/v3/coins/markets", params=params)
        
        # Try to parse the response as JSON
        try:
            page_tokens = response.json()
        except ValueError:
            st.error("Failed to parse API response.")
            return []
        
        # Filter out stablecoins, but only if the token is a valid dictionary with a 'symbol' key
        stablecoins = ["usdt", "usdc", "dai", "busd", "ust"]
        filtered_tokens = [
            token for token in page_tokens 
            if isinstance(token, dict) and 'symbol' in token and token['symbol'] not in stablecoins
        ]
        
        tokens.extend(filtered_tokens)
    
    return tokens

# Function to calculate Potential Gains (e.g., x2, x5, etc.)
def calculate_potential_gains(current_price, ath_price):
    if current_price > 0:
        return ath_price / current_price  # This calculates the potential gain as a multiple
    return 0  # Avoid division by zero

# Main Streamlit app function
def main():
    st.title("Top Crypto Assets: Potential Gains, 7D Price Change, MC/Volume Ratio, and Final Selection")
    st.write("This app fetches the top 1000 tokens by market cap (excluding stablecoins) and ranks them by potential gains from the current price to ATH, 7-day price change, market cap/volume ratio, and identifies any assets appearing in the first 3 categories.")

    # Set sliders with minimum values of 100,000, but keep the original default values
    market_cap_min = st.slider('Minimum Market Cap (in USD)', 100000, 10000000000, 100000000)  # Default 100M
    market_cap_max = st.slider('Maximum Market Cap (in USD)', 100000, 10000000000, 10000000000)  # Default 10B
    volume_min = st.slider('Minimum 24h Volume (in USD)', 100000, 1000000000, 1000000)  # Default 1M

    # Add a button to trigger data fetching and filtering
    if st.button('Show Results'):
        # Fetch tokens and apply filters
        with st.spinner('Fetching data...'):
            top_tokens = get_top_tokens()

        # Display how many tokens were fetched from the API
        st.write(f"Total tokens fetched: {len(top_tokens)}")
        
        # Prepare a list to store token data
        results = []

        # Process token data
        for token in top_tokens:
            token_name = token['name']
            token_symbol = token['symbol']
            current_price = token['current_price']
            ath_price = token['ath']
            volume = token['total_volume']
            market_cap = token['market_cap']
            price_change_7d = token['price_change_percentage_7d_in_currency']
            mc_vol_ratio = market_cap / volume if volume > 0 else 0

            # Calculate Potential Gains
            potential_gains = calculate_potential_gains(current_price, ath_price)

            # Apply filters based on user input
            if market_cap_min < market_cap < market_cap_max and volume > volume_min and potential_gains > 1:
                results.append({
                    "Token Name": token_name,
                    "Symbol": token_symbol.upper(),
                    "Current Price": current_price,
                    "ATH": ath_price,
                    "Potential Gains (x)": potential_gains,
                    "Market Cap": market_cap,
                    "Volume": volume,
                    "Price Change 7D (%)": price_change_7d,
                    "MC/Volume Ratio": mc_vol_ratio
                })

        # Convert results into DataFrame
        df = pd.DataFrame(results)

        # Display how many tokens remain after filtering
        st.write(f"Tokens after filtering: {len(df)}")
        
        # Display DataFrame in Streamlit
        if not df.empty:
            df["Token"] = df["Token Name"] + " (" + df["Symbol"] + ")"
            st.write("### Filtered Tokens", df)

            # Plot Potential Gains
            df_sorted = df.sort_values(by="Potential Gains (x)", ascending=False).head(30)
            df_sorted["Potential Gains (x)"] = df_sorted["Potential Gains (x)"].apply(lambda x: min(x, 1000))  # Cap to 1000x for readability

            st.write("### Top 30 Tokens by Potential Gains from Current Price to ATH")
            fig, ax = plt.subplots(figsize=(10, 12))  # Adjust height to accommodate 30 entries
            ax.barh(df_sorted["Token"], df_sorted["Potential Gains (x)"], color='green')
            ax.set_xlabel("Potential Gains (x)")
            ax.set_ylabel("Token")
            ax.set_title("Top 30 Tokens by Potential Gains (x) from Current Price to ATH")
            ax.invert_yaxis()
            st.pyplot(fig)

            # Plot Price Change Over 7 Days (Log Scale)
            df_sorted_7d = df.sort_values(by="Price Change 7D (%)", ascending=False).head(30)
            st.write("### Top 30 Tokens by Price Change Over 7 Days")
            fig_7d, ax_7d = plt.subplots(figsize=(10, 12))
            ax_7d.barh(df_sorted_7d["Token"], df_sorted_7d["Price Change 7D (%)"], color='blue')
            ax_7d.set_xlabel("Price Change 7D (%)")
            ax_7d.set_ylabel("Token")
            ax_7d.set_title("Top 30 Tokens by Price Change Over 7 Days (Log Scale)")
            ax_7d.set_xscale("log")  # Set log scale for better visualization
            ax_7d.invert_yaxis()
            st.pyplot(fig_7d)

            # Plot Market Cap to Volume Ratio (Lowest is Best)
            df_sorted_mc_vol = df.sort_values(by="MC/Volume Ratio", ascending=True).head(30)  # Sort by lowest MC/Volume
            st.write("### Top 30 Tokens by Market Cap to Volume Ratio")
            fig_mc_vol, ax_mc_vol = plt.subplots(figsize=(10, 12))
            ax_mc_vol.barh(df_sorted_mc_vol["Token"], df_sorted_mc_vol["MC/Volume Ratio"], color='orange')
            ax_mc_vol.set_xlabel("MC/Volume Ratio")
            ax_mc_vol.set_ylabel("Token")
            ax_mc_vol.set_title("Top 30 Tokens by Market Cap to Volume Ratio")
            ax_mc_vol.invert_yaxis()
            st.pyplot(fig_mc_vol)

            # Final Selection: Tokens appearing in all three plots
            tokens_in_all_plots = set(df_sorted["Token"]).intersection(df_sorted_7d["Token"], df_sorted_mc_vol["Token"])

            if tokens_in_all_plots:
                st.write("### Final Selection Consideration: Tokens Appearing in All Three Categories")
                st.write(f"These tokens appear in the top 30 of all three categories: Potential Gains, Price Change 7D, and MC/Volume Ratio.")
                st.write(tokens_in_all_plots)
            else:
                st.write("No tokens appeared in all three categories.")

            # Plot for Tokens Appearing in Two of the Three Categories
            tokens_in_two_plots = (
                set(df_sorted["Token"]).intersection(df_sorted_7d["Token"]).union(
                    set(df_sorted_7d["Token"]).intersection(df_sorted_mc_vol["Token"])).union(
                    set(df_sorted_mc_vol["Token"]).intersection(df_sorted["Token"]))
            ).difference(tokens_in_all_plots)  # Remove tokens appearing in all three

            if tokens_in_two_plots:
                st.write("### Tokens Appearing in Two of the Three Categories")
                st.write(f"These tokens appear in the top 30 of any two of the three categories.")
                st.write(tokens_in_two_plots)
            else:
                st.write("No tokens appeared in two of the three categories.")

        else:
            st.write("No tokens match the selected filters. Try adjusting the filters.")
        
if __name__ == "__main__":
    main()

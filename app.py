import time
import os
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Bright Data Proxy Credentials (Replace with your actual Bright Data username & password)
BRIGHT_DATA_USERNAME = "petehagen@icloud.com"
BRIGHT_DATA_PASSWORD = "3na0m7tdcaca"

# Bright Data Proxy Address (Correct Format)
BRIGHT_DATA_PROXY = f"http://{BRIGHT_DATA_USERNAME}:{BRIGHT_DATA_PASSWORD}@brd.superproxy.io:22225"

# === STREAMLIT UI ===
st.title("🏡 Zillow Mortgage vs Rent Dashboard")
st.markdown("Easily compare estimated mortgage payments to rent prices to find great deals!")

location = st.text_input("📍 Enter Location (City, State)", "Portland, OR")
max_price = st.number_input("💰 Max Home Price ($)", min_value=50000, max_value=2000000, value=600000, step=50000)
loan_term = st.slider("📆 Loan Term (years)", 10, 40, 30)
interest_rate = st.slider("📊 Interest Rate (%)", 1.0, 10.0, 7.0) / 100
down_payment_pct = st.slider("🏦 Down Payment (%)", 0.0, 50.0, 20.0) / 100
mortgage_vs_rent_threshold = st.slider("🏠 Max Mortgage-to-Rent Ratio (e.g., 0.50 = Mortgage is 50% of Rent)", 0.5, 1.5, 0.8)

# === FUNCTION TO CALCULATE MONTHLY MORTGAGE ===
def calculate_mortgage(home_price, down_payment_pct, interest_rate, loan_term):
    loan_amount = home_price * (1 - down_payment_pct)
    monthly_rate = interest_rate / 12
    num_payments = loan_term * 12
    
    mortgage_payment = (loan_amount * monthly_rate * (1 + monthly_rate) ** num_payments) / \
                       ((1 + monthly_rate) ** num_payments - 1)
    return round(mortgage_payment, 2)

# === FETCH ZILLOW LISTINGS USING BRIGHT DATA ===
def fetch_zillow_listings():
    zillow_search_url = f"https://www.zillow.com/homes/{location.replace(' ', '-')}/"
    proxies = {"http": BRIGHT_DATA_PROXY, "https": BRIGHT_DATA_PROXY}
    
    try:
        st.write("🔍 Testing proxy connection...")
        test_response = requests.get("https://ipinfo.io", proxies=proxies, timeout=10)
        if test_response.status_code == 200:
            st.write("✅ Proxy connection successful!")
        else:
            st.error(f"❌ Proxy test failed! Status Code: {test_response.status_code}")
            return []
        
        response = requests.get(zillow_search_url, proxies=proxies, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error fetching Zillow listings: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    listings = soup.find_all("article")  # Adjust selector if necessary
    
    data = []
    for listing in listings:
        try:
            price = listing.find("span", class_="PropertyCardPrice").text.strip()
            price = int(price.replace("$", "").replace(",", "").split("+")[0])
            
            rent_estimate = listing.find("span", class_="RentEstimate").text.strip()
            rent_estimate = int(rent_estimate.replace("$", "").replace(",", "").split("+")[0])
            
            listing_url = urljoin("https://www.zillow.com", listing.find("a")["href"])
            
            mortgage = calculate_mortgage(price, down_payment_pct, interest_rate, loan_term)
            rent_ratio = round(mortgage / rent_estimate, 2) if rent_estimate else None
            
            if rent_ratio and rent_ratio <= mortgage_vs_rent_threshold:
                data.append([price, mortgage, rent_estimate, rent_ratio, listing_url])
        except Exception as e:
            st.write(f"⚠️ Skipping listing due to error: {e}")
            continue  # Skip listings with missing data
    
    return data

# === DISPLAY RESULTS ===
data = fetch_zillow_listings()
df = pd.DataFrame(data, columns=["🏠 Price", "💵 Mortgage", "📊 Rent Estimate", "🔢 Mortgage-to-Rent Ratio", "🔗 URL"])
if not df.empty:
    st.write("### 🏡 Filtered Zillow Listings")
    st.dataframe(df)
else:
    st.write("❌ No listings found matching criteria.")

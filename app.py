import time
import os
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Zyte Proxy API Key (Replace with your actual Zyte API Key)
ZYTE_API_KEY = "d728bad0cd6b4eca95a4af08aed1da30"

# Zyte Proxy URL (Using HTTP instead of HTTPS to fix SSL issue)
ZYTE_PROXY_URL = "http://api.zyte.com:8011"

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

# === TEST ZYTE AUTHENTICATION ===
def test_zyte_auth():
    test_url = "http://ipinfo.io"
    proxies = {"http": ZYTE_PROXY_URL, "https": ZYTE_PROXY_URL}
    headers = {"Authorization": f"Basic {ZYTE_API_KEY}"}
    
    try:
        st.write("🔍 Testing Zyte proxy authentication...")
        response = requests.get(test_url, proxies=proxies, headers=headers, timeout=10)
        if response.status_code == 200:
            st.write("✅ Zyte Authentication Successful!")
        else:
            st.error(f"❌ Zyte Authentication Failed! Status Code: {response.status_code}, Response: {response.text}")
            if response.status_code == 401:
                st.error("🔍 Check your Zyte API Key! Go to Zyte Dashboard and verify it.")
            return False
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Zyte Authentication Error: {e}")
        return False
    return True

# === FETCH ZILLOW LISTINGS USING ZYTE ===
def fetch_zillow_listings():
    if not test_zyte_auth():
        return []  # Stop execution if Zyte auth fails
    
    zillow_search_url = f"https://www.zillow.com/homes/{location.replace(' ', '-')}/"
    proxies = {"http": ZYTE_PROXY_URL, "https": ZYTE_PROXY_URL}
    headers = {"Authorization": f"Basic {ZYTE_API_KEY}"}
    
    try:
        response = requests.get(zillow_search_url, proxies=proxies, headers=headers, timeout=15)
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

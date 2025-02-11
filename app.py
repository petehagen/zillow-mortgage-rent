import time
import pandas as pd
import streamlit as st
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# === STREAMLIT UI ===
st.title("Zillow Mortgage vs Rent Dashboard")

location = st.text_input("Enter Location (City, State)", "Portland, OR")
max_price = st.number_input("Max Home Price", min_value=50000, max_value=2000000, value=600000, step=50000)
loan_term = st.slider("Loan Term (years)", 10, 40, 30)
interest_rate = st.slider("Interest Rate (%)", 1.0, 10.0, 7.0) / 100
down_payment_pct = st.slider("Down Payment (%)", 0.0, 50.0, 20.0) / 100
mortgage_vs_rent_threshold = st.slider("Max Mortgage-to-Rent Ratio", 0.5, 1.0, 0.8)

# === FUNCTION TO CALCULATE MONTHLY MORTGAGE ===
def calculate_mortgage(home_price, down_payment_pct, interest_rate, loan_term):
    loan_amount = home_price * (1 - down_payment_pct)
    monthly_rate = interest_rate / 12
    num_payments = loan_term * 12
    
    mortgage_payment = (loan_amount * monthly_rate * (1 + monthly_rate) ** num_payments) / \
                       ((1 + monthly_rate) ** num_payments - 1)
    return round(mortgage_payment, 2)

# === FETCH ZILLOW LISTINGS USING PLAYWRIGHT ===
def fetch_zillow_listings():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        zillow_search_url = f"https://www.zillow.com/homes/{location.replace(' ', '-')}/"
        page.goto(zillow_search_url)
        time.sleep(5)  # Allow JavaScript to load
        
        soup = BeautifulSoup(page.content(), 'html.parser')
        browser.close()
    
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
            st.write(f"Skipping listing due to error: {e}")
            continue  # Skip listings with missing data
    
    return data

# === DISPLAY RESULTS ===
data = fetch_zillow_listings()
df = pd.DataFrame(data, columns=["Price", "Mortgage", "Rent Estimate", "Mortgage-to-Rent Ratio", "URL"])
if not df.empty:
    st.write("### Filtered Zillow Listings")
    st.dataframe(df)
else:
    st.write("No listings found matching criteria.")

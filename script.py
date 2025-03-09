import requests
import csv
import concurrent.futures
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Environment variables
bearer_token = os.getenv("DUOLINGO_BEARER_TOKEN")
user_id = os.getenv("DUOLINGO_USER_ID")

# Ensure the variable exists
if not bearer_token:
    raise ValueError("Error: DUOLINGO_BEARER_TOKEN is missing in the .env file!")
if not user_id:
    raise ValueError("Error: DUOLINGO_USER_ID is missing in the .env file!")

# Get today's date in the format YYYY-MM-DD
today_date = datetime.today().strftime('%Y-%m-%d')

# URL to fetch all available countries in JSON format from Stripe (No authentication required)
countries_url = "https://js.stripe.com/v3/fingerprinted/data/countries_es-0c588d4d6449e3a2b4d51f68184e2a79.json"

# Base URL to retrieve Duolingo subscription prices
subscription_url = f"https://www.duolingo.com/{today_date}/users/{user_id}/subscription-catalog?billingCountryCode=*COUNTRY_CODE*&supportedLayouts=STANDARD&vendor=VENDOR_STRIPE"

# Headers for subscription requests (Only needed for Duolingo API)
subscription_headers = {
    "Authorization": bearer_token,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
}

# Create a session for better performance (No headers yet)
session = requests.Session()

# List to store subscription data
subscription_plans = []

print("Starting the script...")

try:
    # Fetch the list of countries (No headers needed)
    print("Fetching the list of countries...")
    countries_response = session.get(countries_url)

    if countries_response.status_code != 200:
        print(f"Error fetching countries. Status code: {countries_response.status_code}")
        exit(1)

    # Convert response to JSON format
    countries = countries_response.json()
    print(f"Found {len(countries)} countries.")

    # Function to fetch subscription data for a single country
    def fetch_subscriptions(country):
        """Fetch subscription plans for a given country."""
        country_name = country['label']
        country_code = country['value']

        try:
            # Make request with authentication headers
            response = session.get(
                subscription_url.replace("*COUNTRY_CODE*", country_code),
                headers=subscription_headers  # Headers added here!
            )

            if response.status_code != 200:
                print(f"Error fetching subscriptions for {country_name}. Status code: {response.status_code}")
                return []

            # Parse JSON response
            subscriptions = response.json().get('plusPackageViewModels', [])
            if not subscriptions:
                print(f"No subscriptions found for {country_name}.")
                return []

            # Process and store subscription data
            country_subscriptions = []
            for subscription in subscriptions:
                period_length = subscription.get('periodLengthInMonths')
                is_family = subscription.get('isFamilyPlan', False)
                price = subscription.get('priceInCents', 0) / 100  # Convert cents to real currency
                trial_days = subscription.get('trialPeriodInDays', 0)
                currency = subscription.get('planCurrency', "N/A")

                # Determine subscription type
                if period_length == 1:
                    name = "Duolingo Premium 1 Month"
                    plan_type = "1_month"
                elif period_length == 12 and not is_family:
                    name = "Duolingo Premium 12 Months"
                    plan_type = "12_month"
                elif period_length == 12 and is_family:
                    name = "Duolingo Premium Family 12 Months"
                    plan_type = "12_month_family"
                else:
                    continue  # Skip other plans

                # Append subscription details
                country_subscriptions.append({
                    'subscriptionName': name,
                    'type': plan_type,
                    'periodLengthInMonths': period_length,
                    'country': country_name,
                    'countryCode': country_code,
                    'price': price,
                    'trialPeriodInDays': trial_days,
                    'currency': currency
                })

            return country_subscriptions

        except Exception as e:
            print(f"Error processing {country_name}: {str(e)}")
            return []

    # Use ThreadPoolExecutor to fetch subscriptions in parallel
    print("Fetching subscription data...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_subscriptions, countries))

    # Flatten the list of results
    for result in results:
        subscription_plans.extend(result)

except Exception as e:
    print(f"General error during execution: {str(e)}")
    exit(1)

# Save subscription data to a CSV file
csv_filename = "duolingo_subscriptions.csv"
try:
    print(f"Saving data to '{csv_filename}'...")
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['subscriptionName', 'type', 'periodLengthInMonths', 'country', 'countryCode', 'trialPeriodInDays', 'price', 'currency'])
        writer.writeheader()
        writer.writerows(subscription_plans)

    print("CSV file saved successfully.")

except Exception as e:
    print(f"Error saving CSV file: {str(e)}")

print("Script completed successfully.")

# Made with 🔥 by Sairaj 😎

import requests
import json
import re
import pandas as pd
from datetime import datetime
import time
from sys import exit

# Function to extract headers from cURL command
def extract_headers(curl_command):
    headers = {}
    matches = re.findall(r'-H ["^]+(.*?)"', curl_command)
    for match in matches:
        key_value = match.split(': ', 1)
        if len(key_value) == 2:
            key, value = key_value
            headers[key] = value
    return headers

# Function to extract raw data from cURL command
def extract_data_raw(curl_command):
    data_raw_match = re.search(r'--data-raw\s+(.*?)$', curl_command, re.DOTALL)
    if data_raw_match:
        data_raw = data_raw_match.group(1)
        data_raw = data_raw.replace(r'^\^', '"').replace('^', '').replace('""', '"')
        if data_raw.startswith('"') and data_raw.endswith('"'):
            data_raw = data_raw[1:-1]
        return data_raw
    else:
        return None
    
# Function to parse lead location
def parse_lead_location(lead_location):
    if isinstance(lead_location, list) and len(lead_location) == 3:
        return lead_location[0], lead_location[1], lead_location[2]
    else:
        return None, None, None

# Function to read cURL command from file
def read_curl_command_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            curl_command = file.read()
            if not curl_command.strip():
                raise ValueError("Config file is empty.")
        return curl_command
    except FileNotFoundError:
        print("Error: Config file not found.")
        exit(1)
    except ValueError as ve:
        print("Error:", ve)
        exit(1)

# Main function
def main():
    config_file_path = 'config.txt'
    start_time = time.time()

    curl_command = read_curl_command_from_file(config_file_path)
    headers = extract_headers(curl_command)
    
    print("Fetching data...")
    data_raw = extract_data_raw(curl_command)

    if data_raw:
        try:
            parsed_data = json.loads(data_raw, strict=False)
            total_records = []

            page = 1
            max_records = 2500
            while len(total_records) < max_records:
                parsed_data['pagination']['page'] = page
                response = requests.post('https://dashboard.slintel.com/api/v1/leads/search', headers=headers, json=parsed_data)

                if response.status_code == 200:
                    response_data = response.json()
                    records = response_data.get('data', [])
                    total_records.extend(records)

                    if len(records) < parsed_data['pagination']['size']:
                        break
                    else:
                        page += 1
                elif response.status_code == 440 and "session expired" in response.text.lower():
                    print("Error: Session expired. Please log in again.")
                    exit(1)
                else:
                    print("Error:", response.status_code)
                    print("Response content:", response.content)
                    break

            print("Total records fetched:", len(total_records))

            if total_records:
                df = pd.DataFrame(total_records)

                # Extract values from dictionaries in each column
                for column in df.columns:
                    df[column] = df[column].apply(lambda x: x['value'] if isinstance(x, dict) else x)

                # Parse lead_location into city, state, and country
                df['city'], df['state'], df['country'] = zip(*df['lead_location'].apply(parse_lead_location))

                # Drop the original lead_location column
                df.drop(columns=['lead_location'], inplace=True)

                # Reorder columns as desired
                selected_columns = ['name', 'lead_titles', 'company_name', 'phone', 'email', 'work_phone', 'company_phone_numbers', 'city', 'state', 'country', 'company_size', 'company_industry', 'company_website', 'linkedin_url']
                df = df[selected_columns]

                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                excel_file_path = f"slintel_data_{timestamp}.xlsx"
                df.to_excel(excel_file_path, index=False)
                print("Data has been saved to:", excel_file_path)

            else:
                print("No records fetched.")

        except json.JSONDecodeError as e:
            print("Error parsing JSON:", e)
    else:
        print("\nNo Data Raw section found.")

    end_time = time.time()
    time_taken = end_time - start_time
    print(f"Time taken: {time_taken:.2f} seconds")

if __name__ == "__main__":
    main()
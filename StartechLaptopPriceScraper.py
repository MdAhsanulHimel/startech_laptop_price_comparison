# Load the libraries
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
from tqdm import tqdm
import datetime
import os

# Function to format the price as integer
def format_price(price):
    if price == "TBA":
        return np.NaN
    else:
        # Remove the taka symbol and comma
        price = re.sub('[৳,]', '', price)
        return int(price)

# URL of the website
# this function takes # only available products from startech website by default
def get_url(url = 'https://www.startech.com.bd/laptop-notebook?filter_status=7'):
    url_input = input(f"Do you want to use this site? {url} \n(y/n):")
    if url_input.lower() == "n":
        url_input = input("Enter the url: ")
    else:
        url_input = url
    return url_input
url_parent = get_url()

# Make a GET request to the website
response = requests.get(url_parent)

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.content, 'html.parser')

# Find the total number of pages
total_pages = int(re.search(r'Showing \d+ to \d+ of \d+ \((\d+) Pages\)', soup.find('div', class_='text-right').text).group(1))

# Create an empty list to store the data
data = []

# initialize progress bar
pbar = tqdm(total=total_pages, desc="Scraping", unit="pages")

# Loop through all the pages
for page in range(1, total_pages + 1):
    
    # Make a GET request to the page
    url = f"{url_parent}&page=%d"
    response = requests.get(url, params={'page': page})

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all the product items
    product_items = soup.find_all('div', class_='p-item')

    # Loop through all the product items
    for item in product_items:
        # Extract the product name
        product_name = item.find('div', class_='p-item-details').find('h4', class_='p-item-name').find('a').text
        
        # Extract the product brand
        brand = product_name.split()[0]   

        # Extract the product link
        product_link = item.find('div', class_='p-item-details').find('h4', class_='p-item-name').find('a')['href']
        
        # find all li tags (to obtain detailed info)
        li_tags = item.find('ul').find_all('li')
        # select the second li tag and extract the RAM and Storage information from the <li>
        ram_storage = li_tags[1].text.strip()

        # Extract the product price
        product_price = item.find('div', class_='p-item-price').find('span').text
        # Format the product price as integer
        product_price = format_price(product_price)

        # Append the data to the list
        data.append({'Name': product_name, 
                     'Brand': brand, 
                     'Price': product_price, 
                     'Link': product_link,
                     'Storage': ram_storage})
        
    # update progress bar
    pbar.update(1)

# Convert the list to a DataFrame
df_current = pd.DataFrame(data)

# Add the current date to the CSV filename
today = datetime.datetime.today().strftime('%Y-%m-%d')
filename = f'startech_laptops_{today}.csv'

# Write the DataFrame to a CSV file
df_current.index = pd.RangeIndex(start=1, stop=len(df_current)+1)
df_current.to_csv(filename, index=True)

compare_decision = input(f"\nCurrent date's data has been saved to {filename}.\n\nDo you want to compare the prices with previous prices? (y/n):")

if compare_decision.lower() == "y":
    # Reading previous file whose price will be compared with the current
    # prev_file_name = 'startech_laptops.csv'
    # Get the current working directory
    cwd = os.getcwd()
    # List all the CSV files in the directory
    csv_files = [f for f in os.listdir(cwd) if f.endswith('.csv')]
    # Display the list of CSV files
    print("Select a CSV file to read:")
    for i, file in enumerate(csv_files):
        print(f"{i+1}. {file}")
    # Prompt the user to select a file
    file_num = int(input("Enter the file number you want to compare with: "))
    prev_file_name = os.path.join(cwd, csv_files[file_num-1])

    # read previous data file
    df_prev = pd.read_csv(prev_file_name, index_col=0)

    # merge the two data sets by link as unique identifier
    merged_df = pd.merge(df_prev, df_current, on="Link", how="outer", suffixes=("_old", "_new"))[
        ['Name_old','Price_old','Price_new','Link']].rename(columns={'Name_old': 'Name'})

    # calculate the price difference
    merged_df["Price Diff"] = merged_df["Price_new"] - merged_df["Price_old"]

    # create a new column 'Price Change'
    merged_df['Price Change'] = ''
    merged_df.loc[merged_df['Price Diff'] > 0, 'Price Change'] = 'Increased'
    merged_df.loc[merged_df['Price Diff'] < 0, 'Price Change'] = 'Decreased'

    merged_df["Changed"] = merged_df["Price_old"] != merged_df["Price_new"]
    changed_products = merged_df[merged_df["Changed"] == True][["Link"]]

    increased_products = merged_df[merged_df["Price Change"] == 'Increased'][["Link", "Price_new", "Price_old",'Price Diff']]
    decreased_products = merged_df[merged_df["Price Change"] == 'Decreased'][["Link", "Price_new", "Price_old",'Price Diff']]

    def write_file_function():
        write_file = input("Do you want to record price change logs to a txt file? (y/n): ")
        if write_file.lower() == "y":
            # Add the current date to the txt filename
            today = datetime.datetime.today().strftime('%Y-%m-%d')
            filename = f'price_changes_log_{today}.txt'

            with open(filename, "w") as file:
                file.write("The prices of the following products have changed\n")
                file.write("=========\n")
                file.write("Increased:\n")
                for index, row in increased_products.iterrows():
                    try:
                        file.write(f"- Link {row['Link']} \n\tPrice increased: {row['Price Diff']} Taka\n\tPrevious price: {row['Price_old']} Taka, Increased price: {row['Price_new']} Taka\n\n")
                    except:
                        continue

                file.write("=========\n")
                file.write("Decreased:\n")
                for index, row in decreased_products.iterrows():
                    try:
                        file.write(f"- Link {row['Link']} \n\tPrice decreased: {abs(row['Price Diff'])} Taka\n\tPrevious price: {row['Price_old']} Taka, Decreased price: {row['Price_new']} Taka\n\n")
                    except:
                        continue
            input(f"The price change logs have been written to {filename}.\n\nPress any key to exit.")
        else:
            input("Press any key to exit.")

    if len(changed_products) > 0:
        print("The prices of the following products have changed")
        print("=========")
        print("Increased:")
        increased_products_sorted = increased_products.sort_values('Price Diff', ascending=False)
        for index, row in increased_products_sorted.iterrows():
            try:
                print(f"- Link {row['Link']} \n\tPrice increased: {row['Price Diff']} Taka\n\tPrevious price: {row['Price_old']} Taka, Increased price: {row['Price_new']} Taka\n")
            except:
                continue
        
        print("=========")
        print("Decreased:")
        decreased_products_sorted = decreased_products.sort_values('Price Diff', ascending=True)
        for index, row in decreased_products_sorted.iterrows():
            try:
                print(f"- Link {row['Link']} \n\tPrice decreased: {abs(row['Price Diff'])} Taka\n\tPrevious price: {row['Price_old']} Taka, Decreased price: {row['Price_new']} Taka\n")
            except:
                continue
        
        write_file_function()
    else:
        input("No prices have changed. Press any key to exit.")
else:
    input("Thank you. Press any key to exit.")
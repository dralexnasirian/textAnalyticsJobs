from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup
import openpyxl
import os
import pandas as pd
import re


directory = 'C:\\Users\\arazn\\OneDrive - RMIT University\\0. Python text analytics\\Untitled Folder\\8. trial'

# Lists to hold extracted data
job_names = []
advertisers = []
locations = []
categories = []
job_types = []
salaries = []
contents = []

# List all files in the directory
for filename in os.listdir(directory):
    # Check if the file is an HTML file
    if filename.endswith(".html"):
        filepath = os.path.join(directory, filename)
        
        with open(filepath, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
            
            # Check each div of class "_1wkzzau0 _1pehz540"
            div_contents = soup.find_all("div", class_="_1wkzzau0 _1pehz540")
            
            for div in div_contents:
                for li in div.find_all('li'):
                    # Add space after the closing list tag
                    li.append(" ")

                for p in div.find_all('p'):
                    # Add space at the beginning of each paragraph
                    p.insert(0, " ")

            # Use regex to add a space after the provided sequence or ':'
            div_text = div_contents[0].text if div_contents and len(div_contents) > 0 else ""
            modified_text = re.sub(r'(</strong></p><ul><li>|:)(?!\s)', r'\1 ', div_text)

            # Extract content with modified spaces
            contents.append(modified_text)

            # Extract the job name
            job_names.append(soup.find('h1', class_="_1wkzzau0 a1msqi4y lnocuo0 lnocuol _1d0g9qk4 lnocuom lnocuo21").text if soup.find('h1', class_="_1wkzzau0 a1msqi4y lnocuo0 lnocuol _1d0g9qk4 lnocuom lnocuo21") else None)

            # Extract the advertiser
            span_advertisers = soup.find_all('span', class_='_1wkzzau0 a1msqi4y lnocuo0 lnocuo1 lnocuo21 _1d0g9qk4 lnocuod')
            advertisers.append(span_advertisers[0].text if span_advertisers and len(span_advertisers) > 0 else None)

            # Extract location, category, job_type, and salary
            span_data = soup.find_all('span', class_="_1wkzzau0 a1msqi4y a1msqir")
            locations.append(span_data[0].text if len(span_data) > 0 else None)
            categories.append(span_data[1].text if len(span_data) > 1 else None)
            job_types.append(span_data[2].text if len(span_data) > 2 else None)
            salaries.append(span_data[3].text if len(span_data) > 3 else None)

# Create a DataFrame with the results
dt = pd.DataFrame({
    'job_name': job_names,
    'advertiser': advertisers,
    'location': locations,
    'category': categories,
    'job_type': job_types,
    'salary': salaries,
    'content': contents
})

# Optionally, save the DataFrame to a CSV or Excel file
# df.to_csv('output.csv', index=False)
dt.head(3)

df = dt
df['search_word'] = 'machine_learning'

cols = df.columns.tolist()
cols = [cols[0], 'search_word'] + cols[1:-1]  # Adjust the order
df = df[cols]

# print(df.loc[0,'content'])

#################################################
# dealing with missing values under salary column
#################################################

print('number of rows = ', df.shape[0])
missing_values = df['salary'].isna().sum()
print('cells with missing salary', missing_values)
print('cells without missing salary', df.shape[0] - missing_values)
df = df.dropna(subset=['salary'])


#############################################
# removing rows that don't have any digit
#############################################
df = df[df['salary'].str.contains(r'\d', na=False)]
print('number of row = ', df.shape[0])

#############################################
# removing `$` and `,` from the salary column
#############################################

def remove_comma_and_dollar(salary_str):
    if pd.isna(salary_str):
        return salary_str
    
    cleaned_str = salary_str.replace(',', '').replace('$', '')
    return cleaned_str

df['salary'] = df['salary'].apply(lambda x: x.replace(',', '').replace('$', '') if pd.notna(x) else x)

#############################################
# removing the word `Up to` from the salary
#############################################
df['salary'] = df['salary'].apply(lambda x: x.replace("Up to", "").strip() if pd.notna(x) else x)

#######################################################################
# 1.3 removing the `+`, `inc` and `plus` and what ever comes after it
#######################################################################
df['salary'] = df['salary'].apply(lambda x: re.sub(r'\+.*$', '', x) if pd.notna(x) else x)
df['salary'] = df['salary'].apply(lambda x: re.sub(r'inc.*$', '', x, flags=re.IGNORECASE) if pd.notna(x) else x)
df['salary'] = df['salary'].apply(lambda x: re.sub(r'plus.*$', '', x, flags=re.IGNORECASE) if pd.notna(x) else x)


######################################################################
# 1.5 if there is one or more `letter` before a `digit` remove it
######################################################################
df['salary'] = df['salary'].apply(lambda x: re.sub(r'^[^\d]+', '', x) if pd.notna(x) else x)

###########################################################################
# 1.6. if there is `k` immidiatly after a number replace it by `000`
###########################################################################
df['salary'] = df['salary'].str.replace(r'1[kK]', '1000', regex=True)
df['salary'] = df['salary'].str.replace(r'(\d+)k', lambda m: m.group(1) + '000', regex=True, case=False)

##################################################
# generating `unit_salary` from `salary` column
##################################################
hourly_rate = ['per hour', 'p.h.', 'p/h', 'Per Hour', '/hour']
daily_rate = ['per day', 'p.d.', 'PD', 'P/D', 'a day', 'pd', 'PD', 'day', 'Daily', 'daily', 'p/d']
annual_rate = ['per year', 'p.a.', 'p/a', 'pa', 'p.a', 'per annum']
rates = hourly_rate + daily_rate + annual_rate
rates

def find_rate(salary_str):
    for rate in rates:
        if rate in salary_str:
            return rate
    return None  # If no rate is found in the salary string

df['unit_salary'] = df['salary'].apply(lambda x: find_rate(x))

# Get column names as a list
cols = df.columns.tolist()
# Find the position of 'salary' column
index_salary = cols.index('salary')
# Reorder columns
cols = cols[:index_salary+1] + ['unit_salary'] + cols[index_salary+1:-1]
df = df[cols]

####################################
# 3. generating `unit` column
####################################
def calculate_value(salary_str):
    # Extract all sequences of digits, potentially followed by a dot and more digits
    numbers = [float(num) for num in re.findall(r'\d+\.\d+|\d+', salary_str)]
    
    # If only one number is found, return it
    if len(numbers) == 1:
        return numbers[0]
    
    # If two numbers are found, return their average
    elif len(numbers) == 2:
        return sum(numbers) / 2

    # If no numbers or more than two numbers, return None or handle accordingly
    else:
        return None

# Apply the function to the 'salary' column
df['unit'] = df['salary'].apply(calculate_value)


cols = list(df.columns)
cols.insert(cols.index('unit_salary'), cols.pop(cols.index('unit')))
df = df[cols]

##############################################################
# reasonable guess for `unit_salary` based on `unit` column
##############################################################
def determine_unit_salary(row):
    # Check if the 'unit_salary' cell is blank (NaN)
    if pd.isna(row['unit_salary']):
        if 400 < row['unit'] < 2000:
            return 'day'
        elif row['unit'] < 300:
            return 'per hour'
        elif row['unit'] > 50000:
            return 'per year'
    return row['unit_salary']

df['unit_salary'] = df.apply(lambda row: determine_unit_salary(row), axis=1)


def calculate_annual_salary(unit_value, unit_salary):
    if unit_salary in hourly_rate:
        return unit_value * 8 * 260
    elif unit_salary in daily_rate:
        return unit_value * 260
    elif unit_salary in annual_rate:
        return unit_value
    else:
        return None

df['annual_salary'] = df.apply(lambda row: calculate_annual_salary(row['unit'], row['unit_salary']), axis=1)

cols = list(df.columns)
cols.insert(cols.index('unit_salary') + 1, cols.pop(cols.index('annual_salary')))
df = df[cols]


df.to_csv('html_to_csv.csv', index=False)

df.head(2)

""" =====================================================================================
Automated LSAC Status Tracker

by @ReynardStudy on January 7, 2025

This Python script generates a Selenium browser that logs into an applicant's free LawHub 
account, navigates to the Applications page, and swiftly extracts relevant status data from 
every application portal tied to LSAC. Once it finishes tracking, the script prints all status 
data in the console window, with the most recent updates first.

REQUIREMENTS
   
1.  Any machine with Python 3.7+ enabled in the command line
2.  A LawHub account

HOW TO RUN THIS FILE
   
0.  If you don't already have the required packages installed, run this:
    
    pip install time datetime selenium

1.  At line 234 (the very last line of this script), replace YOUR USERNAME HERE and YOUR 
    PASSWORD HERE with your LSAC login. Example:

    run_scraper("SuperDuperLawyer9000", "t14hereicome!")    <---- keep the quotes!
    
2.  Finally, run:
    
    python3 lsac_tracker.py

Happy tracking!

=========================================================================================
            !!! DO NOT MODIFY ANYTHING UP TO LINE 234 !!!
=========================================================================================
"""

import time

from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def run_scraper(username, password):
    """ The meat and potatoes; runs entire script process

    Args:
        username (str): Applicant's LSAC username, for authentication to LawHub
        password (str): Applicant's LSAC password, also for authentication
    """
    
    start_time = time.time()
    
    """Initiate driver instance"""
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('log-level=3') # log nothing except any error fatal to the code
    driver = webdriver.Chrome(
        options=options,
    )
    
    buttons, applicant_name = lawhub_signin(username, password, driver)
    sorted_info = get_statuses(buttons, driver)
    driver.quit()
    
    print("\nLSAC Statuses for " + applicant_name)
    print("Retrieved {}\n".format(
        datetime.now(timezone.utc).astimezone().strftime("%b %d, %Y at %I:%M:%S %p %Z")))
    print_all(sorted_info)
        
    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)
    print("\nStatuses retrieved in: {} seconds".format(elapsed_time))
    
    
def lawhub_signin(username, password, driver):
    """ Receives authentication information and driver reference and signs into LawHub

    Args:
        username (str): Applicant's LSAC username, for authentication to LawHub
        password (str): Applicant's LSAC password, also for authentication
        driver (WebDriver): The driver reference, passed through
        
    Returns:
        buttons (list): List of WebElements corresponding to the "View Details" buttons
        applicant_name (str): Applicant's preferred first name, retrieved through LawHub
    """
    
    lawhub_url = 'https://app.lawhub.org/applications'
    driver.get(lawhub_url)
    
    # Wait until sign-in button shows up in top-right
    wait = WebDriverWait(driver, 10)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Sign-in')]")))
    sign_in = driver.find_element(By.XPATH, "//*[contains(text(), 'Sign-in')]")
    sign_in.click()
    
    # Wait until orange "sign-in" button shows up, then log in
    wait = WebDriverWait(driver, 10)
    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id=\"next\"]')))
    user = driver.find_element(By.ID, "logonIdentifier")
    pwd = driver.find_element(By.ID, "password")
    login = driver.find_element(By.XPATH, '//*[@id=\"next\"]')
    user.send_keys(username)
    pwd.send_keys(password)
    login.click()
    
    # Wait until page loads properly, with portal links
    wait = WebDriverWait(driver, 10)
    wait.until(EC.all_of(
        EC.title_contains('Application Status Tracker'),
        EC.visibility_of_any_elements_located((By.XPATH, "//*[@id=\"welcome-menu\"]/span")),
        EC.visibility_of_any_elements_located((By.XPATH, "//a[text()='View details']"))
    ))
    
    applicant_name = driver.find_element(
        By.XPATH, "//*[@id=\"welcome-menu\"]/span").text.split(', ', 1)[1]
    buttons = driver.find_elements(By.XPATH, "//a[text()='View details']") # gets all portal links
    return buttons, applicant_name
    
 
def get_statuses(buttons, driver):
    """ Receives authentication information and driver reference and signs into LawHub

    Args:
        buttons (list): List of WebElements corresponding to the "View Details" buttons
        driver (WebDriver): The driver reference, passed through
        
    Returns:
        sorted_data (dict): Statuses of form {k, [v1:v3]} in order of decreasing status date
    """
    
    school_data = {}
    
    for b in buttons: 
        l = b.get_attribute("href") # button link
        s = b.find_element(By.XPATH, "./span").text.title() # school's name
        school_data[of_lowercase(s)] = [l]
    
    for k, v in school_data.items():
        get_status(k, v, driver)
    
    sorted_data = reverse_date_sort(school_data)
    return sorted_data


def get_status(school_name, data_arr, driver):
    """ Driver visits a law school's LSAC portal page and collects the relevant status data. 
        This function makes changes to a single value in the dictionary object

    Args:
        school_name (str): A law school's name
        driver (WebDriver): The driver reference, passed through
        
    Returns:
        sorted_data (dict): Statuses of form {k, [v1:v3]} in order of decreasing status date
    """
    
    driver.get(data_arr[0]) # go to link, in this case [v1]
    
    # Wait until portal page loads properly
    wait = WebDriverWait(driver, 10)
    wait.until(EC.all_of(
        EC.title_contains('Applicant Status Online'),
        EC.visibility_of_any_elements_located((By.CSS_SELECTOR, "div[class = 'section-header']"))
    ))

    try:
        status = driver.find_element(By.XPATH, "//*[contains(text(), 'Application Status:')]")
        table = status.find_elements(By.XPATH, "./../..")
        
        full_text = table[0].text
        
        # Get rid of "CAS Report Status"
        if 'CAS' in full_text: full_text = full_text.split("CAS Report Status:", 1)[0].rstrip()

        # Basically, if the status does not have a date, use an "impossible" date
        if 'Date' not in full_text:
            data_arr += [full_text, "01/01/0001"]
        else:
            split_arr = full_text.split(" Date: ", 1)

            # Handle case for blank date - same "impossible" date for sorting
            if split_arr[1] == "": split_arr[1] = "01/01/0001"
            
            data_arr += split_arr
    except:
        # If no "Application Status" appears, return this message with the manual tracker link
        data_arr += ["App status not found." +  
            "\nPlease manually check tracker for a potential decision!\n" 
            + data_arr[0], "01/01/0001"]


def reverse_date_sort(data_dict):
    """ Helper function: Sorts dictionary with form {k, [v1:v3]} in order of decreasing status date
    
    Returns:
        data_dict with form {k, [v1:v3]}, sorted decreasingly by date in v2
    """
    
    return dict(sorted(data_dict.items(), 
        key=lambda x: datetime.strptime(x[1][2], '%m/%d/%Y'), reverse=True))
   
   
def print_all(data_dict):
    """ Helper function: Prints out formatted dictionary with form {k, [v1:v3]}, with "01/01/0001" 
        date considered
    """
    
    for k, v in data_dict.items():
        print('=' * 75)
        print(k.center(75))
        print('_' * 75)
        
        if v[2] != "01/01/0001": print(v[1] + " Date: " + v[2]) # throw out any "dates" like these
        else: print(v[1])
   
    print('=' * 75)
   

def of_lowercase(s):
    """ Helper function: corrects "of" title cases in law school names
    """
    
    if 'Of The' in s: s = s.replace('Of The', 'of the')
    if 'Of' in s: s = s.replace('Of', 'of')
    return s
   
   
if __name__=="__main__":
    
    """ =================================================================================
            !!! DO NOT MODIFY ANYTHING ABOVE HERE !!!
    ================================================================================= """ 
    run_scraper("YOUR USERNAME HERE", "YOUR PASSWORD HERE")

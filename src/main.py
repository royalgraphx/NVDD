# -----------------------------------------------------------------------------
# 
# NVIDIA Driver Dumper - Allows the manual dumping and retrieving of various NVIDIA Drivers on NVIDIA.com website.
# 
# Copyright (c) 2024 RoyalGraphX - BSD 3-Clause License
# See LICENSE file for more detailed information.
# 
# -----------------------------------------------------------------------------

import os
import re
import sys
import time
import json
import click
import shutil
import string
import getpass
import requests
import platform
import subprocess
from bs4 import BeautifulSoup

# Define various variables
DEBUG = "FALSE"
CARNATIONSINTERNAL = "TRUE"
NVDD_vers = "0.0.1"

def get_host_os():
    """
    Determine the host operating system.

    Returns:
        str: The name of the host operating system ('Linux', 'Windows', 'Darwin' for macOS, etc.).
    """
    return platform.system()

def host_os_pretty():
    """
    Get a pretty-printed version of the host OS with detailed information.

    Returns:
        str: A detailed string describing the host OS.
    """
    os_type = get_host_os()
    
    if os_type == "Linux":
        # Read the os-release file to get distribution information
        try:
            with open('/etc/os-release') as f:
                lines = f.readlines()
                os_info = {}
                for line in lines:
                    key, value = line.strip().split('=', 1)
                    os_info[key] = value.strip('"')
                pretty_name = os_info.get('PRETTY_NAME', 'Linux')
                return pretty_name
        except Exception:
            return "Linux"
    
    elif os_type == "Darwin":
        try:
            # Use sw_vers to get macOS version details
            sw_vers_output = subprocess.check_output(["sw_vers"], text=True).strip().split("\n")
            version_info = {line.split(":")[0].strip(): line.split(":")[1].strip() for line in sw_vers_output}
            kernel_version = get_darwin_kernel_version()
            kernel_type = get_darwin_kernel_type()
            kernel_integrity = get_darwin_kernel_integrity_status()
            kernel_build_string = get_darwin_build_string()
            return f"Darwin {version_info.get('ProductVersion', '')} ({version_info.get('BuildVersion', '')})\n{kernel_integrity}\nDarwin Kernel {kernel_version} ({kernel_type}) - {kernel_build_string}"
        except Exception:
            return "Darwin"
    
    return os_type

def get_system_architecture():
    return platform.machine()

def get_current_user():
    """
    Get the username of the currently active user running the Python script.

    This function uses the getpass module to retrieve the login name of the user.
    It checks the environment variables LOGNAME, USER, LNAME, and USERNAME in order,
    and returns the value of the first non-empty string.

    Returns:
        str: The username of the currently active user.
    """
    username = getpass.getuser()
    return username

def get_current_directory():
    """Gets the current working directory and returns it"""
    return os.getcwd()

def get_last_directory_name(path):
    """
    Get the last directory name from a given path.
    
    Parameters:
        path (str): The path from which to extract the last directory name.
    
    Returns:
        str: The last directory name in the path.
    """
    return os.path.basename(os.path.normpath(path))

def clear_console_deeply():
    """Clears the console deeply by using ANSI escape sequences."""
    # ANSI escape sequence to clear the screen and move cursor to the top left
    os.system('cls' if os.name == 'nt' else 'clear')

def check_and_create_database():
    """
    Check if the data/database.json file exists.
    If it does not exist, create it with an initial structure.
    """
    database_path = "data/database.json"

    # Check if the directory exists, if not, create it
    if not os.path.exists("data"):
        os.makedirs("data")

    # Check if the file exists, if not, create it
    if not os.path.isfile(database_path):
        with open(database_path, 'w') as db_file:
            # Initial structure for the database
            initial_structure = {
                "drivers": []
            }
            json.dump(initial_structure, db_file, indent=4)
        
        if DEBUG.upper() == "TRUE":
            click.echo("Database file created at data/database.json")
    else:
        if DEBUG.upper() == "TRUE":
            click.echo("Database file already exists at data/database.json")

def addDriver(name, version, cuda_version, target_os, release_date, file_size, language, driver_url):
    """
    Add a new driver entry to the database.

    Args:
        name (str): Name of the driver.
        version (str): Version of the driver.
        target_os (str): Target operating system of the driver.
        release_date (str): Release date of the driver (format: YYYY-MM-DD).
        file_size (str): Size of the driver file.
        language (str): Language of the driver.
    """

    # Load current database content
    database_path = "data/database.json"
    with open(database_path, 'r') as db_file:
        database = json.load(db_file)

    # Create new driver entry
    new_driver = {
        "name": name,
        "version": version,
        "cuda_version": cuda_version,
        "target_os": target_os,
        "release_date": release_date,
        "file_size": file_size,
        "language": language,
        "url": driver_url
    }

    # Append new driver to the database
    database["drivers"].append(new_driver)

    # Save updated database content
    with open(database_path, 'w') as db_file:
        json.dump(database, db_file, indent=4)

    click.echo(f"Driver '{name}' added to the database.")

def getPageInfo(driver_url):
    """
    Fetches and extracts information from the given NVIDIA driver page URL.

    Args:
        driver_url (str): The URL of the NVIDIA driver page.

    """
    try:
        # Send a GET request to the driver URL
        response = requests.get(driver_url)
        response.raise_for_status()  # Raise an exception for bad responses

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        if DEBUG.upper() == "TRUE":
            # Print the entire HTML content for debugging
            click.echo("HTML content of the page:")
            click.echo(str(soup))

        # Find and Init rightContent div info
        right_content = soup.find('div', id='rightContent')
        if right_content:
            if DEBUG.upper() == "TRUE":
                click.echo("Page has loaded, rightContent dif Found.")
        else:
            click.echo("Could not find 'rightContent' div.")
        
        # Early check for error message in rightContent
        error_message = right_content.find('span', id='lblErrorMessage')
        if error_message:
            click.echo("The link does not contain a valid driver for parsing. Sorry for the inconvenience.")
            return

        # Print the contents of the 'rightContent' div for debugging
        if DEBUG.upper() == "TRUE":
            click.echo("Raw Contents of 'rightContent':")
            click.echo(right_content.prettify())

        # Initialize variables to store information
        driver_name = None
        driver_version = None
        cuda_driver_version = None
        release_date = None
        operating_system = None
        language = None
        file_size = None

        # Extract and print specific information
        if DEBUG.upper() == "TRUE":
            click.echo("Parsed Content of 'rightContent':")

        # Find Driver Name Information
        driver_title = soup.find('title', id='pageTitle')
        if driver_title:
            driver_name = driver_title.text.split('|')[0].strip()
        else:
            click.echo("Driver Name not found.")

        # Find Version Information
        version = right_content.find('td', class_='contentsummaryright', id='tdVersion')
        if version:
            driver_version = version.text.strip()
        else:
            click.echo("Version information not found.")

        # Find CUDA Version Information
        cuda_version = right_content.find('td', class_='contentsummaryright', id='tdCudaToolkits')
        if cuda_version and cuda_version.text.strip():
            cuda_driver_version = cuda_version.text.strip()
        else:
            cuda_driver_version = None  # Return None if CUDA Version information is not found or empty

        # Find Release Date information
        release_date_elem = right_content.find('td', class_='contentsummaryright', id='tdReleaseDate')
        if release_date_elem:
            release_date = release_date_elem.text.strip()
        else:
            click.echo("Release Date information not found.")

        # Find all tr elements under rightContent
        tr_elements = right_content.find_all('tr')

        # Extract OS information, Language, and File Size
        for tr in tr_elements:
            tds = tr.find_all('td')
            if len(tds) == 2:
                name = tds[0].text.strip()
                data = tds[1].text.strip()
                if name == 'Operating System:':
                    operating_system = data
                elif name == 'Language:':
                    language = data
                elif name == 'File Size:':
                    file_size = data

        # Print or use the variables as needed
        click.echo(f"Driver URL: {driver_url}")
        click.echo(f"Driver Name: {driver_name}")
        click.echo(f"Version: {driver_version}")
        click.echo(f"CUDA Toolkit Version: {cuda_driver_version}")
        click.echo(f"Release Date: {release_date}")
        click.echo(f"Operating System Support: {operating_system}")
        click.echo(f"Language: {language}")
        click.echo(f"File Size: {file_size}")

        # Add the parsed driver to the database
        addDriver(driver_name, driver_version, cuda_driver_version, operating_system, release_date, file_size, language, driver_url)

    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching page: {e}")

    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching page: {e}")

    except AttributeError as ae:
        click.echo(f"AttributeError: {ae}")

@click.command()
def main():
    """Main entry point for Project."""
    while True:
        clear_console_deeply()
        click.echo("Welcome to the NVIDIA Driver Dumper!")
        click.echo("Copyright (c) 2024 RoyalGraphX")
        click.echo(f"Python {get_system_architecture()} Pre-Release {NVDD_vers} for {host_os_pretty()}")
        if CARNATIONSINTERNAL == "TRUE":
            click.echo("CARNATIONSINTERNAL is set to TRUE! Welcome.\n")
        else:
            click.echo("")

        click.echo("What would you like to do?")
        if CARNATIONSINTERNAL == "TRUE":
            click.echo("1. Create NVDD Database JSON")
            click.echo("2. Read NVDD Databse JSON Entries")
            click.echo("3. Download an NVIDIA Driver")
            click.echo("4. Update Sources")
            click.echo("5. Exit")
        else:
            click.echo("1. Download an NVIDIA Driver")
            click.echo("2. Update Sources")
            click.echo("3. Exit")

        choice = click.prompt("Enter your choice", type=int)

        if CARNATIONSINTERNAL == "TRUE":
            if choice == 1:
                createNVDD(71510)
            elif choice == 2:
                readNVDD_DB_menuOption()
            elif choice == 3:
                downloadNVdriver()
            elif choice == 4:
                updateSources()
            elif choice == 5:
                exit_program()
            else:
                click.echo("Invalid choice. Please enter a valid option.")
        else:
            if choice == 1:
                downloadNVdriver()
            elif choice == 2:
                updateSources()
            elif choice == 3:
                exit_program()
            else:
                click.echo("Invalid choice. Please enter a valid option.")

        # Pause to show the result before clearing the screen again
        click.pause()

def createNVDD(start=0):
    """
    Create and populate the NVIDIA Driver Database starting from a given URL ID.

    Args:
        start (int): The starting URL ID. Defaults to 0.
    """
    clear_console_deeply()
    if DEBUG.upper() == "TRUE":
        click.echo("If you see this message, you're in DEBUG mode...")

    # Check and create the database if it doesn't exist
    check_and_create_database()

    base_url = "https://www.nvidia.com/Download/driverResults.aspx/"

    for i in range(start, 1000000):
        driver_url = f"{base_url}{i}"
        click.echo(f"Checking URL: {driver_url}")
        print()
        getPageInfo(driver_url)
        print()

        # Optionally, you can add a delay between requests to avoid hitting the server too hard or getting
        # Rate limited by the website, sometimes errors can happen randomly where the DNS resolution fails.
        # time.sleep(1)  # sleep in between requests

def readNVDD_DB_menuOption():
    clear_console_deeply()
    if DEBUG.upper() == "TRUE":
        click.echo("If you see this message, you're in DEBUG mode...")

    # Placeholder Text where things will continue

def downloadNVdriver():
    clear_console_deeply()
    if DEBUG.upper() == "TRUE":
        click.echo("If you see this message, you're in DEBUG mode...")

    # Placeholder Text where things will continue

def updateSources():
    clear_console_deeply()
    if DEBUG.upper() == "TRUE":
        click.echo("If you see this message, you're in DEBUG mode...")

    # Placeholder Text where things will continue

def exit_program():
    click.echo("Exiting NVDD. Goodbye!")
    raise SystemExit

if __name__ == "__main__":
    main()

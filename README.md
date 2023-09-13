# README
**Welcome to my spending tracker repo page!** :fireworks:
This is my project for recording purchases made at retail stores. You can look at your bank statements to see how much you spend at different stores, but this project aims to track *what* you buy at those stores.
I'll be able to track over time how much I spend on different categories like produce, snacks, etc.

A secondary goal is to figure out how to split grocery bills with my house mate. This will help us decide how to split the bill on items one of us won't use. For example, I don't want to pay for dog food since I don't have any pets.

The python scripts set up the sqlite3 database, ocr the receipts using an api, manage loading data into the database, and basic reporting. 

# :warning: Disclaimer :warning:
This is a work in progress and the path may be dangerous! Continue at your own risk!

# Setting up the environment
I exported my environment to environment.yml with the following line:
`conda env export > environment.yml`

With conda, you can recreate my environment with the following line:
`conda env create -f environment.yml`

# Basic usage
1. Place the image of your receipt in **receipts** folder.
2. In a terminal, run the ocr_api.py script: `python ocr_api.py` This will prompt you for a file name of an image in the **receipts** folder and write a json file in the **json** folder.
3. Check the newly created json file for any errors. For example, make sure discounts are correctly marked as negative numbers and check the date/time.
4. Run the database_manager.py script: `python database_manager.py` It will ask for the filename of the json file in **json**. Follow the rest of the prompts from the terminal.

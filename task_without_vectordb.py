import torch # Import torch
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey # Import SQLAlchemy components
from sqlalchemy.ext.declarative import declarative_base # Import declarative_base
from sqlalchemy.orm import relationship, sessionmaker # Import relationship and sessionmaker
import os # Import os module
from dotenv import load_dotenv # Import load_dotenv

load_dotenv() # Load environment variables from .env file
DB_USER = os.getenv('DB_USER') # Get database user from environment variables
DB_PASSWORD = os.getenv('DB_PASSWORD') # Get database password from environment variables
DB_HOST = os.getenv('DB_HOST') # Get database host from environment variables
DB_PORT_ENV = os.getenv('DB_PORT') # Get DB_PORT from environment
DB_NAME = os.getenv('DB_NAME') # Get database name from environment variables

# Provide a default for DB_PORT if it's not set or is empty
DB_PORT = DB_PORT_ENV if DB_PORT_ENV and DB_PORT_ENV.strip() else '5432' # Set database port, default to 5432 if not specified

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" # Construct database URL
engine = create_engine(DATABASE_URL) # Create a database engine
Base = declarative_base() # Create a base class for declarative models

class Company(Base): # Define the Company model
    __tablename__ = 'companies' # Set the table name
    id = Column(Integer, primary_key=True) # Define the id column
    name = Column(String, nullable=False) # Define the name column
    address = Column(String) # Define the address column
    gst_no = Column(String, unique=True) # Define the gst_no column
    products = relationship("Product", back_populates="company", cascade="all, delete-orphan") # Define the relationship to products

class Product(Base): # Define the Product model
    __tablename__ = 'products' # Set the table name
    id = Column(Integer, primary_key=True) # Define the id column
    product_id = Column(String, unique=True) # Define the product_id column
    name = Column(String, nullable=False) # Define the name column
    description = Column(String) # Define the description column
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False) # Define the company_id foreign key
    company = relationship("Company", back_populates="products") # Define the relationship to company

class FilteredProduct(Base): # Define the FilteredProduct model
    __tablename__ = 'filtered_products' # Set the table name
    id = Column(Integer, primary_key=True) # Define the id column
    product_id = Column(String, ForeignKey('products.product_id')) # Define the product_id foreign key
    name = Column(String, nullable=False) # Define the name column
    description = Column(String) # Define the description column
    product = relationship("Product") # Define the relationship to Product

Base.metadata.create_all(engine) # Create all tables in the database

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # Create a session factory
session = SessionLocal() # Create a new session
products_from_db = session.query(Product.product_id, Product.name, Product.description).all() # Query all products
session.close() # Close the session

flagged_products_for_insertion = set() # Initialize a set to store flagged products for insertion

if products_from_db: # Check if there are any products from the database
    banned_words_file = "banned_words.txt" # Define the path to the banned words file
    banned_words = [] # Initialize an empty list for banned words
    try: # Try to open and read the banned words file
        with open(banned_words_file, 'r') as f: # Open the file in read mode
            banned_words = [line.strip().lower() for line in f if line.strip()] # Read and process each line
        if banned_words: # Check if any banned words were loaded
            print(f"Loaded {len(banned_words)} banned words from {banned_words_file}.") # Print the number of loaded banned words
        else: # If no banned words were found
            print(f"No banned words found in {banned_words_file}.") # Print a message indicating no banned words
    except FileNotFoundError: # Handle the case where the file is not found
        print(f"Error: {banned_words_file} not found. Proceeding without banned words check.") # Print an error message
        banned_words = [] # Ensure banned_words is an empty list

    if banned_words: # Check if there are banned words to process
        print("\nProcessing products for banned words...") # Print a message indicating the start of processing
        for p_id, name, description in products_from_db: # Iterate over each product from the database
            product_text = name.lower() # Convert product name to lowercase
            if description: # Check if description exists
                product_text += " " + description.lower() # Append product description to product_text in lowercase

            for banned_word in banned_words: # Iterate over each banned word
                if banned_word in product_text: # Check if the banned word is in the product text
                    print(f"  Product ID '{p_id}' (Name: '{name}') flagged due to banned word: '{banned_word}'.") # Print flagging information
                    flagged_products_for_insertion.add((p_id, name, description if description else "")) # Add product to flagged set
                    break # Move to the next product once a banned word is found
    else: # If no banned words were loaded
        print("\nSkipping banned words check as no banned words were loaded or found.") # Print a message indicating skipping the check
else: # If no products were found in the database
    print("No products found in the database. Banned word check and insertion skipped.") # Print a message indicating no products found

if flagged_products_for_insertion: # Check if there are any products flagged for insertion
    print(f"\nAttempting to insert {len(flagged_products_for_insertion)} unique flagged product(s) into 'filtered_products' table...") # Print insertion attempt message
    session = SessionLocal() # Create a new session
    inserted_count = 0 # Initialize a counter for inserted products
    for p_id, original_name, desc in flagged_products_for_insertion: # Iterate over flagged products
        exists = session.query(FilteredProduct).filter(FilteredProduct.product_id == p_id).first() # Check if product already exists in filtered_products
        if not exists: # If product does not exist
            filtered_product_entry = FilteredProduct( # Create a new FilteredProduct entry
                product_id=p_id, # Set product_id
                name="",  # Set name to empty string as per original logic
                description=desc # Set description
            )
            session.add(filtered_product_entry) # Add the new entry to the session
            inserted_count += 1 # Increment inserted_count
            print(f"  Flagged product ID '{p_id}' (Original Name: '{original_name}') prepared for insertion into 'filtered_products' with name removed.") # Print preparation message
        else: # If product already exists
            print(f"  Product with ID '{p_id}' (Original Name: '{original_name}') already exists in 'filtered_products'. Skipping.") # Print skipping message
    
    if inserted_count > 0: # Check if any new products were inserted
        session.commit() # Commit the session to save changes to the database
        print(f"Successfully inserted {inserted_count} new product(s) into 'filtered_products' table (with names removed).") # Print success message
    else: # If no new products were inserted
        print("No new products were inserted into 'filtered_products' table (either none flagged or all were duplicates).") # Print message for no new insertions
    session.close() # Close the session
elif products_from_db: # If there were products but none were flagged
    print("\nNo products were flagged for insertion into 'filtered_products' based on banned word check.") # Print message for no flagged products

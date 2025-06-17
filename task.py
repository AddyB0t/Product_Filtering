from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import torch
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT_ENV = os.getenv('DB_PORT') # Get DB_PORT from environment
DB_NAME = os.getenv('DB_NAME')

# Provide a default for DB_PORT if it's not set or is empty
DB_PORT = DB_PORT_ENV if DB_PORT_ENV and DB_PORT_ENV.strip() else '5432'

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Company(Base):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    gst_no = Column(String, unique=True)
    products = relationship("Product", back_populates="company", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    product_id = Column(String, unique=True)
    name = Column(String, nullable=False)
    description = Column(String)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    company = relationship("Company", back_populates="products")

class FilteredProduct(Base):
    __tablename__ = 'filtered_products'
    id = Column(Integer, primary_key=True)
    product_id = Column(String, ForeignKey('products.product_id'))
    name = Column(String, nullable=False)
    description = Column(String)
    product = relationship("Product")

Base.metadata.create_all(engine)

device = "cuda" if torch.cuda.is_available() else "cpu"
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': device},
    encode_kwargs={'normalize_embeddings': True}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()
products_from_db = session.query(Product.product_id, Product.name, Product.description).all()
session.close()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    length_function=len,
    is_separator_regex=False,
)

split_texts = []
split_metadatas = []

for p_id, name, description in products_from_db:
    full_text = name
    if description:
        full_text += f"\n\nDescription: {description}"
    chunks = text_splitter.split_text(full_text)
    for chunk_text in chunks:
        split_texts.append(chunk_text)
        chunk_metadata = {
            "original_product_id": p_id,
            "original_product_name": name,
            "description": description if description else ""
        }
        split_metadatas.append(chunk_metadata)

flagged_products_for_insertion = set()

if split_texts:
    db = FAISS.from_texts(texts=split_texts, embedding=embeddings, metadatas=split_metadatas)
    print("FAISS vector store created successfully from split texts.")

    banned_words_file = "banned_words.txt"
    banned_words = []
    try:
        with open(banned_words_file, 'r') as f:
            banned_words = [line.strip() for line in f if line.strip()]
        if banned_words:
            print(f"Loaded {len(banned_words)} banned words from {banned_words_file}.")
        else:
            print(f"No banned words found in {banned_words_file}.")
    except FileNotFoundError:
        print(f"Error: {banned_words_file} not found. Proceeding without banned words check.")
        banned_words = []

    if banned_words and db:
        print("\nPerforming similarity search for banned words against product data...")
        for banned_word in banned_words:
            search_results = db.similarity_search_with_score(banned_word, k=4)
            if search_results:
                print(f"\n--- Results for banned word: '{banned_word}' ---")
                for doc, score in search_results:
                    original_product_id = doc.metadata.get('original_product_id', 'N/A')
                    original_product_name = doc.metadata.get('original_product_name', 'N/A')
                    description = doc.metadata.get('description', 'N/A')
                    print(f"  Similar chunk: \"{doc.page_content}\" (Score: {score:.4f})")
                    print(f"    Original Product ID: {original_product_id}, Name: {original_product_name}")
                    print(f"    Description: {description}")
                    if original_product_id != 'N/A':
                        flagged_products_for_insertion.add((original_product_id, original_product_name, description if description else ""))
            else:
                print(f"  No significant similarity found for banned word: '{banned_word}'")
    elif not banned_words:
        print("\nSkipping banned words check as no banned words were loaded.")
else:
    print("No products found in the database or no text generated after splitting to create embeddings. Banned word check and insertion skipped.")

if flagged_products_for_insertion:
    print(f"\nAttempting to insert {len(flagged_products_for_insertion)} unique flagged product(s) into 'filtered_products' table...")
    session = SessionLocal()
    inserted_count = 0
    for p_id, original_name, desc in flagged_products_for_insertion:
        exists = session.query(FilteredProduct).filter(FilteredProduct.product_id == p_id).first()
        if not exists:
            filtered_product_entry = FilteredProduct(
                product_id=p_id,
                name="",
                description=desc
            )
            session.add(filtered_product_entry)
            inserted_count += 1
            print(f"  Flagged product ID '{p_id}' (Original Name: '{original_name}') prepared for insertion into 'filtered_products' with name removed.")
        else:
            print(f"  Product with ID '{p_id}' (Original Name: '{original_name}') already exists in 'filtered_products'. Skipping.")
    
    if inserted_count > 0:
        session.commit()
        print(f"Successfully inserted {inserted_count} new product(s) into 'filtered_products' table (with names removed).")
    else:
        print("No new products were inserted into 'filtered_products' table (either none flagged or all were duplicates).")
    session.close()
elif split_texts:
    print("\nNo products were flagged for insertion into 'filtered_products' based on banned word similarity.")

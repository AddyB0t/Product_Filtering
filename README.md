# Project Title: Product Filtering System

## Description

This project is a Python-based system designed to filter products from a database based on a list of banned words. It utilizes semantic similarity search to identify products whose names or descriptions contain or are closely related to any of the specified banned words. Flagged products are then stored in a separate table, with their names removed, for further review or action.

The system connects to a PostgreSQL database to fetch product information and store the filtered results. It uses HuggingFace sentence embeddings and FAISS for efficient similarity searching.

## Features

- **Database Integration**: Connects to a PostgreSQL database to retrieve product data and store filtered product IDs.
- **Semantic Search**: Employs `sentence-transformers` embeddings and FAISS vector store for identifying products similar to banned words.
- **Text Splitting**: Uses `RecursiveCharacterTextSplitter` from Langchain to break down product information into manageable chunks for embedding.
- **Banned Word Filtering**: Reads a list of banned words from a text file and checks product data against this list.
- **Selective Data Storage**: Inserts only the `product_id` and `description` of flagged products into a `filtered_products` table, omitting the name.
- **Environment Configuration**: Uses `.env` files for managing database credentials and other configurations.
- **Automatic Table Creation**: SQLAlchemy models define the database schema, and tables are created automatically if they don'''t exist.

## Technologies Used

- **Python 3.x**
- **Langchain**:
    - `HuggingFaceEmbeddings`: For generating text embeddings.
    - `FAISS`: For efficient similarity search in vector space.
    - `RecursiveCharacterTextSplitter`: For text processing.
- **Sentence Transformers**: `all-MiniLM-L6-v2` model for generating embeddings.
- **SQLAlchemy**: For ORM and database interaction with PostgreSQL.
- **psycopg2-binary**: PostgreSQL adapter for Python.
- **PyTorch**: As a backend for HuggingFace Transformers (CPU/GPU compatible).
- **python-dotenv**: For managing environment variables.
- **NumPy**
- **FAISS-CPU**: For the vector store.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-name>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    Ensure you have `requirements.txt` in your project root.
    ```bash
    pip install -r requirements.txt
    ```
    The `requirements.txt` should include:
    ```
    langchain
    langchain-huggingface
    faiss-cpu
    torch
    sqlalchemy
    psycopg2-binary
    python-dotenv
    sentence-transformers
    numpy
    ```

4.  **Set up PostgreSQL Database:**
    - Ensure you have a PostgreSQL server running.
    - Create a database for this project.
    - Update the `.env` file with your database credentials.

5.  **Configure Environment Variables:**
    Create a `.env` file in the root of the project with the following content, replacing the placeholder values with your actual database connection details:
    ```env
    DB_USER="your_db_user"
    DB_PASSWORD="your_db_password"
    DB_HOST="your_db_host"
    DB_PORT="5432" # Or your PostgreSQL port if different
    DB_NAME="your_db_name"
    ```

## Database Schema

The script defines and uses the following SQLAlchemy models, which correspond to tables in your database:

-   `companies`: Stores company information.
    -   `id` (Integer, Primary Key)
    -   `name` (String, Not Null)
    -   `address` (String)
    -   `gst_no` (String, Unique)
-   `products`: Stores product details, linked to a company.
    -   `id` (Integer, Primary Key)
    -   `product_id` (String, Unique)
    -   `name` (String, Not Null)
    -   `description` (String)
    -   `company_id` (Integer, Foreign Key to `companies.id`)
-   `filtered_products`: Stores products that have been flagged by the system.
    -   `id` (Integer, Primary Key)
    -   `product_id` (String, Foreign Key to `products.product_id`)
    -   `name` (String, Not Null) - *Note: In the script, this is inserted as an empty string for flagged products.*
    -   `description` (String)

The script will automatically create these tables if they do not exist when `Base.metadata.create_all(engine)` is called.

## Banned Words

-   Create a file named `banned_words.txt` in the root directory of the project.
-   Add one banned word or phrase per line in this file.
    Example `banned_words.txt`:
    ```
    prohibited_item
    restricted_substance
    illegal_product_X
    ```
-   The system reads this file to get the list of words to check against product data. If the file is not found or is empty, the banned word check will be skipped.

## Usage

1.  **Populate your database**: Ensure your `companies` and `products` tables in the PostgreSQL database are populated with the necessary data.

2.  **Prepare `banned_words.txt`**: Make sure the `banned_words.txt` file is present in the project root and contains the words/phrases you want to filter by.

3.  **Run the script:**
    Execute the `task.py` script from the root of your project:
    ```bash
    python task.py
    ```

4.  **Output**:
    - The script will print logs to the console, indicating its progress:
        - Database connection status.
        - FAISS vector store creation.
        - Loading of banned words.
        - Results of similarity searches for each banned word.
        - Products flagged for insertion into `filtered_products`.
        - Status of insertion into the `filtered_products` table.
    - Flagged products (their IDs and descriptions) will be inserted into the `filtered_products` table in your database. Their original names will be omitted in this table.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m '''Add some AmazingFeature'''`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details (if applicable, consider adding a LICENSE file). 

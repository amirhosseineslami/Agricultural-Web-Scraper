# Agricultural Web Scraper

This project is a **web scraping tool developed for Lotus Futurist**, designed to extract structured data from various online sources, primarily focusing on **e-commerce and agricultural websites**. It leverages **asynchronous programming with Python and Playwright** to efficiently gather, process, and organize information for analysis and reporting.

---

## Key Features & Benefits

* **Asynchronous Web Scraping:** Uses `asyncio` and `playwright` for concurrent web requests, significantly improving scraping speed.
* **Multiple Website Support:** Capable of scraping data from various websites, including Digikala, Basalam, Agriplus, and more.
* **Data Normalization:** Persian number normalization ensures consistent and clean datasets.
* **Modular Design:** Base searcher class allows easy extension to new websites.
* **Data Processing:** Includes functionality to clean, preprocess, and transform extracted data.
* **File Mapping & Archiving:** Automatically organizes scraped data into file maps and zip archives.

---

## Prerequisites & Dependencies

Ensure the following are installed before running the project:

* **Python 3.7+**
* **Node.js** (required for Playwright)
* **Python Packages:** `playwright`, `pandas`, `aiohttp`
* Install dependencies via a `requirements.txt` file:

```text
playwright
pandas
aiohttp
```

---

## Installation & Setup

1. **Clone the Repository**

```bash
git clone https://github.com/amirhosseineslami/webscraping.git
cd webscraping
```

2. **Create a Virtual Environment (Recommended)**

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

4. **Install Playwright Browsers**

```bash
playwright install
```

---

## Usage Examples

### Run the Main Script

```bash
python main.py
```

Modify the script to specify search queries and target websites.

---

### Persian Number Normalization

```python
from persianNumberNormalizer import PersianNumberNormalizer

normalizer = PersianNumberNormalizer()
persian_number = "۱۲۳۴۵"
normalized_number = normalizer.normalize(persian_number)
print(f"Original Persian number: {persian_number}, Normalized: {normalized_number}")
# Output: Original Persian number: ۱۲۳۴۵, Normalized: 12345
```

---

## Configuration

* **Websites to Scrape:** Edit `constants.py` to add/remove target websites:

```python
sources = [
    "https://www.bbk-iran.com/",
    "https://shimistore.com/",
    # Add more as needed
]
```

* **Search Queries:** Modify queries in `main.py` or specific site modules (e.g., `searchInDigikoud.py`) to target desired data.

---

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature or bugfix branch
3. Implement your changes following project conventions
4. Test thoroughly
5. Submit a pull request explaining your changes

---

## License

All rights reserved by **Amirhossein Eslami**. License is not specified.

---

## Acknowledgments

* Developed for **Lotus Futurist**.
* Utilizes **Playwright** for web automation and scraping.
* Structured according to **Python best practices** for modular, maintainable code.

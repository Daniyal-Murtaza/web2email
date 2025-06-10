from flask import Flask, request, render_template
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "daniyalmurtaza77@gmail.com"
SMTP_PASSWORD = "vkej tzrb pdfo albd"

def get_basic_template() -> str:
    """Return a Bootstrap-based HTML template."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Webpage Snapshot</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            .book-card { margin-bottom: 20px; }
            .book-image { max-width: 200px; height: auto; }
            .book-title { font-size: 1.2rem; font-weight: bold; }
            .book-price { color: #28a745; font-weight: bold; }
            .book-rating { color: #ffc107; }
            .category-header { background-color: #f8f9fa; padding: 20px; margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <div class="container py-4">
            <div class="category-header">
                <h1 id="title" class="mb-3"></h1>
                <div id="category-info" class="text-muted"></div>
            </div>
            <div class="row" id="main-content">
                <!-- Book cards will be inserted here -->
            </div>
        </div>
    </body>
    </html>
    """

def extract_content(soup: BeautifulSoup) -> dict:
    """Extract content from the webpage."""
    content = {
        "title": "",
        "category_info": "",
        "books": [],
        "images": []
    }
    
    try:
        # Extract title
        if soup.title:
            content["title"] = soup.title.string
            logger.info(f"Extracted title: {content['title']}")
        
        # Extract category info
        category_info = soup.find('div', class_='woocommerce-result-count')
        if category_info:
            content["category_info"] = category_info.get_text(strip=True)
        
        # Extract books
        book_elements = soup.find_all('li', class_='product')
        for book in book_elements:
            book_data = {
                'title': '',
                'price': '',
                'rating': '',
                'image': '',
                'link': ''
            }
            
            # Extract title
            title_elem = book.find('h2', class_='woocommerce-loop-product__title')
            if title_elem:
                book_data['title'] = title_elem.get_text(strip=True)
            
            # Extract price
            price_elem = book.find('span', class_='price')
            if price_elem:
                book_data['price'] = price_elem.get_text(strip=True)
            
            # Extract rating
            rating_elem = book.find('div', class_='star-rating')
            if rating_elem:
                book_data['rating'] = rating_elem.get('title', '')
            
            # Extract image
            img_elem = book.find('img')
            if img_elem and img_elem.get('src'):
                book_data['image'] = img_elem['src']
            
            # Extract link
            link_elem = book.find('a', class_='woocommerce-LoopProduct-link')
            if link_elem and link_elem.get('href'):
                book_data['link'] = link_elem['href']
            
            if book_data['title']:  # Only add if we have at least a title
                content["books"].append(book_data)
        
        logger.info(f"Extracted {len(content['books'])} books")
        
    except Exception as e:
        logger.error(f"Error extracting content: {e}")
    
    return content

def create_email_html(content: dict) -> str:
    """Create email HTML from content."""
    try:
        template = get_basic_template()
        soup = BeautifulSoup(template, 'html.parser')
        
        # Set title
        title_elem = soup.find('h1', id='title')
        if title_elem:
            title_elem.string = content["title"] or "Webpage Snapshot"
        
        # Set category info
        category_info_elem = soup.find('div', id='category-info')
        if category_info_elem and content["category_info"]:
            category_info_elem.string = content["category_info"]
        
        # Set main content
        main_content_elem = soup.find('div', id='main-content')
        if main_content_elem:
            # Add book cards
            for book in content["books"]:
                # Create book card
                card = soup.new_tag('div')
                card['class'] = 'col-md-4 book-card'
                
                # Create card content
                card_html = f"""
                    <div class="card h-100">
                        <img src="{book['image']}" class="card-img-top book-image mx-auto mt-3" alt="{book['title']}">
                        <div class="card-body">
                            <h5 class="card-title book-title">{book['title']}</h5>
                            <p class="card-text book-rating">{book['rating']}</p>
                            <p class="card-text book-price">{book['price']}</p>
                        </div>
                    </div>
                """
                card.append(BeautifulSoup(card_html, 'html.parser'))
                main_content_elem.append(card)
        
        return str(soup)
    except Exception as e:
        logger.error(f"Error creating email HTML: {e}")
        return ""

def send_email(html_content: str, subject: str, to_email: str):
    """Send the email."""
    if not html_content:
        raise ValueError("Empty HTML content")
    
    msg = MIMEText(html_content, "html")
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        logger.info(f"✅ Email sent to {to_email}")
    except Exception as e:
        logger.error(f"❌ Email sending failed: {e}")
        raise

@app.route('/', methods=['GET', 'POST'])
def index():
    email_html = ""
    error = ""
    success = ""

    if request.method == 'POST':
        url = request.form.get('url')
        recipient = request.form.get('recipient')

        try:
            logger.info(f"Processing URL: {url}")
            
            # Fetch and parse the webpage
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'iframe', 'noscript']):
                tag.decompose()
            
            # Extract content
            content = extract_content(soup)
            logger.info("Content extracted successfully")
            
            # Create email HTML
            email_html = create_email_html(content)
            if not email_html:
                raise ValueError("Failed to create email HTML")
            
            logger.info("Email HTML created successfully")
            
            # Save for inspection
            with open("email_template.html", "w", encoding="utf-8") as f:
                f.write(email_html)
            logger.info("Email template saved to file")

            if recipient:
                send_email(email_html, f"Snapshot of {url}", recipient)
                success = f"✅ Email sent successfully to {recipient}!"

        except Exception as e:
            error = f"❌ Error: {e}"
            logger.error(f"Error in index route: {e}")

    return render_template('index.html', email_html=email_html, error=error, success=success)

if __name__ == '__main__':
    app.run(debug=True)

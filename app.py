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
    """Return a simplified HTML template."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Webpage Snapshot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                text-align: center;
                padding: 20px 0;
                background: #fff;
                margin-bottom: 20px;
            }
            .logo {
                max-width: 200px;
                height: auto;
            }
            .book-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 20px;
                padding: 20px;
            }
            .book-card {
                background: #fff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: transform 0.2s;
                display: flex;
                flex-direction: column;
            }
            .book-card:hover {
                transform: translateY(-5px);
            }
            .book-image-container {
                width: 100%;
                height: 300px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f8f8f8;
                padding: 20px;
            }
            .book-image {
                max-width: 100%;
                max-height: 100%;
                width: auto;
                height: auto;
                object-fit: contain;
            }
            .book-info {
                padding: 15px;
                flex-grow: 1;
                display: flex;
                flex-direction: column;
            }
            .book-title {
                font-size: 16px;
                font-weight: bold;
                margin: 0 0 10px 0;
                color: #333;
                line-height: 1.4;
                min-height: 44px; /* Approximately 2 lines of text */
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .book-price {
                color: #28a745;
                font-weight: bold;
                margin: 5px 0;
            }
            .book-rating {
                color: #ffc107;
                margin: 5px 0;
            }
            .category-title {
                background: #fff;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .footer {
                text-align: center;
                padding: 20px;
                background: #fff;
                margin-top: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .btn {
                display: inline-block;
                padding: 10px 20px;
                background: #007bff;
                color: #fff;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 10px;
            }
            .btn:hover {
                background: #0056b3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="#" id="site-logo-link">
                    <img id="site-logo" class="logo" src="" alt="Todos Los Libros">
                </a>
            </div>
            
            <div class="category-title">
                <h1 id="title"></h1>
                <div id="category-info"></div>
            </div>
            
            <div class="book-grid" id="main-content">
                <!-- Book cards will be inserted here -->
            </div>
            
            <div class="footer">
                <p>Visit our website for more books and information</p>
                <a href="#" id="footer-link" class="btn">Visit Website</a>
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
        "logo": {"src": "", "link": ""},
        "site_url": ""
    }
    
    try:
        # Extract site URL
        content["site_url"] = soup.find('link', rel='canonical')
        if content["site_url"]:
            content["site_url"] = content["site_url"].get('href', '')
        
        # Extract logo - try multiple specific selectors
        logo_selectors = [
            'div.custom-logo-link img',
            'div.site-logo img',
            'header img.logo',
            'a.custom-logo-link img',
            'img.custom-logo',
            'img[src*="logo"]',
            'img[src*="todosloslibros"]'
        ]
        
        for selector in logo_selectors:
            logo = soup.select_one(selector)
            if logo:
                content["logo"]["src"] = logo.get('src', '')
                # Try to get the parent link
                parent_link = logo.find_parent('a')
                if parent_link:
                    content["logo"]["link"] = parent_link.get('href', '')
                break
        
        # If still no logo, try to find the site title
        if not content["logo"]["src"]:
            site_title = soup.select_one('div.site-title, h1.site-title')
            if site_title:
                content["logo"]["text"] = site_title.get_text(strip=True)
        
        # Extract title
        title = soup.select_one('h1.page-title, h1.entry-title, h1.product_title')
        if title:
            content["title"] = title.get_text(strip=True)
        elif soup.title:
            content["title"] = soup.title.string
        
        # Extract category info
        category_info = soup.select_one('div.woocommerce-result-count, p.woocommerce-result-count')
        if category_info:
            content["category_info"] = category_info.get_text(strip=True)
        
        # Extract books
        book_elements = soup.select('li.product, div.product')
        for book in book_elements:
            book_data = {
                'title': '',
                'price': '',
                'rating': '',
                'image': '',
                'link': ''
            }
            
            # Extract title and link
            title_elem = book.select_one('h2.woocommerce-loop-product__title, h2.product-title')
            if title_elem:
                book_data['title'] = title_elem.get_text(strip=True)
                link_elem = title_elem.find_parent('a')
                if link_elem:
                    book_data['link'] = link_elem.get('href', '')
            
            # Extract price
            price_elem = book.select_one('span.price, p.price')
            if price_elem:
                book_data['price'] = price_elem.get_text(strip=True)
            
            # Extract rating
            rating_elem = book.select_one('div.star-rating')
            if rating_elem:
                book_data['rating'] = rating_elem.get('title', '')
            
            # Extract image
            img_elem = book.select_one('img.attachment-woocommerce_thumbnail, img.wp-post-image')
            if img_elem and img_elem.get('src'):
                book_data['image'] = img_elem['src']
            
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
        
        # Set logo
        logo_elem = soup.find('img', id='site-logo')
        if logo_elem:
            if content["logo"]["src"]:
                logo_elem['src'] = content["logo"]["src"]
            elif "text" in content["logo"]:
                # If no logo image, use text
                logo_elem.replace_with(BeautifulSoup(f'<h1 class="site-title">{content["logo"]["text"]}</h1>', 'html.parser'))
        
        logo_link = soup.find('a', id='site-logo-link')
        if logo_link and content["logo"]["link"]:
            logo_link['href'] = content["logo"]["link"]
        
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
                card_html = f"""
                    <div class="book-card">
                        <a href="{book['link']}" style="text-decoration: none; color: inherit;">
                            <div class="book-image-container">
                                <img src="{book['image']}" class="book-image" alt="{book['title']}">
                            </div>
                            <div class="book-info">
                                <h3 class="book-title" title="{book['title']}">{book['title']}</h3>
                                <p class="book-rating">{book['rating']}</p>
                                <p class="book-price">{book['price']}</p>
                            </div>
                        </a>
                    </div>
                """
                main_content_elem.append(BeautifulSoup(card_html, 'html.parser'))
        
        # Set footer link
        footer_link = soup.find('a', id='footer-link')
        if footer_link and content["site_url"]:
            footer_link['href'] = content["site_url"]
        
        return str(soup)
    except Exception as e:
        logger.error(f"Error creating email HTML: {e}")
        return ""

def send_email(html_content: str, subject: str, to_emails: list):
    """Send the email to multiple recipients."""
    if not html_content:
        raise ValueError("Empty HTML content")
    
    if not to_emails:
        raise ValueError("No recipients specified")
    
    msg = MIMEText(html_content, "html")
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(to_emails)  # Join multiple emails with commas

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_emails, msg.as_string())
        logger.info(f"✅ Email sent to {len(to_emails)} recipients")
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
        recipients = request.form.get('recipients', '').strip()

        try:
            # Validate and process recipients
            if not recipients:
                raise ValueError("No recipients specified")
            
            # Split recipients by comma or newline and clean up
            recipient_list = [email.strip() for email in recipients.replace('\n', ',').split(',') if email.strip()]
            
            # Basic email validation
            for email in recipient_list:
                if '@' not in email or '.' not in email:
                    raise ValueError(f"Invalid email address: {email}")

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

            if recipient_list:
                send_email(email_html, f"Snapshot of {url}", recipient_list)
                success = f"✅ Email sent successfully to {len(recipient_list)} recipients!"

        except Exception as e:
            error = f"❌ Error: {e}"
            logger.error(f"Error in index route: {e}")

    return render_template('index.html', email_html=email_html, error=error, success=success)

if __name__ == '__main__':
    app.run(debug=True)

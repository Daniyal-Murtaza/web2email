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
SMTP_USER = "danielzaydee@gmail.com"
SMTP_PASSWORD = "ahcc crvg xyao lseq"

def get_basic_template() -> str:
    """Return a simplified HTML template suitable for a 4-column grid flyer-style book layout."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Book Flyer</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

            body {
                font-family: 'Poppins', sans-serif;
                background-color: #1e1e1e;
                margin: 0;
                padding: 0;
                color: #ffffff;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }

            .book-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 30px;
                padding: 20px 0;
            }

            .book-card {
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
                background: transparent;
                color: #ffffff;
            }

            .book-image-container {
                width: 100%;
                height: 240px;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
                background-color: #2d2d2d;
                border-radius: 8px;
            }

            .book-image {
                max-height: 100%;
                max-width: 100%;
                object-fit: contain;
            }

            .book-info {
                margin-top: 10px;
            }

            .book-title {
                font-size: 15px;
                font-weight: 600;
                line-height: 1.3;
                color: #ffffff;
                margin: 10px 0 0 0;
                max-height: 40px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            /* Optional Responsive Tweak */
            @media (max-width: 1024px) {
                .book-grid {
                    grid-template-columns: repeat(3, 1fr);
                }
            }

            @media (max-width: 768px) {
                .book-grid {
                    grid-template-columns: repeat(2, 1fr);
                }
            }

            @media (max-width: 480px) {
                .book-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="book-grid" id="main-content">
                <!-- Dynamic book cards will be inserted here -->
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
                logo_elem.replace_with(BeautifulSoup(f'<h1 class="site-title">{content["logo"]["text"]}</h1>', 'html.parser'))

        logo_link = soup.find('a', id='site-logo-link')
        if logo_link and content["logo"]["link"]:
            logo_link['href'] = content["logo"]["link"]

        # Set title
        title_elem = soup.find('h1', id='title')
        if title_elem:
            title_elem.string = content.get("title", "Webpage Snapshot")

        # Set category info
        category_info_elem = soup.find('div', id='category-info')
        if category_info_elem and content.get("category_info"):
            category_info_elem.string = content["category_info"]

        # Set main content
        main_content_elem = soup.find('div', id='main-content')
        if main_content_elem:
            # Create a table to ensure 4-column layout compatibility in email
            table_html = '<table width="100%" cellspacing="0" cellpadding="10" style="border-collapse: collapse;"><tbody>'
            
            books = content.get("books", [])
            for i in range(0, len(books), 4):
                table_html += '<tr>'
                for j in range(4):
                    if i + j < len(books):
                        book = books[i + j]
                        table_html += f"""
                            <td align="center" valign="top" width="25%" style="padding: 10px;">
                                <a href="{book['link']}" style="text-decoration: none; color: inherit;">
                                    <div class="book-image-container" style="width: 100%; height: 250px; background-color: #2d2d2d; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                                        <img src="{book['image']}" class="book-image" alt="{book['title']}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                                    </div>
                                    <div class="book-info" style="margin-top: 10px; text-align: center;">
                                        <h3 class="book-title" style="font-size: 15px; font-weight: 600; color: #ffffff; margin: 10px 0 0 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{book['title']}</h3>
                                    </div>
                                </a>
                            </td>
                        """
                    else:
                        table_html += '<td></td>'  # Fill remaining cells if not multiple of 4
                table_html += '</tr>'
            table_html += '</tbody></table>'

            # Replace content with the table
            main_content_elem.clear()
            main_content_elem.append(BeautifulSoup(table_html, 'html.parser'))

        # Set footer link
        footer_link = soup.find('a', id='footer-link')
        if footer_link and content.get("site_url"):
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
        mode = request.form.get('mode', 'url')
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

            if mode == 'url':
                url = request.form.get('url')
                if not url:
                    raise ValueError("URL is required in URL mode")

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
                
                subject = f"Snapshot of {url}"
            else:  # direct mode
                subject = request.form.get('subject', '')
                if not subject:
                    raise ValueError("Subject is required in direct mode")
                
                email_content = request.form.get('email_content', '')
                if not email_content:
                    raise ValueError("Email content is required in direct mode")
                
                # Create a basic HTML template for direct email
                email_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{subject}</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            max-width: 800px;
                            margin: 0 auto;
                            padding: 20px;
                        }}
                    </style>
                </head>
                <body>
                    {email_content}
                </body>
                </html>
                """
            
            logger.info("Email HTML created successfully")
            
            # Save for inspection
            with open("email_template.html", "w", encoding="utf-8") as f:
                f.write(email_html)
            logger.info("Email template saved to file")

            if recipient_list:
                send_email(email_html, subject, recipient_list)
                success = f"✅ Email sent successfully to {len(recipient_list)} recipients!"

        except Exception as e:
            error = f"❌ Error: {e}"
            logger.error(f"Error in index route: {e}")

    return render_template('index.html', email_html=email_html, error=error, success=success)

if __name__ == '__main__':
    app.run(debug=True)

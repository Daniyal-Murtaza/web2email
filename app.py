from flask import Flask, request, render_template
import requests
from bs4 import BeautifulSoup
from premailer import transform
import smtplib
from email.mime.text import MIMEText
from urllib.parse import urljoin, urlparse
import re

app = Flask(__name__)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "daniyalmurtaza77@gmail.com"  # Replace with your Gmail address
SMTP_PASSWORD = "vkej tzrb pdfo albd"     # Replace with your Gmail App Password

def send_email(html_content, subject, to_email):
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
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        raise

def fetch_css(css_url):
    try:
        resp = requests.get(css_url, timeout=5)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"⚠️ Could not fetch CSS {css_url}: {e}")
        return ""

def inline_images(soup, base_url):
    # Optionally, you can embed images as base64 (may increase email size)
    # For now, fix relative src attributes
    for img in soup.find_all('img'):
        if img.has_attr('src'):
            img['src'] = urljoin(base_url, img['src'])
    return soup

@app.route('/', methods=['GET', 'POST'])

def index():
    email_html = ""
    error = ""
    success = ""

    if request.method == 'POST':
        url = request.form.get('url')
        recipient = request.form.get('recipient')

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove scripts, iframes, noscript, comments for safety
            for tag in soup(['script', 'iframe', 'noscript']):
                tag.decompose()

            # Remove comments - sometimes they break premailer
            for comment in soup.find_all(string=lambda text: isinstance(text, type(soup.Comment))):
                comment.extract()

            # Fix all relative URLs for <img>, <a>, <link>, and background images in inline styles
            for tag in soup.find_all(['img', 'a', 'link']):
                attr = 'href' if tag.name in ['a', 'link'] else 'src'
                if tag.has_attr(attr):
                    tag[attr] = urljoin(url, tag[attr])

            # Fix background URLs in inline styles (e.g. style="background: url(...)")
            for tag in soup.find_all(style=True):
                style = tag['style']
                urls = re.findall(r'url\((.*?)\)', style)
                for u in urls:
                    clean_url = u.strip('\'"')
                    abs_url = urljoin(url, clean_url)
                    style = style.replace(u, abs_url)
                tag['style'] = style

            # Fetch external CSS from all <link rel="stylesheet"> and remove the links
            combined_css = ""
            for link in soup.find_all('link', rel='stylesheet'):
                href = link.get('href')
                if href:
                    combined_css += fetch_css(href) + "\n"
                link.decompose()

            # Insert combined CSS inside <style> in <head>
            style_tag = soup.new_tag("style")
            style_tag.string = combined_css
            if soup.head:
                soup.head.append(style_tag)
            else:
                new_head = soup.new_tag("head")
                new_head.append(style_tag)
                soup.insert(0, new_head)

            # Optionally fix <meta charset> tag for emails (some clients need it)
            if not soup.head.find('meta', attrs={'charset': True}):
                meta_tag = soup.new_tag("meta", charset="UTF-8")
                soup.head.insert(0, meta_tag)

            # Convert soup back to html string
            raw_html = str(soup)

            # Use premailer to inline styles (with options)
            email_html = transform(
                raw_html,
                base_url=url,
                remove_classes=True,
                strip_important=False,
                keep_style_tags=True,
                include_star_selectors=True
            )

            # Save for inspection (optional)
            with open("email_template.html", "w", encoding="utf-8") as f:
                f.write(email_html)

            if recipient:
                send_email(email_html, f"Snapshot of {url}", recipient)
                success = f"✅ Email sent successfully to {recipient}!"

        except Exception as e:
            error = f"❌ Error: {e}"

    return render_template('index.html', email_html=email_html, error=error, success=success)

if __name__ == '__main__':
    app.run(debug=True)

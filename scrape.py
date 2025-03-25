from selenium.webdriver import Remote, ChromeOptions
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
AUTH = 'brd-customer-hl_39ef1813-zone-poke_scraper:2ae8wsj35itx'
SBR_WEBDRIVER = f'https://{AUTH}@brd.superproxy.io:9515'


def scrapeSite(url):
    sbr_connection = ChromiumRemoteConnection(SBR_WEBDRIVER, 'goog', 'chrome')
    with Remote(sbr_connection, options=ChromeOptions()) as driver:
        print('Connected! Navigating...')
        driver.get(url)
        print('Taking page screenshot to file page.png')
        driver.get_screenshot_as_file('./page.png')
        print('Navigated! Scraping page content...')
        html = driver.page_source
        print(html)
        return html

def extract_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    bodyContent = soup.body
    if bodyContent: 
        return str(bodyContent)
    else:
        return None
    
def cleanBody(bodyContent):
    soup = BeautifulSoup(bodyContent, 'html.parser')

    for scriptOrStyle in soup(['script', 'style']):
        scriptOrStyle.extract()
    cleanContent = soup.get_text(separator='\n')
    cleanContent = "\n".join(line.strip() for line in cleanContent.splitlines() if line.strip())
    return cleanContent

def splitDomContent(content, max_length=5000):
    return [
        content[i:i+max_length] for i in range(0, len(content), max_length)
    ]



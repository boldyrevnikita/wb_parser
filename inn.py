from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
import time
import os
import sys
import random
import csv
from datetime import datetime
import re

def scrape_wildberries_sellers(max_total_products=100, batch_size=10):
    """Скрипт для сбора информации о продавцах на Wildberries
    
    Args:
        max_total_products: Максимальное количество товаров для обработки (по умолчанию 100)
        batch_size: Количество товаров для обработки в одном пакете (по умолчанию 10)
    """
    
    print("Starting the Wildberries scraper...")
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Hide automation
    
    # Try different user agents to avoid detection
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ]
    
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    # Add experimental options to avoid detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Add SSL error handling
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    
    # Create results directory
    results_dir = "sellers_info"
    os.makedirs(results_dir, exist_ok=True)
    
    # Create CSV file for results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = os.path.join(results_dir, f"wildberries_sellers_{timestamp}.csv")
    
    # Create CSV file and write header
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['product_name', 'product_url', 'seller_name', 'seller_info']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    # List of categories to try in case we run out of products
    categories = [
        "https://www.wildberries.ru/catalog/dom-i-dacha/kuhnya/poryadok-na-kuhne",
        "https://www.wildberries.ru/catalog/dom-i-dacha/kuhnya/stolovye-pribory",
        "https://www.wildberries.ru/catalog/dom-i-dacha/kuhnya/posuda-dlya-prigotovleniya",
        "https://www.wildberries.ru/catalog/dom-i-dacha/kuhnya/chayniki",
        "https://www.wildberries.ru/catalog/bytovaya-tehnika/tehnika-dlya-kuhni",
        "https://www.wildberries.ru/catalog/krasota/uhod-za-kozhey/uhod-za-litsom",
        "https://www.wildberries.ru/catalog/elektronika/tehnika-dlya-doma"
    ]
    
    # Keep track of processed products
    processed_urls = set()
    processed_ids = set()
    results = []
    total_processed = 0
    current_category_index = 0
    
    try:
        # Try using an existing Chrome installation or default to ChromeDriver directly
        print("Initializing Chrome driver...")
        driver_path = None
        
        # Check if chromedriver exists in the current directory
        if os.path.exists("chromedriver.exe"):
            driver_path = "chromedriver.exe"
            print(f"Using local chromedriver: {driver_path}")
            driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        else:
            # Try to initialize Chrome without webdriver_manager
            print("Trying to initialize Chrome directly...")
            driver = webdriver.Chrome(options=chrome_options)
        
        print("Chrome driver initialized successfully.")
        
        # Set a page load timeout
        driver.set_page_load_timeout(60)
        
        try:
            # Add bot detection evasion
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                """
            })
            
            # Function to extract product ID from URL
            def extract_product_id(url):
                if not url:
                    return None
                try:
                    match = re.search(r'/catalog/(\d+)/', url)
                    if match:
                        return match.group(1)
                    return None
                except:
                    return None
            
            # Function to find product cards in different ways
            def find_product_cards():
                # First, try product cards with detail links
                try:
                    detail_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/detail.aspx')]")
                    if detail_links and len(detail_links) > 0:
                        print(f"Found {len(detail_links)} direct product links with '/detail.aspx'")
                        return detail_links, "Direct product links"
                except Exception as e:
                    print(f"Failed to find direct product links: {str(e)}")
                
                # Second, try with data-nm-id attribute
                try:
                    items_with_nm_id = driver.find_elements(By.XPATH, "//*[@data-nm-id]")
                    if items_with_nm_id and len(items_with_nm_id) > 0:
                        print(f"Found {len(items_with_nm_id)} elements with 'data-nm-id' attribute")
                        return items_with_nm_id, "data-nm-id elements"
                except Exception as e:
                    print(f"Failed to find elements with data-nm-id: {str(e)}")
                
                # Try different selectors for product cards
                product_card_selectors = [
                    ".product-card__wrapper", 
                    ".product-card",
                    ".j-card-item",
                    "article[class*='product-card']",
                    ".card-cell",
                    ".catalog-card",
                    "a[class*='product-card__main']",
                    ".j-card",
                    "a.product-card__img"
                ]
                
                for selector in product_card_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and len(elements) > 0:
                            print(f"Found {len(elements)} elements with selector: {selector}")
                            return elements, selector
                    except Exception as e:
                        print(f"Selector {selector} failed: {str(e)}")
                
                # XPath alternatives
                xpath_selectors = [
                    "//div[contains(@class, 'product-card')]",
                    "//article[contains(@class, 'product')]",
                    "//a[contains(@href, '/catalog/') and contains(@href, '/detail.aspx')]",
                    "//a[contains(@class, 'product-card__main')]"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, xpath)
                        if elements and len(elements) > 0:
                            print(f"Found {len(elements)} elements with XPath: {xpath}")
                            return elements, xpath
                    except Exception as e:
                        print(f"XPath {xpath} failed: {str(e)}")
                
                # Last resort - all catalog links
                try:
                    catalog_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/catalog/')]")
                    valid_links = []
                    for link in catalog_links:
                        href = link.get_attribute('href')
                        # Filter out category links
                        if href and '/catalog/' in href and not any(x in href for x in ['/zhenshchinam', '/muzhchinam', '/detyam', '/dom-i-dacha', '/krasota', '/aksessuary', '/elektronika']):
                            valid_links.append(link)
                    
                    if valid_links and len(valid_links) > 0:
                        print(f"Found {len(valid_links)} potential product links")
                        return valid_links, "Filtered catalog links"
                except Exception as e:
                    print(f"Failed to find catalog links: {str(e)}")
                
                return None, None
            
            # Function to get product details from a card
            def get_product_details(product_card, card_index):
                try:
                    product_name = ""
                    product_url = ""
                    
                    # Try to get product name
                    try:
                        name_selectors = [".product-card__name", ".goods-name", "span[class*='name']", ".card__title"]
                        for selector in name_selectors:
                            elements = product_card.find_elements(By.CSS_SELECTOR, selector)
                            if elements and len(elements) > 0 and elements[0].text:
                                product_name = elements[0].text
                                break
                        
                        # If still no name, try to get any text
                        if not product_name:
                            product_name = product_card.text.split('\n')[0] if product_card.text else f"Product {card_index}"
                    except:
                        product_name = f"Product {card_index}"
                    
                    # Try to get product URL
                    try:
                        # If card is an <a> tag, get href
                        if product_card.tag_name == 'a':
                            product_url = product_card.get_attribute('href')
                        else:
                            # Look for an anchor tag inside the card
                            links = product_card.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute('href')
                                if href and ('/detail.aspx' in href or '/catalog/' in href):
                                    product_url = href
                                    break
                            
                        # If we couldn't get URL from card, try URL from data-nm-id
                        if not product_url:
                            nm_id = product_card.get_attribute('data-nm-id')
                            if nm_id:
                                product_url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
                    except:
                        pass
                    
                    # Try to extract product ID
                    product_id = extract_product_id(product_url)
                    
                    # Validate product URL (should contain /detail.aspx or a numeric ID)
                    is_valid = False
                    if product_url and ('/detail.aspx' in product_url or (product_id and product_id.isdigit())):
                        is_valid = True
                    
                    if not is_valid:
                        return None, None, None
                    
                    return product_name, product_url, product_id
                except Exception as e:
                    print(f"Error getting product details: {str(e)}")
                    return None, None, None
            
            # Function to navigate and find products in a category
            def process_category(category_url, page=1):
                try:
                    # Navigate to category URL with page parameter
                    url = category_url
                    if page > 1:
                        if '?' in url:
                            url = f"{url}&page={page}"
                        else:
                            url = f"{url}?page={page}"
                    
                    print(f"\n===== Processing category page: {url} =====\n")
                    driver.get(url)
                    
                    # Wait for page to load
                    time.sleep(5)
                    
                    # Scroll to load dynamic content
                    print("Scrolling to load more products...")
                    for i in range(5):
                        driver.execute_script(f"window.scrollBy(0, {random.randint(500, 1000)});")
                        time.sleep(random.uniform(0.5, 1.5))
                    
                    # Try to find 'Show more' button and click it
                    try:
                        show_more_buttons = driver.find_elements(By.XPATH, 
                            "//button[contains(text(), 'Показать ещё')] | " + 
                            "//button[contains(text(), 'Загрузить ещё')] | " + 
                            "//a[contains(text(), 'Показать ещё')]")
                        
                        for button in show_more_buttons:
                            if button.is_displayed():
                                print("Clicking 'Show more' button...")
                                driver.execute_script("arguments[0].click();", button)
                                time.sleep(3)
                                # Scroll more after clicking
                                for i in range(3):
                                    driver.execute_script(f"window.scrollBy(0, {random.randint(500, 1000)});")
                                    time.sleep(random.uniform(0.5, 1.0))
                                break
                    except Exception as e:
                        print(f"Failed to click 'Show more' button: {str(e)}")
                    
                    # Find product cards
                    product_cards, selector_used = find_product_cards()
                    
                    if not product_cards or len(product_cards) == 0:
                        print("No product cards found on this page")
                        return []
                    
                    print(f"Found {len(product_cards)} product cards using {selector_used}")
                    
                    # Get unique products
                    unique_products = []
                    for i, card in enumerate(product_cards):
                        name, url, product_id = get_product_details(card, i + 1)
                        
                        # Skip invalid products
                        if not url:
                            continue
                        
                        # Skip already processed products
                        if url in processed_urls:
                            continue
                        
                        if product_id and product_id in processed_ids:
                            continue
                        
                        unique_products.append((name, url, product_id))
                    
                    print(f"Found {len(unique_products)} unique products on this page")
                    return unique_products
                    
                except Exception as e:
                    print(f"Error processing category: {str(e)}")
                    return []
            
            # Main processing loop
            while total_processed < max_total_products and current_category_index < len(categories):
                category_url = categories[current_category_index]
                print(f"\n===== Processing category {current_category_index + 1}/{len(categories)}: {category_url} =====\n")
                
                # Process pages of the current category
                page = 1
                consecutive_empty_pages = 0
                max_consecutive_empty_pages = 3
                
                while total_processed < max_total_products and page <= 10 and consecutive_empty_pages < max_consecutive_empty_pages:
                    print(f"\n===== Processing page {page} of category {current_category_index + 1} =====\n")
                    
                    # Get products from current page
                    products = process_category(category_url, page)
                    
                    if not products or len(products) == 0:
                        print(f"No new products found on page {page}")
                        consecutive_empty_pages += 1
                        page += 1
                        continue
                    
                    # Reset counter since we found products
                    consecutive_empty_pages = 0
                    
                    # Process each product
                    for product_name, product_url, product_id in products:
                        if total_processed >= max_total_products:
                            break
                        
                        print(f"\n--- Processing product {total_processed + 1}/{max_total_products} ---")
                        print(f"Product name: {product_name}")
                        print(f"Product URL: {product_url}")
                        print(f"Product ID: {product_id}")
                        
                        # Add to processed sets
                        processed_urls.add(product_url)
                        if product_id:
                            processed_ids.add(product_id)
                        
                        # Navigate to product URL
                        try:
                            print(f"Navigating directly to product URL: {product_url}")
                            driver.get(product_url)
                            print("Navigation successful")
                        except Exception as e:
                            print(f"Error navigating to product: {str(e)}")
                            continue
                        
                        # Wait for product page to load
                        print("Waiting for product page to load...")
                        time.sleep(5)
                        
                        # Print page title and URL for debugging
                        print(f"Product page title: {driver.title}")
                        print(f"Product page URL: {driver.current_url}")
                        
                        # Look for seller info - EXACTLY as in original script
                        seller_info_selectors = [
                            ".seller-info__name", 
                            "span[class*='seller-info']", 
                            "a[href*='/seller/']",
                            ".seller__name",
                            "a[class*='seller']",
                            "div[class*='seller'] a",
                            "div[class*='seller'] span",
                            "span[class*='brand']",
                            "a[class*='brand']",
                            ".brand__info",
                            "a[href*='/brands/']",
                            "*[class*='seller']",
                            "*[class*='vendor']",
                            "*[class*='brand']"
                        ]
                        
                        # XPath alternatives
                        seller_xpath_selectors = [
                            "//span[contains(@class, 'seller')]",
                            "//a[contains(@href, '/seller/')]",
                            "//a[contains(@href, '/brands/')]",
                            "//*[contains(@class, 'seller')]//a",
                            "//*[contains(text(), 'Продавец')]/..//a",  # "Продавец" means "Seller" in Russian
                            "//*[contains(text(), 'Бренд')]/..//a",     # "Бренд" means "Brand" in Russian
                            "//a[contains(@class, 'seller')]"
                        ]
                        
                        seller_info = None
                        seller_selector_used = None
                        
                        # Try CSS selectors first
                        for selector in seller_info_selectors:
                            print(f"Trying to find seller info with selector: {selector}")
                            try:
                                # First try find_elements
                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                if elements and len(elements) > 0:
                                    for elem in elements:
                                        try:
                                            if elem.is_displayed():
                                                # Check if this is a real seller element (not "Sell on Wildberries")
                                                text = elem.text
                                                if not text or text == "Продавайте на Wildberries":
                                                    continue
                                                
                                                print(f"Found visible seller element with selector: {selector}")
                                                seller_info = elem
                                                seller_selector_used = selector
                                                break
                                        except:
                                            continue
                                    
                                    if seller_info:
                                        break
                                
                                # If not found, try WebDriverWait
                                seller_info = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                                # Check if this is a real seller element
                                if seller_info:
                                    text = seller_info.text
                                    if not text or text == "Продавайте на Wildberries":
                                        seller_info = None
                                        continue
                                        
                                    print(f"Found seller info with selector: {selector} using WebDriverWait")
                                    seller_selector_used = selector
                                    break
                            except (TimeoutException, NoSuchElementException):
                                print(f"Selector {selector} did not yield results.")
                        
                        # If CSS selectors fail, try XPath
                        if not seller_info:
                            print("CSS selectors failed, trying XPath for seller info...")
                            for xpath in seller_xpath_selectors:
                                print(f"Trying to find seller info with XPath: {xpath}")
                                try:
                                    elements = driver.find_elements(By.XPATH, xpath)
                                    if elements and len(elements) > 0:
                                        for elem in elements:
                                            try:
                                                if elem.is_displayed():
                                                    # Check if this is a real seller element
                                                    text = elem.text
                                                    if not text or text == "Продавайте на Wildberries":
                                                        continue
                                                        
                                                    print(f"Found visible seller element with XPath: {xpath}")
                                                    seller_info = elem
                                                    seller_selector_used = xpath + " (XPath)"
                                                    break
                                            except:
                                                continue
                                        
                                        if seller_info:
                                            break
                                except Exception as e:
                                    print(f"XPath {xpath} failed: {str(e)}")
                        
                        if not seller_info:
                            print("Failed to find seller info. Skipping this product.")
                            continue
                        
                        print(f"Successfully found seller info using: {seller_selector_used}")
                        seller_name = ""
                        seller_url = ""
                        
                        try:
                            seller_name = seller_info.text
                            seller_url = seller_info.get_attribute('href') or ""
                            print(f"Seller info text: {seller_name}")
                            print(f"Seller info href: {seller_url}")
                        except:
                            print("Could not get seller info text or href")
                        
                        # Click on the seller info 
                        print("Clicking on seller info...")
                        try:
                            # Try navigating to href first
                            if seller_url:
                                print(f"Navigating to seller URL: {seller_url}")
                                driver.get(seller_url)
                                print("Navigation to seller URL successful")
                            else:
                                # Try direct click if no URL
                                seller_info.click()
                                print("Direct click on seller info successful")
                        except Exception as e:
                            print(f"First attempt to access seller info failed: {str(e)}, trying JavaScript click...")
                            try:
                                driver.execute_script("arguments[0].click();", seller_info)
                                print("JavaScript click on seller info successful")
                            except Exception as e2:
                                print(f"JavaScript click on seller info failed: {str(e2)}, trying alternative...")
                                try:
                                    # Try to find seller URL in any way possible
                                    all_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/seller/') or contains(@href, '/brands/')]")
                                    if all_links and len(all_links) > 0:
                                        seller_url = all_links[0].get_attribute('href')
                                        print(f"Found seller URL: {seller_url}")
                                        driver.get(seller_url)
                                        print("Navigation to found seller URL successful")
                                    else:
                                        raise Exception("No seller URL found")
                                except Exception as e3:
                                    print(f"All attempts to access seller info failed: {str(e3)}")
                                    print("Could not access seller page, skipping detailed info")
                                    
                                    # Move to next product
                                    continue
                        
                        # Wait for seller details page to load
                        print("Waiting for seller details to load...")
                        time.sleep(5)
                        
                        # Print page title and URL for debugging
                        print(f"Seller page title: {driver.title}")
                        print(f"Seller page URL: {driver.current_url}")
                        
                        # Try different selectors for seller details tip
                        tip_selectors = [
                            ".seller-details__tip-info", 
                            "span[class*='seller-details__tip']", 
                            "span[class*='tip-info']",
                            ".seller__tip",
                            "span[class*='info']",
                            "div[class*='seller'] span",
                            ".info-icon",
                            ".info__icon",
                            "i[class*='info']",
                            "*[title*='информац']",  # Elements with title containing "информац" (information in Russian)
                            "*[data-tip-selector]"   # Elements that might trigger tooltips
                        ]
                        
                        # XPath alternatives
                        tip_xpath_selectors = [
                            "//span[contains(@class, 'tip')]",
                            "//span[contains(@class, 'info')]",
                            "//i[contains(@class, 'info')]",
                            "//*[contains(@class, 'tip-info')]",
                            "//*[contains(@title, 'информац')]",
                            "//*[contains(@class, 'tooltip')]",
                            "//span[contains(@class, 'seller-details')]",
                            "//*[@data-tip-selector]"
                        ]
                        
                        seller_details_tip = None
                        tip_selector_used = None
                        
                        # Try CSS selectors first
                        for selector in tip_selectors:
                            print(f"Trying to find seller details tip with selector: {selector}")
                            try:
                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                if elements and len(elements) > 0:
                                    for elem in elements:
                                        try:
                                            if elem.is_displayed():
                                                print(f"Found visible tip element with selector: {selector}")
                                                seller_details_tip = elem
                                                tip_selector_used = selector
                                                break
                                        except:
                                            continue
                                    
                                    if seller_details_tip:
                                        break
                                
                                seller_details_tip = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                                if seller_details_tip:
                                    print(f"Found seller details tip with selector: {selector} using WebDriverWait")
                                    tip_selector_used = selector
                                    break
                            except TimeoutException:
                                print(f"Selector {selector} did not yield results.")
                        
                        # If CSS selectors fail, try XPath
                        if not seller_details_tip:
                            print("CSS selectors failed, trying XPath for seller details tip...")
                            for xpath in tip_xpath_selectors:
                                print(f"Trying to find seller details tip with XPath: {xpath}")
                                try:
                                    elements = driver.find_elements(By.XPATH, xpath)
                                    if elements and len(elements) > 0:
                                        for elem in elements:
                                            try:
                                                if elem.is_displayed():
                                                    print(f"Found visible tip element with XPath: {xpath}")
                                                    seller_details_tip = elem
                                                    tip_selector_used = xpath + " (XPath)"
                                                    break
                                            except:
                                                continue
                                        
                                        if seller_details_tip:
                                            break
                                except Exception as e:
                                    print(f"XPath {xpath} failed: {str(e)}")
                        
                        if not seller_details_tip:
                            print("Failed to find seller details tip. Looking for any clickable icons...")
                            try:
                                # Look for any small elements that might be info icons
                                icons = driver.find_elements(By.XPATH, "//i | //span[string-length(text()) < 5] | //*[contains(@class, 'icon')]")
                                print(f"Found {len(icons)} potential icon elements")
                                for i_icon, icon in enumerate(icons[:10]):  # Try first 10 icons
                                    try:
                                        if icon.is_displayed():
                                            class_name = icon.get_attribute('class')
                                            title = icon.get_attribute('title')
                                            if 'info' in (class_name or '').lower() or 'tip' in (class_name or '').lower() or (title and len(title) > 0):
                                                seller_details_tip = icon
                                                tip_selector_used = f"Found icon {i_icon}"
                                                break
                                    except:
                                        continue
                            except Exception as e:
                                print(f"Error finding icons: {str(e)}")
                        
                        seller_info_text = ""
                        
                        if seller_details_tip:
                            # Found the tooltip info icon, click it
                            print(f"Successfully found seller details tip using: {tip_selector_used}")
                            try:
                                print(f"Seller details tip text: {seller_details_tip.text}")
                                print(f"Seller details tip attributes: title='{seller_details_tip.get_attribute('title')}', class='{seller_details_tip.get_attribute('class')}'")
                            except:
                                print("Could not get seller details tip text or attributes")
                            
                            # Click on the seller details tip info
                            print("Clicking on seller details tip info...")
                            try:
                                # Wait a bit before clicking (important!)
                                time.sleep(1)
                                
                                # Try direct click first
                                seller_details_tip.click()
                                print("Direct click on seller details tip successful")
                            except Exception as e:
                                print(f"Direct click on seller details tip failed: {str(e)}, trying JavaScript click...")
                                try:
                                    driver.execute_script("arguments[0].click();", seller_details_tip)
                                    print("JavaScript click on seller details tip successful")
                                except Exception as e2:
                                    print(f"JavaScript click on seller details tip failed: {str(e2)}")
                                    print("Could not click on seller details tip")
                            
                            # Wait for tooltip to appear
                            print("Waiting for tooltip content to load...")
                            time.sleep(5)
                            
                            # Try different selectors for tooltip content
                            tooltip_selectors = [
                                ".tooltip_content", 
                                "div[class*='tooltip']", 
                                "div[class*='popup']",
                                ".tippy-content",
                                ".popover-content",
                                ".popover-inner",
                                "div[class*='popover']",
                                "div[class*='modal']",
                                "div[role='tooltip']",
                                ".seller-details__tooltip",
                                "div[class*='tooltip-content']",
                                "div[class*='tip-content']"
                            ]
                            
                            # XPath alternatives
                            tooltip_xpath_selectors = [
                                "//div[contains(@class, 'tooltip')]",
                                "//div[contains(@class, 'popover')]",
                                "//div[contains(@class, 'popup')]",
                                "//div[@role='tooltip']",
                                "//div[contains(@class, 'modal')][contains(., 'ИНН')]",  # Modal containing "ИНН" (Russian tax ID)
                                "//div[contains(@class, 'modal')][contains(., 'ОГРН')]", # Modal containing "ОГРН" (Russian business ID)
                                "//div[contains(@class, 'tippy')]"
                            ]
                            
                            tooltip_content = None
                            tooltip_selector_used = None
                            
                            # Try CSS selectors first
                            for selector in tooltip_selectors:
                                print(f"Trying to find tooltip content with selector: {selector}")
                                try:
                                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                    if elements and len(elements) > 0:
                                        for elem in elements:
                                            try:
                                                if elem.is_displayed():
                                                    print(f"Found visible tooltip with selector: {selector}")
                                                    tooltip_content = elem
                                                    tooltip_selector_used = selector
                                                    break
                                            except:
                                                continue
                                        
                                        if tooltip_content:
                                            break
                                    
                                    tooltip_content = WebDriverWait(driver, 5).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                    )
                                    if tooltip_content:
                                        print(f"Found tooltip content with selector: {selector} using WebDriverWait")
                                        tooltip_selector_used = selector
                                        break
                                except TimeoutException:
                                    print(f"Selector {selector} did not yield results.")
                            
                            # If CSS selectors fail, try XPath
                            if not tooltip_content:
                                print("CSS selectors failed, trying XPath for tooltip content...")
                                for xpath in tooltip_xpath_selectors:
                                    print(f"Trying to find tooltip content with XPath: {xpath}")
                                    try:
                                        elements = driver.find_elements(By.XPATH, xpath)
                                        if elements and len(elements) > 0:
                                            for elem in elements:
                                                try:
                                                    if elem.is_displayed():
                                                        print(f"Found visible tooltip with XPath: {xpath}")
                                                        tooltip_content = elem
                                                        tooltip_selector_used = xpath + " (XPath)"
                                                        break
                                                except:
                                                    continue
                                            
                                            if tooltip_content:
                                                break
                                    except Exception as e:
                                        print(f"XPath {xpath} failed: {str(e)}")
                            
                            if not tooltip_content:
                                print("Looking for any recently appeared elements that might be tooltips...")
                                
                                # Check for elements containing INN or OGRN
                                try:
                                    text_elements = driver.find_elements(By.XPATH, "//*[string-length(text()) > 0]")
                                    print(f"Found {len(text_elements)} text elements")
                                    for j, elem in enumerate(text_elements[:30]):  # Check first 30 elements
                                        try:
                                            if elem.is_displayed():
                                                text = elem.text
                                                # Check for business identifiers
                                                if any(keyword in text for keyword in ['ИНН', 'ОГРН', 'регистрации', 'предприниматель']):
                                                    print(f"Found potential tooltip text: {text[:100]}...")
                                                    tooltip_content = elem
                                                    tooltip_selector_used = f"Text element containing business identifiers"
                                                    break
                                        except:
                                            continue
                                except Exception as e:
                                    print(f"Error finding text elements: {str(e)}")
                            
                            if tooltip_content:
                                print(f"Successfully found tooltip content using: {tooltip_selector_used}")
                                
                                # Extract the seller information
                                print("Extracting seller information...")
                                try:
                                    seller_info_text = tooltip_content.text
                                    print("\n=== ИНФОРМАЦИЯ О ПРОДАВЦЕ ===")
                                    print(seller_info_text)
                                    print("============================\n")
                                except Exception as e:
                                    print(f"Error extracting text from tooltip: {str(e)}")
                                    seller_info_text = "Error extracting seller information"
                            else:
                                # If couldn't find tooltip, use seller name
                                seller_info_text = seller_name
                                print(f"Could not find tooltip content, using seller name: {seller_name}")
                        else:
                            # If no tooltip button found, use seller name
                            seller_info_text = seller_name
                            print(f"No tooltip button found, using seller name: {seller_name}")
                        
                        # Check if we got full seller info with "ИНН" and "ОГРН"
                        has_full_info = "ИНН" in seller_info_text or "ОГРН" in seller_info_text
                        
                        if has_full_info:
                            # Format the seller info text exactly as required
                            formatted_seller_info = f"=== ИНФОРМАЦИЯ О ПРОДАВЦЕ ===\n{seller_info_text}\n============================"
                            
                            # Save the results
                            result = {
                                'product_name': product_name,
                                'product_url': product_url,
                                'seller_name': seller_name,
                                'seller_info': formatted_seller_info
                            }
                            
                            results.append(result)
                            
                            # Write to CSV
                            with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                                fieldnames = ['product_name', 'product_url', 'seller_name', 'seller_info']
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writerow(result)
                            
                            total_processed += 1
                            print(f"Seller info for product saved to CSV. Progress: {total_processed}/{max_total_products}")
                        else:
                            print("No full seller info found, not saving to CSV")
                        
                        # Add a delay between products
                        delay = random.uniform(2, 4)
                        print(f"Waiting {delay:.2f} seconds before next product...")
                        time.sleep(delay)
                    
                    # Move to next page
                    page += 1
                    
                    # Add a delay between pages
                    delay = random.uniform(2, 4)
                    print(f"Waiting {delay:.2f} seconds before next page...")
                    time.sleep(delay)
                
                # Move to next category if we've finished this one
                current_category_index += 1
                
                # If we've processed enough products, break
                if total_processed >= max_total_products:
                    print(f"\nReached the maximum number of products to process ({max_total_products})")
                    break
                
                # Add a longer delay between categories
                if current_category_index < len(categories):
                    delay = random.uniform(3, 6)
                    print(f"Waiting {delay:.2f} seconds before next category...")
                    time.sleep(delay)
            
            # Print summary statistics
            print("\n===== Итоговая статистика =====")
            print(f"Всего обработано товаров: {total_processed}")
            print(f"Товаров с полной информацией о продавце: {len(results)}/{total_processed} ({len(results)/max(total_processed, 1)*100:.1f}% успешных)")
            print(f"Результаты сохранены в файл: {csv_filename}")
            
            return results
            
        except Exception as e:
            print(f"Error during navigation: {e}")
            driver.save_screenshot(os.path.join(results_dir, "error_screenshot.png"))
            return None
            
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        return None
        
    finally:
        try:
            # Close the browser
            if 'driver' in locals() and driver:
                driver.quit()
                print("Browser closed. Scraping completed.")
        except Exception as e:
            print(f"Error closing browser: {e}")

if __name__ == "__main__":
    # Запуск скрипта с обработкой 100 товаров
    scrape_wildberries_sellers(max_total_products=100, batch_size=10)
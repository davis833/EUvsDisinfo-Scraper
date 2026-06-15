import csv
import time
from datetime import datetime
from bs4 import BeautifulSoup as bs # type: ignore
import undetected_chromedriver as uc # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore

BASE_URL = "https://euvsdisinfo.eu/disinformation-cases/page/{}/?date=01.02.2022%20-%2014.09.2025"
TOTAL_PAGES = 1
OUTPUT_FILE = "euvsdisinfo_full2.csv"

def extract_article_metadata(url, driver):
    driver.get(url)
    time.sleep(1.5)
    soup = bs(driver.page_source, "html.parser")
    data = {}

    # Page title
    title_tag = soup.find("title")
    if title_tag:
        data["page_title"] = title_tag.get_text(strip=True)

    # Keywords
    keywords_div = soup.find("div", class_="b-report__keywords")
    if keywords_div:
        keywords_list = [span.get_text(strip=True) for span in keywords_div.find_all("span")]
        data["keywords_list"] = ", ".join(keywords_list)

    # Article details
    details_div = soup.find("div", class_="b-report__details")
    if details_div:
        li_elements = details_div.find_all("li")

        for li in li_elements:
            full_text = li.get_text(separator=" ", strip=True)

            # Outlet
            if full_text.startswith("Outlet:"):
                outlets = []
                for span in li.find_all("span", class_="outlet-group"):
                    a_tag = span.find("a")
                    if a_tag:
                        outlet_name = a_tag.get_text(strip=True)
                        outlet_name = outlet_name.replace("(opens in a new tab)", "").strip()
                        outlets.append(outlet_name)
                data["outlets"] = "; ".join(outlets)

            # Date of publication
            elif full_text.startswith("Date of publication:"):
                span = li.find("span")
                if span:
                    data["date_of_publication"] = span.get_text(strip=True)

            # Article language(s)
            elif full_text.startswith("Article language(s):"):
                span = li.find("span")
                if span:
                    data["article_languages"] = span.get_text(strip=True)

            # Countries / regions discussed
            elif full_text.startswith("Countries / regions discussed:"):
                span = li.find("span")
                if span:
                    data["countries_regions_discussed"] = span.get_text(strip=True)

    return data

def scrape_all_articles():
    driver = uc.Chrome()
    all_data = []

    for page in range(1, TOTAL_PAGES + 1):
        url = BASE_URL.format(page)
        print(f"Fetching page {page}: {url}")
        driver.get(url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.b-archive__database-item"))
            )
        except:
            print(f"No links found on page {page}, skipping.")
            continue

        articles = []
        link_elements = driver.find_elements(By.CSS_SELECTOR, "a.b-archive__database-item")
        for link in link_elements:
            try:
                article_url = link.get_attribute("href")
                date_text = link.find_element(By.CSS_SELECTOR, ".b-archive__database-item-date").text
                title_text = link.find_element(By.CSS_SELECTOR, ".b-archive__database-item-title").text
                articles.append((article_url, date_text, title_text))
            except Exception as e:
                print(f"Skipping link due to error: {e}")
                continue

        for article_url, date_text, title_text in articles:
            try:
                print(f"Scraping: {date_text} | {title_text}")
                metadata = extract_article_metadata(article_url, driver)
                metadata["article_url"] = article_url
                metadata["headline"] = title_text
                metadata["raw_date"] = date_text

                # Uniform date
                try:
                    dt = datetime.strptime(date_text, "%d.%m.%Y")
                    metadata["uniform_date"] = dt.strftime("%Y-%m-%d")
                except:
                    metadata["uniform_date"] = date_text

                all_data.append(metadata)
            except Exception as e:
                print(f"Skipping article due to error: {e}")
                continue
        time.sleep(1.0)

    driver.quit()
    return all_data

def save_to_csv(data, filename):
    if not data:
        print("No data to save.")
        return

    headers = set()
    for row in data:
        headers.update(row.keys())
    headers = sorted(headers)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    print(f"Saved {len(data)} articles to {filename}")

if __name__ == "__main__":
    scraped_data = scrape_all_articles()
    save_to_csv(scraped_data, OUTPUT_FILE)

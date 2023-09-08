import csv
import os
import time
import configparser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import urlparse

#retreive configuration values
config = configparser.ConfigParser()
config.read('configuration.ini')

folderpath = str(config.get('Global','SaveLocation'))
delay = int(config.get('Woolworths','DelaySeconds'))

# Create a new csv file for Woolworths
filename = "Woolworths" + ".csv"
filepath = os.path.join(folderpath,filename)
if os.path.exists(filepath):
    os.remove(filepath)

print("Saving to " + filepath)

#write the header
with open(filepath, "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Product Code", "Category", "Item Name", "Best Price", "Best Unit Price", "Item Price", "Unit Price", "Price Was", "Special Text", "Complex Promo Text", "Link"])
f.close()

# Configure options
options = webdriver.EdgeOptions()
options.add_argument("--app=https://www.woolworths.com.au")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

# Start EdgeDriver
print("Starting Woolworths...")
driver = webdriver.Edge(options=options)

# Navigate to the Woolies Website
url = "https://www.woolworths.com.au"
driver.get(url)
time.sleep(delay)

#open the menu drawer to get the category list
driver.find_element(By.XPATH, "//button[@class='wx-header__drawer-button browseMenuDesktop']").click()
time.sleep(delay)

# Parse the page content
page_contents = BeautifulSoup(driver.page_source, "html.parser")

# Find all product categories on the page
categories = page_contents.find_all("a", class_="item ng-star-inserted")

print("Categories:")
for category in categories:
    print(category.text)

for category in categories:
    # Get the link to the categories page
    category_link = category.get("href")
    if category_link != "/shop/browse/front-of-store" and category_link != "/shop/browse/liquor" and category_link != "/shop/browse/healthylife-pharmacy":

        category_link = url + category_link
        print("Current Category: " + category.text)

        # Follow the link to the category page
        driver.get(category_link)
        time.sleep(delay)

        # Parse page content
        page_contents = BeautifulSoup(driver.page_source, "html.parser")

        # Get the number of pages in this category
        try:
            pageselement = driver.find_element(By.XPATH, "//span[@class='page-count']")
            total_pages = int(pageselement.get_attribute('innerText'))
        except:
            total_pages = 1
        
        print("Total Pages in this Category: " + str(total_pages))

        for page in range(1, total_pages): #change back to 1

            # Parse the page content
            page_contents = BeautifulSoup(driver.page_source, "html.parser")
            
            #get the element containing the products
            productsgrid = page_contents.find("div", class_="ng-tns-c113-3 ng-trigger ng-trigger-staggerFadeInOut product-grid-v2")

            # Find all products on the page
            products = productsgrid.find_all("section", class_="product-tile-v2")
            print("Products on this page: " + str(len(products)))

            for product in products:
                name = product.find("div", class_="product-tile-title")
                itemprice = product.find("div", class_="primary")
                unitprice = product.find("span", class_="price-per-cup")
                specialtext = product.find("div", class_="ng-star-inserted")
                promotext = product.find("div", class_="product-tile-promo-info ng-star-inserted")
                price_was_struckout = product.find("span", class_="was-price ng-star-inserted")

                productLink = product.find("a", class_="product-title-link")["href"]
                productcode = productLink.split("/")[-1]                

                if name and itemprice:
                    name = name.text.strip()
                    itemprice = itemprice.text.strip()
                    unitprice = unitprice.text.strip()
                    specialtext = specialtext.text.strip()
                    best_price = itemprice
                    best_unitprice = unitprice
                    link = url + productLink

                    #Was Price (this is different to promotext)
                    if(price_was_struckout):
                        price_was = price_was_struckout.text.strip()
                    else:
                        price_was = None

                    if(promotext):
                        promotext = promotext.text.strip()
                        print("Promo Text: " + str(promotext))

                        #"Range Was" or "Was"
                        if(promotext.find("Was ") != -1 or promotext.find("Range was ") != -1):
                            price_was = promotext[promotext.find("$"):promotext.find(" - ")]
                        

                        #Member x for x promos
                        if(promotext.find("MEMBER PRICE ") != -1 or promotext.find(" for ") != -1): 
                            #member price
                            if(promotext.find("MEMBER PRICE ") != -1):
                                 promotext = promotext.replace("MEMBER PRICE ", "")
                                 
                            #generic 2fer pricing
                            promo_itemcount = int(promotext[0:promotext.find(" for")])
                            promo_price = float(promotext[promotext.find("$")+1:promotext.find(" - ")])
                        
                            #set Best price Update Best Unit Price from the memberpromo price
                            best_price = "$" + str(round(promo_price / promo_itemcount, 2)) 
                            #check if a unit price is presented for a 2-for special, they aren't always 
                            if (promotext.find(" - ") != -1):
                                best_unitprice = promotext[promotext.find(" - ")+3:len(promotext)]
                            
                        else:
                            memberpromo = None
                      
                    else:
                        promotext = None

                    #write contents to file                       
                    with open(filepath, "a", newline="") as f:
                        writer = csv.writer(f)  
                        writer.writerow([productcode, category.text, name, best_price, best_unitprice, itemprice, unitprice, price_was, specialtext, promotext, link])

                #reset variables
                name = None
                itemprice = None
                unitprice = None
                specialtext = None
                promotext = None
                memberpromo = None
                productLink = None
                productcode = None
                specialtext = None
                complexpromo = None
                complex_itemcount = None
                complex_cost = None
                best_price = None
                best_unitprice = None
                price_was = None


            # Get the link to the next page
            next_page_link = f"{category_link}?pageNumber={page + 1}"
            # Navigate to the next page
            if(total_pages > 1 and page + 1 <= total_pages):
                print("Getting Next Page (" + str(page + 1) + " of " + str(total_pages) + ")...")
                driver.get(next_page_link)

            time.sleep(delay)

        #wait the delay time before the next page
        time.sleep(delay)

driver.quit
print("Finished")
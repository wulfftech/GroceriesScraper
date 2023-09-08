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
delay = int(config.get('Coles','DelaySeconds'))
ccsuburb = str(config.get('Coles','ClickAndCollectSuburb'))

# Create a new csv file for Coles
filename = "Coles" + ".csv"
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
options.add_argument("--app=https://www.coles.com.au")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

# Start EdgeDriver
print("Starting Coles...")
driver = webdriver.Edge(options=options)

# Navigate to the Coles website
url = "https://www.coles.com.au"
driver.get(url + "/browse")
time.sleep(delay)

#Set Loacation via Menu Items
driver.find_element(By.XPATH, "//button[@data-testid='delivery-selector-button']").click()
time.sleep(delay)

driver.find_element(By.XPATH, "//a[@id='shopping-method-label-0']").click()
time.sleep(delay)

driver.find_element(By.XPATH, "//input[@aria-label='Search address']").send_keys(ccsuburb)
time.sleep(delay)

driver.find_element(By.XPATH, "//div[@id='react-select-search-location-box-option-0']").click()
time.sleep(delay)

driver.find_element(By.XPATH, "//input[@name='radio-group-name'][@value='0']").click()
time.sleep(delay)

driver.find_element(By.XPATH, "//button[@data-testid='set-location-button']").click()
time.sleep(delay)

# Parse the page content
page_contents = BeautifulSoup(driver.page_source, "html.parser")

# Find all product categories on the page
categories = page_contents.find_all("a", class_="coles-targeting-ShopCategoriesShopCategoryStyledCategoryContainer")

print("Categories:")
for category in categories:
    print(category.text)
# Iterate through each category and follow the link to get the products
for category in categories:
    # Get the link to the categories page
    category_link = category.get("href")
    if category_link != "/browse/tobacco" and category_link != "/browse/liquor":

        category_link = url + category_link
        print("Current Category: " + category.text)

        # Follow the link to the category page
        driver.get(category_link)

        # Parse page content
        page_contents = BeautifulSoup(driver.page_source, "html.parser")

        # Get the number of pages in this category
        try:
            pagination = page_contents.find("ul", class_="coles-targeting-PaginationPaginationUl")
            pages = pagination.find_all("li")
            total_pages = int(pages[-2].text.strip())
        except:
            total_pages = 1
        
        print("Total Pages in this Category: " + str(total_pages))

        for page in range(1, total_pages):

            # Parse the page content
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Find all products on the page
            products = soup.find_all("header", class_="product__header")
            print("Products on this page: " + str(len(products)))

            # Iterate through each product and extract the product name, price and link
            for product in products:
                name = product.find("h2", class_="product__title")
                itemprice = product.find("span", class_="price__value")
                unitprice = product.find("div", class_="price__calculation_method")
                specialtext = product.find("span", class_="roundel-text")
                complexpromo = product.find("span", class_="product_promotion complex")
                productLink = product.find("a", class_="product__link")["href"]
                productcode = productLink.split("-")[-1]
                
                if name and itemprice:
                    name = name.text.strip()
                    itemprice = itemprice.text.strip()
                    best_price = itemprice
                    best_unitprice = unitprice                    
                    link = url + productLink

                    #Unit Price and Was Price
                    if(unitprice):
                        unitprice = unitprice.text.strip()
                    
                        price_was_pos = unitprice.find("| Was $")
                        if(price_was_pos != -1):
                            price_was = unitprice[price_was_pos + 6:len(unitprice)]
                            unitprice = unitprice[0:unitprice.find("|")].strip()
                    
                    #Special Text
                    if(specialtext):
                        specialtext = specialtext.text.strip()
                        if(specialtext == "1/2"):
                            specialtext = "50%"
                    
                    #Complex Promo
                    if(complexpromo):
                        complexpromo = complexpromo.text.strip() 
                        #Get ComplexPromo price
                        if(complexpromo.find("Pick any ") != -1 or complexpromo.find("Buy ") != -1):
                            complexpromo = complexpromo.replace("Pick any ", "")
                            complexpromo = complexpromo.replace("Buy ", "")
                            complex_itemcount = int(complexpromo[0:complexpromo.find(" for")])
                            complex_cost = float(complexpromo[complexpromo.find("$")+1:len(complexpromo)])
                            best_price = "$" + str(round(complex_cost / complex_itemcount, 2))

                    #write contents to file                       
                    with open(filepath, "a", newline="") as f:
                        writer = csv.writer(f)  
                        writer.writerow([productcode, category.text, name, best_price, best_unitprice, itemprice, unitprice, price_was, specialtext, complexpromo, link])
                
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
            next_page_link = f"{category_link}?page={page + 1}"
            # Navigate to the next page
            if(total_pages > 1 and page + 1 <= total_pages):
                print("Getting Next Page (" + str(page + 1) + " of " + str(total_pages) + ")...")
                driver.get(next_page_link)
            
            #wait the delay time before the next page
            time.sleep(delay)

driver.quit
print("Finished")
import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver import FirefoxService as Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update

firstRunWoko = True
firstRunWGRoom = True

MAX_PAGES = 5

def main():
    #setup of telegram api to listen updates
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher
    
    #setup of /start command
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    
    #bot is started
    updater.start_polling()
    
    #60 second loop that runs forever
    while True:
        scrapeWoko()
        try:
            scrapeWGZimmer()
        except:
            print("Error in scraping WGZimmer")
        print("Searching for new rooms...")
        time.sleep(60)

#function that scraps the Woko website  
def scrapeWoko():
    
    global firstRunWoko
    #a list of already present advertisements is loaded
    file = open("existingWoko.txt","r+")
    existingAdvWoko = file.read()
    
    #html is taken from the website
    url = 'https://www.woko.ch/en/zimmer-in-zuerich'
    headers = { 'User-Agent': 'Generic user agent' }
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.text, 'html.parser')

    #advertisements are filtered from the rest
    dataHtml = soup.find_all("div", {"class": "inserat"})
    for adv in dataHtml:
        #text is cleaned
        data = adv.getText()
        text = data.replace('\r', '')
        text = text.replace('\t', '')
        text = text.replace('\n\n', '\n')
        text = text.replace('\n\n\n', '\n')

        #looks for a link (I stole this)
        a_class = adv.find_all('a')
        url = a_class[0].get('href')
        
        #gets the price from the text for later use
        ncounter = 0
        lcounter = 0
        price = ""
        for letter in text:
            if letter =="\n":
                ncounter+=1
                if ncounter==11:
                    price=text[lcounter+1:]
            lcounter+=1
        price = price[:-4]

        #a token different for every adv is taken
        identifierToken = url[-4:]
        url = "https://www.woko.ch/en/zimmer-in-zuerich" + "-details/" + identifierToken
        #final message is created
        finalMsg = text + url

        #if the adv is a new one
        if url not in existingAdvWoko:
            if firstRunWoko==False:
                #url is written to the list of urls
                file.write(url+"\n")
                print("Found New Adv")
                #message is sent
                sendMessage(finalMsg,price)
            else:
                file.write(url+"\n")
                print("Skipped because of restart")
    file.close()
    if firstRunWoko == True:
        firstRunWoko = False
        print("First run completed Woko")

##function that scraps the WGZimmer website
def scrapeWGZimmer():

    global firstRunWGRoom

    #existing urls are taken
    file = open("existingWGZimmer.txt","r+")
    existingAdvWGZimmer = file.read()

    #this website is a little bit different, I have to send
    #a post request to simulate the click of the search button


    # service = Service("/snap/bin/firefox.geckodriver")
    # driver = webdriver.Firefox( service=service)

    driver = webdriver.Firefox()
    driver.get("https://www.wgzimmer.ch/wgzimmer/search/mate.html")

    consent_button = driver.find_element(By.CSS_SELECTOR, ".fc-cta-consent")
    consent_button.click()

    zurich_button = driver.find_element(By.CSS_SELECTOR, "span.stateShortcut:nth-child(10)")
    zurich_button.click()

    search_button = driver.find_element(By.CSS_SELECTOR, ".button-wrapper > input:nth-child(1)")
    search_button.click()

    result_list = None

    while result_list is None:
        time.sleep(5)

        try: 
            result_list = driver.find_element(By.ID, "search-result-list")
        except:
            continue

    adsHtml = []

    for i in range(MAX_PAGES):
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        adsHtml += soup.find_all("li", {"class": "search-result-entry search-mate-entry"})

        if i == MAX_PAGES-1:
            break

        page_no = driver.find_element(By.CSS_SELECTOR, "div.result-navigation:nth-child(6) > div:nth-child(3) > span:nth-child(2)")
        page_no = page_no.text.split(" ")[1]
        page_no = page_no.partition("/")
        if page_no[0] == page_no[2]:
            break

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "div.result-navigation:nth-child(6) > div:nth-child(3) > a:nth-child(3)")
            next_button.click()
        except:
            break

        sleep(1)

    driver.quit()

    #for every ad  
    for adv in adsHtml:
        finalMsgArray = []
        price = ""

        #text is filtered and prettified (is that a word?)
        data = adv.find_all("strong")
        counter = 0
        for d in data:
            if counter==2:
                untilData =" ".join(d.parent.text[1:].split(" ")[1:])
            d = d.text
            if counter == 0:
                b = "Creation date: "+ d[1:]
                finalMsgArray.append(b)
            elif d=="\n":
                a = 1
            elif counter==2:
                finalMsgArray.append("From: "+d)
            elif counter==3:
                price = d
            else:
                finalMsgArray.append(d)
            counter+=1
        
        #this piece of data couldn't be found in <strong>, and so I'm taking it manually
        # untilData = text[29]
        # untilData = untilData[1:]

        # temp = finalMsgArray[3]
        # finalMsgArray[3] = untilData
        # finalMsgArray.append(temp[1:])

        #price is filtered for later
        # price = temp[5:-3]

        finalMsgArray.append(untilData)

        finalMsg = ""
        for i in finalMsgArray:
            finalMsg+=i +'\n'
        
        #url is taken
        a_class = adv.find_all('a')
        url = a_class[0].get('href')
        url = 'https://www.wgzimmer.ch' + url
        finalMsg += url + "\n"

        # print(finalMsg)
        # print("Price: " + price)

        #if url already exists 
        if url not in existingAdvWGZimmer:

            #if its notthe first run
            if firstRunWGRoom==False:
                #message is sent
                print("Found Room Wgroom")
                sendMessage(finalMsg,price)
                #url is written to the txt file
                file.write(url+"\n")
            else:
                file.write(url+"\n")
                print("Skipped because of restart")
    
    file.close()
    if firstRunWGRoom == True:
        firstRunWGRoom = False
        print("First run completed WGRoom")


#function that runs when /start is entered
def start(update: Update, context: CallbackContext):

    #the id of the user is taken
    chat_id = update.message.chat_id
    
    #checks if the id is in the list of autorized ids
    if str(chat_id) in idList:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Account is autorized, bot is working")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Ops, you are not autorized yet. Send this number "+str(chat_id)+" to @bskdany to be whitelisted. Cheers.")

#function that sends the adv to the user        
def sendMessage(message,price):
    for id in idList:
        if int(price)<=800:
            #if the max price is higher the adv is sent in chat
            requests.get("https://api.telegram.org/bot"+token+"/sendMessage?chat_id="+id+"&text={}".format(message))
        
#function that reads the ids and max prices and puts them in an array
def getIdList():
    #file is processed
    file = open("idList.txt","r")
    temp = file.readlines()
    idList = []
    for i in temp:
        idList.append(i[:-1])
    file.close()
    return idList

#user data
token = "YOURTOKEN"
idList = getIdList()
print("Authorized Ids:")
for id in idList:
    print(id)

if __name__ == '__main__':
    main()
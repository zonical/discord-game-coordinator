import requests
import json
import os

currentdir = os.path.dirname(os.path.abspath(__file__))

regions = {
    "us": 0,
    "eu": 1,
    "ru": 2,
    "au": 3,
    "sg": 4,
}

class GameCoordinator_Server:
    ServerAddress = ()
    ServerName = ""
    ServerPlayers = -1
    ServerMaxPlayers = -1
    ServerRegionID = -1
    ServerMap = ""
    ServerPlayerNames = []

class Provider:
    ProviderName = ""
    ProviderURL = ""
    ProviderServers = []
    ProviderID = -1

def CreateProviders():
    dictOfProviders = {}
    
    #Open our configuration file, which has all of our needed information like
    #provider names, URLs for server querying, etc...
    with open(currentdir + "/ProviderConfig.json") as file:
        jsonObject = json.load(file) #Load our information as JSON.
        listOfProviders = jsonObject["providers"]

        #Iterate over our providers.
        for provider in listOfProviders:
            providerDict = listOfProviders[provider]
            obj = Provider() #Create an object to store our information.
            obj.ProviderName = providerDict["name"]
            obj.ProviderID = providerDict["providerID"]
            obj.ProviderURL = providerDict["url"]

            #And finally, add it to our final list.
            dictOfProviders[obj.ProviderID] = obj
    
    return dictOfProviders
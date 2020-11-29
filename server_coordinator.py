import requests
import json
import os

currentdir = os.path.dirname(os.path.abspath(__file__))

class GameCoordinator_Server:
    ServerAddress = ()
    ServerName = ""
    ServerPlayers = -1
    ServerMaxPlayers = -1
    ServerRegionID = -1
    ServerMap = ""
    ServerPlayerNames = []

#This is the class that holds the provider information we load in from ProviderConfig.json.
class GameServerProvider:
    ProviderName = ""
    ProviderID_API = -1
    ProviderID_GC = -1
    ProviderURL = ""
    ProviderAPIType = -1
    ProviderServers = []

    #Provider Regions. For the purposes of ease of use, we'll be using numerical ID's.
    #The ID's go as follows:
    #ID - Region.
    #0 - USA.
    #1 - Europe.
    #2 - Russia.
    #3 - Australia/Oceania.
    #4 - Singapore/Asia
    #5 - Brazil/South America
    #6 - Norway.
    ProviderRegionIDs = []

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
            obj = GameServerProvider() #Create an object to store our information.
            obj.ProviderName = providerDict["name"]
            obj.ProviderID_GC = providerDict["providerID"]
            obj.ProviderURL = providerDict["url"]
            
            #We are dealing with the Creators.TF API when making our requests:
            if obj.ProviderURL.startswith("https://creators.tf"):
                #Double check we are using the correct API function:
                if ("api/IServers/GServerList?provider=" in obj.ProviderURL):
                    obj.ProviderAPIType = 1
                    obj.ProviderID_API = obj.ProviderURL.split('=')[1]
                else:
                    print(f"[ERROR] Provider {obj.ProviderName} is under Creators.TF, but is not using the API in it's query URL?")
            else:
                print(f"[SETUP] Provider {obj.ProviderName} is using an unknown service, cannot assign a API ID.")

            #Get our list of regions:
            obj.ProviderRegionIDs = providerDict["regions"]

            #And finally, add it to our final list.
            dictOfProviders[obj.ProviderID_GC] = obj
    
    return dictOfProviders
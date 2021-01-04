import discord
import json
import os

currentdir = os.path.dirname(os.path.abspath(__file__))
DefaultSettings = { # DEFAULT SETTINGS, we need this for the constructor
    # this probably shouldnt be as hardcoded as it is right now but i dont see us adding more settings
    "min_players": 0,
    "max_players": 32,
    "default_provider": None,
    "default_region": None
}
Users = {}

class UserData:
    UserID = -1
    Settings = DefaultSettings

    def __init__(self, id, settings = DefaultSettings ): # right now theres not much purpose to creating instances except registering users, will probably change this later
        self.UserID = id
        self.Settings = settings

        Users[id] = settings

    @staticmethod
    def GetUsers():
        return Users

    @staticmethod
    def GetUser(id):
        if not id in Users:
            return False
        return Users[id]

    @staticmethod
    def GetOrRegisterUser(id):
        if not id in Users:
            UserData(id)
        return Users[id]

    @staticmethod
    def SetUserSetting(id, key, val):
        if not Users[id]: #incase the user isnt registered
            return False
        Users[id][key] = val
        return True

    @staticmethod
    def ReadUsers():
        with open(currentdir + "/data/UserData.json") as file: # thank you server_coordinator.py
            allUserData = json.load(file)["users"] #Load our information as JSON.
            for id in allUserData:
                UserData(int(id), allUserData[id]) #why must json get rid of data types??? why???
         
        return Users # incase we want to use it immediately
    
    @staticmethod
    def WriteUsers():
        with open(currentdir + "/data/UserData.json", "w") as file: # the same as before but writable
            json.dump({"users":Users},file) # dict to make it into the correct format # not sure if this is the most effective way of doing this but fuck it
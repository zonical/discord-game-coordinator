import discord
import json
import os

currentdir = os.path.dirname(os.path.abspath(__file__))


"""

HARDCODED VALUES DISPLEASE ME, SO I HAVE REMOVED THEM!

DefaultSettings = { # DEFAULT SETTINGS, we need this for the constructor
    # this probably shouldnt be as hardcoded as it is right now but i dont see us adding more settings
    "min_players": 0,
    "max_players": 32,
    "default_provider": None,
    "default_region": None
}
"""

Settings = {}
class UserSettings:
    Key = "",
    Value = -1,
    DisplayName = Key

    def __init__(self, key, value, displayname): # you really shouldnt call this outside of readsettings since it doesnt get saved
        self.Key = key
        self.Value = value
        self.DisplayName = displayname

        Settings[key] = self

    @staticmethod
    def Read():
        with open(currentdir + "/Settings.json") as file: # thank you server_coordinator.py
            allSettings = json.load(file)
            for key in allSettings:
                UserSettings(key, allSettings[key]['value'], allSettings[key]["displayname"]) # this time we can let the code handle the type conversion

    @staticmethod
    def GetAll():
        return Settings

    @staticmethod
    def Get(key): # this unlike GetUser returns the settings object, not the value so be careful
        return Settings[key]

Users = {}
class UserData:
    UserID = -1
    Settings = Settings

    def __init__(self, id, settings = Settings ): # right now theres not much purpose to creating instances except registering users, will probably change this later
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
        if not id in Users: #incase the user isnt registered
            return False
        Users[id][key] = val
        return True

    @staticmethod
    def ReadUsers():
        if os.path.exists(currentdir + "/data/UserData.json"):
            with open(currentdir + "/data/UserData.json") as file: # thank you server_coordinator.py
                allUserData = json.load(file) #Load our information as JSON.
                for id in allUserData:
                    UserData(int(id), allUserData[id]) #why must json get rid of data types??? why???
        else:
            if not os.path.exists(currentdir + "/data"): #create the dir first
                os.makedirs("data")
            with open(currentdir + "/data/UserData.json", "w") as file: # the same as before but writable
                json.dump({},file)
         
        return Users # incase we want to use it immediately
    
    @staticmethod
    def WriteUsers():
        with open(currentdir + "/data/UserData.json", "w") as file: # the same as before but writable
            json.dump(Users,file) # dict to make it into the correct format # not sure if this is the most effective way of doing this but fuck it

DefaultServerSettings = { # now this doesnt need to be changable since this exists pretty much for these two settings
    "queue_channel": False,
    "queue_notify_role": False,
    "queue_admin_only": False
}

Servers = {} # same as the users dict, doesnt actually store instances
class ServerData:
    ServerID = -1
    Settings = DefaultServerSettings

    def __init__(self, id, settings = Settings ): # right now theres not much purpose to creating instances except registering users, will probably change this later
        self.ServerID = id
        self.Settings = settings

        Servers[id] = settings

    @staticmethod
    def GetAll():
        return Servers

    @staticmethod
    def Get(id):
        if not id in Servers: #incase the server isnt registered
            return False
        return Servers[id]
    
    @staticmethod
    def GetOrRegister(id):
        if not id in Servers:
            return ServerData(id)
        return Servers[id]

    @staticmethod
    def GetServerSetting(id, key):
        if not id in Servers: #incase the server isnt registered
            return False
        return Servers[id][key]

    @staticmethod
    def SetServerSetting(id, key, val):
        if not Servers[id]: #incase the server isnt registered
            return False
        Servers[id][key] = val
        return True

    @staticmethod
    def Read():
        if os.path.exists(currentdir + "/data/ServerData.json"):
            with open(currentdir + "/data/ServerData.json", "r") as file: # thank you server_coordinator.py
                allServerData = json.load(file) #Load our information as JSON.
                for id in allServerData:
                    ServerData(int(id), allServerData[id]) #why must json get rid of data types??? why???
        else:
            if not os.path.exists(currentdir + "/data"): # create the dir first
                os.makedirs("data")
            with open(currentdir + "/data/ServerData.json", "w") as file: # the same as before but writable
                json.dump({},file)
    
    @staticmethod
    def Write():
        with open(currentdir + "/data/ServerData.json", "w") as file: # the same as before but writable
            json.dump(Servers,file)

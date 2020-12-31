import discord
import json
import os

currentdir = os.path.dirname(os.path.abspath(__file__))

class UserData:
    UserID = -1
    Settings = { # DEFAULT SETTINGS
        "min_players": 0,
        "max_players": 32
    }

    def __init__(self, id, settings = UserData.Settings):
        if not hasattr(UserData, "Users"):
            UserData.ReadUsers()

        self.UserID = id
        self.Settings = settings

        UserData.Users[id] = settings

    @staticmethod
    def ReadUsers():
        if not hasattr(UserData, "Users"):
            # i could also do this by setting a default value but i dont want Users to exist on a object level
            UserData.Users = dict() # if Users doesnt exist, create it

        with open(currentdir + "/UserData.json") as file: # thank you server_coordinator.py
            allUserData = json.load(file)["users"] #Load our information as JSON.
            for id in allUserData:
                UserData(id, allUserData[id]["settings"])
         
        return UserData.Users # incase we want to use it immediately
    
    @staticmethod
    def WriteUsers():
        if not hasattr(UserData, "Users"): # if for some reason we write before read
            return False
        json.dump({"users":UserData.Users}) # dict to make it into the correct format
        return True
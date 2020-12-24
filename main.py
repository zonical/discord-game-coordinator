import discord
import asyncio
import lobby
import a2s
import server_coordinator
import requests
import json
import re
from discord.ext import commands, tasks
from sys import argv

IDtoEmojis = {
    1: ("1️⃣", ":one:"),
    2: ("2️⃣", ":two:"),
    3: ("3️⃣", ":three:"),
    4: ("4️⃣", ":four:"),
    5: ("5️⃣", ":five:"),
    6: ("6️⃣", ":six:"),
    7: ("7️⃣", ":seven:"),
    8: ("8️⃣", ":eight:"),
    9: ("9️⃣", ":nine"),
}

RegionIDToInformation = {
    #ID: (raw emoji code, discord emoji code, display name)
    0: ("🇺🇸", ":flag_us:", "USA/North America"),
    1: ("🇪🇺", ":flag_eu:", "Europe"),
    2: ("🇷🇺", ":flag_ru:", "Russia"),
    3: ("🇦🇺", ":flag_au:", "Australia/Oceania"),
    4: ("🇸🇬", ":flag_sg:", "Singapore"),
    5: ("🇧🇷", ":flag_br:", "Brazil"),
    6: ("🇳🇴", ":flag_no:", "Norway"),
}


NameToProviderID = {
    #Name: provider id
    "creators.tf": 1,
    "c.tf": 1,
    "creators": 1,
    "ctf": 1,
    "bmod": 2,
    "balancemod": 2,
    "balancemod/creators": 2,
    "events": 3,
    "event": 3
}

NameToRegionID = {
    #name: region id
    "usa": 0,
    "us": 0,
    "na": 0,
    "america": 0,
    "europe": 1,
    "eu": 1,
    "russia": 2,
    "ru": 2,
    "oceania": 3,
    "australia": 3,
    "aus": 3,
    "singapore": 4,
    "brazil": 5,
    "bra": 5,
    "norway": 6,
    "nor": 6
}


#The Game Coordinator bot class. This bot has three main purposes:
#1) Getting the latest server information of Creators.TF servers.
#2) Providing a matchmaking service for the C.TF Discord.
#3) Having this matchmaking service be customisable (e.g search by region, map, etc.)
class GameCoordinatorBot(discord.Client):
    providerdict = {}
    lobbylist = {}
    waitinglist = []

    def __init__(self):
        #Initalise the bot.
        super().__init__()

        #Call for servers.
        self.providerdict = server_coordinator.CreateProviders()

        self.loop_serverquerying.start()
        self.loop_lobbymatchmaking.start()

        #And now, launch the bot.
        self.run(argv[1], reconnect=True)

    async def on_ready(self):
        print("[START] Game Coordinator Bot has started.")
        print(f"[START] Information: Version 0.1a, Created by ZoNiCaL. Bot Account: {self.user}")
        
    #The on_message event. Whenever a message is sent on a server with the bot,
    #it picks it up and processes it in this function.
    async def on_message(self, message : discord.Message):
        #Don't worry about anything from DM's.
        if message.guild is None:
            return

        #Check that we're actually processing commands and not just random text.
        if message.content.startswith("c!") == False:
            return

        #Assemble our command:
        commandArgs = message.content.split(' ')
        actualCommand = commandArgs.pop(0)

        #Get sender:
        sender = message.author
        print(f"[COMMAND] Command coming in from {message.author}: {actualCommand}")

        if actualCommand not in self.commands:
            print(f"[COMMAND] Invalid command from {message.author}: {actualCommand}")
            return
        
        #We have a dictionary object full of command names, and the functions that we're calling.
        await self.commands[actualCommand](self, sender, message.channel, commandArgs)

    #c!findserver. This will construct an embed where users can select what they want.
    async def command_findserver(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        if sender.id in self.lobbylist:
            #Construct an embed.
            embedMessage = discord.Embed(title="Discord Game Coordinator.")
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You are already in the matchmaking queue. You can leave the queue with the command c!stop.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
            return

        #Create our lobby class:
        theLobby = lobby.Lobby()
        theLobby.LobbyOwner = sender
        theLobby.LobbyChannelSentIn = channel
        
        if len(arguments) > 0 and str(arguments[0]).lower() in NameToProviderID: # are there any arguments? is the provider valid?
            theLobby.LobbyProvider = NameToProviderID[str(arguments[0]).lower()] # easy provider id getting
        else: # no arguments or invalid provider
            #Make the embed, with all of our providers.
            embedMessage = discord.Embed(title="Discord Game Coordinator.")
            embedMessage.add_field(name="Provider Selection.", value="Please pick a provider to search from using the reactions below.",inline=False)

            #Loop through all of our registered providers and add them to the Embed:
            for provider in self.providerdict.values():
                EmojiTuple = IDtoEmojis[provider.ProviderID_GC]
                embedMessage.add_field(name=provider.ProviderName, value=EmojiTuple[1], inline=True)

            actualMessage = await channel.send(embed=embedMessage) #Send here, returns a message object where we can add reactions.
            
            #Add our emoji reactions so the user doesn't have to.
            for provider in self.providerdict:
                emojiTuple = IDtoEmojis[provider]
                await actualMessage.add_reaction(emojiTuple[0])

            #Wait for a reaction back:
            def check(reaction, user):
                return user == sender

            try: #Start our waiting process.
                reaction, user = await self.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError: #We waited for too long :(
                await channel.send(f"<@{sender.id}>, your request to use the Game Coordinator has expired.")
                return

            #Set our provider by grabbing a value from the dict.
            for providerID, emoji in IDtoEmojis.items():
                if (str(reaction.emoji) == emoji[0]):
                    theLobby.LobbyProvider = providerID
                    break
        
            #Could not grab the emoji :(
            if (theLobby.LobbyProvider == -1):
                await channel.send(f"<@{sender.id}>, your request to use the Game Coordinator has failed. Please submit a proper reaction next time.")
                return

            await actualMessage.clear_reactions() #Clear the reactions.

        #======================================================================================================================================

        #Create our ProviderObject so we can use it for later things:
        ProviderObject = self.providerdict[theLobby.LobbyProvider]

        if len(arguments) > 1 and str(arguments[1]).lower() in NameToRegionID: # same as provider but with region
            theLobby.LobbyRegion = NameToRegionID[str(arguments[1]).lower()]
        else: #again, fall back to the reactions if theres no region
            #Make our second embed, with all of our regions.
            embedMessage = discord.Embed(title="Discord Game Coordinator.")
            embedMessage.add_field(name="Region Selection.", value="Please pick a region to search in using the reactions below.",inline=False)
            
            for region in ProviderObject.ProviderRegionIDs:
                regionTuple = RegionIDToInformation[region]
                embedMessage.add_field(name=regionTuple[2], value=regionTuple[0],inline=True)

            await actualMessage.edit(embed=embedMessage) #Edit the original message.
            
            for region in ProviderObject.ProviderRegionIDs:
                emojiTuple = RegionIDToInformation[region]
                await actualMessage.add_reaction(emojiTuple[0])

            #Wait for our reaction back:
            try: #Start our waiting process.
                reaction, user = await self.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError: #We waited for too long :(
                await channel.send(f"<@{sender.id}>, your request to use the Game Coordinator has expired.")
                return

            #Set our provider by grabbing a value from the dict.
            for regionID, emojituple in RegionIDToInformation.items():
                if (str(reaction.emoji) == emojituple[0]):
                    theLobby.LobbyRegion = regionID
                    break
            
            #Could not grab the emoji :(
            if (theLobby.LobbyRegion == -1):
                await channel.send(f"<@{sender.id}>, your request to use the Game Coordinator has failed. Please submit a proper reaction next time.")
                return

            await actualMessage.clear_reactions() #Clear the reactions.

        messageContent = "" # we need to use this later
        if len(arguments) > 2: # are there any arguments left?
            messageContent = ','.join(arguments[2:len(arguments)]) #turn arguments into usable string
        else: #again, fall back to the reactions if theres no region
            #Make our third embed, for the gamemode selection.
            embedMessage = discord.Embed(title="Discord Game Coordinator.")
            embedMessage.add_field(name="Gamemode/Map Selection.", value="Please select the gamemodes/maps you would like to play on.",inline=False)
            embedMessage.add_field(name="How to select a gamemode:", value="Please type which gamemodes you would to play using their map prefix. Example: koth, pl.", inline=True)
            embedMessage.add_field(name="How to select a specifc map:", value="Please type part of their map name. Example: pl_cactuscanyon, koth_clear.", inline=True)
            embedMessage.add_field(name="Selecting multiple items:", value="Please split each item in your selection with a comma (,). Spaces are not required. Example: koth, pl_cactuscaynon, plr_hightower.", inline=True)
            embedMessage.add_field(name="Selecting all maps:", value="Please either type *, any, or all as your map selection. Do not add any other maps.", inline=True)
            await actualMessage.edit(embed=embedMessage) #Edit the original message.
            
            #Wait for this message of maps/gamemodes back.
            def mapCheck(message : discord.Message):
                if message.author.id == sender.id:
                    return message.content
            
            #Wait for our message back:
            try: #Start our waiting process.
                maps = await self.wait_for('message', timeout=30.0, check=mapCheck)
            except asyncio.TimeoutError: #We waited for too long :(
                await channel.send(f"<@{sender.id}>, your request to use the Game Coordinator has expired.")
                return

            #The message we've received.
            messageContent = maps.content

        #If we want to select ANY map or gamemode, lets do it here.
        for tmpStr in ["*", "any", "all"]:
            if tmpStr in messageContent:
                theLobby.LobbyMaps = tmpStr
                break
        else:
            #Remove whitespace from the maps/gamemodes, and set our lobby map/gamemode list.
            messageContent = re.sub(r'\s+', '', messageContent)
            theLobby.LobbyMaps = messageContent.split(',').copy()
        
        #Get the name of our provider.
        providerName = self.providerdict[theLobby.LobbyProvider].ProviderName

        #Make our fourth embed, to start searching.
        embedMessage = discord.Embed(title="Discord Game Coordinator.")
        embedMessage.add_field(name="Blast off! :sunglasses:", value="You have now been added into the matchmaking queue.",inline=False)
        embedMessage.add_field(name="Provider", value=f"{providerName}", inline=True)
        embedMessage.add_field(name="Region:", value=f"{reaction}", inline=True)
        embedMessage.add_field(name="Maps/Gamemodes:", value=f"{theLobby.LobbyMaps}", inline=True)

        await actualMessage.edit(embed=embedMessage) #Edit the original message.
        print(f"[LOBBY] Final constructed lobby:\n", theLobby.LobbyOwner, theLobby.LobbyProvider, theLobby.LobbyRegion, theLobby.LobbyChannelSentIn)
        self.lobbylist[sender.id] = theLobby
        return
    #c!stop. Stops searching for servers.
    async def command_stop(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        if sender.id in self.lobbylist:
            self.lobbylist.pop(sender.id) #Remove.
            #Construct an embed.
            embedMessage = discord.Embed(title="Discord Game Coordinator.")
            embedMessage.add_field(name="Unexpected landing! :cry:", value="You have been removed from the matchmaking queue. You can requeue with the command c!play.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
        else:
            await channel.send(f"<@{sender.id}>, you are currently not in the matchmaking queue.")

    class ServerQueryFail(BaseException):
        pass

    #The loop that handles server querying. Pings all of the servers in a list, which updates the list itself.
    @tasks.loop(seconds=10)
    async def loop_serverquerying(self):
        #Go through each provider, and then each server:
        for provider in self.providerdict:
            ServerCount = 0
            NewServerList = []
            providerObj = self.providerdict[provider]
            
            #Are we using the Creators.TF API?
            if providerObj.ProviderAPIType == 1:
                #Region ID's that match up with our pre-defined ones.
                #Specific to the Creators API.
                Regions = {
                    "us": 0,
                    "eu": 1,
                    "ru": 2,
                    "au": 3,
                    "sg": 4,
                    "br": 5,
                    "no": 6, }
                try:
                    #Request the server information using the Creators.TF API.
                    RequestObject_Obj = requests.get(providerObj.ProviderURL)

                    if not RequestObject_Obj.json():
                        raise self.ServerQueryFail(f"Failed to get list of servers for {providerObj.ProviderName}. Status code {RequestObject_Obj.status_code}\nUnable to construct a proper JSON object.")
                        continue
                    ServerReqJSON_Obj = RequestObject_Obj.json()

                    #GET request returned something that wasn't OK.
                    if RequestObject_Obj.status_code != 200:
                        raise self.ServerQueryFail(f"Failed to get list of servers for {providerObj.ProviderName}. Status code {RequestObject_Obj.status_code}")
                        continue

                    #API returned an error.
                    if ServerReqJSON_Obj["result"] != "SUCCESS":
                        ErrorInformation = ServerReqJSON_Obj["error"]
                        ErrorCode = ErrorInformation["code"]
                        ErrorTitle = ErrorInformation["title"]
                        ErrorContent = ErrorInformation["content"]
                        raise self.ServerQueryFail(f"[SERVER] Failed to get list of servers for {providerObj.ProviderName}. Status code {ErrorCode}.\n{ErrorTitle}\n{ErrorContent}")
                        continue
                    
                #General error processing incase something goes wrong.
                except self.ServerQueryFail as ServerQFail:
                    print(f"[EXCEPTION] ServerQueryFail reported: \n{ServerQFail}")
                    continue
                except json.JSONDecodeError:
                    print(f"[EXCEPTION] Failed to get list of servers for {providerObj.ProviderName}. Status code {RequestObject_Obj.status_code}\nUnable to construct a proper JSON object.")
                    continue
                
                ServerJSON_Obj = ServerReqJSON_Obj["servers"]

                #Now construct server objects:
                for server in ServerJSON_Obj:
                    #Don't bother with these servers if we can't get to them.
                    if server["is_down"] or server["passworded"] == True:
                        continue
                    
                    #Construct the server object.
                    Obj = server_coordinator.GameCoordinator_Server()
                    Obj.ServerAddress = (server["ip"], server["port"])
                    Obj.ServerName = server["hostname"]
                    Obj.ServerRegionID = Regions.get(server["region"])
                    Obj.ServerMap = server["map"]
                    Obj.ServerPlayers = server["online"]
                    Obj.ServerMaxPlayers = server["maxplayers"]
                    NewServerList.append(Obj)
                    ServerCount += 1

                providerObj.ProviderServers = NewServerList
                print(f"[SERVER] Provider {providerObj.ProviderName} processed {ServerCount} servers.")

    @tasks.loop(seconds=5)
    async def loop_lobbymatchmaking(self):
        def PerformChecks(lobbyObj, server):
            #Compatiable region?
            if lobbyObj.LobbyRegion != server.ServerRegionID:
                print(f"[LOBBY] {lobbyObj.LobbyOwner}'s lobby is incompatiable. Server Region {server.ServerRegionID} != Lobby Region {lobbyObj.LobbyRegion}")
                return False

            #Is the server full?
            if server.ServerPlayers == server.ServerMaxPlayers:
                print(f"[LOBBY] {lobbyObj.LobbyOwner}'s lobby is incompatiable. Server is full.")
                return False

            #Has more than the "best server" of players?
            if self.bestServer: #The server could be None at this point, so just ignore the check if it is.
                if self.bestServer.ServerPlayers > server.ServerPlayers:
                    print(f"[LOBBY] {lobbyObj.LobbyOwner}'s lobby is incompatiable. The best server has more players. ({self.bestServer.ServerPlayers} > {server.ServerPlayers})")
                    return False

            #We have specified maps/gamemodes we want to play, find them:
            if type(lobbyObj.LobbyMaps) == list:          
                FoundMap = False

                #Is one of our maps on this server currently?
                for item in lobbyObj.LobbyMaps:
                    print(f"[LOBBY] Map Comparison: {item} -> {server.ServerMap}")
                    if item not in server.ServerMap:
                        continue
                    else: #Found it!
                        FoundMap = True
                        print(f"[LOBBY] {lobbyObj.LobbyOwner}: Map found!")
                        break

                if FoundMap == False:
                    print(f"[LOBBY] {lobbyObj.LobbyOwner}'s lobby is incompatiable. No map found.")
                    return False
            else:
                print(f"[LOBBY] {lobbyObj.LobbyOwner}'s lobby wants any map.")

            #We've passed all of our checks. Lets make this the best server.
            self.bestServer = server
            return True

        #Loop through all the lobbies currently in our queue.
        for key in self.lobbylist.copy():
            lobbyObj = self.lobbylist.copy()[key]
            await asyncio.sleep(0.5)
            print(f"[LOBBY] Processing Lobby owned by: {lobbyObj.LobbyOwner}")
            self.bestServer = None #Store the best server that we have so far.
            provider = self.providerdict[lobbyObj.LobbyProvider]
            
            if not provider: #Invalid provider check.
                continue
            
            #Loop through the avaliable servers and check a few things.
            for server in provider.ProviderServers:
                PerformChecks(lobbyObj, server)

            #We do not have the "best" server.
            if not self.bestServer:
                continue

            #Ping the server again to get the latest info.
            try:
                #Query the server with A2S here.
                ServerQueryResponse = a2s.info(self.bestServer.ServerAddress, timeout=2.0)
                ServerPlayersQueryResponse = a2s.players(self.bestServer.ServerAddress, timeout=2.0)
                if not ServerQueryResponse: #If we somehow fail to query the server and the object is not fully created, pull out.
                    raise self.ServerQueryFail("A2S object was not properly constructed.")
                    continue

                #Now we'll update this server object.
                self.bestServer.ServerName = ServerQueryResponse.server_name
                self.bestServer.ServerPlayers = len(ServerPlayersQueryResponse)
                self.bestServer.ServerMaxPlayers = ServerQueryResponse.max_players
                self.bestServer.ServerMap = ServerQueryResponse.map_name
            except:
                continue
            
            #The best server has gotten worse, continue on.
            if PerformChecks(lobbyObj, self.bestServer) == False:
                continue

            providerObj = self.providerdict[lobbyObj.LobbyProvider]
            providerName = providerObj.ProviderName

            #This dict holds our emojis, as well as the values for our regions.
            #dictOfEmoji = {"🇺🇸": 1, "🇪🇺": 2, "🇷🇺": 3, "🇦🇺": 4, "🇸🇬": 5}
            dictOfEmoji = {0:"🇺🇸", 1:"🇪🇺", 2:"🇷🇺"}

            reaction = dictOfEmoji[lobbyObj.LobbyRegion]

            #Make our embed that we send off to players.
            embedMessage = discord.Embed(title="Discord Game Coordinator")
            # MapImageReq = requests.get("https://creators.tf/api/mapthumb?map=" + self.bestServer.ServerMap)

            # #Lets be over the top and lets make something cool with the API features we have.
            # if MapImageReq.status_code == 200:
            #     img = Image.open(BytesIO(MapImageReq.content))
            #     imagedraw = ImageDraw.Draw(img)

            #     fnt = ImageFont.truetype('tf2build.ttf', 30)
            #     fnt2 = ImageFont.truetype('tf2build.ttf', 20)
            #     imagedraw.text((20,20), "You're on your way to...", font=fnt, fill=(255, 255, 255))
            #     imagedraw.text((20,50), self.bestServer.ServerMap, font=fnt2, fill=(255, 255, 255))
            #     img.save("tmp.png")
            #     imgFile = discord.File("tmp.png")
            #     embedMessage.set_image(imgFile)

            embedMessage.set_image(url=f"https://creators.tf/api/mapthumb?map={self.bestServer.ServerMap}")
            embedMessage.add_field(name="Touchdown :rocket: :sunglasses:", value="A server has been found for you!",inline=False)
            embedMessage.add_field(name="Provider", value=f"{providerName}", inline=True)
            embedMessage.add_field(name="Server Name:", value=f"{self.bestServer.ServerName}", inline=True)
            embedMessage.add_field(name="Region:", value=f"{reaction}", inline=True)
            embedMessage.add_field(name="Map", value=f"{self.bestServer.ServerMap}", inline=True)
            embedMessage.add_field(name="Players", value=f"{self.bestServer.ServerPlayers}/{self.bestServer.ServerMaxPlayers}", inline=True)
            embedMessage.add_field(name="Connect using Steam:", value=f"steam://connect/{self.bestServer.ServerAddress[0]}:{self.bestServer.ServerAddress[1]}", inline=False)
            embedMessage.add_field(name="Or use the Console:", value=f"connect {self.bestServer.ServerAddress[0]}:{self.bestServer.ServerAddress[1]}", inline=False)

            await lobbyObj.LobbyChannelSentIn.send(f"<@{lobbyObj.LobbyOwner.id}>", embed=embedMessage) #Edit the original message.

            self.lobbylist.pop(lobbyObj.LobbyOwner.id)
            await asyncio.sleep(0.5)

    commands = {
        "c!findserver": command_findserver,
        "c!find": command_findserver,
        "c!play": command_findserver,
        "c!stop": command_stop,
        "c!stopsearch": command_stop,
        "c!help": None,
    }

gcObj = GameCoordinatorBot()

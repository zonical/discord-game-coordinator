import discord
import asyncio
import lobby
import a2s
import server_coordinator
import requests
import json
import re
from discord.ext import commands, tasks
from discord.utils import get
from sys import argv
from settings import UserData, UserSettings, ServerData, DefaultServerSettings

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

# c!play argument helpers
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

# c!help helpers
# the basic information about each command
cmdHelp = {
    "c!help [command]": "Shows all the commands and information about them.",
    "c!play [provider] [region] [maps]": "Enters you into a matchmaking lobby.",
    "c!startqueue (player amount target) (provider) (region) [maps]": "Creates a queue for people to join",
    "c!join (queueid)": "Joins a queue with the given id.",
    "c!stop": "Removes you from your matchmaking lobby.",
    "c!setting (name) (value)": "Changes various user settings.",
    "c!settings": "Shows your current settings."
}

# more in depth info when using c!help [command]
cmdAdvHelp = {
    "help": "Shows all the commands and information about them\nParameters: [] = optional, () = required",
    "play": "Enters you into a matchmaking lobby.\n[provider] = Server Prodiver (creators, bmod, events)\n[region] = Server Region (eu, na, ru, australia, singapore, brazil, norway)\n[maps] = Maps and gamemodes you want to play (koth, pl_coldwater, *)",
    "stop": "Removes you from your matchmaking lobby",
    "setting": "Changes various user settings\n(name) = Name of the setting you want to change (min_players, max_players)\n(value) = Value to set that setting to",
    "settings": "Shows your current settings."
}

# Enables console printing of a lot of stuff
debug = False
if len(argv) > 2:
    debug = bool(argv[2])

# global utility functions
def debugPrint(str):
    if debug:
        print(str)

def defaultEmbed():
    return discord.Embed(title="Discord Game Coordinator.")


#The Game Coordinator bot class. This bot has three main purposes:
#1) Getting the latest server information of Creators.TF servers.
#2) Providing a matchmaking service for the C.TF Discord.
#3) Having this matchmaking service be customisable (e.g search by region, map, etc.)

botVersion = "0.1d"

class GameCoordinatorBot(discord.Client):
    providerdict = {}
    lobbylist = []
    # waitinglist = [] this does nothing so i removed it

    @property
    def queueingAmount(self):
        return len(self.lobbylist)

    queuelist = []

    def isInQueue(self, id):
        for queue in self.queuelist:
            if queue.Owner.id == id:
                return True, self.queuelist.index(queue), True
            for member in queue.Members:
                if member.id == id:
                    return True, self.queuelist.index(queue), False
        return False, None, False

    def __init__(self):
        #Initalise the bot.
        super().__init__()

        #Call for servers.
        self.providerdict = server_coordinator.CreateProviders()

        # Load default server stuff too
        ServerData.Read()

        # Load default settings
        UserSettings.Read()
        # Update the users
        UserData.ReadUsers()

        self.loop_serverquerying.start()
        self.loop_lobbymatchmaking.start()
        self.loop_querymatchmaking.start()

        #And now, launch the bot.
        self.run(argv[1], reconnect=True)

    async def on_ready(self):
        print("[START] Game Coordinator Bot has started.")
        print(f"[START] Information: Version {botVersion}, Created by ZoNiCaL, Modified by qualitycont. Bot Account: {self.user}")
        
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
            debugPrint(f"[COMMAND] Invalid command from {message.author}: {actualCommand}")
            return
        
        #We have a dictionary object full of command names, and the functions that we're calling.
        await self.commands[actualCommand](self, sender, message.channel, commandArgs)

    # help command
    async def command_help(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        embedMessage = defaultEmbed()
        if( len(arguments) == 1 and arguments[0] in cmdAdvHelp):
            info = cmdAdvHelp[arguments[0]]
            embedMessage.add_field(name=f"c!{arguments[0]}", value=info, inline=False)
        else:
            for cmd in cmdHelp:
                embedMessage.add_field(name=f"{cmd}", value=cmdHelp[cmd], inline=False)
        await channel.send(f"<@{sender.id}>", embed=embedMessage)

    # c!setting. this is to change per user settings such as min and max players
    async def command_setting(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        embedMessage = defaultEmbed()
        if not len(arguments) == 2:
            embedMessage.add_field(name="Couldnt change setting! :tear:", value="You didnt specify exactly 2 parameters!", inline = False)
        else:
            if not UserData.GetUser(sender.id):
                UserData(sender.id)

            k = arguments[0] # name of the setting
            v = arguments[1] # the value to set it to

            if k in UserData.Settings:
                UserData.SetUserSetting(sender.id, k, v)
                UserData.WriteUsers()
                embedMessage.add_field(name="Setting Changed!", value=f"Setting {k} changed to {v}!", inline=False)
            else:
                embedMessage.add_field(name="Couldnt change setting! :tear:", value=f"Setting {k} does not exist!", inline = False)
        await channel.send(f"<@{sender.id}>", embed=embedMessage)

    async def command_showsettings(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        embedMessage = defaultEmbed()

        embedMessage.set_thumbnail(url=sender.avatar_url)
        embedMessage.set_author(name=sender.name)
        
        data = UserData.GetOrRegisterUser(sender.id)
        for k in data:
            embedMessage.add_field(name=f"{UserSettings.Get(k).DisplayName}", value=f"{data[k]}", inline=False)
        await channel.send(f"<@{sender.id}>", embed=embedMessage)

    async def command_joinqueue(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        if sender.id in self.lobbylist or self.isInQueue(sender.id)[0]:
            #Construct an embed.
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You are already in the matchmaking queue. You can leave the queue with the command c!stop.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
            return
        
        if len(arguments) < 1:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You did not provide enough arguments to use this command!",inline=False)
            await channel.send(f"<@{sender.id}>",embed=embedMessage)
            return
        
        id = int(arguments[0])

        if not self.queuelist[id]:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value=f"The queue {id} does not exist!!",inline=False)
            await channel.send(f"<@{sender.id}>",embed=embedMessage)
            return
        
        await self.queuelist[id].AddMember(sender)

        embedMessage = defaultEmbed()
        embedMessage.add_field(name="Blast off! :sunglasses:", value=f"You have joined queue #{id}!",inline=False)
        await channel.send(embed=embedMessage)

    # COMMAND: STARTQUEUE
    async def command_startqueue(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        inQueue, _1, _2 = self.isInQueue(sender.id)
        if sender.id in self.lobbylist or inQueue:
            #Construct an embed.
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You are already in the matchmaking queue. You can leave the queue with the command c!stop.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
            return

        adminOnly = ServerData.GetServerSetting(channel.guild.id, "queue_admin_only")
        if adminOnly and not sender.permissions_in(channel).manage_messages:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You do not have the correct permissions to start a queue!.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
            return

        theQueue = lobby.QueueLobby()
        theQueue.Owner = sender
        theQueue.ChannelSentIn = channel

        actualMessage = await channel.send(embed=defaultEmbed())

        if len(arguments) < 3:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You did not provide enough arguments to use this command!",inline=False)
            await actualMessage.edit(content=f"<@{sender.id}>",embed=embedMessage)
            return
        
        theQueue.PlayerTarget = int(arguments[0])

        if arguments[1] in NameToProviderID:
            theQueue.Provider = NameToProviderID[arguments[1]]
        else:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="The provider specified does not exist!",inline=False)
            await actualMessage.edit(content=f"<@{sender.id}>",embed=embedMessage)
            return
            
        if arguments[2] in NameToRegionID:
            theQueue.Region = NameToRegionID[arguments[2]]
        else:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="The region specified does not exist!",inline=False)
            await actualMessage.edit(content=f"<@{sender.id}>",embed=embedMessage)
            return
        
        if len(arguments) > 3:
            #If we want to select ANY map or gamemode, lets do it here.
            for tmpStr in ["*", "any", "all"]:
                if tmpStr in arguments[3]:
                    theQueue.Maps = tmpStr
                    break
            else:
                #Remove whitespace from the maps/gamemodes, and set our queue map/gamemode list.
                messageContent = arguments[3:]
                theQueue.Maps = messageContent.copy()
        else:
            theQueue.Maps = "*"

        #Get the name of our provider.
        providerName = self.providerdict[theQueue.Provider].ProviderName

        #Get the region emoji
        regionEmoji = RegionIDToInformation[theQueue.Region][1]

        broadcastChannel = get(channel.guild.text_channels, name=ServerData.GetServerSetting(channel.guild.id, "queue_channel"))
        if broadcastChannel:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Queue Created!", value=f"More information in #{broadcastChannel}!",inline=False)
            await actualMessage.edit(embed=embedMessage)

            extraEmbedMessage = defaultEmbed()
            extraEmbedMessage.add_field(name="Provider", value=f"{providerName}", inline=True)
            extraEmbedMessage.add_field(name="Region:", value=f"{regionEmoji}", inline=True)
            extraEmbedMessage.add_field(name="Maps/Gamemodes:", value=f"{theQueue.Maps}", inline=True)
            extraEmbedMessage.add_field(name="Player Target:", value=f"{arguments[0]}", inline=True) 
            extraEmbedMessage.add_field(name="Join this queue!", value=f"You can join this queue using c!join {len(self.queuelist)}")
            extraEmbedMessage.insert_field_at(4, name="Players Queueing", value=f"{sender.name}", inline=True) # we need to edit this later so im using 4 as an index

            toPingString = f"<@{sender.id}>"
            broadcastRole = ServerData.GetServerSetting(channel.guild.id, "queue_notify_role")
            if broadcastRole:
                toPingString += f" {broadcastRole}"

            theQueue.MessageToUpdate = await broadcastChannel.send(content=toPingString,embed=extraEmbedMessage)
        else:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Provider", value=f"{providerName}", inline=True)
            embedMessage.add_field(name="Region:", value=f"{regionEmoji}", inline=True)
            embedMessage.add_field(name="Maps/Gamemodes:", value=f"{theQueue.Maps}", inline=True)
            embedMessage.add_field(name="Player Target:", value=f"{arguments[0]}", inline=True) 
            embedMessage.add_field(name="Join this queue!", value=f"You can join this queue using c!join {len(self.queuelist)}")
            embedMessage.insert_field_at(4, name="Players Queueing", value=f"{sender.name}", inline=True) # we need to edit this later so im using 4 as an index

            await actualMessage.edit(embed=embedMessage)
            theQueue.MessageToUpdate = actualMessage

        self.queuelist.append(theQueue)


    async def command_serversetting(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        if not sender.permissions_in(channel).manage_channels:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You do not have permissions to change server settings.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
            return

        if len(arguments) < 2:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You did not specify enough arguments to uss this command.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
            return

        if not arguments[0] in DefaultServerSettings:
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value=f"The server setting {arguments[0]} does not exist!",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
            return

        id = channel.guild.id
        ServerData.GetOrRegister(id)
        ServerData.SetServerSetting(id, arguments[0], arguments[1])
        ServerData.Write()

        embedMessage = defaultEmbed()
        embedMessage.add_field(name="Setting Changed!", value=f"Setting {arguments[0]} changed to {arguments[1]}",inline=False)
        await channel.send(f"<@{sender.id}>", embed=embedMessage)
        return

    #c!findserver. This will construct an embed where users can select what they want.
    async def command_findserver(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        if sender.id in self.lobbylist or self.isInQueue(sender.id):
            #Construct an embed.
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :tear:", value="You are already in the matchmaking queue. You can leave the queue with the command c!stop.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
            return

        #Create our lobby class:
        theLobby = lobby.Lobby()
        theLobby.Owner = sender
        theLobby.ChannelSentIn = channel
        
        #things we might need later
        def check(reaction, user):
            return user == sender

        actualMessage = await channel.send(embed=defaultEmbed())

        settings = UserData.GetOrRegisterUser(sender.id)

        # confirmation emoji dict
        confirmationEmojis = {
            "✅": True,
            "❌": False
        }

        # util function for checking if we want the default value
        async def defaultCheck(settingK, settingV):
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Do you want to use the default setting?", value=f"You have a valid default value \"{settingV}\" for the setting {settingK}, do you want to use it?")

            await actualMessage.edit(embed=embedMessage)
            for emoji in confirmationEmojis:
                await actualMessage.add_reaction(emoji)
            
            try: #Start our waiting process.
                reaction, user = await self.wait_for('reaction_add', timeout=10.0, check=check)
            except asyncio.TimeoutError: #We waited for too long :(
                await  actualMessage.edit(f"<@{sender.id}>, you took too long to confirm the default setting, assumed no.")
                await actualMessage.clear_reactions() #Clear the reactions.
                return False

            await actualMessage.clear_reactions() #Clear the reactions again
            if not reaction.emoji in confirmationEmojis:
                await actualMessage.edit(f"<@{sender.id}>, invalid reaction!.")
                await actualMessage.clear_reactions() #Clear the reactions.
                return False # incase somebody adds a random emoji
            
            return confirmationEmojis[reaction.emoji]

        defaultProvider = settings["default_provider"]
        if len(arguments) > 0 and str(arguments[0]).lower() in NameToProviderID: # are there any arguments? is the provider valid?
            theLobby.Provider = NameToProviderID[str(arguments[0]).lower()] # easy provider id getting
        elif defaultProvider != None and defaultProvider in NameToProviderID and await defaultCheck("default_provider",defaultProvider): # if theres a default provider and the user wants to use it, no need for selection
            theLobby.Provider = NameToProviderID[defaultProvider]
        else: # no arguments or invalid provider
            #Make the embed, with all of our providers.
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Provider Selection.", value="Please pick a provider to search from using the reactions below.",inline=False)

            #Loop through all of our registered providers and add them to the Embed:
            for provider in self.providerdict.values():
                EmojiTuple = IDtoEmojis[provider.ProviderID_GC]
                embedMessage.add_field(name=provider.ProviderName, value=EmojiTuple[1], inline=True)

            await actualMessage.edit(embed=embedMessage) #Send here, returns a message object where we can add reactions.
            
            #Add our emoji reactions so the user doesn't have to.
            for provider in self.providerdict:
                emojiTuple = IDtoEmojis[provider]
                await actualMessage.add_reaction(emojiTuple[0])


            try: #Start our waiting process.
                reaction, user = await self.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError: #We waited for too long :(
                await channel.send(f"<@{sender.id}>, your request to use the Game Coordinator has expired.")
                return

            #Set our provider by grabbing a value from the dict.
            for providerID, emoji in IDtoEmojis.items():
                if (str(reaction.emoji) == emoji[0]):
                    theLobby.Provider = providerID
                    break
        
            #Could not grab the emoji :(
            if (theLobby.Provider == -1):
                await channel.send(f"<@{sender.id}>, your request to use the Game Coordinator has failed. Please submit a proper reaction next time.")
                return

            await actualMessage.clear_reactions() #Clear the reactions.

        #======================================================================================================================================

        #Create our ProviderObject so we can use it for later things:
        ProviderObject = self.providerdict[theLobby.Provider]

        defaultRegion = settings["default_region"]
        if len(arguments) > 1 and str(arguments[1]).lower() in NameToRegionID: # same as provider but with region
            theLobby.Region = NameToRegionID[str(arguments[1]).lower()]
        elif defaultRegion != None and defaultRegion in NameToRegionID and await defaultCheck("default_region",defaultRegion): # if theres a default region and the user wants to use it, no need for selection
            theLobby.Region = NameToRegionID[defaultRegion]
        else: #again, fall back to the reactions if theres no region
            #Make our second embed, with all of our regions.
            embedMessage = defaultEmbed()
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
                    theLobby.Region = regionID
                    break
            
            #Could not grab the emoji :(
            if (theLobby.Region == -1):
                await channel.send(f"<@{sender.id}>, your request to use the Game Coordinator has failed. Please submit a proper reaction next time.")
                return

            await actualMessage.clear_reactions() #Clear the reactions.

        messageContent = "" # we need to use this later
        if len(arguments) > 2: # are there any arguments left?
            messageContent = ','.join(arguments[2:len(arguments)]) #turn arguments into usable string
        else: #again, fall back to the reactions if theres no region
            #Make our third embed, for the gamemode selection.
            embedMessage = defaultEmbed()
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
                theLobby.Maps = tmpStr
                break
        else:
            #Remove whitespace from the maps/gamemodes, and set our lobby map/gamemode list.
            messageContent = re.sub(r'\s+', '', messageContent)
            theLobby.Maps = messageContent.split(',').copy()
        
        #Get the name of our provider.
        providerName = self.providerdict[theLobby.Provider].ProviderName

        #Get the region emoji
        regionEmoji = RegionIDToInformation[theLobby.Region][1]

        #Make our fourth embed, to start searching.
        embedMessage = defaultEmbed()
        embedMessage.add_field(name="Blast off! :sunglasses:", value="You have now been added into the matchmaking queue.",inline=False)
        embedMessage.add_field(name="Provider", value=f"{providerName}", inline=True)
        embedMessage.add_field(name="Region:", value=f"{regionEmoji}", inline=True)
        embedMessage.add_field(name="Maps/Gamemodes:", value=f"{theLobby.Maps}", inline=True)

        await actualMessage.edit(embed=embedMessage) #Edit the original message.
        print(f"[LOBBY] Final constructed lobby:\n", theLobby.Owner, theLobby.Provider, theLobby.Region, theLobby.ChannelSentIn)
        self.lobbylist[sender.id] = theLobby
        return
    #c!stop. Stops searching for servers.
    async def command_stop(self, sender : discord.User, channel : discord.TextChannel, arguments : list):
        inQueue, queue, isOwner = self.isInQueue(sender.id)
        if sender.id in self.lobbylist:
            self.lobbylist.pop(sender.id) #Remove.
            #Construct an embed.
            embedMessage = defaultEmbed()
            embedMessage.add_field(name="Unexpected landing! :cry:", value="You have been removed from the matchmaking queue. You can requeue with the command c!play.",inline=False)
            await channel.send(f"<@{sender.id}>", embed=embedMessage)
        elif inQueue:
            queueObj = self.queuelist[queue]
            if isOwner:
                await queueObj.Close()
            else:
                await queueObj.Close()
            self.queuelist.remove(queueObj)
            #Construct an embed.
            embedMessage = defaultEmbed()
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
                debugPrint(f"[SERVER] Provider {providerObj.ProviderName} processed {ServerCount} servers.")

    @tasks.loop(seconds=15)
    async def loop_querymatchmaking(self):
        def PerformChecks(queueObj : lobby.QueueLobby, server): 
            #Compatiable region?
            if queueObj.Region != server.ServerRegionID:
                debugPrint(f"[LOBBY] {queueObj.Owner}'s queue is incompatiable. Server Region {server.ServerRegionID} != Lobby Region {queueObj.Region}")
                return False

            #with players in queue
            theoreticalPlayers = server.ServerPlayers+queueObj.MemberCount

            #Do we meet the player target?
            if theoreticalPlayers < queueObj.PlayerTarget:
                debugPrint(f"[LOBBY] {queueObj.Owner}'s queue is incompatiable. Not enough players.")
                return False

            if server.ServerPlayers > queueObj.PlayerTarget: #+1 so theres a need for at least one more person
                debugPrint(f"[LOBBY] {queueObj.Owner}'s queue is incompatiable. Too Many players.")
                return False

            #We have specified maps/gamemodes we want to play, find them:
            if type(queueObj.Maps) == list:          
                FoundMap = False

                #Is one of our maps on this server currently?
                for item in queueObj.Maps:
                    debugPrint(f"[LOBBY] Map Comparison: {item} -> {server.ServerMap}")
                    if item not in server.ServerMap:
                        continue
                    else: #Found it!
                        FoundMap = True
                        debugPrint(f"[LOBBY] {queueObj.Owner}: Map found!")
                        break

                if FoundMap == False:
                    debugPrint(f"[LOBBY] {queueObj.Owner}'s lqueue is incompatiable. No map found.")
                    return False
            else:
                debugPrint(f"[LOBBY] {queueObj.Owner}'s queue wants any map.")

            #We've passed all of our checks. Lets make this the best server.
            self.bestServer = server
            return True

        for queueObj in self.queuelist.copy():
            await asyncio.sleep(0.5)
            debugPrint(f"[LOBBY] Processing Lobby owned by: {queueObj.Owner}")
            self.bestServer = None #Store the best server that we have so far.
            provider = self.providerdict[queueObj.Provider]
            
            if not provider: #Invalid provider check.
                continue
            
            #Loop through the avaliable servers and check a few things.
            for server in provider.ProviderServers:
                PerformChecks(queueObj, server)

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
            if PerformChecks(queueObj, self.bestServer) == False:
                continue

            providerObj = self.providerdict[queueObj.Provider]
            providerName = providerObj.ProviderName

            #This dict holds our emojis, as well as the values for our regions.
            #dictOfEmoji = {"🇺🇸": 1, "🇪🇺": 2, "🇷🇺": 3, "🇦🇺": 4, "🇸🇬": 5}
            dictOfEmoji = {0:"🇺🇸", 1:"🇪🇺", 2:"🇷🇺"}

            reaction = dictOfEmoji[queueObj.Region]

            #Make our embed that we send off to players.
            embedMessage = defaultEmbed()

            embedMessage.set_image(url=f"https://creators.tf/api/mapthumb?map={self.bestServer.ServerMap}")
            embedMessage.add_field(name="Touchdown :rocket: :sunglasses:", value="A server has been found for you!",inline=False)
            embedMessage.add_field(name="Provider", value=f"{providerName}", inline=True)
            embedMessage.add_field(name="Server Name:", value=f"{self.bestServer.ServerName}", inline=True)
            embedMessage.add_field(name="Region:", value=f"{reaction}", inline=True)
            embedMessage.add_field(name="Map", value=f"{self.bestServer.ServerMap}", inline=True)
            embedMessage.add_field(name="Players", value=f"{self.bestServer.ServerPlayers}/{self.bestServer.ServerMaxPlayers} (+{queueObj.MemberCount})", inline=True)
            embedMessage.add_field(name="Connect using Steam:", value=f"steam://connect/{self.bestServer.ServerAddress[0]}:{self.bestServer.ServerAddress[1]}", inline=False)
            embedMessage.add_field(name="Or use the Console:", value=f"connect {self.bestServer.ServerAddress[0]}:{self.bestServer.ServerAddress[1]}", inline=False)

            memberPingString = f"<@{queueObj.Owner.id}>"
            for member in queueObj.Members:
                memberPingString += f" <@{member.id}>"

            await queueObj.ChannelSentIn.send(memberPingString, embed=embedMessage) #Edit the original message.

            await queueObj.Close()
            self.queuelist.remove(queueObj)
            await asyncio.sleep(0.5)

    @tasks.loop(seconds=5)
    async def loop_lobbymatchmaking(self): # for c!play queueing
        def PerformChecks(lobbyObj, server): 
            # get the settings for later
            settings = UserData.GetOrRegisterUser(lobbyObj.Owner.id)

            #Compatiable region?
            if lobbyObj.Region != server.ServerRegionID:
                debugPrint(f"[LOBBY] {lobbyObj.Owner}'s lobby is incompatiable. Server Region {server.ServerRegionID} != Lobby Region {lobbyObj.Region}")
                return False

            #Is the server full?
            if server.ServerPlayers == server.ServerMaxPlayers:
                debugPrint(f"[LOBBY] {lobbyObj.Owner}'s lobby is incompatiable. Server is full.")
                return False

            #Has more than the "best server" of players?
            if self.bestServer: #The server could be None at this point, so just ignore the check if it is.
                if self.bestServer.ServerPlayers > server.ServerPlayers:
                    debugPrint(f"[LOBBY] {lobbyObj.Owner}'s lobby is incompatiable. The best server has more players. ({self.bestServer.ServerPlayers} > {server.ServerPlayers})")
                    return False

            #We have specified maps/gamemodes we want to play, find them:
            if type(lobbyObj.Maps) == list:          
                FoundMap = False

                #Is one of our maps on this server currently?
                for item in lobbyObj.Maps:
                    debugPrint(f"[LOBBY] Map Comparison: {item} -> {server.ServerMap}")
                    if item not in server.ServerMap:
                        continue
                    else: #Found it!
                        FoundMap = True
                        debugPrint(f"[LOBBY] {lobbyObj.Owner}: Map found!")
                        break

                if FoundMap == False:
                    debugPrint(f"[LOBBY] {lobbyObj.Owner}'s lobby is incompatiable. No map found.")
                    return False
            else:
                debugPrint(f"[LOBBY] {lobbyObj.Owner}'s lobby wants any map.")

            if server.ServerPlayers < int(settings["min_players"]): # because json has everything as string, we have to int() it here
                debugPrint(f"[LOBBY] {lobbyObj.Owner}'s lobby is incompatible, it has has less players then required from user settings")
                return False # not enough players
            
            if server.ServerPlayers > int(settings["max_players"]): # same for this
                debugPrint(f"[LOBBY] {lobbyObj.Owner}'s lobby is incompatible, it has has more players then required from user settings")
                return False # too many players

            #We've passed all of our checks. Lets make this the best server.
            self.bestServer = server
            return True

        #Loop through all the lobbies currently in our queue.
        for key in self.lobbylist.copy():
            lobbyObj = self.lobbylist.copy()[key]
            await asyncio.sleep(0.5)
            debugPrint(f"[LOBBY] Processing Lobby owned by: {lobbyObj.Owner}")
            self.bestServer = None #Store the best server that we have so far.
            provider = self.providerdict[lobbyObj.Provider]
            
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

            providerObj = self.providerdict[lobbyObj.Provider]
            providerName = providerObj.ProviderName

            #This dict holds our emojis, as well as the values for our regions.
            #dictOfEmoji = {"🇺🇸": 1, "🇪🇺": 2, "🇷🇺": 3, "🇦🇺": 4, "🇸🇬": 5}
            dictOfEmoji = {0:"🇺🇸", 1:"🇪🇺", 2:"🇷🇺"}

            reaction = dictOfEmoji[lobbyObj.Region]

            #Make our embed that we send off to players.
            embedMessage = defaultEmbed()
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

            await lobbyObj.ChannelSentIn.send(f"<@{lobbyObj.Owner.id}>", embed=embedMessage) #Edit the original message.

            self.lobbylist.pop(lobbyObj.Owner.id)
            await asyncio.sleep(0.5)

    commands = {
        "c!help": command_help,
        "c!findserver": command_findserver,
        "c!find": command_findserver,
        "c!play": command_findserver,
        "c!startqueue": command_startqueue,
        "c!join": command_joinqueue,
        "c!stop": command_stop,
        "c!stopsearch": command_stop,
        "c!setting": command_setting,
        "c!settings": command_showsettings,
        "c!serversetting":command_serversetting
    }

gcObj = GameCoordinatorBot()

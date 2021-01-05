import discord
import asyncio

class Lobby:
    Owner = None
    ChannelSentIn = None
    Provider = -1
    Region = -1
    Maps = None

class QueueLobby(Lobby):
    Members = []
    MessageToUpdate = None
    
    # this also has settings but i dont see a point in making them modular like the user ones since they arent persistance so im just hard coding it
    PlayerTarget = 8 # players on the server + players in queue should add up to this, 12 is enough for 4v4 which means decently fun gameplay

    @property
    def MemberCount(self):
        return len(self.Members)+1
    
    async def AddMember(self, member: discord.Client):
        self.Members.insert(member)
        await updateMsg(self)
    
    async def RemoveMember(self, member:discord.Client):
        if member in self.Members:
            self.Members.remove(member)
            await updateMsg(self)
    
    async def Close(self):
        newEmbed = discord.Embed(title="Discord Game Coordinaotr")
        newEmbed.add_field(name="Queue Done", value="A server has been found, you can no longer join this queue.")
        await self.MessageToUpdate.edit(embed=newEmbed)

async def updateMsg(queue: QueueLobby):
    # upadte the player
    newEmbed = queue.MessageToUpdate.embeds[0]
    newEmbed.set_field_at(index=69, name="Players Queueing", value=f"{queue.Owner}, {queue.Members}", inline=True) 

    await queue.MessageToUpdate.edit(embed=newEmbed)
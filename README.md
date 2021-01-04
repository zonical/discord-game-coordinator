# discord-game-coordinator
A bot which is designed to find the best servers for Discord users. Originally made for the Creators.TF Discord, it can support many other server providers and regions.

## How it Works:
This bot is written in Python, using the discord.py and python-a2s libraries. To use the bot, users simply need to type in `c!play`. This will bring up a Discord Embed prompt which will ask users for which provider they'd like to play on (e.g Creators.TF), the region they'd like to play on (e.g USA, Europe, Russia), and which maps or gamemodes they'd like to play on (e.g `pl_cactuscanyon`, `cp`). The bot periodically makes API calls to the providers for the latest server information, which is stored internally. When a player creates a lobby, their settings are checked against the internal information to find the best server. A check is done on this server to see if it's still compatiable; if so, it is sent back to the user in Discord with all of the information they'll need.

## Setup
If you wish to just invite the current bot to your server, you can use this link: https://discord.com/api/oauth2/authorize?client_id=595515100698247169&permissions=59392&scope=bot . This bot asks for the following permissions: Send Messages, Manage Messages, Embed Links, and Attach Files. If the bot can't be added due to bot limits by Discord (it's not verified *yet!*), contact ZoNiCaL#9740 on Discord ASAP.

If you wish to host the bot yourself, there are a few steps involved in setup:
- Have the latest version of Python installed (anything > 3.8 should work okay).
- Install the latest versions of the discord.py and python-a2s libraries by typing this into a command prompt: `pip3 install -r requirements.txt` (The requirements file already includes the most up to date versions of the libraries.)
- Create an application, create a bot account and generate a bot token (https://discord.com/developers/applications).
- Launch `main.py`, with the bot token as a parameter: e.g `python3 main.py ABCDEFGHIJKLMNOPQRSTUVWXYZ`.

If you are hosting the bot yourself, and you wish to add more providers, you'll need to edit `ProviderConfig.json` as follows:
- Under the `"providers"` tag, create a new section with your provider name as the title (for an example, we'll use Creators.TF):

```json
{
    "providers":
    {
        "Creators.TF":
        {
```
- Then, add in the following, and fill in the appropiate information with your own. `name` will be the display name in the console and in Discord. `url` is the URL used for API querying. providerID is a unique interger (1-9 *at the moment, to do!*). `regions` is the ID's of which regions are supported.
```json
            "name": "Creators.TF",
            "url": "https://creators.tf/api/IServers/GServerList?provider=15",
            "providerID": 1,

            "regions": [
                0, 1, 2
            ]
        }
```

The regions are as follows:
*KEY: ID: (raw emoji code, discord emoji code, display name)*
```python
RegionIDToInformation = {
    0: ("🇺🇸", ":flag_us:", "USA/North America"),
    1: ("🇪🇺", ":flag_eu:", "Europe"),
    2: ("🇷🇺", ":flag_ru:", "Russia"),
    3: ("🇦🇺", ":flag_au:", "Australia/Oceania"),
    4: ("🇸🇬", ":flag_sg:", "Singapore"),
    5: ("🇧🇷", ":flag_br:", "Brazil"),
    6: ("🇳🇴", ":flag_no:", "Norway"),
}
```

If you wish to add your own regions, goto `main.py`, line 24; add or remove items/tuples from the dict as you please.

## Reporting Issues, or suggesting features:
If you have any issues with setting up the Game Coordinator for your own server, or if you want to make a feature request, the best way to get to me is DMing me on Discord at ZoNiCaL#9740. My DM's are always open, and a friend request isn't required. Feel free to make pull requests with new features; I won't always be checking this repo everyday, but I'll eventually see something if you post it.

## Special Mentions:
Big Mc'thankies from Mc'spankies to [Qualitycont](https://github.com/qualitycont) for contributing a lot of quality-of-life changes to the bot.

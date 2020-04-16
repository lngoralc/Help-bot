import discord
import json
import time
from datetime import datetime
import sys
import asyncio  # Testing proper Ctrl-C handling, needed for now

# Define custom exceptions: XlistedWord, CASViolation
class XlistedWord(Exception):
    pass

class CASViolation(Exception):
    pass

# Generate config
try:
    with open('config/config.json', encoding='utf8') as confFile:
        config = json.load(confFile)
except FileNotFoundError:
    with open('config/config.json', 'w', encoding='utf8') as confFile:
        config = {}
        json.dump({
            "name": "Help-bot",
            "description": "Serve Friend Computer!",
            "invoker": "$",
            "creator": "Friend Computer",
            "gitLink": "https://github.com/lngoralc/Help-bot",
            "computerRole": "Core System", # the role to assign to the person playing the Computer
            "computerUser": "Friend Computer", # the nickname to assign to the person playing the Computer
            "maxMsgLength": 0, # should be less than 2000 (discord char limit) minus the overhead of the longest alert/warn message below
            "topicResponse": "WARN: You have mentioned a restricted topic. This has been logged.", # feedback to a bad citizen
            "casResponse": "WARN: You have abused CAS. This has been logged.", # feedback to a bad citizen
            "topicAlert": "{} ```\nALERT: Conversation flagged for review.\nTime:           {}\nChannel:        {}\nCitizen:        {}\nClearance:      {}\nInfractions:    {}\nMessage:        {} ```", # monitoring message to the Computer
            "topicWarn": "```WARN: Possible mention of restricted topic in conversation.\nTime:           {}\nChannel:        {}\nCitizen:        {}\nMessage:        {} ```", # monitoring message to the Computer
            "casAlert": "{} ```\nALERT: Citizen abused Clearance Alert System.\nTime:           {}\nChannel:        {}\nCitizen:        {}\nClearance:      {}\nCAS Level:      {} ```", # monitoring message to the Computer
            "wordBlacklist": ["mutant", "treason", "commie", "communist"], # full or partial blacklisted words
            "wordWhitelist": ["anti-"], # partial whitelisted words (overrides an otherwise-blacklisted word, if the whitelisted phrase is present)
            "alertChannel": "monitoring", # name of the channel to send alerts to
            "PAChannel": "announcements", # name of the channel to send announcements to
            "DMChannels": "Computer Links", # name of the category for private citizen-computer comms
            "privateChannels": "Private Links" # name of the category for private citizen-citizen comms
        }, confFile, indent = 4, ensure_ascii = False)
        sys.exit("Config file created. "
            "Please make modifications as desired to the config.json file and restart the bot.");

try:
    with open('config/user-info.json', encoding='utf8') as confFile:
        userInfo = json.load(confFile)
        generalInfo = userInfo['generalInfo']
except FileNotFoundError:
    with open('config/user-info.json', 'w', encoding='utf8') as confFile:
        userInfo = {}
        json.dump({
            "generalInfo":{
                "discordToken": "",
                "userID": "",
                "clientID": "",
                "clientSecret": ""
            },
            "serverID": ""
        }, confFile, indent = 4, ensure_ascii = False)
        sys.exit("user info file created. "
            "Please fill out the user-info.json file and restart the bot.");

maxMsgLength = config['maxMsgLength']
client = discord.Client(description=config['description'], max_messages=100)
server = None
alertChannel = None
PAChannel = None
ComputerRole = None
Computer = None

@client.event
async def on_ready():
    print("\nInitializing...\n")
    global server
    global alertChannel
    global PAChannel
    global ComputerRole
    global Computer
    print("Model:                " + client.user.name)
    print("Number:               " + client.user.discriminator)
    
    serverID = userInfo['serverID']
    serverList = client.guilds
    print("Regions: ")
    for serv in serverList:
        print("    " + str(serv.id))
        if serv.id == int(serverID):
            server = serv
            break
#    print("    end of region list")
    if server != None:
        print("\nActive region:        " + str(server.id))
    else:
        print("\nERROR: Could not get server!\n")
        return
        
    print("Authorization code:   " + str(client.user.id))
    
    alertChannel = discord.utils.get(server.text_channels, name=config['alertChannel'])
    if alertChannel != None:
        print("Alert comm line:      " + str(alertChannel.id))
    else:
        print("\nERROR: Could not get alert comm line!\n")
        return
    
    PAChannel = discord.utils.get(server.text_channels, name=config['PAChannel'])
    if PAChannel != None:
        print("PA comm line:         " + str(PAChannel.id))
    else:
        print("\nERROR: Could not get public announcement line!\n")
        return
        
    print("\nLinking to the Computer...")
    ComputerRole = discord.utils.get(server.roles, name=config['computerRole'])
    Computer = discord.utils.get(server.members, display_name=config['computerUser'])
    if ComputerRole != None and Computer != None:
        print("Activated link to Computer.")
    else:
        print("\nWARN: Could not activate link to Computer.\n")
        return

    print("\n........................................\n")
    print("Initialization complete. Ready to serve!\n")

@client.event
async def on_message(msg: discord.Message):
    content = msg.content
    # Discord char limit is 2000, but the topic alert message length adds its base length to an up-to-2000-char triggering message
    # Therefore ignoring any characters in the message above a configured limit (configure according to your alert message base length)
    if len(content) > maxMsgLength:
        content = content[:maxMsgLength]

    contentLower = content.lower()
    author = msg.author
    authorClearance = author.top_role
    
    # Admin commands
    if content.startswith(config['invoker']) and author.guild_permissions.administrator:
        content = content[len(config['invoker']):].strip()
        args = content.split()
        command = args[0]
        args.remove(args[0])
        
        if command == "infractions":
            return
            
        if command == "shutdown":
            await shutdown()
            return
        
        if command == "updateLinks":
            await updateLinks()
            return
    
    # Do not trigger on Alpha Complex infrastructure
    elif author.bot or authorClearance == ComputerRole:
        return
        
    # Scan message content for infractions
    else:
        # Topic monitoring - don't monitor the Computer
        if not ComputerRole in author.roles and any([badword in contentLower for badword in config['wordBlacklist']]):
            blacklistCount = 0
            
            words = contentLower.split()
            for i in range(len(words)):
                word = words[i]
                try:
                    # skip word if it contains whitelisted phrase
                    for whitelisted in config['wordWhitelist']:
                        if whitelisted in word:
                            raise XlistedWord()
                    for blacklisted in config['wordBlacklist']:
                        badWords = blacklisted.split()
                        if len(badWords) > 1:
                            badPhrase = True
                            for j in range(len(badWords)):
                                if badWords[j] not in words[i+j]:
                                    badPhrase = False
                                    break
                            if badPhrase:
                                blacklistCount += 1
                                raise XlistedWord()
                        # if short blacklisted word, check if content exactly equal; otherwise check if content contains
                        elif len(blacklisted) < 5 and blacklisted == word:
                            blacklistCount += 1
                            raise XlistedWord()
                        elif len(blacklisted) >= 5 and blacklisted in word:
                            blacklistCount += 1
                            raise XlistedWord()
                except XlistedWord:
                    continue
            
            if blacklistCount > 0:
                # Warn the author of their infraction
                await msg.channel.send("{}\n{}".format(
                    author.mention, config['topicResponse']
                ))
                # Alert the Computer of the infraction - substitutions must match response in config
                await alertChannel.send(config['topicAlert'].format(
                    ComputerRole.mention, datetime.now(), msg.channel.name, author.display_name, authorClearance, blacklistCount, content
                ))
            else:
                # Couldn't find an exact offender (possibly due to the whitelist), but a blacklisted phrase was in the message
                # Silently send a private warn to the alert channel, instead of an alert + public warning
                await alertChannel.send(config['topicWarn'].format(
                    datetime.now(), msg.channel.name, author.display_name, content
                ))
        # End topic monitoring
        
        
        # CAS-abuse monitoring
        try:
            highestCAS = None
            highestCASPos = 0
            
            # Alert if clearance less than Ultraviolet directly mentions the Computer
            # (assumes there's no extra roles in the server hierarchy between UV and the Computer's role)
            if Computer in msg.mentions and authorClearance.position < ComputerRole.position - 1:
                highestCAS = Computer.display_name
                raise CASViolation()
                
            # Find the highest mentioned clearance level
            for mention in msg.role_mentions:
                if mention.position > highestCASPos:
                    highestCAS = mention
                    highestCASPos = mention.position
                    
            # Alert if the mentioned clearance was more than 1 level above the author's
            if highestCAS != None and highestCASPos > authorClearance.position + 1:
                raise CASViolation()
            
        except CASViolation:
            # Warn the author of their infraction
            await msg.channel.send("{}\n{}".format(
                author.mention, config['casResponse']
            ))
            # Alert the Computer of the infraction - substitutions must match response in config
            await alertChannel.send(config['casAlert'].format(
                ComputerRole.mention, datetime.now(), msg.channel.name, author.display_name, authorClearance, highestCAS
            ))
        # End CAS-abuse monitoring
        

def run_client(client, token):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run(token))
    
async def shutdown():
    await client.close()
    await sys.exit()
    
async def updateLinks():
    oldCitizenLinks = server.text_channels
    citizens = server.members

    # Sort alphabetically by display name
    citizens.sort(key=lambda x: x.display_name)
    
    DMCategory = None
    privateCategory = None
    for category in server.categories:
        if category.name == config['DMChannels']:
            DMCategory = category
        elif category.name == config['privateChannels']:
            privateCategory = category
    
    # Delete old channels
    for link in oldCitizenLinks:
        if link.category == DMCategory or link.category == privateCategory:
            await link.delete()
    
    # Create public shared channel
    PublicPermissions = {
        server.default_role: discord.PermissionOverwrite(read_messages=True),
        server.me: discord.PermissionOverwrite(read_messages=True)
    }
    await server.create_text_channel('computer-all', overwrites=PublicPermissions, category=DMCategory)
    
    # Create private channel for each citizen-citizen and citizen-Computer pair
    for i in range(len(citizens)):
        if citizens[i].bot or ComputerRole in citizens[i].roles:
            continue
        
        for j in range(i+1, len(citizens)):
            if citizens[j].bot or ComputerRole in citizens[j].roles:
                continue
            
            privatePermissions = {
                server.default_role: discord.PermissionOverwrite(read_messages=False),
                citizens[i]: discord.PermissionOverwrite(read_messages=True),
                citizens[j]: discord.PermissionOverwrite(read_messages=True),
                server.me: discord.PermissionOverwrite(read_messages=True)
            }
            await server.create_text_channel(citizens[i].display_name+'-'+citizens[j].display_name, overwrites=privatePermissions, category=privateCategory)
            
        DMPermissions = {
            server.default_role: discord.PermissionOverwrite(read_messages=False),
            citizens[i]: discord.PermissionOverwrite(read_messages=True),
            server.me: discord.PermissionOverwrite(read_messages=True)
        }
        await server.create_text_channel('computer-'+citizens[i].display_name, overwrites=DMPermissions, category=DMCategory)
        
    return

if __name__ == '__main__':
    try:
        run_client(client, generalInfo['discordToken'])
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    except Exception as e:
        print(e)

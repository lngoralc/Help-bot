import discord
import json
import time
from datetime import datetime
import sys
import asyncio  # Testing proper Ctrl-C handling, needed for now

# Generate config
try:
    with open('config/config.json', encoding='utf8') as f:                                                             
        config = json.load(f)
except FileNotFoundError:
    with open('config/config.json', 'w', encoding='utf8') as f:
        config = {}
        json.dump({
            "description": "Serve Friend Computer!",
            "name": "Help-bot", 
            "invoker": "?", 
            "creator": "Friend Computer",
            "git_link": "https://github.com/lngoralc/Help-bot",
            "Topic_response": "WARN: You have mentioned a restricted topic. This has been logged.",
            "CAS_response": "WARN: You have abused CAS. This has been logged.",
            "Topic_alert": "",
            "CAS_alert": "",
            "bad_words": ["mutant", "treason", "commie", "communist"], 
            "bad_word_exceptions": ["anti-"],
            "alert_channel": ""
        }, f, indent = 4, ensure_ascii = False)
        sys.exit("config file created. "
            "Please make any modifications needed to the config.json file and restart the bot.");

try:
    with open('config/user-info.json', encoding='utf8') as f:
        userInfo = json.load(f)
        generalInfo = userInfo['generalInfo']
except FileNotFoundError:
    with open('config/user-info.json', 'w', encoding='utf8') as f:
        userInfo = {}
        json.dump({
            "generalInfo":{
                "discordToken": "",
                "userID": "",
                "clientID": "",
                "clientSecret": ""
            },
            "serverID": ""
        }, f, indent = 4, ensure_ascii = False)
        sys.exit("user info file created. "
            "Please fill out the user-info.json file and restart the bot.");

desc = config['description']
client = discord.Client(description=desc, max_messages=100)
server = None
alertChannel = None
Computer = None

@client.event
async def on_ready():
    print("\nInitializing...\n")
    global server
    global alertChannel
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
    
    alertChannel = discord.utils.get(server.text_channels, name=config['alert_channel'])
    if alertChannel != None:
        print("ALERT comm line:      " + str(alertChannel.id))
    else:
        print("\nERROR: Could not get ALERT comm line!\n")
        return
        
    print("\nLinking to the Computer...")
    Computer = discord.utils.get(server.roles, name="Computer")
    if Computer != None:
        print("Activated link to Computer.")
    else:
        print("\nWARN: Could not activate link to Computer.\n")
        return

    print("\n........................................\n")
    print("Initialization complete. Ready to serve!\n")

@client.event
async def on_message(msg: discord.Message):
    content = msg.content
    contentLower = content.lower()
    author = msg.author
    authorClearance = author.roles[-1]
    badwordCount = 0
    
    # Do not trigger on bots
    if author.bot:
        return
        
        
    # Topic monitoring
    if any([badword in contentLower for badword in config['bad_words']]):
        for word in contentLower.split():
            try:
                for goodword in config['bad_word_exceptions']:
                    if goodword in word:
                        raise Exception()
                for badword in config['bad_words']:
                    if badword in word:
                        badwordCount = badwordCount + 1
                        raise Exception()
            except:
                continue
        
        if badwordCount > 0:
            # Warn the author of their infraction - substitutions must match response in config
            await msg.channel.send("{}\n{}".format(
                author.mention, config['Topic_response']
            ))
            # Alert the Computer of the infraction - substitutions must match response in config
            await alertChannel.send(config['Topic_alert'].format(
                Computer.mention, datetime.now(), msg.channel.name, author.display_name, authorClearance, badwordCount, content
            ))
    # End topic monitoring
    
    
    # CAS-abuse monitoring
    highestCAS = None
    highestCASPos = 0
    
    # Find the highest mentioned clearance level
    for mention in msg.role_mentions:
        if mention.position > highestCASPos:
            highestCAS = mention
            highestCASPos = mention.position
    
    if highestCAS != None:
        # Alert if the mentioned clearance was more than 1 level above the author's
        if highestCASPos > authorClearance.position + 1:
            # Warn the author of their infraction - substitutions must match response in config
            await msg.channel.send("{}\n{}".format(
                author.mention, config['CAS_response']
            ))
            # Alert the Computer of the infraction - substitutions must match response in config
            await alertChannel.send(config['CAS_alert'].format(
                Computer.mention, datetime.now(), msg.channel.name, author.display_name, authorClearance, highestCAS
            ))
    # End CAS-abuse monitoring
        

def run_client(client, token):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.run(token))
    
if __name__ == '__main__':
    try:
        run_client(client, generalInfo['discordToken'])
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    except Exception as e:
        print(e)
    finally:
        client.close()
#        sys.exit()
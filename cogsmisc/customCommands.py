'''
Created on Sep 11, 2016

@author: andrew
'''

import asyncio
import errno
import json
import os
import random

import discord
from discord.ext import commands

from utils import checks


class CustomCommands:
    '''
    Custom Command management commands. Server-dependent.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.ccDict = {} #dict with struct {server: {command: [responses]}}
        self.servers = []
        #self.rawCCs = [] #list of dicts with structure {cc, serv}
        #self.allCCs = [] #list of dicts with structure {cc ({commands, responses}), serv}
        self.ccSep = '|'
        
    @commands.group(pass_context=True)
    async def cc(self, ctx):
        """Commands to manage custom commands."""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Incorrect usage. Use .help cc for help.")
        
    
    async def on_ready(self):
        for serv in self.bot.servers:
            self.servers.append(serv.id)
        self.ccDict = self.bot.db.not_json_get('commands.json', {})
            #print("Serv: {0} ({1}) [invite:{2}]".format(serv, serv.id, (await self.bot.create_invite(serv)).url))
#         if os.path.isfile("./commands.json"):
#             self.loadAllCCs()
#         else:
#             self.oldLoadAllCCs()

        
    def loadAllCCs(self):
        with open('./commands.json', mode='r', encoding='utf-8') as f:
            self.ccDict = json.load(f)
        
    def oldLoadAllCCs(self):
        for serv in self.servers:
            try:
                with open('./{}/commands.txt'.format(serv), 'r') as f:
                    ccObj = list(f)
                out = {}
                for c in ccObj:
                    try:
                        cmd = c.split(self.ccSep)[0].lower()
                        response = c.split(self.ccSep)[1]
                    except Exception as e:
                        print(e)
                    else:
                        try:
                            out[cmd].append(response)
                        except KeyError:
                            out[cmd] = [response]
                        except Exception as e:
                            print(e)
            except Exception as e:
                print(e)
                out = {}
            
            self.ccDict[serv] = out
            
    
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        isDM = False
        try:
            contextualCCs = self.ccDict[message.server.id]
        except Exception:
            isDM = True
            
        if not isDM:
            try:
                contextualResponses = contextualCCs[message.content.lower()]
                await self.bot.send_message(message.channel, random.choice(contextualResponses))
            except:
                pass
        
    @cc.command(pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def add(self, ctx, *, cmdStr : str):
        """Does command magic.
        Usage: .cc add CMD|RESP
        Requires: Bot Mod or Manage Messages"""
        
        try:
            cmd = cmdStr.split(self.ccSep)[0]
            response = cmdStr.split(self.ccSep)[1]
        except Exception:
            await self.bot.say("Custom command not formatted correctly! Format is CMD|RESP")
            return
        else:
            
            if cmd == response:
                await self.bot.say("`Error: Command cannot be the same as the response.`")
                return
            
            if len(response) > 2000 or len(cmd) > 2000:
                await self.bot.say("`Error: Command or response too long.`")
                return
            
            await self.bot.say("`Adding custom response \"{1}\" on command \"{0}\"`".format(cmd, response))
            try:
                servDict = self.ccDict[ctx.message.server.id]
            except Exception as e:
                self.ccDict[ctx.message.server.id] = {}
                servDict = {}
                print(e)
                
            try:
                servDict[cmd.lower()].append(response)
            except KeyError:
                servDict[cmd.lower()] = [response]
            except Exception as e:
                print(e)
            
            self.ccDict[ctx.message.server.id] = servDict
            
            self.bot.db.not_json_set('commands.json', self.ccDict)
#             with open('./commands.json', mode='w', encoding='utf-8') as f:
#                 json.dump(self.ccDict, f, sort_keys=True, indent=4)
            
    @cc.command(pass_context=True, name="list")
    async def ccListFunc(self, ctx, page : str = "1"):
        """Displays a list of custom commands.
        Usage: .cc list"""
        try:
            page = int(page) - 1
        except Exception:
            specificList = page
            page = None
            
        try:
            contextualCCs = self.ccDict[ctx.message.server.id]
        except:
            await self.bot.say("There are no custom commands on this server.")
            return
        
        if page is not None:
            pageStart = page * 10
            pageEnd = ((page + 1) * 10) - 1
            
            page = {k: contextualCCs[k] for k in sorted(contextualCCs.keys())[pageStart:pageEnd]}
            
            out = "Commands {0} - {1} of {2}:".format(pageStart, pageEnd, len(contextualCCs)) + "```\n"
            for v in page:
                out += "{}\n".format(v)
                for r in page[v]:
                    if r[-1] is '\n':
                        out += "|- {}".format(r)
                    else:
                        out += "|- {}\n".format(r)
                out += "\n"
            out += "```"
            
            out = self.discord_trim(out)
            for o in out:
                await self.bot.say(o)
        else:
            responses = contextualCCs.get(specificList)
            if responses is not None:
                out = "Responses for command {}:".format(specificList) + "```\n"
                for r in responses:
                    if r[-1] is '\n':
                        out += "|- {}".format(r)
                    else:
                        out += "|- {}\n".format(r)
                out += "```"
                out = self.discord_trim(out)
                for o in out:
                    await self.bot.say(o)
            else:
                await self.bot.say("That command does not exist.")
        
    @cc.command(pass_context=True, name='remove')
    @checks.mod_or_permissions(manage_messages=True)
    async def removeCC(self, ctx, *, cmd : str):
        """Removes a custom command from the server.
        Usage: .cc remove <COMMAND>
        Requires: Bot Mod or Manage Messages"""
        try:
            del self.ccDict[ctx.message.server.id][cmd.lower()]
        except:
            await self.bot.say("Command not found.")
        else:
#             with open('./commands.json', mode='w', encoding='utf-8') as f:
#                 json.dump(self.ccDict, f, sort_keys=True, indent=4)
            self.bot.db.not_json_set('commands.json', self.ccDict)
            await self.bot.say("Command removed.")
            
    @cc.command(pass_context=True)
    async def dump(self, ctx):
        """Dumps a server's custom commands to a JSON file.
        Usage: .cc dump"""
        try:
            contextualCCs = self.ccDict[ctx.message.server.id]
        except:
            await self.bot.say("There are no custom commands on this server.")
            return
        with open('./dump.json', mode='w', encoding='utf-8') as f:
            json.dump(contextualCCs, f, sort_keys=True, indent=4)
        await self.bot.send_file(ctx.message.channel, './dump.json')
        
    def make_sure_path_exists(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
            
    def discord_trim(self, str):
        result = []
        trimLen = 0
        lastLen = 0
        while trimLen <= len(str):
            trimLen += 1999
            result.append(str[lastLen:trimLen])
            lastLen += 1999
        return result        
            
    
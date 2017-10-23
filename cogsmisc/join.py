'''
Created on Jun 23, 2017

@author: andrew
'''
import random

import discord
from discord.ext import commands

from utils import checks


class JoinAnnouncer:
    """A cog to announce member joins."""
    
    def __init__(self, bot):
        self.bot = bot
        
    async def on_member_join(self, member):
        await self.bot.wait_until_ready()
        join_announcement_settings = self.bot.db.jget("ja-settings", {})
        server_settings = join_announcement_settings.get(member.server.id, {})
        if not server_settings.get('enabled', True): return
        destination = member.server.get_channel(server_settings.get('destination')) or member.server
        messages = server_settings.get('messages', [])
        try:
            message = random.choice(messages).replace('@', member.mention)
        except:
            message = "Welcome to the server " + member.mention + "!"
        await self.bot.send_message(destination, message)
        
    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_server=True)
    async def ja(self, ctx):
        """Commands to manage server join announcements."""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Incorrect usage. Use .help ja for help.")
    
    @ja.command(pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def toggle(self, ctx):
        """Toggles join announcements in a server."""
        join_announcement_settings = self.bot.db.jget("ja-settings", {})
        server_settings = join_announcement_settings.get(ctx.message.server.id, {})
        
        server_settings['enabled'] = not server_settings.get('enabled', True)
        await self.bot.say("Server join announcments {}.".format('enabled' if server_settings['enabled'] else 'disabled'))
        
        join_announcement_settings[ctx.message.server.id] = server_settings
        self.bot.db.jset("ja-settings", join_announcement_settings)
        
    @ja.command(pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def channel(self, ctx, chan:discord.Channel):
        """Sets the channel that join announcments are displayed in."""
        join_announcement_settings = self.bot.db.jget("ja-settings", {})
        server_settings = join_announcement_settings.get(ctx.message.server.id, {})
        
        server_settings['destination'] = chan.id
        await self.bot.say("Server join announcment channel set to {}.".format(chan))
        
        join_announcement_settings[ctx.message.server.id] = server_settings
        self.bot.db.jset("ja-settings", join_announcement_settings)
        
    @ja.group(pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def messages(self, ctx):
        """Commands to edit a server's join messages. Any `@` will be replaced with the name of the joining member."""
        if ctx.invoked_subcommand is None:
            join_announcement_settings = self.bot.db.jget("ja-settings", {})
            server_settings = join_announcement_settings.get(ctx.message.server.id, {})
            messages = server_settings.get('messages', [])
            
            if len(messages) < 1:
                return await self.bot.say("This server does not have any custom join messages.")
            else:
                await self.bot.say('\n\n'.join(messages))
    
    
    @messages.command(pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def list(self, ctx):
        """Lists all the join announcement messages."""
        join_announcement_settings = self.bot.db.jget("ja-settings", {})
        server_settings = join_announcement_settings.get(ctx.message.server.id, {})
        messages = server_settings.get('messages', []) or []
        
        if len(messages) < 1:
            return await self.bot.say("This server does not have any custom join messages.")
        else:
            await self.bot.say('\n\n'.join(messages))
    
    @messages.command(pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def add(self, ctx, *, msg):
        """Adds a join announcement message. Any `@` will be replaced with the name of the new user."""
        join_announcement_settings = self.bot.db.jget("ja-settings", {})
        server_settings = join_announcement_settings.get(ctx.message.server.id, {})
        
        if server_settings.get('messages') is None:
            server_settings['messages'] = []
        server_settings['messages'].append(msg)
        await self.bot.say("Added new join message.")
        
        join_announcement_settings[ctx.message.server.id] = server_settings
        self.bot.db.jset("ja-settings", join_announcement_settings)
    
    @messages.command(pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def remove(self, ctx, *, msg):
        """Removes a join announcement message."""
        join_announcement_settings = self.bot.db.jget("ja-settings", {})
        server_settings = join_announcement_settings.get(ctx.message.server.id, {})
        
        try:
            msg = next(m for m in server_settings.get('messages', []) if msg in m)
        except StopIteration:
            return await self.bot.say("Join message not found.")
        
        a = server_settings.get('messages', []).remove(msg)
        server_settings['messages'] = a
        await self.bot.say("Removed join message: `{}`".format(msg))
        
        join_announcement_settings[ctx.message.server.id] = server_settings
        self.bot.db.jset("ja-settings", join_announcement_settings)
    
    
    
    
        
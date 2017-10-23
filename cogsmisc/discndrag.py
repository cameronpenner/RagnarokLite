'''
Created on Feb 22, 2017

@author: andrew
'''
import discord
from discord.ext import commands
from discord.errors import NotFound
import asyncio
from utils import checks

class DiscordTimeoutException(Exception):
    pass

class DiscNDrag:
    '''
    Commands to help moderate a server.
    '''


    def __init__(self, bot):
        self.bot = bot
        self.posting = set()
        self.lfgs = self.bot.db.not_json_get('lfg', {})
        self.ping_roles = self.bot.db.not_json_get('ping_roles', {})
        self.lfg_id = self.bot.db.not_json_get('lfg_id', 0)
        self.groups = self.bot.db.not_json_get('groups', {})  # {server: [{dm:Member(id), name:str, dm_role: (id), player_role: (id)}]}
    
    @commands.group(pass_context=True, no_pm=True)
    async def role(self, ctx):
        """Commands to auto-manage roles."""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Incorrect usage. Use .help role for help.")
            
    @role.command(pass_context=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def create(self, ctx, *, name):
        """Creates a role.
        You must be a Moderator or have Manage Roles permissions to use this command."""
        serv_roles = self.ping_roles.get(ctx.message.server.id, [])
        server = ctx.message.server
        if len([group for group in serv_roles if group['name'].lower() == name.lower()]) > 0:
            return await self.bot.say('There is already a role with that name!')
        ping_role = await self.bot.create_role(server, name=name, mentionable=True, permissions=discord.Permissions())
        role = {'name': name, 'id': ping_role.id}
        serv_roles.append(role)
        self.ping_roles[server.id] = serv_roles
        self.bot.db.not_json_set('ping_roles', self.ping_roles)
        await self.bot.say('\u2705')
        
    @role.command(pass_context=True, name='add')
    async def role_add(self, ctx, *, name):
        """Joins a role."""
        serv_roles = self.ping_roles.get(ctx.message.server.id, [])
        try:
            role = next(r for r in serv_roles if r['name'].lower() == name.lower())
        except StopIteration:
            return await self.bot.say("Role not found.")
        role = discord.utils.get(ctx.message.server.roles, id=role['id'])
        try:
            await self.bot.add_roles(ctx.message.author, role)
        except:
            await self.bot.say('\u26d4')
        else:
            await self.bot.say('\u2705')
        
    @role.command(pass_context=True, name='remove')
    async def role_remove(self, ctx, *, name):
        """Leaves a role."""
        serv_roles = self.ping_roles.get(ctx.message.server.id, [])
        try:
            role = next(r for r in serv_roles if r['name'].lower() == name.lower())
        except StopIteration:
            return await self.bot.say("Role not found.")
        role = discord.utils.get(ctx.message.server.roles, id=role['id'])
        try:
            await self.bot.remove_roles(ctx.message.author, role)
        except:
            await self.bot.say('\u26d4')
        else:
            await self.bot.say('\u2705')
    
    @commands.group(pass_context=True, no_pm=True)
    async def group(self, ctx):
        """Commands to auto-manage groups."""
        if ctx.invoked_subcommand is None:
            await self.bot.say("Incorrect usage. Use .help group for help.")
        
    @group.command(pass_context=True)
    @checks.mod_or_permissions(manage_channels=True)
    async def add(self, ctx, dm:discord.Member, *, name):
        """Creates a group.
        You must be a Moderator or have Manage Channels permissions to use this command."""
        serv_groups = self.groups.get(ctx.message.server.id, [])
        server = ctx.message.server
        name = name.title().replace(' ', '')
        if len([group for group in serv_groups if group['name'].lower() == name.lower()]) > 0:
            return await self.bot.say('There is already a group with that name!')
        dm_role = await self.bot.create_role(server, name=name + 'DM', mentionable=True, permissions=discord.Permissions())
        player_role = await self.bot.create_role(server, name=name + 'Player', mentionable=True, permissions=discord.Permissions())
        await self.bot.add_roles(dm, dm_role)
        everyone = discord.PermissionOverwrite(send_messages=False, connect=False)
        player_perms = discord.PermissionOverwrite(send_messages=True, connect=True)
        dm_perms = discord.PermissionOverwrite(send_messages=True, connect=True, manage_messages=True, mute_members=True)
        mod_role = discord.utils.find(lambda m: m.name.lower() == 'moderator', server.roles)
        if mod_role is not None:
            await self.bot.create_channel(server, name,
                                         (server.default_role, everyone),
                                         (player_role, player_perms),
                                         (dm_role, dm_perms),
                                         (server.me, player_perms),
                                         (mod_role, player_perms))
            await self.bot.create_channel(server, name,
                                         (server.default_role, everyone),
                                         (player_role, player_perms),
                                         (dm_role, dm_perms),
                                         (server.me, player_perms),
                                         (mod_role, player_perms), type=discord.ChannelType.voice)
        else:
            await self.bot.create_channel(server, name,
                                         (server.default_role, everyone),
                                         (player_role, player_perms),
                                         (dm_role, dm_perms),
                                         (server.me, player_perms))
            await self.bot.create_channel(server, name,
                                         (server.default_role, everyone),
                                         (player_role, player_perms),
                                         (dm_role, dm_perms),
                                         (server.me, player_perms), type=discord.ChannelType.voice)
        group = {'dm': dm.id, 'name': name, 'dm_role': dm_role.id, 'player_role': player_role.id}
        serv_groups.append(group)
        self.groups[server.id] = serv_groups
        self.bot.db.not_json_set('groups', self.groups)
        await self.bot.say('\u2705')
        
    @group.command(pass_context=True)
    async def invite(self, ctx, player:discord.Member, *, name):
        """Adds a player to your game if you are a DM."""
        serv_groups = self.groups.get(ctx.message.server.id, [])
        name = name.title().replace(' ', '')
        try:
            game = next(g for g in serv_groups if g['name'].lower() == name.lower())
        except StopIteration:
            return await self.bot.say('Game not found.')
        if not ctx.message.author.id == game['dm']: return await self.bot.say('You are not this game\'s DM.')
        player_role = discord.utils.get(ctx.message.server.roles, id=game['player_role'])
        await self.bot.add_roles(player, player_role)
        await self.bot.say('\u2705')
        
    async def on_member_remove(self, member):
        lfgchan = discord.utils.get(member.server.channels, name='looking-for-group')
        if lfgchan is None: return
        serv_lfgs = self.lfgs.get(member.server.id, [])
        member_lfgs = [post for post in serv_lfgs if post['author'] == member.id]
        for lfg in member_lfgs:
            try:
                msg = await self.bot.get_message(lfgchan, lfg['msg_id'])
            except NotFound:
                serv_lfgs.remove(lfg)
            try:
                await self.bot.delete_message(msg)
                serv_lfgs.remove(lfg)
            except:
                pass
            await asyncio.sleep(1)
        self.lfgs[member.server.id] = serv_lfgs
        self.bot.db.not_json_set('lfg', self.lfgs)
        
    @commands.command(pass_context=True, no_pm=True)
    async def lfg(self, ctx):
        """Posts a lfg entry in #looking-for-game. Questions are on a 10 minute timeout.
        Run this command, and Ragnarok will ask a few questions."""
        if ctx.message.author.id in self.posting:
            return await self.bot.reply('you are already posting a LFG!')
        self.posting.add(ctx.message.author.id)
        author = ctx.message.author
        channel = ctx.message.channel
        lfgchan = discord.utils.get(ctx.message.server.channels, name='looking-for-group')
        try:
            await self.bot.reply('Title of post?')
            title = await self.bot.wait_for_message(timeout=600, author=author, channel=channel)
            if title is None:
                raise DiscordTimeoutException('Timed out waiting for a response.')
            await self.bot.reply('Are you a player or DM?')
            player = await self.bot.wait_for_message(timeout=600, author=author, channel=channel)
            if player is None:
                raise DiscordTimeoutException('Timed out waiting for a response.')
            await self.bot.reply('Timezone and Time(s)?')
            tz = await self.bot.wait_for_message(timeout=600, author=author, channel=channel)
            if tz is None:
                raise DiscordTimeoutException('Timed out waiting for a response.')
            await self.bot.reply('Game description?')
            info = await self.bot.wait_for_message(timeout=600, author=author, channel=channel)
            if info is None:
                raise DiscordTimeoutException('Timed out waiting for a response.')
        except DiscordTimeoutException:
            await self.bot.reply('Timed out waiting for a response.')
        else:
            if lfgchan is not None:
                serv_lfgs = self.lfgs.get(ctx.message.server.id, [])
                lfg_id = self.lfg_id + 1
                self.lfg_id += 1
                embed = discord.Embed()
                embed.title = title.content
                embed.description = 'LFG ID: {}'.format(lfg_id)
                embed.colour = 0x738bd7
                embed.set_author(name=str(author), icon_url=author.avatar_url)
                embed.add_field(name='Role', value=player.content)
                embed.add_field(name='Date/Time/Timezone', value=tz.content)
                embed.add_field(name='Information', value=info.content, inline=False)
                lfg_msg = await self.bot.send_message(lfgchan, author.mention + ' is looking for a group!',embed=embed)
                await self.bot.send_message(author, 'Thank you for your LFG post (ID {})! Remember to delete your LFG post with `.dellfg {}` when you have found your group!'.format(lfg_id, lfg_id))
                serv_lfgs.append({'id': lfg_id, 'author': author.id, 'msg_id': lfg_msg.id})
                self.lfgs[ctx.message.server.id] = serv_lfgs
                self.bot.db.not_json_set('lfg', self.lfgs)
                self.bot.db.not_json_set('lfg_id', self.lfg_id)
            else:
                await self.bot.send_message(author, 'The server admin has not set up lfg in this server. Please contact them to set up a #looking-for-group channel.')
        self.posting.remove(author.id)
        
    @commands.command(pass_context=True, no_pm=True)
    async def dellfg(self, ctx, _id):
        """Deletes a LFG posting from the server LFG channel."""
        serv_lfgs = self.lfgs.get(ctx.message.server.id, [])
        lfgchan = discord.utils.get(ctx.message.server.channels, name='looking-for-group')
        try:
            lfg = next(post for post in serv_lfgs if post['id'] == int(_id))
        except StopIteration:
            return await self.bot.say('Invalid LFG ID.')
        if ctx.message.author.id == lfg['author']:
            try:
                msg = await self.bot.get_message(lfgchan, lfg['msg_id'])
            except NotFound:
                serv_lfgs.remove(lfg)
                await self.bot.say('LFG post not found, cleaning database.')
                self.lfgs[ctx.message.server.id] = serv_lfgs
                self.bot.db.not_json_set('lfg', self.lfgs)
                return
            try:
                await self.bot.delete_message(msg)
            except Exception as e:
                return await self.bot.say('Failed to delete LFG post: {}'.format(e))
            serv_lfgs.remove(lfg)
            await self.bot.say('Post deleted!')
            self.lfgs[ctx.message.server.id] = serv_lfgs
            self.bot.db.not_json_set('lfg', self.lfgs)
        else:
            await self.bot.say('You are not the author of this LFG!')
    
    @commands.command(pass_context=True, hidden=True, no_pm=True)
    @checks.is_owner()
    async def clean_lfg_db(self, ctx):
        serv_lfgs = self.lfgs.get(ctx.message.server.id, [])
        lfgchan = discord.utils.get(ctx.message.server.channels, name='looking-for-group')
        out = ''
        for lfg in serv_lfgs:
            try:
                await self.bot.get_message(lfgchan, lfg['msg_id'])
            except NotFound:
                serv_lfgs.remove(lfg)
                out += 'LFG {} missing.\n'.format(lfg['id'])
                
        self.lfgs[ctx.message.server.id] = serv_lfgs
        self.bot.db.not_json_set('lfg', self.lfgs)
        await self.bot.say('LFG DB cleaned!\n'+out)
        
        

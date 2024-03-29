from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from core import Quotient

from contextlib import suppress

import discord

from constants import EsportsLog, EsportsRole, RegDeny
from core import Cog
from models import ArrayAppend, AssignedSlot, EasyTag, ReservedSlot, Scrim, TagCheck, Timer, Tourney
from utils import plural

from .helpers import delete_denied_message, scrim_work_role, tourney_work_role


class SMError(Cog):
    def __init__(self, bot: Quotient):
        self.bot = bot

    @staticmethod
    def red_embed(description: str):
        embed = discord.Embed(color=discord.Color.red(), description=description)
        return embed

    @Cog.listener()
    async def on_tourney_registration_deny(self, message: discord.Message, _type: RegDeny, tourney: Tourney, **kwargs):
        logschan = tourney.logschan
        if not logschan:
            return

        text = f"Registration of [{str(message.author)}]({message.jump_url}) has been denied in {message.channel.mention}\n**Reason:** "

        with suppress(discord.NotFound, discord.NotFound, AttributeError, discord.HTTPException):
            await message.add_reaction(tourney.cross_emoji)

            if _type == RegDeny.botmention:
                await message.reply(
                    embed=self.red_embed("Don't mention Bots. Mention your real teammates."),
                    delete_after=5,
                )
                text += f"Mentioned Bots."

            elif _type == RegDeny.nomention:
                await message.reply(
                    embed=self.red_embed(
                        f"{str(message.author)}, **`{plural(tourney.required_mentions):mention is |mentions are}`** required for successful registration."
                    ),
                    delete_after=5,
                )

                text += f"Insufficient Mentions (`{len(message.mentions)}/{tourney.required_mentions}`)"

            elif _type == RegDeny.banned:
                await message.reply(
                    embed=self.red_embed(
                        f"{str(message.author)}, You are banned from the tournament. You cannot register."
                    ),
                    delete_after=5,
                )
                text += f"They are banned from tournament."

            elif _type == RegDeny.multiregister:
                await message.reply(
                    embed=self.red_embed(f"{str(message.author)}, This server doesn't allow multiple registerations."),
                    delete_after=5,
                )

                text += f"They have already registered once.\n\nIf you wish to allow multiple registerations,\nuse: `tourney edit {tourney.id}`"

            elif _type == RegDeny.noteamname:
                await message.reply(
                    embed=self.red_embed(f"{str(message.author)}, Team Name is required to register."),
                    delete_after=5,
                )
                text += f"Teamname compulsion is on and I couldn't find teamname in their registration\n\nIf you wish allow without teamname,\nUse: `tourney edit {tourney.id}`"

            elif _type == RegDeny.duplicate:
                await message.reply(
                    embed=self.red_embed(f"{str(message.author)}, Someone already registered with the same team name."),
                    delete_after=5,
                )
                text += f"Duplicate teamname. Someone already registered with the same team name."

            elif _type == RegDeny.nolines:
                await message.reply(
                    embed=self.red_embed(
                        f"{str(message.author)}, Your registration message is too short. It seems you missed some required information."
                    ),
                    delete_after=5,
                )
                text += f"Insufficient lines in their registration message."

            elif _type == RegDeny.faketag:
                records = kwargs.get("records")
                jump_url = records[0]["jump_url"]

                await message.reply(
                    embed=self.red_embed(
                        f"{str(message.author)}, Someone already registered with the same mentions {jump_url}"
                        "\n\n`If you think this is a mistake contact moderators ASAP.`"
                    ),
                    delete_after=10,
                )
                text += f"Fake tag used. {jump_url}"

            if tourney.autodelete_rejected:
                self.bot.loop.create_task(delete_denied_message(message))

            embed = discord.Embed(color=discord.Color.red(), description=text)
            with suppress(discord.Forbidden):
                return await logschan.send(embed=embed)

    @Cog.listener()
    async def on_tourney_log(self, _type: EsportsLog, tourney: Tourney, **kwargs):
        """
        Same as on_scrim_log but for tourneys
        """
        logschan = tourney.logschan
        if not logschan:
            return

        registration_channel = tourney.registration_channel
        modrole = tourney.modrole

        open_role = tourney_work_role(tourney, EsportsRole.open)
        important = False

        embed = discord.Embed(color=0x00B1FF)
        if _type == EsportsLog.closed:
            permission_updated = kwargs.get("permission_updated")

            embed.description = (
                f"Registration closed for {open_role} in {registration_channel.mention}(TourneyID: `{tourney.id}`)"
            )
            if not permission_updated:
                important = True
                embed.color = discord.Color.red()
                embed.description += f"\nI couldn't close {registration_channel.mention}."

        elif _type == EsportsLog.success:
            message: discord.Message = kwargs.get("message")
            embed.color = discord.Color.green()
            embed.description = (
                f"Registration of [{message.author}]({message.jump_url}) has been accepted in {message.channel.mention}"
            )

        with suppress(discord.Forbidden, AttributeError):
            await logschan.send(
                content=modrole.mention if modrole is not None and important is True else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True),
            )

    @Cog.listener()
    async def on_scrim_log(self, _type: EsportsLog, scrim: Scrim, **kwargs):
        """
        A listener that is dispatched everytime registration starts/ends or a registration is accepted.
        """
        logschan = scrim.logschan
        if not logschan:
            return

        registration_channel = scrim.registration_channel
        modrole = scrim.modrole

        open_role = scrim_work_role(scrim, EsportsRole.open)

        important = False

        embed = discord.Embed(color=0x00B1FF)
        with suppress(discord.NotFound, discord.Forbidden, AttributeError, discord.HTTPException):
            if _type == EsportsLog.open:
                embed.description = (
                    f"Registration opened for {open_role} in {registration_channel.mention}(ScrimsID: `{scrim.id}`)"
                )

            elif _type == EsportsLog.closed:
                permission_updated = kwargs.get("permission_updated")
                embed.description = f"Registration closed for {open_role} in {registration_channel.mention}(ScrimsID: `{scrim.id}`)\n\nUse `smanager slotlist edit {scrim.id}` to edit the slotlist."

                await logschan.send(await scrim.get_text_slotlist())

                if not permission_updated:
                    important = True
                    embed.color = discord.Color.red()
                    embed.description += f"\nI couldn't close {registration_channel.mention}."

            # elif _type == EsportsLog.success:

            #     message = kwargs.get("message")

            #     embed.color = discord.Color.green()
            #     embed.description = f"Registration of [{message.author}]({message.jump_url}) has been accepted in {message.channel.mention}"

            await logschan.send(
                content=modrole.mention if modrole is not None and important is True else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True),
            )

    # ==========================================================================================================================
    # ==========================================================================================================================

    @Cog.listener()
    async def on_scrim_registration_deny(self, message: discord.Message, _type: RegDeny, scrim: Scrim, **kwargs):
        logschan = scrim.logschan
        if logschan is None:
            return

        text = f"Registration of [{str(message.author)}]({message.jump_url}) has been denied in {message.channel.mention}\n**Reason:** "

        with suppress(discord.NotFound, discord.Forbidden, AttributeError, discord.HTTPException):
            await message.add_reaction(scrim.cross_emoji)

            if _type == RegDeny.botmention:
                await message.reply(
                    embed=self.red_embed("Don't mention Bots. Mention your real teammates."),
                    delete_after=5,
                )
                text += f"Mentioned Bots."

            elif _type == RegDeny.nomention:
                await message.reply(
                    embed=self.red_embed(
                        f"{str(message.author)}, **`{plural(scrim.required_mentions):mention is |mentions are}`** required for successful registration."
                    ),
                    delete_after=5,
                )
                text += f"Insufficient Mentions (`{len(message.mentions)}/{scrim.required_mentions}`)"

            elif _type == RegDeny.banned:
                await message.reply(
                    embed=self.red_embed(f"{str(message.author)}, You are banned from the scrims. You cannot register."),
                    delete_after=5,
                )
                text += f"They are banned from scrims."

            elif _type == RegDeny.multiregister:
                await message.reply(
                    embed=self.red_embed(f"{str(message.author)}, This server doesn't allow multiple registerations."),
                    delete_after=5,
                )
                text += f"They have already registered once.\n\nIf you wish to allow multiple registerations,\nuse: `smanager toggle {scrim.id} multiregister`"

            elif _type == RegDeny.noteamname:
                await message.reply(
                    embed=self.red_embed(f"{str(message.author)}, Team Name is required to register."),
                    delete_after=5,
                )
                text += f"Teamname compulsion is on and I couldn't find teamname in their registration\n\nIf you wish allow without teamname,\nUse: `smanager edit {scrim.id}`"

            elif _type == RegDeny.duplicate:
                await message.reply(
                    embed=self.red_embed(
                        f"{str(message.author)}, Someone has already registered with the same teamname."
                    ),
                    delete_after=5,
                )
                text += f"No duplicate team names is ON and someone has already registered with the same team name\nIf you wish to allow duplicate team names,\nUse: `smanager edit {scrim.id}`"

            elif _type == RegDeny.nolines:
                await message.reply(
                    embed=self.red_embed(
                        f"{str(message.author)}, Your registration message is too short. It seems you missed some required information."
                    ),
                    delete_after=5,
                )
                text += f"Insufficient lines in their registration message."

            elif _type == RegDeny.faketag:
                records = kwargs.get("records")
                jump_url = records[0]["jump_url"]

                await message.reply(
                    embed=self.red_embed(
                        f"{str(message.author)}, Someone already registered with the same mentions {jump_url}"
                        "\n\n`If you think this is a mistake contact moderators ASAP.`"
                    ),
                    delete_after=10,
                )
                text += f"Fake tag used. {jump_url}"

            # elif _type == RegDeny.bannedteammate:
            #     await message.reply(
            #         embed = self.red_embed(
            #             f"{str(message.author)}, Your registration cannot be accepted because one your teammates is banned from scrims."
            #     ),
            #     delete_after = 5,
            #     )
            #     text += f"One of their teammate is banned from scrims."

            if scrim.autodelete_rejects:
                self.bot.loop.create_task(delete_denied_message(message))

            embed = discord.Embed(color=discord.Color.red(), description=text)
            return await logschan.send(embed=embed)

    # ==========================================================================================================================
    # ==========================================================================================================================

    @Cog.listener()
    async def on_scrim_reserve_timer_complete(self, timer: Timer):
        scrim_id = timer.kwargs["scrim_id"]
        team_name = timer.kwargs["team_name"]
        user_id = timer.kwargs["user_id"]

        scrim = await Scrim.get_or_none(pk=scrim_id)
        if scrim is None:
            return

        guild = scrim.guild
        if not guild:
            return

        if not user_id in await scrim.reserved_user_ids():
            return

        team = await scrim.reserved_slots.filter(user_id=user_id).first()

        if team.expires != timer.expires:
            return

        await ReservedSlot.filter(id=team.id).delete()

        logschan = scrim.logschan
        if logschan is not None and logschan.permissions_for(guild.me).send_messages:
            user = self.bot.get_user(user_id)
            embed = discord.Embed(
                color=discord.Color.green(),
                description=f"Reservation period of **{team_name.title()}** ({user}) is now over.\nSlot will not be reserved for them in Scrim (`{scrim_id}`).",
            )

            await logschan.send(embed=embed)

    @Cog.listener()
    async def on_scrim_cmd_log(self, **kwargs):
        ...

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        # will delete scrim/tournament if its registration channel.
        self.bot.cache.eztagchannels.discard(channel.id)
        self.bot.cache.tagcheck.discard(channel.id)
        self.bot.cache.scrim_channels.discard(channel.id)
        self.bot.cache.tourney_channels.discard(channel.id)

        await Scrim.filter(registration_channel_id=channel.id).delete()
        await Tourney.filter(registration_channel_id=channel.id).delete()
        await TagCheck.filter(channel_id=channel.id).delete()
        await EasyTag.filter(channel_id=channel.id).delete()

    @Cog.listener()
    async def on_scrim_registration_delete(self, scrim: Scrim, message: discord.Message, slot):
        assert message.guild is not None

        self.bot.loop.create_task(message.author.remove_roles(scrim.role))
        await AssignedSlot.filter(id=slot.id).delete()
        await Scrim.filter(id=scrim.id).update(available_slots=ArrayAppend("available_slots", slot.num))
        if scrim.logschan is not None:
            embed = discord.Embed(color=discord.Color.red())
            embed.description = f"Slot of {message.author.mention} was deleted from Scrim: {scrim.id}, because their registration was deleted from {message.channel.mention}"
            await scrim.logschan.send(embed=embed)

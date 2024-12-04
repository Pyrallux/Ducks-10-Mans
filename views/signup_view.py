import discord
from discord.ui import Button, View
from database import users

from views.mode_vote_view import ModeVoteView
import asyncio


class SignupView(discord.ui.View):
    def __init__(self, ctx, bot):
        super().__init__()
        self.ctx = ctx
        self.bot = bot

        self.signup_refresh_task = asyncio.create_task(self.refresh_signup_message())

        self.signup_active = False
        self.current_signup_message = None
        self.queue = []

        self.sign_up_button = Button(label=f"Sign Up (0/10)", style=discord.ButtonStyle.green)
        self.leave_queue_button = Button(label="Leave Queue", style=discord.ButtonStyle.red)
        self.add_item(self.sign_up_button)
        self.add_item(self.leave_queue_button)
        # Link callbacks to buttons
        self.setup_callbacks()

    async def sign_up_callback(self, interaction: discord.Interaction):
        existing_user = users.find_one({"discord_id": str(interaction.user.id)})
        if existing_user:
            if interaction.user.id not in [player["id"] for player in self.queue]:
                self.queue.append({"id": interaction.user.id, "name": interaction.user.name})
                if interaction.user.id not in self.bot.player_mmr:
                    self.bot.player_mmr[interaction.user.id] = {"mmr": 1000, "wins": 0, "losses": 0}
                self.bot.player_names[interaction.user.id] = interaction.user.name

                self.sign_up_button.label = f"Sign Up ({len(self.queue)}/10)"
                await interaction.response.edit_message(content="Click a button to manage your queue status!",
                                                        view=self)

                await interaction.followup.send(
                    f"{interaction.user.name} added to the queue! Current queue count: {len(self.queue)}",
                    ephemeral=True,
                )

                if len(self.queue) == 10:
                    await interaction.channel.send("The queue is now full, proceeding to the voting stage.")
                    self.cancel_signup_refresh()

                    self.signup_active = False

                    mode_vote = ModeVoteView(self.ctx, self.bot, self.queue)
                    await mode_vote.send_view()
            else:
                await interaction.response.send_message("You're already in the queue!", ephemeral=True)
        else:
            await interaction.response.send_message(
                "You must link your Riot account to queue. Use `!linkriot Name#Tag` to link your account",
                ephemeral=True
            )

    async def leave_queue_callback(self, interaction: discord.Interaction):
        self.queue[:] = [player for player in self.queue if player["id"] != interaction.user.id]
        self.sign_up_button.label = f"Sign Up ({len(self.queue)}/10)"
        await interaction.response.edit_message(content="Click a button to manage your queue status!", view=self)

        await interaction.followup.send(
            f"{interaction.user.name} removed from the queue! Current queue count: {len(self.queue)}",
            ephemeral=True,
        )

    def setup_callbacks(self):
        self.sign_up_button.callback = self.sign_up_callback
        self.leave_queue_button.callback = self.leave_queue_callback

    # refresh the signup message every minute
    async def refresh_signup_message(self):
        try:
            while self.signup_active:
                await asyncio.sleep(60)

                try:
                    await signup_message.delete()
                except discord.NotFound:
                    pass

                # Send new signup message
                signup_message = await self.ctx.send("Click a button to manage your queue status!", view=self)
        except asyncio.CancelledError:
            pass

    # Function to cancel the signup refresh
    def cancel_signup_refresh(self):
        if self.signup_refresh_task:
            self.signup_refresh_task.cancel()
            self.signup_refresh_task = None

    async def send_signup(self):
        return await self.ctx.send(content="Click a button to manage your queue status!", view=self)

    async def update_signup(self):
        if self.current_signup_message:
            self.sign_up_button.label = f"Sign Up ({len(self.queue)}/10)"
            await self.current_signup_message.edit(content="Click a button to manage your queue status!", view=self)

    def add_player_to_queue(self, player):
        self.queue.append(player)

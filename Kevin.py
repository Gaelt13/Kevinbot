import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import os

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

canales_temporales = {}  # canal_id: user_id

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')

class RenombrarModal(Modal):
    def __init__(self, canal):
        super().__init__(title="Renombrar canal")
        self.canal = canal
        self.add_item(TextInput(label="Nuevo nombre del canal", placeholder="Escribe el nuevo nombre aquí..."))

    async def callback(self, interaction: discord.Interaction):
        new_name = self.children[0].value
        await self.canal.edit(name=new_name)
        await interaction.response.send_message(f"🔧 El canal ha sido renombrado a: {new_name}", ephemeral=True)

class CanalControlView(View):
    def __init__(self, canal, autor_id):
        super().__init__(timeout=None)
        self.canal = canal
        self.autor_id = autor_id
        self.limite = 2  # valor inicial
        self.boton_limite = Button(label=f"👥 Límite: {self.limite}", style=discord.ButtonStyle.primary, disabled=True)
        self.add_item(self.boton_limite)
        self.add_item(Button(label="➕", style=discord.ButtonStyle.success, custom_id="aumentar"))
        self.add_item(Button(label="➖", style=discord.ButtonStyle.danger, custom_id="disminuir"))
        self.add_item(Button(label="📝 Renombrar canal", style=discord.ButtonStyle.secondary, custom_id="renombrar"))
        self.add_item(Button(label="🔄 Transferir propiedad", style=discord.ButtonStyle.secondary, custom_id="transferir"))
        self.add_item(Button(label="❌ Eliminar canal", style=discord.ButtonStyle.danger, custom_id="eliminar"))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.autor_id or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ Solo el creador del canal o un admin puede usar estos botones.", ephemeral=True)
        return False

    @discord.ui.button(label="", style=discord.ButtonStyle.secondary, custom_id="boton_general", disabled=True)
    async def on_button_interaction(self, interaction: discord.Interaction, button: Button):
        pass

    @discord.ui.button(label="", style=discord.ButtonStyle.secondary)
    async def on_interaction(self, interaction: discord.Interaction, button: Button):
        pass

    async def interaction_handler(self, interaction: discord.Interaction):
        if interaction.data["custom_id"] == "aumentar":
            if self.limite < 99:
                self.limite += 1
                await self.canal.edit(user_limit=self.limite)
                self.boton_limite.label = f"👥 Límite: {self.limite}"
                await interaction.response.edit_message(view=self)

        elif interaction.data["custom_id"] == "disminuir":
            if self.limite > 0:
                self.limite -= 1
                await self.canal.edit(user_limit=self.limite)
                self.boton_limite.label = f"👥 Límite: {self.limite}"
                await interaction.response.edit_message(view=self)

        elif interaction.data["custom_id"] == "renombrar":
            modal = RenombrarModal(self.canal)
            await interaction.response.send_modal(modal)

        elif interaction.data["custom_id"] == "transferir":
            if not self.canal.members:
                await interaction.response.send_message("❌ No hay usuarios en el canal para transferir.", ephemeral=True)
                return
            user_list = [member.mention for member in self.canal.members if member.id != interaction.user.id]
            user_str = '\n'.join(user_list)
            await interaction.response.send_message(f"Selecciona un usuario para transferir la propiedad:\n{user_str}", ephemeral=True)

        elif interaction.data["custom_id"] == "eliminar":
            await interaction.response.send_message("🗑️ Canal eliminado.", ephemeral=True)
            await self.canal.delete()
            canales_temporales.pop(self.canal.id, None)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

@bot.command()
async def ayuda(ctx):
    embed = discord.Embed(title="Comandos del Bot", description="Aquí están los comandos disponibles:", color=discord.Color.blue())
    embed.add_field(name="!crearvoz", value="Crea un canal de voz temporal y te da control sobre él.", inline=False)
    embed.add_field(name="!ayuda", value="Muestra esta ayuda.", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def crearvoz(ctx):
    nombre_usuario = ctx.author.display_name
    nombre_canal = f"Sala de {nombre_usuario}"

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        ctx.author: discord.PermissionOverwrite(manage_channels=True, move_members=False),
    }
    for rol in ctx.guild.roles:
        if rol.permissions.administrator:
            overwrites[rol] = discord.PermissionOverwrite(manage_channels=True, move_members=True)

    canal = await ctx.guild.create_voice_channel(nombre_canal, overwrites=overwrites)
    canales_temporales[canal.id] = ctx.author.id

    embed = discord.Embed(title="Nuevo Canal de Voz", description=f"Se ha creado el canal **{nombre_canal}**.", color=discord.Color.green())
    embed.add_field(name="Creador", value=ctx.author.mention, inline=False)
    embed.add_field(name="Opciones", value="Usa los botones abajo para gestionar el canal.", inline=False)

    view = CanalControlView(canal, ctx.author.id)
    message = await ctx.send(embed=embed, view=view)

    async def wait_for_buttons():
        while True:
            interaction = await bot.wait_for("interaction", check=lambda i: i.message.id == message.id and i.user.id == ctx.author.id)
            await view.interaction_handler(interaction)

    bot.loop.create_task(wait_for_buttons())

    if ctx.author.voice:
        await ctx.author.move_to(canal)
        await ctx.send(f'🔊 {ctx.author.mention} ha sido movido al canal.')

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel.id in canales_temporales:
        if len(before.channel.members) == 0:
            await asyncio.sleep(3)
            if len(before.channel.members) == 0:
                await before.channel.delete()
                canales_temporales.pop(before.channel.id, None)
                print(f'🗑️ Canal eliminado: {before.channel.name}')

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

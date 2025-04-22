import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
canales_temporales = {}

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')

class ControlLimiteView(View):
    def __init__(self, canal, autor_id, limite_inicial=2):
        super().__init__(timeout=None)
        self.canal = canal
        self.autor_id = autor_id
        self.limite = limite_inicial
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.autor_id or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ Solo el creador del canal o un admin puede usar estos botones.", ephemeral=True)
        return False

    @discord.ui.button(label="🔼", style=discord.ButtonStyle.secondary)
    async def aumentar(self, interaction: discord.Interaction, button: Button):
        if self.limite < 99:
            self.limite += 1
            await self.canal.edit(user_limit=self.limite)
            await self.actualizar_embed(interaction)

    @discord.ui.button(label="🔽", style=discord.ButtonStyle.secondary)
    async def disminuir(self, interaction: discord.Interaction, button: Button):
        if self.limite > 0:
            self.limite -= 1
            await self.canal.edit(user_limit=self.limite)
            await self.actualizar_embed(interaction)

    @discord.ui.button(label="❌ Eliminar canal", style=discord.ButtonStyle.danger)
    async def eliminar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🗑️ Canal eliminado.", ephemeral=True)
        await self.canal.delete()
        canales_temporales.pop(self.canal.id, None)

    async def actualizar_embed(self, interaction):
        embed = discord.Embed(
            title="🎛️ Control del Canal de Voz",
            description=f"**Canal:** {self.canal.name}\n**Límite de usuarios:** {self.limite}",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=self)

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

    # Crear un canal de texto asociado
    text_channel = await ctx.guild.create_text_channel(f"text-{nombre_usuario}", overwrites=overwrites)

    embed = discord.Embed(
        title="🔊 Nuevo Canal de Voz",
        description=f"Se ha creado el canal de voz **{nombre_canal}**.\nPuedes ajustar el límite de usuarios con los botones.",
        color=discord.Color.green()
    )
    embed.add_field(name="Creador", value=ctx.author.mention, inline=False)
    embed.add_field(name="Límite actual", value="2", inline=False)

    view = ControlLimiteView(canal, ctx.author.id, limite_inicial=2)

    # Enviar el embed en el canal de texto creado
    mensaje = await text_channel.send(embed=embed, view=view)
    view.message = mensaje

    # Mover al creador si está en un canal de voz
    if ctx.author.voice and ctx.author.voice.channel:
        try:
            await ctx.author.move_to(canal)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para mover al usuario.")
    else:
        await ctx.send("ℹ️ Únete a un canal de voz primero para que pueda moverte automáticamente.")

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

@bot.command()
async def ayuda(ctx):
    embed = discord.Embed(
        title="Comandos del Bot",
        description="Aquí están los comandos disponibles:",
        color=discord.Color.blue()
    )
    embed.add_field(name="!crearvoz", value="Crea un canal de voz temporal con control dinámico.", inline=False)
    embed.add_field(name="!ayuda", value="Muestra esta ayuda.", inline=False)
    await ctx.send(embed=embed)

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

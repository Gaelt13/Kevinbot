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
        canal_info = canales_temporales.get(self.canal.id)
        if canal_info:
            canal_texto = interaction.guild.get_channel(canal_info["texto_id"])
            if canal_texto:
                await canal_texto.delete()
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
    nombre_canal_voz = f"🔊│Sala de {nombre_usuario}"
    nombre_canal_texto = f"💬│chat-de-{nombre_usuario}"

    # Permisos para el canal de voz
    overwrites_voz = {
        ctx.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        ctx.author: discord.PermissionOverwrite(manage_channels=True, move_members=False),
    }

    # Permisos para el canal de texto (oculto inicialmente)
    overwrites_texto = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }

    # Añadir permisos para admins en ambos canales
    for rol in ctx.guild.roles:
        if rol.permissions.administrator:
            overwrites_voz[rol] = discord.PermissionOverwrite(manage_channels=True, move_members=True)
            overwrites_texto[rol] = discord.PermissionOverwrite(read_messages=True)

    # Crear canal de voz
    canal_voz = await ctx.guild.create_voice_channel(nombre_canal_voz, overwrites=overwrites_voz)
    
    # Crear canal de texto asociado
    canal_texto = await ctx.guild.create_text_channel(nombre_canal_texto, overwrites=overwrites_texto)

    # Guardar información en el diccionario
    canales_temporales[canal_voz.id] = {
        "autor": ctx.author.id,
        "texto_id": canal_texto.id
    }

    # Crear embed con controles
    embed = discord.Embed(
        title="🔊 Nuevo Canal de Voz",
        description=f"Se ha creado el canal de voz **{nombre_canal_voz}**.\nPuedes ajustar el límite de usuarios con los botones.",
        color=discord.Color.green()
    )
    embed.add_field(name="Creador", value=ctx.author.mention, inline=False)
    embed.add_field(name="Límite actual", value="2", inline=False)

    view = ControlLimiteView(canal_voz, ctx.author.id, limite_inicial=2)

    # Enviar el embed al canal de texto asociado
    mensaje = await canal_texto.send(embed=embed, view=view)
    view.message = mensaje

    # Mover al creador si está en un canal de voz
    if ctx.author.voice and ctx.author.voice.channel:
        try:
            await ctx.author.move_to(canal_voz)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para mover al usuario.")
    else:
        await ctx.send("ℹ️ Únete a un canal de voz primero para que pueda moverte automáticamente.", delete_after=10)

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

@bot.event
async def on_voice_state_update(member, before, after):
    # Actualizar permisos del canal de texto cuando alguien entra/sale
    if after.channel and after.channel.id in canales_temporales:
        canal_info = canales_temporales[after.channel.id]
        canal_texto = member.guild.get_channel(canal_info["texto_id"])
        if canal_texto:
            await canal_texto.set_permissions(member, read_messages=True)
    
    if before.channel and before.channel.id in canales_temporales:
        canal_info = canales_temporales[before.channel.id]
        canal_texto = member.guild.get_channel(canal_info["texto_id"])
        
        # Quitar permisos al usuario que salió
        if canal_texto:
            await canal_texto.set_permissions(member, read_messages=False)
        
        # Eliminar canales si están vacíos
        if len(before.channel.members) == 0:
            await asyncio.sleep(3)
            if len(before.channel.members) == 0:
                if canal_texto:
                    await canal_texto.delete()
                await before.channel.delete()
                canales_temporales.pop(before.channel.id, None)
                print(f'🗑️ Canales eliminados: {before.channel.name} y su chat asociado')

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

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

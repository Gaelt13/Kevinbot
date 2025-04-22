import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from discord import app_commands
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
tree = app_commands.CommandTree(bot)
canales_temporales = {}

class PersonalizarCanalModal(Modal, title='Personalizar Canal'):
    nuevo_nombre = TextInput(label='Nuevo nombre del canal', required=True)
    nuevo_color = TextInput(label='Color (ej. FF5733)', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        canal_info = canales_temporales.get(interaction.user.voice.channel.id)
        if not canal_info:
            await interaction.response.send_message("❌ No estás en un canal temporal válido.", ephemeral=True)
            return

        try:
            # Actualizar nombre del canal de voz
            canal_voz = interaction.guild.get_channel(interaction.user.voice.channel.id)
            await canal_voz.edit(name=f"🔊│{self.nuevo_nombre.value}")

            # Actualizar nombre del canal de texto si existe
            if canal_info.get("texto_id"):
                canal_texto = interaction.guild.get_channel(canal_info["texto_id"])
                await canal_texto.edit(name=f"💬│chat-{self.nuevo_nombre.value[:20]}")

            # Cambiar color si se especificó
            if self.nuevo_color.value:
                color = int(self.nuevo_color.value.replace("#", ""), 16)
                embed = discord.Embed(
                    title="✅ Canal personalizado",
                    description=f"Nombre: {self.nuevo_nombre.value}\nColor: #{self.nuevo_color.value}",
                    color=color
                )
            else:
                embed = discord.Embed(
                    title="✅ Canal personalizado",
                    description=f"Nombre actualizado: {self.nuevo_nombre.value}",
                    color=discord.Color.blurple()
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error al personalizar el canal: {e}", ephemeral=True)

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

    @discord.ui.button(label="🎨 Personalizar", style=discord.ButtonStyle.primary)
    async def personalizar(self, interaction: discord.Interaction, button: Button):
        if interaction.user.voice and interaction.user.voice.channel.id == self.canal.id:
            await interaction.response.send_modal(PersonalizarCanalModal())
        else:
            await interaction.response.send_message("❌ Debes estar en el canal de voz para personalizarlo.", ephemeral=True)

    @discord.ui.button(label="❌ Eliminar", style=discord.ButtonStyle.danger)
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

@bot.event
async def on_ready():
    await tree.sync()
    print(f'✅ Bot conectado como {bot.user}')

@tree.command(name="crearvoz", description="Crea un canal de voz temporal con controles")
async def crearvoz(interaction: discord.Interaction, nombre: str = "Mi Sala"):
    """Crea un canal de voz temporal con un canal de texto asociado"""
    nombre_canal_voz = f"🔊│{nombre}"
    nombre_canal_texto = f"💬│chat-{nombre[:20]}"

    # Permisos para los canales
    overwrites_voz = {
        interaction.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        interaction.user: discord.PermissionOverwrite(manage_channels=True, move_members=False),
    }

    overwrites_texto = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True)
    }

    # Permisos para admins
    for rol in interaction.guild.roles:
        if rol.permissions.administrator:
            overwrites_voz[rol] = discord.PermissionOverwrite(manage_channels=True, move_members=True)
            overwrites_texto[rol] = discord.PermissionOverwrite(read_messages=True)

    try:
        # Crear canales
        canal_voz = await interaction.guild.create_voice_channel(nombre_canal_voz, overwrites=overwrites_voz)
        canal_texto = await interaction.guild.create_text_channel(nombre_canal_texto, overwrites=overwrites_texto)

        # Guardar información
        canales_temporales[canal_voz.id] = {
            "autor": interaction.user.id,
            "texto_id": canal_texto.id
        }

        # Crear embed con controles
        embed = discord.Embed(
            title="🔊 Nuevo Canal de Voz",
            description=f"Se ha creado el canal de voz **{nombre_canal_voz}**.",
            color=discord.Color.green()
        )
        embed.add_field(name="Creador", value=interaction.user.mention, inline=False)
        embed.add_field(name="Límite actual", value="2", inline=False)
        embed.add_field(name="Controles", value="Usa los botones para gestionar tu canal", inline=False)

        view = ControlLimiteView(canal_voz, interaction.user.id)
        mensaje = await canal_texto.send(embed=embed, view=view)
        view.message = mensaje

        # Mover al usuario si está en un canal de voz
        if interaction.user.voice and interaction.user.voice.channel:
            try:
                await interaction.user.move_to(canal_voz)
            except discord.Forbidden:
                await interaction.response.send_message("❌ No tengo permisos para moverte.", ephemeral=True)
                return

        await interaction.response.send_message(f"✅ Canal creado: {canal_voz.mention}", ephemeral=True, delete_after=10)

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al crear el canal: {e}", ephemeral=True)

@tree.command(name="ayuda", description="Muestra información sobre los comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Comandos del Bot",
        description="Aquí están los comandos disponibles:",
        color=discord.Color.blue()
    )
    embed.add_field(name="/crearvoz [nombre]", value="Crea un canal de voz temporal con controles", inline=False)
    embed.add_field(name="/ayuda", value="Muestra esta ayuda", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

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

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

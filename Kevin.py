import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
canales_temporales = {}

LOBBY_VOICE_ID = 1252337087102058516

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')

class NombreModal(Modal, title="Cambiar nombre del canal"):
    nuevo_nombre = TextInput(label="Nuevo nombre", placeholder="Ingresa el nuevo nombre", max_length=100)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        await self.view.canal.edit(name=self.nuevo_nombre.value)
        await interaction.response.send_message(f"✅ Nombre cambiado a: {self.nuevo_nombre.value}", ephemeral=True)
        await self.view.actualizar_embed(interaction)

class ControlLimiteView(View):
    def __init__(self, canal, autor_id, limite_inicial=2):
        super().__init__(timeout=None)
        self.canal = canal
        self.autor_id = autor_id
        self.limite = limite_inicial
        self.publico = True

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

    @discord.ui.button(label="📝 Renombrar", style=discord.ButtonStyle.primary)
    async def renombrar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(NombreModal(self))

    @discord.ui.button(label="🆘 Ayuda", style=discord.ButtonStyle.secondary)
    async def ayuda(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="ℹ️ Ayuda de Controles del Canal",
                              description="Este panel te permite controlar tu canal de voz temporal.\n\n\n🔼 / 🔽: Aumenta o disminuye el límite de usuarios.\n📝: Cambia el nombre del canal.\n🔁: Transfiere propiedad del canal.\n🔒: Cierra el canal temporalmente.\n❌: Elimina el canal.",
                              color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔁 Transferir", style=discord.ButtonStyle.success)
    async def transferir(self, interaction: discord.Interaction, button: Button):
        if not interaction.channel.members:
            return await interaction.response.send_message("❌ No hay usuarios en el canal para transferir.", ephemeral=True)
        otros = [m for m in interaction.channel.members if m.id != interaction.user.id]
        if not otros:
            return await interaction.response.send_message("❌ No hay otros usuarios para transferir la propiedad.", ephemeral=True)
        nuevo_owner = otros[0]
        self.autor_id = nuevo_owner.id
        await interaction.response.send_message(f"👑 Propiedad transferida a {nuevo_owner.mention}", ephemeral=True)
        await self.actualizar_embed(interaction)

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.danger)
    async def cerrar(self, interaction: discord.Interaction, button: Button):
        self.publico = not self.publico
        overwrite = discord.PermissionOverwrite(connect=self.publico)
        await self.canal.set_permissions(self.canal.guild.default_role, overwrite=overwrite)
        estado = "🌐 Público" if self.publico else "🔒 Cerrado"
        await interaction.response.send_message(f"🔁 Estado actualizado: {estado}", ephemeral=True)
        await self.actualizar_embed(interaction)

    @discord.ui.button(label="❌ Eliminar", style=discord.ButtonStyle.danger)
    async def eliminar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🗑️ Canal eliminado.", ephemeral=True)
        if self.canal.id in canales_temporales:
            del canales_temporales[self.canal.id]
        await self.canal.delete()

    async def actualizar_embed(self, interaction):
        estado = "🌐 Público" if self.publico else "🔒 Cerrado"
        limite_str = f"✋ {self.limite}" if self.limite > 0 else "✋ Ilimitado"
        embed = discord.Embed(
            title="🌀 Administra tu Canal Temporal",
            description="Controla y personaliza tu canal como prefieras.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="👑 Dueño del Canal", value=f"<@{self.autor_id}>", inline=False)
        embed.add_field(name="📛 Nombre del Canal", value=self.canal.name, inline=False)
        embed.add_field(name="👥 Límite de Usuarios", value=limite_str, inline=True)
        embed.add_field(name="🌐 Estado", value=estado, inline=True)
        await interaction.message.edit(embed=embed, view=self)

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == LOBBY_VOICE_ID:
        guild = after.channel.guild
        nombre_canal = f"🔊│Sala de {member.display_name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(manage_channels=True)
        }

        canal_temporal = await guild.create_voice_channel(
            nombre_canal,
            overwrites=overwrites,
            category=after.channel.category
        )

        await member.move_to(canal_temporal)

        canales_temporales[canal_temporal.id] = {
            "autor": member.id,
            "creado_en": discord.utils.utcnow()
        }

        webhook = await canal_temporal.create_webhook(name="Dynamic Voice")

        embed = discord.Embed(
            title="🌀 Administra tu Canal Temporal",
            description="Controla y personaliza tu canal como prefieras.",
            color=discord.Color.green()
        )
        embed.add_field(name="👑 Dueño del Canal", value=f"<@{member.id}>", inline=False)
        embed.add_field(name="📛 Nombre del Canal", value=canal_temporal.name, inline=False)
        embed.add_field(name="👥 Límite de Usuarios", value="✋ 2", inline=True)
        embed.add_field(name="🌐 Estado", value="🌐 Público", inline=True)
        embed.set_footer(text=f"Creado por {member.display_name}")

        view = ControlLimiteView(canal_temporal, member.id)

        await webhook.send(
            embed=embed,
            view=view,
            username=f"{bot.user.name}",
            avatar_url=bot.user.avatar.url
        )
        await webhook.delete()

    if before.channel and before.channel.id in canales_temporales:
        if len(before.channel.members) == 0:
            await asyncio.sleep(5)
            if len(before.channel.members) == 0:
                await before.channel.delete()
                del canales_temporales[before.channel.id]

@bot.command()
async def ayuda(ctx):
    embed = discord.Embed(
        title="Ayuda del Bot de Canales Temporales",
        description="Este bot crea canales de voz temporales automáticamente al unirte al canal lobby.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

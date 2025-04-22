import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
canales_temporales = {}

# ID del canal "lobby" que activará la creación de canales temporales (cámbialo al tuyo)
LOBBY_VOICE_ID = 1252337087102058516  # Reemplaza con el ID de tu canal lobby

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')

class ControlLimiteView(View):
    def __init__(self, canal, autor_id, limite_inicial=2):
        super().__init__(timeout=None)
        self.canal = canal
        self.autor_id = autor_id
        self.limite = limite_inicial

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
        if self.canal.id in canales_temporales:
            del canales_temporales[self.canal.id]
        await self.canal.delete()

    async def actualizar_embed(self, interaction):
        embed = discord.Embed(
            title="🎛️ Control del Canal de Voz",
            description=f"**Canal:** {self.canal.name}\n**Límite de usuarios:** {self.limite}",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=self)

@bot.event
async def on_voice_state_update(member, before, after):
    # Crear canal temporal al unirse al lobby
    if after.channel and after.channel.id == LOBBY_VOICE_ID:
        guild = after.channel.guild
        nombre_canal = f"🔊│Sala de {member.display_name}"
        
        # Permisos (opcional: personaliza según tu necesidad)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(manage_channels=True)
        }

        # Crear canal de voz temporal
        canal_temporal = await guild.create_voice_channel(
            nombre_canal,
            overwrites=overwrites,
            category=after.channel.category  # Misma categoría que el lobby
        )
        
        # Mover al usuario al nuevo canal
        await member.move_to(canal_temporal)
        
        # Guardar información del canal temporal
        canales_temporales[canal_temporal.id] = {
            "autor": member.id,
            "creado_en": discord.utils.utcnow()
        }

        # Crear un webhook para enviar el embed al canal de voz (los bots no pueden enviar mensajes directamente a canales de voz)
        webhook = await canal_temporal.create_webhook(name="Dynamic Voice")
        
        # Embed con controles
        embed = discord.Embed(
            title="🔊 Canal Temporal Creado",
            description=f"**Canal:** {canal_temporal.name}\n**Límite inicial:** 2 usuarios\n\nUsa los botones para controlar el canal.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Creado por {member.display_name}")
        
        view = ControlLimiteView(canal_temporal, member.id)
        
        # Enviar embed usando el webhook (simula un mensaje en el canal de voz)
        await webhook.send(
            embed=embed,
            view=view,
            username=f"{bot.user.name}",
            avatar_url=bot.user.avatar.url
        )
        
        # Eliminar webhook después de enviar el mensaje (opcional)
        await webhook.delete()

    # Eliminar canal temporal si queda vacío
    if before.channel and before.channel.id in canales_temporales:
        if len(before.channel.members) == 0:
            await asyncio.sleep(5)  # Pequeño delay para evitar eliminar si alguien se reconecta
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

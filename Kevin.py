import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
canales_temporales = {}
preferencias_idioma = {}  # Guardar idioma por usuario

# Idiomas soportados
IDIOMAS = {
    'es': 'Español',
    'en': 'English',
    'pt': 'Português',
    'ja': '日本語'
}

# Textos traducidos para botones y mensajes
TEXTOS = {
    "no_autor": {
        "es": "❌ Solo el creador del canal puede cambiar el idioma.",
        "en": "❌ Only the channel creator can change the language.",
        "pt": "❌ Apenas o criador do canal pode mudar o idioma.",
        "ja": "❌ チャンネルの作成者のみが言語を変更できます。"
    },
    "canal_eliminado": {
        "es": "🗑️ Canal eliminado.",
        "en": "🗑️ Channel deleted.",
        "pt": "🗑️ Canal deletado.",
        "ja": "🗑️ チャンネルが削除されました。"
    },
    "ayuda": {
        "es": "Este bot crea canales de voz temporales automáticamente al unirte al canal lobby.",
        "en": "This bot automatically creates temporary voice channels when you join the lobby channel.",
        "pt": "Este bot cria canais de voz temporários automaticamente ao entrar no canal do lobby.",
        "ja": "このボットは、ロビーチャンネルに参加すると一時的なボイスチャンネルを自動的に作成します。"
    },
    "eliminar": {
        "es": "❌ Eliminar canal",
        "en": "❌ Delete Channel",
        "pt": "❌ Deletar Canal",
        "ja": "❌ チャンネルを削除"
    }
}

# ID del canal "lobby" que activará la creación de canales temporales (cámbialo al tuyo)
LOBBY_VOICE_ID = 1252337087102058516

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')

def traducir_embed(idioma, canal, autor, limite, estado="Público", region="Automática"):
    textos = {
        'es': {
            'title': '🌀 Administra tu Canal Temporal',
            'desc': 'Controla y personaliza tu canal como prefieras.',
            'owner': '👑 Dueño del Canal',
            'name': '🔊 Nombre del Canal',
            'limit': '✋ Límite de Usuarios',
            'region': '🌎 Región',
            'state': '🌐 Estado',
            'created': f'Creado por {autor.display_name}'
        },
        'en': {
            'title': '🌀 Manage your Dynamic Channel',
            'desc': 'Take control of your channel and customize it.',
            'owner': '👑 Channel Owner',
            'name': '🔊 Channel Name',
            'limit': '✋ User Limit',
            'region': '🌎 Region',
            'state': '🌐 State',
            'created': f'Created by {autor.display_name}'
        },
        'pt': {
            'title': '🌀 Gerencie seu Canal Temporário',
            'desc': 'Controle e personalize seu canal como preferir.',
            'owner': '👑 Dono do Canal',
            'name': '🔊 Nome do Canal',
            'limit': '✋ Limite de Usuários',
            'region': '🌎 Região',
            'state': '🌐 Estado',
            'created': f'Criado por {autor.display_name}'
        },
        'ja': {
            'title': '🌀 一時的なチャンネルを管理',
            'desc': 'チャンネルを自由にカスタマイズしましょう。',
            'owner': '👑 チャンネル所有者',
            'name': '🔊 チャンネル名',
            'limit': '✋ ユーザー制限',
            'region': '🌎 リージョン',
            'state': '🌐 状態',
            'created': f'{autor.display_name} により作成'
        }
    }
    t = textos.get(idioma, textos['es'])
    embed = discord.Embed(title=t['title'], description=t['desc'], color=discord.Color.blurple())
    embed.add_field(name=t['owner'], value=f"<@{autor.id}>", inline=False)
    embed.add_field(name=t['name'], value=canal.name, inline=False)
    embed.add_field(name=t['limit'], value=f"{limite if limite > 0 else '∞'}", inline=False)
    embed.add_field(name=t['region'], value=region, inline=True)
    embed.add_field(name=t['state'], value=estado, inline=True)
    embed.set_footer(text=t['created'])
    return embed

class IdiomaSelect(Select):
    def __init__(self, autor_id, canal, view):
        self.autor_id = autor_id
        self.canal = canal
        self.view = view
        options = [
            discord.SelectOption(label=nombre, value=code)
            for code, nombre in IDIOMAS.items()
        ]
        super().__init__(placeholder="🌍 Cambiar idioma", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.autor_id:
            idioma = preferencias_idioma.get(interaction.user.id, 'es')
            await interaction.response.send_message(TEXTOS["no_autor"][idioma], ephemeral=True)
            return
        preferencias_idioma[self.autor_id] = self.values[0]
        embed_actualizado = traducir_embed(self.values[0], self.canal, interaction.user, self.view.limite)
        await interaction.response.edit_message(embed=embed_actualizado, view=self.view)

class ControlLimiteView(View):
    def __init__(self, canal, autor_id, limite_inicial=2):
        super().__init__(timeout=None)
        self.canal = canal
        self.autor_id = autor_id
        self.limite = limite_inicial
        self.estado = "Público"
        self.region = "Automática"
        self.add_item(IdiomaSelect(autor_id, canal, self))

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.autor_id or interaction.user.guild_permissions.administrator

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

    @discord.ui.button(label=TEXTOS["eliminar"]["es"], style=discord.ButtonStyle.danger, custom_id="eliminar")
    async def eliminar(self, interaction: discord.Interaction, button: Button):
        idioma = preferencias_idioma.get(interaction.user.id, 'es')
        await interaction.response.send_message(TEXTOS["canal_eliminado"][idioma], ephemeral=True)
        if self.canal.id in canales_temporales:
            del canales_temporales[self.canal.id]
        await self.canal.delete()

    async def actualizar_embed(self, interaction):
        idioma = preferencias_idioma.get(self.autor_id, 'es')
        embed = traducir_embed(idioma, self.canal, interaction.user, self.limite)
        await interaction.response.edit_message(embed=embed, view=self)

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
        idioma = preferencias_idioma.get(member.id, 'es')
        view = ControlLimiteView(canal_temporal, member.id)
        embed = traducir_embed(idioma, canal_temporal, member, view.limite)
        avatar_url = bot.user.avatar.url if bot.user.avatar else None
        await webhook.send(
            embed=embed,
            view=view,
            username=f"{bot.user.name}",
            avatar_url=avatar_url
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
    idioma = preferencias_idioma.get(ctx.author.id, 'es')
    embed = discord.Embed(
        title="🆘 Ayuda / Help",
        description=TEXTOS["ayuda"][idioma],
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
canales_temporales = {}
preferencias_idioma = {}  # usuario_id -> idioma

LOBBY_VOICE_ID = 1252337087102058516
IDIOMAS = ["es", "en", "pt", "jp"]

TRADUCCIONES = {
    "es": {
        "embed_title": "🎛️ Control del Canal de Voz",
        "embed_desc": "**Canal:** {nombre}\n**Límite de usuarios:** {limite}",
        "btn_up": "🔼",
        "btn_down": "🔽",
        "btn_delete": "❌ Eliminar canal",
        "btn_rename": "✏️ Renombrar",
        "btn_help": "❓ Ayuda",
        "btn_lang": "🌍 Idioma",
        "msg_delete": "🗑️ Canal eliminado.",
        "msg_perm_denied": "❌ Solo el creador del canal o un admin puede usar estos botones.",
        "embed_help_title": "📘 Ayuda del canal dinámico",
        "embed_help_desc": "Puedes controlar este canal con los siguientes botones..."
    },
    "en": {
        "embed_title": "🎛️ Voice Channel Control",
        "embed_desc": "**Channel:** {nombre}\n**User limit:** {limite}",
        "btn_up": "🔼",
        "btn_down": "🔽",
        "btn_delete": "❌ Delete Channel",
        "btn_rename": "✏️ Rename",
        "btn_help": "❓ Help",
        "btn_lang": "🌍 Language",
        "msg_delete": "🗑️ Channel deleted.",
        "msg_perm_denied": "❌ Only the channel creator or an admin can use these buttons.",
        "embed_help_title": "📘 Dynamic Channel Help",
        "embed_help_desc": "You can control this channel using the following buttons..."
    },
    "pt": {
        "embed_title": "🎛️ Controle do Canal de Voz",
        "embed_desc": "**Canal:** {nombre}\n**Limite de usuários:** {limite}",
        "btn_up": "🔼",
        "btn_down": "🔽",
        "btn_delete": "❌ Excluir canal",
        "btn_rename": "✏️ Renomear",
        "btn_help": "❓ Ajuda",
        "btn_lang": "🌍 Idioma",
        "msg_delete": "🗑️ Canal excluído.",
        "msg_perm_denied": "❌ Apenas o criador ou um admin pode usar esses botões.",
        "embed_help_title": "📘 Ajuda do Canal Dinâmico",
        "embed_help_desc": "Você pode controlar este canal usando os botões abaixo..."
    },
    "jp": {
        "embed_title": "🎛️ ボイスチャンネルコントロール",
        "embed_desc": "**チャンネル:** {nombre}\n**ユーザー制限:** {limite}",
        "btn_up": "🔼",
        "btn_down": "🔽",
        "btn_delete": "❌ チャンネル削除",
        "btn_rename": "✏️ 名前変更",
        "btn_help": "❓ ヘルプ",
        "btn_lang": "🌍 言語",
        "msg_delete": "🗑️ チャンネルが削除されました。",
        "msg_perm_denied": "❌ 作成者または管理者のみが使用できます。",
        "embed_help_title": "📘 ダイナミックチャンネルのヘルプ",
        "embed_help_desc": "以下のボタンでチャンネルを管理できます..."
    }
}

def get_idioma(user_id):
    return preferencias_idioma.get(user_id, "es")

def get_text(user_id, key, **kwargs):
    idioma = get_idioma(user_id)
    texto = TRADUCCIONES[idioma][key]
    return texto.format(**kwargs)

class ControlLimiteView(View):
    def __init__(self, canal, autor_id, limite_inicial=2):
        super().__init__(timeout=None)
        self.canal = canal
        self.autor_id = autor_id
        self.limite = limite_inicial
        self.update_labels()

    def update_labels(self):
        idioma = get_idioma(self.autor_id)
        self.children[0].label = TRADUCCIONES[idioma]['btn_up']
        self.children[1].label = TRADUCCIONES[idioma]['btn_down']
        self.children[2].label = TRADUCCIONES[idioma]['btn_delete']
        self.children[3].label = TRADUCCIONES[idioma]['btn_rename']
        self.children[4].label = TRADUCCIONES[idioma]['btn_help']
        self.children[5].label = TRADUCCIONES[idioma]['btn_lang']

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.autor_id or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(get_text(interaction.user.id, "msg_perm_denied"), ephemeral=True)
        return False

    @discord.ui.button(label="", style=discord.ButtonStyle.secondary)
    async def aumentar(self, interaction: discord.Interaction, button: Button):
        if self.limite < 99:
            self.limite += 1
            await self.canal.edit(user_limit=self.limite)
            await self.actualizar_embed(interaction)

    @discord.ui.button(label="", style=discord.ButtonStyle.secondary)
    async def disminuir(self, interaction: discord.Interaction, button: Button):
        if self.limite > 0:
            self.limite -= 1
            await self.canal.edit(user_limit=self.limite)
            await self.actualizar_embed(interaction)

    @discord.ui.button(label="", style=discord.ButtonStyle.danger)
    async def eliminar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(get_text(interaction.user.id, "msg_delete"), ephemeral=True)
        if self.canal.id in canales_temporales:
            del canales_temporales[self.canal.id]
        await self.canal.delete()

    @discord.ui.button(label="", style=discord.ButtonStyle.primary)
    async def renombrar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("✏️ Ingresa el nuevo nombre del canal:", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
            await self.canal.edit(name=msg.content)
            await msg.delete()
            await self.actualizar_embed(interaction)
        except asyncio.TimeoutError:
            await interaction.followup.send("⌛ Tiempo agotado para renombrar.", ephemeral=True)

    @discord.ui.button(label="", style=discord.ButtonStyle.secondary)
    async def ayuda(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title=get_text(interaction.user.id, "embed_help_title"),
            description=get_text(interaction.user.id, "embed_help_desc"),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="", style=discord.ButtonStyle.secondary)
    async def cambiar_idioma(self, interaction: discord.Interaction, button: Button):
        actual = get_idioma(interaction.user.id)
        idx = (IDIOMAS.index(actual) + 1) % len(IDIOMAS)
        nuevo = IDIOMAS[idx]
        preferencias_idioma[interaction.user.id] = nuevo
        self.update_labels()
        await self.actualizar_embed(interaction)

    async def actualizar_embed(self, interaction):
        embed = discord.Embed(
            title=get_text(self.autor_id, "embed_title"),
            description=get_text(self.autor_id, "embed_desc", nombre=self.canal.name, limite="✋ Ilimitado" if self.limite == 0 else self.limite),
            color=discord.Color.blurple()
        )
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
        view = ControlLimiteView(canal_temporal, member.id)
        embed = discord.Embed(
            title=get_text(member.id, "embed_title"),
            description=get_text(member.id, "embed_desc", nombre=canal_temporal.name, limite=2),
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Creado por {member.display_name}")
        await webhook.send(embed=embed, view=view, username=bot.user.name, avatar_url=bot.user.avatar.url)
        await webhook.delete()

    if before.channel and before.channel.id in canales_temporales:
        if len(before.channel.members) == 0:
            await asyncio.sleep(5)
            if len(before.channel.members) == 0:
                await before.channel.delete()
                del canales_temporales[before.channel.id]

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

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
    nuevo_nombre = TextInput(label='Nuevo nombre del canal', style=discord.TextStyle.short, required=True)
    nuevo_color = TextInput(label='Color (ej. FF5733)', style=discord.TextStyle.short, required=False, max_length=6)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.response.send_message("❌ Debes estar en un canal de voz para personalizarlo.", ephemeral=True)
                return

            canal_info = canales_temporales.get(interaction.user.voice.channel.id)
            if not canal_info:
                await interaction.response.send_message("❌ No estás en un canal temporal válido.", ephemeral=True)
                return

            canal_voz = interaction.guild.get_channel(interaction.user.voice.channel.id)
            if not canal_voz:
                await interaction.response.send_message("❌ No se pudo encontrar el canal de voz.", ephemeral=True)
                return

            # Validar y aplicar nuevo nombre
            nuevo_nombre_voz = f"🔊│{self.nuevo_nombre.value[:25]}"
            await canal_voz.edit(name=nuevo_nombre_voz)

            # Actualizar canal de texto si existe
            if canal_info.get("texto_id"):
                canal_texto = interaction.guild.get_channel(canal_info["texto_id"])
                if canal_texto:
                    nuevo_nombre_texto = f"💬│chat-{self.nuevo_nombre.value[:20]}"
                    await canal_texto.edit(name=nuevo_nombre_texto)

            # Aplicar nuevo color si se especificó
            color = discord.Color.blurple()
            if self.nuevo_color.value:
                try:
                    color = discord.Color(int(self.nuevo_color.value, 16))
                except ValueError:
                    pass

            embed = discord.Embed(
                title="✅ Canal personalizado",
                description=f"**Nombre:** {nuevo_nombre_voz}\n**Color:** #{getattr(color, 'value', 'FFFFFF'):06x}",
                color=color
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Error en personalización: {e}")
            await interaction.response.send_message("❌ Ocurrió un error al personalizar el canal.", ephemeral=True)

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
        try:
            if self.limite < 99:
                self.limite += 1
                await self.canal.edit(user_limit=self.limite)
                await self.actualizar_embed(interaction)
        except Exception as e:
            print(f"Error al aumentar límite: {e}")
            await interaction.response.send_message("❌ Error al actualizar el límite.", ephemeral=True)

    @discord.ui.button(label="🔽", style=discord.ButtonStyle.secondary)
    async def disminuir(self, interaction: discord.Interaction, button: Button):
        try:
            if self.limite > 0:
                self.limite -= 1
                await self.canal.edit(user_limit=self.limite)
                await self.actualizar_embed(interaction)
        except Exception as e:
            print(f"Error al disminuir límite: {e}")
            await interaction.response.send_message("❌ Error al actualizar el límite.", ephemeral=True)

    @discord.ui.button(label="🎨 Personalizar", style=discord.ButtonStyle.primary)
    async def personalizar(self, interaction: discord.Interaction, button: Button):
        try:
            if interaction.user.voice and interaction.user.voice.channel and interaction.user.voice.channel.id == self.canal.id:
                await interaction.response.send_modal(PersonalizarCanalModal())
            else:
                await interaction.response.send_message("❌ Debes estar en el canal de voz para personalizarlo.", ephemeral=True)
        except Exception as e:
            print(f"Error en personalización: {e}")
            await interaction.response.send_message("❌ Error al abrir el menú de personalización.", ephemeral=True)

    @discord.ui.button(label="❌ Eliminar", style=discord.ButtonStyle.danger)
    async def eliminar(self, interaction: discord.Interaction, button: Button):
        try:
            canal_info = canales_temporales.get(self.canal.id)
            if canal_info:
                if canal_info.get("texto_id"):
                    canal_texto = interaction.guild.get_channel(canal_info["texto_id"])
                    if canal_texto:
                        await canal_texto.delete()
            
            await self.canal.delete()
            canales_temporales.pop(self.canal.id, None)
            await interaction.response.send_message("🗑️ Canal eliminado correctamente.", ephemeral=True)
        except Exception as e:
            print(f"Error al eliminar canal: {e}")
            await interaction.response.send_message("❌ Error al eliminar el canal.", ephemeral=True)

    async def actualizar_embed(self, interaction):
        try:
            embed = discord.Embed(
                title="🎛️ Control del Canal de Voz",
                description=f"**Canal:** {self.canal.name}\n**Límite de usuarios:** {self.limite}",
                color=discord.Color.blurple()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            print(f"Error al actualizar embed: {e}")

@bot.event
async def on_ready():
    try:
        await tree.sync()
        print(f'✅ Bot conectado como {bot.user}')
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

@tree.command(name="crearvoz", description="Crea un canal de voz temporal con controles")
@app_commands.describe(nombre="Nombre para tu canal de voz")
async def crearvoz(interaction: discord.Interaction, nombre: str = "Mi Sala"):
    try:
        await interaction.response.defer(ephemeral=True)
        
        nombre_canal_voz = f"🔊│{nombre[:25]}"
        nombre_canal_texto = f"💬│chat-{nombre[:20]}"

        # Verificar permisos del bot
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Necesito permisos de gestión de canales para funcionar.", ephemeral=True)
            return

        # Configurar permisos
        overwrites_voz = {
            interaction.guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True),
            interaction.user: discord.PermissionOverwrite(manage_channels=True, move_members=False),
        }

        overwrites_texto = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True)
        }

        # Dar permisos a admins
        for rol in interaction.guild.roles:
            if rol.permissions.administrator:
                overwrites_voz[rol] = discord.PermissionOverwrite(manage_channels=True, move_members=True)
                overwrites_texto[rol] = discord.PermissionOverwrite(read_messages=True)

        # Crear canales
        canal_voz = await interaction.guild.create_voice_channel(
            nombre_canal_voz, 
            overwrites=overwrites_voz,
            reason=f"Canal temporal creado por {interaction.user}"
        )
        
        canal_texto = await interaction.guild.create_text_channel(
            nombre_canal_texto,
            overwrites=overwrites_texto,
            reason=f"Canal de texto para {nombre_canal_voz}"
        )

        # Registrar canales
        canales_temporales[canal_voz.id] = {
            "autor": interaction.user.id,
            "texto_id": canal_texto.id
        }

        # Crear panel de control
        embed = discord.Embed(
            title="🔊 Nuevo Canal de Voz",
            description=f"**Canal:** {canal_voz.mention}\n**Límite inicial:** 2 usuarios",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Creado por {interaction.user.display_name}")

        view = ControlLimiteView(canal_voz, interaction.user.id)
        mensaje = await canal_texto.send(embed=embed, view=view)
        view.message = mensaje

        # Mover al usuario si está en un canal de voz
        if interaction.user.voice and interaction.user.voice.channel:
            try:
                await interaction.user.move_to(canal_voz)
            except:
                pass

        await interaction.followup.send(
            f"✅ Canal creado: {canal_voz.mention}\n"
            f"📝 Panel de control: {canal_texto.mention}",
            ephemeral=True
        )

    except Exception as e:
        print(f"Error en /crearvoz: {e}")
        await interaction.followup.send(
            "❌ Error al crear el canal. Verifica mis permisos e inténtalo nuevamente.",
            ephemeral=True
        )

@tree.command(name="ayuda", description="Muestra información sobre los comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Comandos del Bot de Canales Temporales",
        description="Aquí están los comandos disponibles:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="/crearvoz [nombre]",
        value="Crea un canal de voz temporal con panel de control personalizable",
        inline=False
    )
    embed.add_field(
        name="Controles del Canal",
        value="Una vez creado, puedes:\n"
              "- 🔼/🔽 Ajustar límite de usuarios\n"
              "- 🎨 Cambiar nombre/color\n"
              "- ❌ Eliminar el canal",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    try:
        # Manejar entrada a canales
        if after.channel and after.channel.id in canales_temporales:
            canal_info = canales_temporales[after.channel.id]
            if canal_info.get("texto_id"):
                canal_texto = member.guild.get_channel(canal_info["texto_id"])
                if canal_texto:
                    await canal_texto.set_permissions(member, read_messages=True)
        
        # Manejar salida de canales
        if before.channel and before.channel.id in canales_temporales:
            canal_info = canales_temporales[before.channel.id]
            
            # Quitar permisos del canal de texto
            if canal_info.get("texto_id"):
                canal_texto = member.guild.get_channel(canal_info["texto_id"])
                if canal_texto:
                    await canal_texto.set_permissions(member, read_messages=False)
            
            # Eliminar canales si están vacíos
            if len(before.channel.members) == 0:
                await asyncio.sleep(5)  # Espera para evitar eliminación accidental
                
                if before.channel.id in canales_temporales and len(before.channel.members) == 0:
                    canal_info = canales_temporales[before.channel.id]
                    try:
                        if canal_info.get("texto_id"):
                            canal_texto = member.guild.get_channel(canal_info["texto_id"])
                            if canal_texto:
                                await canal_texto.delete()
                        await before.channel.delete()
                    except:
                        pass
                    finally:
                        canales_temporales.pop(before.channel.id, None)
    except Exception as e:
        print(f"Error en on_voice_state_update: {e}")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ No se encontró el token de Discord")
    exit(1)

try:
    bot.run(TOKEN)
except Exception as e:
    print(f"Error al iniciar el bot: {e}")

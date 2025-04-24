from discord.ui import Select

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

    @discord.ui.select(
        placeholder="Selecciona un idioma...",
        options=[
            discord.SelectOption(label="Español", value="es"),
            discord.SelectOption(label="English", value="en"),
            discord.SelectOption(label="Português", value="pt"),
            discord.SelectOption(label="日本語", value="jp"),
        ]
    )
    async def seleccionar_idioma(self, interaction: discord.Interaction, select: Select):
        nuevo_idioma = select.values[0]
        preferencias_idioma[interaction.user.id] = nuevo_idioma
        self.update_labels()
        await self.actualizar_embed(interaction)

    async def actualizar_embed(self, interaction):
        embed = discord.Embed(
            title=get_text(self.autor_id, "embed_title"),
            description=get_text(self.autor_id, "embed_desc", nombre=self.canal.name, limite="✋ Ilimitado" if self.limite == 0 else self.limite),
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=self)

"""
2	User settings cog for CoderAgent
3	Handles quality selection, API key management, and language settings
4	"""
5	import discord
6	from discord.ext import commands
7	from discord import app_commands
8	from logger import setup_logger
9	from modules.database.repository import UserRepository, APIKeyRepository, UsageLogRepository
10	from modules.utils.i18n import i18n
11	from config.ai_models import model_manager
12	import asyncio
13	
14	logger = setup_logger(__name__)
15	
16	
17	class SettingView(discord.ui.View):
18	    """Persistent View for /setting (Public Panel)"""
19	    
20	    def __init__(self, bot: commands.Bot):
21	        super().__init__(timeout=None)
22	        self.bot = bot
23	
24	    @discord.ui.button(
25	        label="Start Settings", 
26	        style=discord.ButtonStyle.primary, 
27	        emoji="⚙️",
28	        custom_id="persistent:setting_start_button"
29	    )
30	    async def start_setting(self, interaction: discord.Interaction, button: discord.ui.Button):
31	        """Handle 'Start Settings' button click - Show Ephemeral Panel"""
32	        db_session = self.bot.db_manager.get_session()
33	        try:
34	            user = await UserRepository.get_or_create_user(
35	                db_session, 
36	                str(interaction.user.id), 
37	                interaction.user.name, 
38	                interaction.user.discriminator
39	            )
40	            lang = user.language or "en-US"
41	            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
42	            daily_count = await UsageLogRepository.get_daily_usage_count(db_session, user.id)
43	            
44	            # Quality level mapping for display
45	            quality_labels = {
46	                "high_quality": "高品質",
47	                "standard": "標準",
48	                "fast": "高速"
49	            }
50	            current_quality = quality_labels.get(user.model_preset, "標準")
51	
52	            # AI Model Status
53	            active_models = [m for m, s in model_manager.model_status.items() if s["status"] == "active"]
54	            cooldown_models = [m for m, s in model_manager.model_status.items() if s["status"] == "cooldown"]
55	
56	            # Create Status Embed
57	            embed = discord.Embed(
58	                title=i18n.translate(lang, "SETTING.CURRENT_STATUS_TITLE"),
59	                color=discord.Color.blue()
60	            )
61	            embed.add_field(name="AI品質", value=current_quality, inline=True)
62	            embed.add_field(name=i18n.translate(lang, "SETTING.LANG_SETTING"), value="🇺🇸 English" if lang == "en-US" else "🇯🇵 日本語", inline=True)
63	            embed.add_field(name="API Key", value="✅ Registered" if api_key else "❌ Not Registered", inline=True)
64	            embed.add_field(name="今日利用回数", value=f"{daily_count} / 50", inline=True)
65	            
66	            if active_models:
67	                embed.add_field(name="現在利用AI", value=", ".join(active_models[:3]), inline=False)
68	            if cooldown_models:
69	                embed.add_field(name="現在Cooldown中AI", value=", ".join(cooldown_models[:3]), inline=False)
70	            
71	            embed.set_footer(text="Made by RovaexTeam")
72	            
73	            # Create Detail View with Select Menu
74	            view = SettingDetailView(self.bot, lang)
75	            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
76	        finally:
77	            await db_session.close()
78	
79	
80	class SettingDetailView(discord.ui.View):
81	    """Ephemeral View for detailed settings"""
82	    
83	    def __init__(self, bot: commands.Bot, lang: str):
84	        super().__init__(timeout=300)
85	        self.bot = bot
86	        self.lang = lang
87	        
88	        # Add select menu
89	        self.select = discord.ui.Select(
90	            placeholder=i18n.translate(lang, "SETTING.SELECT_PLACEHOLDER"),
91	            options=[
92	                discord.SelectOption(label="AI品質変更", value="quality", emoji="🚀", description="AIの回答品質レベルを変更します"),
93	                discord.SelectOption(label=i18n.translate(lang, "SETTING.API_KEY_MGMT"), value="apikey", emoji="🔑", description=i18n.translate(lang, "SETTING.API_KEY_MGMT_DESC")),
94	                discord.SelectOption(label=i18n.translate(lang, "SETTING.LANG_SETTING"), value="lang", emoji="🌐", description=i18n.translate(lang, "SETTING.LANG_SETTING_DESC")),
95	            ]
96	        )
97	        self.select.callback = self.select_callback
98	        self.add_item(self.select)
99	
100	    async def select_callback(self, interaction: discord.Interaction):
101	        action = self.select.values[0]
102	        
103	        if action == "quality":
104	            await self._show_quality_selection(interaction)
105	        elif action == "apikey":
106	            await self._show_apikey_mgmt(interaction)
107	        elif action == "lang":
108	            await self._show_lang_setting(interaction)
109	
110	    async def _show_quality_selection(self, interaction: discord.Interaction):
111	        embed = discord.Embed(
112	            title="AI品質レベル選択",
113	            description="用途に合わせてAIの品質レベルを選択してください。",
114	            color=discord.Color.blue()
115	        )
116	        embed.add_field(name="🚀 高品質", value="大規模実装・設計・デバッグ向け。高性能モデルを使用します。", inline=False)
117	        embed.add_field(name="⚖️ 標準", value="通常の開発・修正向け。バランスの取れたモデルを使用します。", inline=False)
118	        embed.add_field(name="💻 高速", value="簡単なコード・質問回答向け。軽量で高速なモデルを使用します。", inline=False)
119	        embed.set_footer(text="Made by RovaexTeam")
120	        view = QualitySelectionView(self.bot, self.lang)
121	        await interaction.response.edit_message(embed=embed, view=view)
122	
123	    async def _show_apikey_mgmt(self, interaction: discord.Interaction):
124	        db_session = self.bot.db_manager.get_session()
125	        try:
126	            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
127	            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
128	            
129	            if api_key:
130	                embed = discord.Embed(
131	                    title=i18n.translate(self.lang, "SETTING.API_KEY_MGMT"),
132	                    description=i18n.translate(self.lang, "SETTING.API_KEY_DELETE_CONFIRM"),
133	                    color=discord.Color.red()
134	                )
135	                embed.set_footer(text="Made by RovaexTeam")
136	                view = APIKeyDeleteConfirmView(self.bot, self.lang)
137	                await interaction.response.edit_message(embed=embed, view=view)
138	            else:
139	                modal = APIKeyModal(self.bot, self.lang)
140	                await interaction.response.send_modal(modal)
141	        finally:
142	            await db_session.close()
143	
144	    async def _show_lang_setting(self, interaction: discord.Interaction):
145	        embed = discord.Embed(
146	            title=i18n.translate(self.lang, "SETTING.LANG_SETTING"),
147	            description=i18n.translate(self.lang, "SETTING.LANG_SETTING_DESC"),
148	            color=discord.Color.purple()
149	        )
150	        embed.set_footer(text="Made by RovaexTeam")
151	        view = LanguageSelectionView(self.bot, self.lang)
152	        await interaction.response.edit_message(embed=embed, view=view)
153	
154	
155	class QualitySelectionView(discord.ui.View):
156	    def __init__(self, bot, lang):
157	        super().__init__(timeout=300)
158	        self.bot = bot
159	        self.lang = lang
160	
161	    @discord.ui.button(label="高品質", style=discord.ButtonStyle.primary, emoji="🚀")
162	    async def high_button(self, interaction: discord.Interaction, button: discord.ui.Button):
163	        await self._set_quality(interaction, "high_quality")
164	
165	    @discord.ui.button(label="標準", style=discord.ButtonStyle.primary, emoji="⚖️")
166	    async def standard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
167	        await self._set_quality(interaction, "standard")
168	
169	    @discord.ui.button(label="高速", style=discord.ButtonStyle.primary, emoji="💻")
170	    async def fast_button(self, interaction: discord.Interaction, button: discord.ui.Button):
171	        await self._set_quality(interaction, "fast")
172	
173	    async def _set_quality(self, interaction: discord.Interaction, quality: str):
174	        db_session = self.bot.db_manager.get_session()
175	        try:
176	            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
177	            user.model_preset = quality
178	            await db_session.commit()
179	            
180	            quality_labels = {"high_quality": "高品質", "standard": "標準", "fast": "高速"}
181	            msg = f"AI品質を **{quality_labels[quality]}** に設定しました。"
182	            await interaction.response.edit_message(content=msg, embed=None, view=None)
183	        finally:
184	            await db_session.close()
185	
186	    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, row=1)
187	    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
188	        view = SettingDetailView(self.bot, self.lang)
189	        await interaction.response.edit_message(content=None, view=view)
190	
191	
192	class LanguageSelectionView(discord.ui.View):
193	    def __init__(self, bot, lang):
194	        super().__init__(timeout=60)
195	        self.bot = bot
196	        self.lang = lang
197	
198	    @discord.ui.button(label="English", style=discord.ButtonStyle.primary, emoji="🇺🇸")
199	    async def en_button(self, interaction: discord.Interaction, button: discord.ui.Button):
200	        await self._set_language(interaction, "en-US")
201	
202	    @discord.ui.button(label="日本語", style=discord.ButtonStyle.primary, emoji="🇯🇵")
203	    async def ja_button(self, interaction: discord.Interaction, button: discord.ui.Button):
204	        await self._set_language(interaction, "ja")
205	
206	    async def _set_language(self, interaction: discord.Interaction, new_lang: str):
207	        db_session = self.bot.db_manager.get_session()
208	        try:
209	            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
210	            user.language = new_lang
211	            await db_session.commit()
212	            
213	            msg = i18n.translate(new_lang, "SETTING.LANG_CHANGE_SUCCESS")
214	            await interaction.response.edit_message(content=msg, embed=None, view=None)
215	        finally:
216	            await db_session.close()
217	
218	
219	class APIKeyModal(discord.ui.Modal):
220	    def __init__(self, bot, lang):
221	        title = i18n.translate(lang, "SETTING.API_KEY_MGMT")
222	        super().__init__(title=title)
223	        self.bot = bot
224	        self.lang = lang
225	        
226	        self.key_input = discord.ui.TextInput(
227	            label="OpenRouter API Key",
228	            placeholder="sk-or-v1-...",
229	            required=True,
230	            min_length=10
231	        )
232	        self.add_item(self.key_input)
233	
234	    async def on_submit(self, interaction: discord.Interaction):
235	        await interaction.response.defer(ephemeral=True)
236	        db_session = self.bot.db_manager.get_session()
237	        try:
238	            user = await UserRepository.get_or_create_user(
239	                db_session, 
240	                str(interaction.user.id), 
241	                interaction.user.name, 
242	                interaction.user.discriminator
243	            )
244	            encrypted_key = self.bot.encryption_manager.encrypt(self.key_input.value)
245	            
246	            await APIKeyRepository.set_api_key(db_session, user.id, encrypted_key, "Default")
247	            await db_session.commit()
248	            
249	            await interaction.followup.send(i18n.translate(self.lang, "SETTING.API_KEY_SET_SUCCESS"), ephemeral=True)
250	        finally:
251	            await db_session.close()
252	
253	
254	class APIKeyDeleteConfirmView(discord.ui.View):
255	    def __init__(self, bot, lang):
256	        super().__init__(timeout=60)
257	        self.bot = bot
258	        self.lang = lang
259	
260	    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
261	    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
262	        db_session = self.bot.db_manager.get_session()
263	        try:
264	            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
265	            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
266	            if api_key:
267	                await db_session.delete(api_key)
268	                await db_session.commit()
269	            
270	            await interaction.response.edit_message(content=i18n.translate(self.lang, "SETTING.API_KEY_DELETE_SUCCESS"), embed=None, view=None)
271	        finally:
272	            await db_session.close()
273	
274	    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
275	    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
276	        await interaction.response.edit_message(content=i18n.translate(self.lang, "COMMON.CANCEL"), embed=None, view=None)
277	
278	
279	class SettingCog(commands.Cog):
280	    """Cog for user settings"""
281	    
282	    def __init__(self, bot: commands.Bot):
283	        self.bot = bot
284	    
285	    @app_commands.command(
286	        name="setting", 
287	        description="設定用パネルを表示します"
288	    )
289	    async def setting(self, interaction: discord.Interaction):
290	        """Show User Settings Panel (Public Start Button)"""
291	        db_session = self.bot.db_manager.get_session()
292	        try:
293	            user = await UserRepository.get_or_create_user(
294	                db_session, 
295	                str(interaction.user.id), 
296	                interaction.user.name, 
297	                interaction.user.discriminator
298	            )
299	            lang = user.language or "en-US"
300	            
301	            embed = discord.Embed(
302	                title=i18n.translate(lang, "SETTING.PANEL_TITLE"),
303	                description=i18n.translate(lang, "SETTING.PANEL_DESC"),
304	                color=discord.Color.blue()
305	            )
306	            embed.set_footer(text="Made by RovaexTeam")
307	            
308	            view = SettingView(self.bot)
309	            # Update button label based on language
310	            for item in view.children:
311	                if isinstance(item, discord.ui.Button) and item.custom_id == "persistent:setting_start_button":
312	                    item.label = i18n.translate(lang, "SETTING.START_BUTTON")
313	            
314	            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
315	        finally:
316	            await db_session.close()
317	
318	
319	async def setup(bot: commands.Bot):
320	    """Setup the cog"""
321	    await bot.add_cog(SettingCog(bot))

"""
Coding commands for CoderAgent
Handles /coding start, /coding end commands and AI chat in CodingRooms
"""
import discord
from discord.ext import commands
from discord import app_commands
from logger import setup_logger
from modules.database.repository import UserRepository, APIKeyRepository, MessageRepository, SessionRepository, UsageLogRepository
from modules.session.manager import SessionManager
from modules.ai.openrouter import OpenRouterClient, AIService, CerebrasClient
from config import Config
import json
from modules.utils.i18n import i18n
from modules.project.manager import ProjectManager
import asyncio

logger = setup_logger(__name__)


class ProjectRenameModal(discord.ui.Modal, title="Rename Project"):
    project_id_input = discord.ui.TextInput(
        label="Project ID",
        placeholder="Enter the Project ID to rename",
        required=True,
        style=discord.TextStyle.short
    )
    new_name_input = discord.ui.TextInput(
        label="New Project Name",
        placeholder="Enter the new name for the project",
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, parent_view: 'CodingPanelView', lang: str):
        super().__init__()
        self.parent_view = parent_view
        self.lang = lang
        self.project_id_input.label = i18n.translate(self.lang, "CODING.MODAL_PROJ_ID_LABEL")
        self.project_id_input.placeholder = i18n.translate(self.lang, "CODING.MODAL_PROJ_ID_RENAME_PLACEHOLDER")
        self.new_name_input.label = i18n.translate(self.lang, "CODING.MODAL_NEW_PROJ_NAME_LABEL")
        self.new_name_input.placeholder = i18n.translate(self.lang, "CODING.MODAL_NEW_PROJ_NAME_PLACEHOLDER")
        self.title = i18n.translate(self.lang, "CODING.MODAL_PROJ_RENAME_TITLE")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        project_id = self.project_id_input.value.strip()
        new_name = self.new_name_input.value.strip()
        user_id = interaction.user.id

        renamed_project = await self.parent_view.project_manager.rename_project(user_id, project_id, new_name)

        if renamed_project:
            await interaction.followup.send(
                i18n.translate(self.lang, "CODING.PROJ_RENAMED_SUCCESS", project_id=project_id, new_name=new_name),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                i18n.translate(self.lang, "CODING.PROJ_RENAME_FAILED", project_id=project_id),
                ephemeral=True
            )


class ProjectInfoModal(discord.ui.Modal, title="Project Details"): 
    project_id_input = discord.ui.TextInput(
        label="Project ID",
        placeholder="Enter the Project ID",
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, parent_view: 'CodingPanelView', lang: str):
        super().__init__()
        self.parent_view = parent_view
        self.lang = lang
        self.project_id_input.label = i18n.translate(self.lang, "CODING.MODAL_PROJ_ID_LABEL")
        self.project_id_input.placeholder = i18n.translate(self.lang, "CODING.MODAL_PROJ_ID_PLACEHOLDER")
        self.title = i18n.translate(self.lang, "CODING.MODAL_PROJ_INFO_TITLE")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        project_id = self.project_id_input.value.strip()
        user_id = interaction.user.id

        project = await self.parent_view.project_manager.get_project(user_id, project_id)

        if not project:
            await interaction.followup.send(i18n.translate(self.lang, "CODING.PROJ_NOT_FOUND", project_id=project_id), ephemeral=True)
            return

        embed = discord.Embed(
            title=i18n.translate(self.lang, "CODING.PROJ_DETAILS_TITLE"),
            color=discord.Color.green()
        )
        embed.add_field(name=i18n.translate(self.lang, "CODING.PROJ_ID"), value=f"`{project["id"]}`", inline=False)
        embed.add_field(name=i18n.translate(self.lang, "CODING.PROJ_NAME"), value=project["name"], inline=False)
        embed.add_field(name=i18n.translate(self.lang, "CODING.PROJ_CREATED_AT"), value=f"<t:{int(project["created_at"])}:F>", inline=False)
        embed.add_field(name=i18n.translate(self.lang, "CODING.PROJ_UPDATED_AT"), value=f"<t:{int(project["updated_at"])}:F>", inline=False)
        embed.add_field(name=i18n.translate(self.lang, "CODING.PROJ_FILES_DIR"), value=f"`{project["files_dir"]}`", inline=False)
        embed.set_footer(text="Made by RovaexTeam")

        await interaction.followup.send(embed=embed, ephemeral=True)


class CodingPanelView(discord.ui.View):
    """Persistent View for /coding panel (Public Panel)"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.session_manager = SessionManager(bot)
        self.project_manager = ProjectManager()
    
    async def _get_user_lang(self, interaction: discord.Interaction):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(
                db_session, 
                str(interaction.user.id), 
                interaction.user.name, 
                interaction.user.discriminator
            )
            return user.language or "en-US"
        finally:
            await db_session.close()

    @discord.ui.select(
        placeholder="🎯 Select an option",
        options=[
            discord.SelectOption(label="Start Development", value="start", emoji="🚀", description="Start a new coding session"),
            discord.SelectOption(label="Project List", value="list", emoji="📋", description="View your projects"),
            discord.SelectOption(label="Project Info", value="info", emoji="ℹ️", description="Check project details"),
            discord.SelectOption(label="Rename Project", value="rename", emoji="✏️", description="Change project name"),
        ],
        custom_id="persistent:coding_panel_select"
    )
    async def panel_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle selection from Public Panel"""
        lang = await self._get_user_lang(interaction)
        action = select.values[0]
        
        if action == "start":
            await self._handle_start(interaction, lang)
        elif action == "list":
            await self._handle_list(interaction, lang)
        elif action == "info":
            await self._handle_info(interaction, lang)
        elif action == "rename":
            await self._handle_rename(interaction, lang)
    
    async def _handle_start(self, interaction: discord.Interaction, lang: str):
        """Handle start (New Ephemeral)"""
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        active_session = self.session_manager.get_user_active_session(user_id)
        
        if active_session:
            msg = i18n.translate(lang, "CODING.SESSION_ALREADY_ACTIVE", session_id=active_session[:8])
            await interaction.followup.send(msg, ephemeral=True)
            return
        
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(db_session, user_id, interaction.user.name, interaction.user.discriminator)
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            
            if not api_key:
                await interaction.followup.send(i18n.translate(lang, "CODING.API_KEY_MISSING"), ephemeral=True)
                return
            
            # Generate session ID
            import uuid
            short_uuid = str(uuid.uuid4())[:8]
            channel_name = f"session-{short_uuid}"
            
            session_uuid, coding_room = await self.session_manager.create_session(
                db_session, 
                interaction.user, 
                interaction.guild, 
                channel_name
            )
            
            embed = discord.Embed(
                title=i18n.translate(lang, "CODING.SESSION_START_TITLE"),
                description=i18n.translate(lang, "CODING.SESSION_START_DESC"),
                color=discord.Color.green()
            )
            embed.add_field(name=i18n.translate(lang, "CODING.SESSION_ID"), value=f"`{session_uuid[:8]}`", inline=False)
            embed.add_field(name=i18n.translate(lang, "CODING.CHANNEL"), value=coding_room.mention, inline=False)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Coding Room welcome
            welcome_embed = discord.Embed(
                title=i18n.translate(lang, "CODING.WELCOME_TITLE"),
                description=i18n.translate(lang, "CODING.WELCOME_DESC"),
                color=discord.Color.blue()
            )
            welcome_embed.add_field(name="Tips", value=i18n.translate(lang, "CODING.WELCOME_TIPS"), inline=False)
            welcome_embed.set_footer(text="Made by RovaexTeam")
            await coding_room.send(embed=welcome_embed)
        except Exception as e:
            logger.error(f"Error in _handle_start: {e}", exc_info=True)
            await interaction.followup.send(i18n.translate(lang, "COMMON.ERROR", error=str(e)), ephemeral=True)
        finally:
            await db_session.close()
    
    async def _handle_list(self, interaction: discord.Interaction, lang: str):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        projects = await self.project_manager.list_projects(user_id)

        if not projects:
            await interaction.followup.send(i18n.translate(lang, "CODING.PROJ_LIST_EMPTY"), ephemeral=True)
            return

        embed = discord.Embed(
            title=i18n.translate(lang, "CODING.PROJ_LIST_TITLE"),
            description=i18n.translate(lang, "CODING.PROJ_LIST_DESC"),
            color=discord.Color.blue()
        )

        for project in projects:
            embed.add_field(
                name=f"`{project['id'][:8]}`: {project['name']}",
                value=f"Created: <t:{int(project['created_at'])}:R>\nUpdated: <t:{int(project['updated_at'])}:R>",
                inline=False
            )
        embed.set_footer(text="Made by RovaexTeam")
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _handle_info(self, interaction: discord.Interaction, lang: str):
        modal = ProjectInfoModal(self, lang)
        await interaction.response.send_modal(modal)
    
    async def _handle_rename(self, interaction: discord.Interaction, lang: str):
        modal = ProjectRenameModal(self, lang)
        await interaction.response.send_modal(modal)


class CodingCog(commands.Cog):
    """Cog for coding-related commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_manager = SessionManager(bot)
        self.project_manager = ProjectManager() # Add ProjectManager initialization

    async def _get_user_lang_from_message(self, message: discord.Message):
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(
                db_session, 
                str(message.author.id), 
                message.author.name, 
                message.author.discriminator
            )
            return user.language or "en-US"
        finally:
            await db_session.close()

    async def _handle_room_list(self, message: discord.Message):
        lang = await self._get_user_lang_from_message(message)
        user_id = message.author.id
        projects = await self.project_manager.list_projects(user_id)

        if not projects:
            await message.reply(i18n.translate(lang, "CODING.PROJ_LIST_EMPTY"))
            return

        embed = discord.Embed(
            title=i18n.translate(lang, "CODING.PROJ_LIST_TITLE"),
            description=i18n.translate(lang, "CODING.PROJ_LIST_DESC"),
            color=discord.Color.blue()
        )

        for project in projects:
            embed.add_field(
                name=f"`{project["id"][:8]}`: {project["name"]}",
                value=f"Created: <t:{int(project["created_at"])}:R>\nUpdated: <t:{int(project["updated_at"])}:R>",
                inline=False
            )
        embed.set_footer(text="Made by RovaexTeam")
        await message.reply(embed=embed)

    async def _handle_room_get(self, message: discord.Message, command: str):
        lang = await self._get_user_lang_from_message(message)
        parts = command.split(' ', 1)
        if len(parts) < 2:
            await message.reply(i18n.translate(lang, "CODING.GET_COMMAND_USAGE"))
            return
        
        project_id = parts[1].strip()
        user_id = message.author.id

        project = await self.project_manager.get_project(user_id, project_id)

        if not project:
            await message.reply(i18n.translate(lang, "CODING.PROJ_NOT_FOUND", project_id=project_id))
            return

        files_dir = project["files_dir"]
        
        # Create a temporary zip file
        zip_file_path = f"/tmp/{project_id}.zip"
        await self.project_manager.zip_project_files(files_dir, zip_file_path)

        try:
            await message.reply(i18n.translate(lang, "FILE.ZIP_PREPARING"))
            await message.channel.send(file=discord.File(zip_file_path))
            await message.channel.send(i18n.translate(lang, "FILE.ZIP_SENT"))
        except Exception as e:
            logger.error(f"Error sending zip file: {e}", exc_info=True)
            await message.reply(i18n.translate(lang, "COMMON.ERROR", error=str(e)))
        finally:
            # Clean up the temporary zip file
            import os
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)

    async def _handle_room_readme(self, message: discord.Message):
        lang = await self._get_user_lang_from_message(message)
        channel_id = str(message.channel.id)
        session_uuid = None
        for uuid, info in self.session_manager.active_sessions.items():
            if info["channel_id"] == channel_id:
                session_uuid = uuid
                break

        if not session_uuid:
            await message.reply(i18n.translate(lang, "CODING.NO_ACTIVE_SESSION"))
            return

        session_info = self.session_manager.active_sessions[session_uuid]
        user_id = session_info["discord_user_id"]

        project = await self.project_manager.get_active_project(user_id)

        if not project:
            await message.reply(i18n.translate(lang, "CODING.NO_ACTIVE_PROJECT"))
            return

        readme_path = os.path.join(project["files_dir"], "README.md")

        if not os.path.exists(readme_path):
            await message.reply(i18n.translate(lang, "CODING.README_NOT_FOUND"))
            return

        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()
            
            if len(readme_content) > 2000:
                # Discord message limit is 2000 characters
                await message.reply(i18n.translate(lang, "CODING.README_TOO_LONG"))
                # Optionally, send as a file
                await message.channel.send(file=discord.File(readme_path))
            else:
                await message.reply(f"```markdown\n{readme_content}\n```")
        except Exception as e:
            logger.error(f"Error reading README.md: {e}", exc_info=True)
            await message.reply(i18n.translate(lang, "COMMON.ERROR", error=str(e)))
    
    coding_group = app_commands.Group(
        name="coding", 
        description="AI Coding related commands"
    )
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle AI chat in CodingRooms"""
        if message.author.bot:
            return
        
        channel_id = str(message.channel.id)
        session_uuid = None
        for uuid, info in self.session_manager.active_sessions.items():
            if info["channel_id"] == channel_id:
                session_uuid = uuid
                break
        
        if not session_uuid:
            db_session = self.bot.db_manager.get_session()
            try:
                from sqlalchemy import select
                from modules.database.models import Session
                stmt = select(Session).where((Session.channel_id == channel_id) & (Session.is_active == True))
                result = await db_session.execute(stmt)
                db_session_obj = result.scalar_one_or_none()
                if db_session_obj:
                    session_uuid = db_session_obj.session_uuid
                    self.session_manager.active_sessions[session_uuid] = {
                        "user_id": db_session_obj.user_id,
                        "discord_user_id": str(message.author.id),
                        "guild_id": str(message.guild.id),
                        "channel_id": channel_id,
                        "db_session_id": db_session_obj.id
                    }
            except Exception as e:
                logger.error(f"Error restoring session: {e}")
            finally:
                await db_session.close()

        if not session_uuid:
            return

        if message.content.startswith(self.bot.command_prefix):
            command = message.content[len(self.bot.command_prefix):].strip().lower()
            if command == "list":
                await self._handle_room_list(message)
            elif command.startswith("get "):
                await self._handle_room_get(message, command)
            elif command == "readme":
                await self._handle_room_readme(message)
            return

        # Check if session is already processing
        session_info = self.session_manager.active_sessions[session_uuid]
        if session_info.get("status") == "processing":
            return await message.reply("⚠️ 現在別の処理を実行中です。完了までお待ちください。")

        async with message.channel.typing():
            # Set status to processing
            session_info["status"] = "processing"
            db_session = self.bot.db_manager.get_session()
            try:
                session_info = self.session_manager.active_sessions[session_uuid]
                user = await UserRepository.get_user_by_discord_id(db_session, str(message.author.id))
                lang = user.language or "en-US"
                api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
                
                if not api_key:
                    await message.reply(i18n.translate(lang, "CODING.API_KEY_MISSING"))
                    return
                
                decrypted_key = self.bot.encryption_manager.decrypt(api_key.encrypted_key)
                history = await MessageRepository.get_session_messages(db_session, session_info["db_session_id"])
                formatted_history = [{"role": m.role, "content": m.content} for m in history[-10:]]
                
                openrouter_client = OpenRouterClient(decrypted_key)
                cerebras_client = None
                if Config.CEREBRAS_API_KEY:
                    cerebras_client = CerebrasClient(Config.CEREBRAS_API_KEY)
                ai_service = AIService(openrouter_client, cerebras_client)

                ai_service.set_model_by_preset(getattr(user, "model_preset", "balance"))
                
                await MessageRepository.add_message(db_session, session_info["db_session_id"], "user", message.content)
                
                from modules.ai.agent import CodingAgent
                from modules.ai.views import RequirementApprovalView
                from modules.database.repository import RequirementRepository
                import json
                
                agent = CodingAgent(ai_service)
                response_msg = await message.reply(i18n.translate(lang, "CODING.THINKING"))
                
                # Phase 1: Requirement Definition
                requirement_json = await agent.define_requirements(message.content, formatted_history)
                
                if "error" in requirement_json:
                    await response_msg.edit(content=i18n.translate(lang, "COMMON.ERROR", error=requirement_json["error"]))
                    return

                # Store requirement in DB
                requirement = await RequirementRepository.create_requirement(
                    db_session, 
                    session_info["db_session_id"], 
                    requirement_json
                )

                # Display Requirements to User
                embed = discord.Embed(
                    title=i18n.translate(lang, "CODING.REQUIREMENT_TITLE"),
                    color=discord.Color.blue()
                )
                embed.add_field(name=i18n.translate(lang, "CODING.REQUIREMENT_SUMMARY"), value=requirement_json.get("task_summary", "---"), inline=False)
                
                tech_reqs = "\n".join([f"• {r}" for r in requirement_json.get("technical_requirements", [])])
                embed.add_field(name=i18n.translate(lang, "CODING.REQUIREMENT_TECH"), value=tech_reqs or "---", inline=False)
                
                if requirement_json.get("is_ready"):
                    embed.description = i18n.translate(lang, "CODING.REQUIREMENT_READY")
                    view = RequirementApprovalView(agent, requirement.id, str(message.author.id), lang)
                    await response_msg.edit(content=None, embed=embed, view=view)
                else:
                    embed.description = i18n.translate(lang, "CODING.REQUIREMENT_NOT_READY")
                    await response_msg.edit(content=None, embed=embed)
                
                await MessageRepository.add_message(db_session, session_info["db_session_id"], "user", message.content)
                await MessageRepository.add_message(db_session, session_info["db_session_id"], "assistant", json.dumps(requirement_json, ensure_ascii=False))
                
                await db_session.commit()
            except Exception as e:
                logger.error(f"Error in AI chat: {e}", exc_info=True)
                await message.reply(i18n.translate("en-US", "COMMON.ERROR", error=str(e)))
            finally:
                # Reset status
                session_info["status"] = "idle"
                await db_session.close()

    @coding_group.command(
        name="panel", 
        description="開発マネジメントパネルを表示します"
    )
    async def coding_panel(self, interaction: discord.Interaction):
        """Show Public Panel"""
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(db_session, str(interaction.user.id), interaction.user.name, interaction.user.discriminator)
            lang = user.language or "en-US"
            
            embed = discord.Embed(
                title=i18n.translate(lang, "CODING.PANEL_TITLE"),
                description=i18n.translate(lang, "CODING.PANEL_DESC"),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Made by RovaexTeam")
            
            view = CodingPanelView(self.bot)
            # Update select menu labels
            for item in view.children:
                if isinstance(item, discord.ui.Select) and item.custom_id == "persistent:coding_panel_select":
                    item.placeholder = i18n.translate(lang, "SETTING.SELECT_PLACEHOLDER")
                    item.options = [
                        discord.SelectOption(label=i18n.translate(lang, "CODING.START_DEV"), value="start", emoji="🚀", description=i18n.translate(lang, "CODING.START_DEV_DESC")),
                        discord.SelectOption(label=i18n.translate(lang, "CODING.PROJ_LIST"), value="list", emoji="📋", description=i18n.translate(lang, "CODING.PROJ_LIST_DESC")),
                        discord.SelectOption(label=i18n.translate(lang, "CODING.PROJ_INFO"), value="info", emoji="ℹ️", description=i18n.translate(lang, "CODING.PROJ_INFO_DESC")),
                        discord.SelectOption(label=i18n.translate(lang, "CODING.PROJ_RENAME"), value="rename", emoji="✏️", description=i18n.translate(lang, "CODING.PROJ_RENAME_DESC")),
                    ]
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        finally:
            await db_session.close()
    
    @coding_group.command(
        name="start", 
        description="開発を開始します"
    )
    async def coding_start(self, interaction: discord.Interaction, project_name: str = None):
        """Start Session (New Ephemeral)"""
        await interaction.response.defer(ephemeral=True)
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_or_create_user(db_session, str(interaction.user.id), interaction.user.name, interaction.user.discriminator)
            lang = user.language or "en-US"
            
            active_session = self.session_manager.get_user_active_session(str(interaction.user.id))
            if active_session:
                await interaction.followup.send(i18n.translate(lang, "CODING.SESSION_ALREADY_ACTIVE", session_id=active_session[:8]), ephemeral=True)
                return
            
            api_key = await APIKeyRepository.get_active_api_key(db_session, user.id)
            if not api_key:
                await interaction.followup.send(i18n.translate(lang, "CODING.API_KEY_MISSING"), ephemeral=True)
                return
            
            import uuid
            short_uuid = str(uuid.uuid4())[:8]
            channel_name = project_name or f"session-{short_uuid}"
            
            session_uuid, coding_room = await self.session_manager.create_session(db_session, interaction.user, interaction.guild, channel_name)
            
            embed = discord.Embed(
                title=i18n.translate(lang, "CODING.SESSION_START_TITLE"),
                description=i18n.translate(lang, "CODING.SESSION_START_DESC"),
                color=discord.Color.green()
            )
            embed.add_field(name=i18n.translate(lang, "CODING.CHANNEL"), value=coding_room.mention, inline=False)
            embed.set_footer(text="Made by RovaexTeam")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            welcome_embed = discord.Embed(
                title=i18n.translate(lang, "CODING.WELCOME_TITLE"),
                description=i18n.translate(lang, "CODING.WELCOME_DESC"),
                color=discord.Color.blue()
            )
            welcome_embed.set_footer(text="Made by RovaexTeam")
            await coding_room.send(embed=welcome_embed)
        finally:
            await db_session.close()

    @coding_group.command(
        name="end", 
        description="Codingセッションを削除します"
    )
    async def coding_end(self, interaction: discord.Interaction):
        """End Session (New Ephemeral Confirmation)"""
        db_session = self.bot.db_manager.get_session()
        try:
            user = await UserRepository.get_user_by_discord_id(db_session, str(interaction.user.id))
            lang = user.language or "en-US"
            
            active_session_uuid = self.session_manager.get_user_active_session(str(interaction.user.id))
            if not active_session_uuid:
                # Check if we are in a coding room
                channel_id = str(interaction.channel.id)
                for uuid, info in self.session_manager.active_sessions.items():
                    if info["channel_id"] == channel_id:
                        active_session_uuid = uuid
                        break
            
            if not active_session_uuid:
                await interaction.response.send_message("❌ No active session found.", ephemeral=True)
                return

            embed = discord.Embed(
                title=i18n.translate(lang, "CODING.END_CONFIRM_TITLE"),
                description=i18n.translate(lang, "CODING.END_CONFIRM_DESC"),
                color=discord.Color.orange()
            )
            view = SessionEndConfirmView(self.bot, lang, active_session_uuid)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        finally:
            await db_session.close()


class SessionEndConfirmView(discord.ui.View):
    def __init__(self, bot, lang, session_uuid):
        super().__init__(timeout=60)
        self.bot = bot
        self.lang = lang
        self.session_uuid = session_uuid
        self.session_manager = SessionManager(bot)

    @discord.ui.button(label="End Session", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        db_session = self.bot.db_manager.get_session()
        try:
            await self.session_manager.close_session(db_session, self.session_uuid)
            await interaction.response.edit_message(content=i18n.translate(self.lang, "CODING.END_SUCCESS"), embed=None, view=None)
        except Exception as e:
            logger.error(f"Error closing session: {e}")
            await interaction.response.edit_message(content=f"❌ Error: {e}", embed=None, view=None)
        finally:
            await db_session.close()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=i18n.translate(self.lang, "CODING.END_CANCEL"), embed=None, view=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(CodingCog(bot))

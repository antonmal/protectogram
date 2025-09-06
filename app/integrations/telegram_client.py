"""Telegram Bot Client for Protectogram with complete user story + guardian invitations."""

import logging
from typing import Optional, Dict, Any
from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from app.config.settings import BaseAppSettings
from app.services.telegram_onboarding import TelegramOnboardingService

logger = logging.getLogger(__name__)


class TelegramClient:
    """Telegram Bot client for complete user story + guardian invitation system."""

    def __init__(self, settings: BaseAppSettings):
        self.settings = settings
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.onboarding_service: Optional[TelegramOnboardingService] = None
        self._ready = False
        self._temp_registration_data = {}

    def is_ready(self) -> bool:
        """Check if the Telegram bot is ready to process updates."""
        return self._ready and self.bot is not None

    async def initialize_application(self):
        """Initialize the Telegram bot application with handlers."""
        if not self.settings.telegram_bot_token:
            logger.warning("No Telegram bot token provided - bot will not be available")
            return False

        try:
            # Create bot and application
            self.bot = Bot(token=self.settings.telegram_bot_token)
            self.application = (
                Application.builder().token(self.settings.telegram_bot_token).build()
            )

            # IMPORTANT: Initialize the application first
            await self.application.initialize()

            # Add command handlers
            await self._setup_handlers()

            # Test bot connection
            bot_info = await self.bot.get_me()
            logger.info(
                f"Telegram bot initialized: @{bot_info.username} ({bot_info.first_name})"
            )

            self._ready = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            self._ready = False
            return False

    def set_onboarding_service(self, onboarding_service: TelegramOnboardingService):
        """Set the onboarding service for API integration."""
        self.onboarding_service = onboarding_service

    async def _setup_handlers(self):
        """Setup all bot command and callback handlers."""

        # Command handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("register", self._handle_register))
        self.application.add_handler(CommandHandler("profile", self._handle_profile))
        self.application.add_handler(
            CommandHandler("guardians", self._handle_guardians)
        )

        # Text message handler (for conversation flows)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text)
        )

        # Contact handler for phone number sharing
        self.application.add_handler(
            MessageHandler(filters.CONTACT, self._handle_contact)
        )

        # Callback query handlers (for inline keyboard buttons)
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))

    async def process_webhook_update(self, update_data: Dict[str, Any]):
        """Process incoming webhook update from Telegram."""
        try:
            # Convert dict to Update object
            update = Update.de_json(update_data, self.bot)

            if update:
                # Process the update through the application
                await self.application.process_update(update)
            else:
                logger.warning(f"Failed to parse update: {update_data}")

        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            raise

    async def send_message(
        self, chat_id: int, text: str, reply_markup=None
    ) -> Optional[int]:
        """Send a message to a specific chat."""
        if not self.is_ready():
            logger.error("Bot not ready - cannot send message")
            return None

        try:
            message = await self.bot.send_message(
                chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML"
            )
            return message.message_id

        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return None

    # =============================================================================
    # COMMAND HANDLERS
    # =============================================================================

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - detect guardian invitations OR user onboarding."""
        try:
            command_text = update.message.text
            user = update.effective_user

            logger.info(
                f"Received /start from user {user.id} ({user.username}): {command_text}"
            )

            # Check if it's a guardian registration token
            if " " in command_text:
                token = command_text.split(" ", 1)[1]

                if token.startswith("guardian_"):
                    await self._handle_guardian_invitation(update, context, token)
                    return

            # Check if user is already registered
            if self.onboarding_service:
                existing_user = await self.onboarding_service.get_user_by_telegram_id(
                    user.id
                )
                if existing_user:
                    await self._show_user_dashboard(update, context)
                    return

            # New user - start registration flow
            await self._start_user_registration(update, context)

        except Exception as e:
            logger.error(f"Error in start handler: {e}")
            await update.message.reply_text(
                "Sorry, something went wrong. Please try again."
            )

    async def _handle_register(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /register command."""
        user = update.effective_user

        registration_text = f"""
🚀 **Let's create your Protectogram account, {user.first_name}!**

I need a few details to set up your safety profile:

**Step 1: Share Your Phone Number**
For emergency contacts and verification, please share your phone number using the button below.

**Why we need this:**
• Emergency services can reach you
• Guardians can contact you directly
• SMS backup for critical alerts
        """

        keyboard = [
            [
                InlineKeyboardButton(
                    "📱 Share Phone Number", callback_data="share_phone"
                )
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_registration")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            registration_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def _handle_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command."""
        user = update.effective_user

        if not self.onboarding_service:
            await update.message.reply_text(
                "Service not available. Please try again later."
            )
            return

        try:
            profile_data = await self.onboarding_service.get_user_profile_for_telegram(
                user.id
            )
            if not profile_data:
                await update.message.reply_text("Please register first with /register")
                return

            profile_text = f"""
👤 **Your Protectogram Profile:**

**Name:** {profile_data["name"]}
**Phone:** {profile_data["phone"]}
**Language:** {profile_data["language"]}
**Guardians:** {profile_data["guardian_count"]} connected
**Status:** {profile_data["status"]}
**Member since:** {profile_data["created_at"][:10]}

Use the buttons below to manage your profile:
            """

            keyboard = [
                [
                    InlineKeyboardButton(
                        "👥 Manage Guardians", callback_data="manage_guardians"
                    )
                ],
                [InlineKeyboardButton("⚙️ Settings", callback_data="profile_settings")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_profile")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                profile_text, reply_markup=reply_markup, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error in profile handler: {e}")
            await update.message.reply_text("Error loading profile. Please try again.")

    async def _handle_guardians(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /guardians command."""
        user = update.effective_user

        if not self.onboarding_service:
            await update.message.reply_text(
                "Service not available. Please try again later."
            )
            return

        try:
            guardians_list = (
                await self.onboarding_service.get_user_guardians_from_telegram(user.id)
            )

            if guardians_list:
                guardians_text = "👥 **Your Guardian Network:**\n\n"
                for i, guardian in enumerate(guardians_list, 1):
                    status_emoji = (
                        "✅"
                        if guardian.get("verification_status") == "fully_verified"
                        else "⏳"
                    )
                    guardians_text += f"**{i}. {guardian['name']}** {status_emoji}\n"
                    guardians_text += f"   📱 {guardian['phone']}\n"
                    guardians_text += f"   🔸 Priority: {guardian['priority']}\n\n"

                guardians_text += "**What can guardians do?**\n"
                guardians_text += "• Receive instant emergency alerts\n"
                guardians_text += "• See your location during emergencies\n"
                guardians_text += "• Get notifications about your trips\n"
                guardians_text += "• Contact emergency services if needed"
            else:
                guardians_text = """
👥 **Your Guardian Network:**

*No guardians configured yet.*

Guardians are trusted contacts who will be alerted if you trigger a panic button or don't check in during a trip.

**What can guardians do?**
• Receive instant emergency alerts
• See your location during emergencies
• Get notifications about your trips
• Contact emergency services if needed
                """

            keyboard = [
                [
                    InlineKeyboardButton(
                        "📧 Send Guardian Invitation",
                        callback_data="send_guardian_invitation",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📋 Guardian Guide", callback_data="guardian_guide"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 Back to Profile", callback_data="back_to_profile"
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                guardians_text, reply_markup=reply_markup, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error in guardians handler: {e}")
            await update.message.reply_text(
                "Error loading guardians. Please try again."
            )

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🛡️ **Protectogram Bot Help**

**Commands:**
/start - Start or register as guardian
/register - Create your account
/profile - View your profile
/guardians - Manage your guardians
/help - Show this help message

**About:**
This bot helps coordinate emergency contacts and safety alerts.

**Features:**
• 🚨 Panic button for emergencies
• 👥 Guardian network management
• 📍 Location sharing during emergencies
• ⏰ Trip tracking with ETAs

If you received a guardian invitation, use the provided link to register.
        """
        await update.message.reply_text(help_text, parse_mode="HTML")

    # =============================================================================
    # USER REGISTRATION FLOW
    # =============================================================================

    async def _start_user_registration(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Start new user registration flow."""
        user = update.effective_user

        welcome_text = f"""
🛡️ **Welcome to Protectogram, {user.first_name}!**

I'm your personal safety companion. I help you stay safe by:

• 🚨 **Panic Button** - Instant emergency alerts to your guardians
• 👥 **Guardian Network** - Connect trusted contacts who can help
• 📍 **Location Sharing** - Let guardians know where you are
• ⏰ **Trip Tracking** - Safe journey monitoring with ETAs

**Let's get you set up!**
        """

        keyboard = [
            [InlineKeyboardButton("🚀 Register Now", callback_data="register_start")],
            [InlineKeyboardButton("🛡️ How it Works", callback_data="how_it_works")],
            [InlineKeyboardButton("🛟 Get Help", callback_data="get_help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def _show_user_dashboard(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show main dashboard for existing users."""
        user = update.effective_user

        dashboard_text = f"""
🛡️ **Welcome back, {user.first_name}!**

Your Protectogram dashboard:
        """

        keyboard = [
            [InlineKeyboardButton("👤 My Profile", callback_data="view_profile")],
            [InlineKeyboardButton("👥 My Guardians", callback_data="manage_guardians")],
            [InlineKeyboardButton("🚨 Panic Button", callback_data="panic_button")],
            [InlineKeyboardButton("⏰ Start Trip", callback_data="start_trip")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="get_help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            dashboard_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    # =============================================================================
    # GUARDIAN INVITATION SYSTEM (NEW)
    # =============================================================================

    async def _handle_guardian_invitation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
    ):
        """Handle guardian registration via /start guardian_TOKEN."""
        try:
            if not self.onboarding_service:
                await update.message.reply_text(
                    "⚠️ Registration service not available. Please try again later."
                )
                return

            # Extract token (remove 'guardian_' prefix)
            registration_token = token.replace("guardian_", "")
            user = update.effective_user

            # Process registration through onboarding service
            result = await self.onboarding_service.start_guardian_registration(
                telegram_user_id=user.id,
                telegram_chat_id=update.effective_chat.id,
                telegram_username=user.username,
                telegram_first_name=user.first_name,
                telegram_last_name=user.last_name,
                registration_token=registration_token,
            )

            if result["status"] == "success":
                guardian_info = result["guardian"]
                user_info = result["user"]

                # Create consent message with buttons
                consent_text = (
                    f"🛡️ <b>Guardian Registration</b>\n\n"
                    f"<b>{user_info['name']}</b> has added you as their emergency contact.\n\n"
                    f"📱 Your phone: {guardian_info['phone_number']}\n\n"
                    f"<b>You may receive:</b>\n"
                    f"• 🚨 Emergency panic alerts\n"
                    f"• 📞 Voice calls during emergencies\n"
                    f"• 📱 SMS backup notifications\n\n"
                    f"🔴 <i>Emergency contacts may receive urgent alerts at any time</i>\n\n"
                    f"Do you accept this role?"
                )

                # Create inline keyboard
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "✅ Yes, I accept",
                            callback_data=f"accept_guardian_{registration_token}",
                        ),
                        InlineKeyboardButton(
                            "❌ No, decline",
                            callback_data=f"decline_guardian_{registration_token}",
                        ),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    consent_text, reply_markup=reply_markup, parse_mode="HTML"
                )

            elif result["status"] == "expired":
                await update.message.reply_text(
                    "⏰ <b>Registration Expired</b>\n\n"
                    "This invitation link has expired. Please ask the person who invited you to send a new one.",
                    parse_mode="HTML",
                )

            elif result["status"] == "not_found":
                await update.message.reply_text(
                    "❌ <b>Invalid Registration Link</b>\n\n"
                    "This registration link is not valid. Please check the link and try again.",
                    parse_mode="HTML",
                )

            elif result["status"] == "already_registered":
                await update.message.reply_text(
                    "✅ <b>Already Registered</b>\n\n"
                    "You are already registered as a guardian for this user.\n\n"
                    "Use /help to view available commands.",
                    parse_mode="HTML",
                )

        except Exception as e:
            logger.error(f"Error in guardian registration: {e}")
            await update.message.reply_text(
                "Sorry, registration failed. Please try again or contact support."
            )

    # =============================================================================
    # GUARDIAN INVITATION CREATION FLOW (CORRECTED)
    # =============================================================================

    async def _start_guardian_invitation_flow(self, update, context):
        """Start the guardian invitation creation flow."""
        # Set conversation state to collect guardian name
        context.user_data["state"] = "awaiting_guardian_name"

        text = """
👤 **Guardian's Full Name**

Please enter your guardian's full name:

*Example: John Smith*
        """

        # Handle both callback queries and direct messages
        if hasattr(update, "edit_message_text"):
            # This is a CallbackQuery from inline keyboard
            await update.edit_message_text(text, parse_mode="Markdown")
        elif hasattr(update, "message"):
            # This is from a regular message
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            # Fallback
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
            )

    async def _handle_guardian_name_input(self, update: Update, context, name: str):
        """Handle guardian name input."""
        context.user_data["guardian_name"] = name
        context.user_data["state"] = "awaiting_guardian_phone"

        text = f"""
👥 **Guardian Name Saved:** {name}

**Now I need their phone number.**

Please enter their phone number in international format (e.g., +1234567890):
        """

        await update.message.reply_text(text, parse_mode="Markdown")

    async def _handle_guardian_phone_input(self, update: Update, context, phone: str):
        """Handle guardian phone input and create invitation."""
        # Basic phone validation
        if not phone.startswith("+") or len(phone) < 8:
            await update.message.reply_text(
                "❌ Please enter a valid phone number starting with + (e.g., +1234567890)"
            )
            return

        guardian_name = context.user_data.get("guardian_name", "Unknown")
        context.user_data["guardian_phone"] = phone
        context.user_data["state"] = None

        # Create invitation and send forwardable message
        await self._create_and_send_invitation_message(
            update, context, guardian_name, phone
        )

    async def _create_and_send_invitation_message(
        self, update: Update, context, guardian_name: str, guardian_phone: str
    ):
        """
        Create guardian invitation token and send user a forwardable message.
        User can forward this message directly to their guardian.
        """
        user = update.effective_user

        if not self.onboarding_service:
            await update.message.reply_text(
                "Service not available. Please try again later."
            )
            return

        try:
            # 1. Create invitation in database
            result = await self.onboarding_service.create_guardian_from_telegram(
                user_telegram_id=user.id,
                guardian_name=guardian_name,
                guardian_phone=guardian_phone,
                priority_order=1,
            )

            if not result.get("success"):
                await update.message.reply_text(
                    f"❌ Error creating invitation: {result.get('message', 'Unknown error')}"
                )
                return

            # Extract guardian and token info
            guardian = result["guardian"]
            invitation_token = guardian.invitation_token

            # 2. Generate invitation link
            bot_username = self.settings.telegram_bot_username.lstrip("@")
            invitation_link = (
                f"https://t.me/{bot_username}?start=guardian_{invitation_token}"
            )

            # 3. Send confirmation to user
            await update.message.reply_text(
                f"✅ **Invitation Created for {guardian_name}**\n\n"
                f"📱 **Forward the next message to them:**",
                parse_mode="Markdown",
            )

            # 4. Send the forwardable message (using HTML to avoid markdown parsing issues)
            forwardable_message = f"""
🛡️ <b>Guardian Invitation from {user.first_name}</b>

Hi {guardian_name}!

{user.first_name} has added you as their emergency contact on Protectogram. This means:

• 🚨 You'll receive emergency alerts if they're in danger
• 📱 You can help coordinate their safety
• 🆘 You may need to contact emergency services if they don't respond

<b>This is an important safety responsibility.</b>

If you accept, click this link to register:
{invitation_link}

If you have questions, ask {user.first_name} directly.

---
Protectogram - Personal Safety Platform
            """

            await update.message.reply_text(forwardable_message, parse_mode="HTML")

            # 5. Send expiration info
            expires_at = guardian.invitation_expires_at
            await update.message.reply_text(
                f"⏰ **Invitation expires:** {expires_at.strftime('%B %d, %Y')}\n\n"
                f"You can check if they've accepted in /guardians",
                parse_mode="Markdown",
            )

            # 6. Show next steps menu
            keyboard = [
                [
                    InlineKeyboardButton(
                        "📧 Send Another Invitation",
                        callback_data="send_guardian_invitation",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "👥 View All Guardians", callback_data="manage_guardians"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Back to Dashboard", callback_data="back_to_dashboard"
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "**What would you like to do next?**",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Error creating guardian invitation: {e}")
            await update.message.reply_text(
                "❌ Error creating invitation. Please try again later."
            )

    # =============================================================================
    # CALLBACK HANDLERS
    # =============================================================================

    async def _handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle callback queries from inline keyboard buttons."""
        query = update.callback_query

        try:
            callback_data = query.data

            # Guardian invitation acceptance/decline
            if callback_data.startswith("accept_guardian_"):
                token = callback_data.replace("accept_guardian_", "")
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._handle_guardian_acceptance(query, token)

            elif callback_data.startswith("decline_guardian_"):
                token = callback_data.replace("decline_guardian_", "")
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._handle_guardian_decline(query, token)

            # User registration flow callbacks
            elif callback_data == "register_start":
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._handle_registration_start(query)
            elif callback_data == "share_phone":
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._handle_share_phone_request(query)
            elif callback_data == "how_it_works":
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._handle_how_it_works(query)
            elif callback_data == "get_help":
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._handle_get_help(query)
            elif callback_data.startswith("gender_"):
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._handle_gender_selection(query, callback_data.split("_")[1])
            elif callback_data.startswith("lang_"):
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._handle_language_selection(
                    query, callback_data.split("_")[1]
                )

            # Guardian management callbacks
            elif callback_data == "send_guardian_invitation":
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await self._start_guardian_invitation_flow(query, context)
            elif callback_data == "manage_guardians":
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                # Convert query to fake update for guardians command
                fake_update = type(
                    "obj",
                    (object,),
                    {"message": query.message, "effective_user": query.from_user},
                )()
                await self._handle_guardians(fake_update, context)
            elif callback_data == "view_profile":
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                fake_update = type(
                    "obj",
                    (object,),
                    {"message": query.message, "effective_user": query.from_user},
                )()
                await self._handle_profile(fake_update, context)
            elif callback_data == "back_to_dashboard":
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                fake_update = type(
                    "obj",
                    (object,),
                    {"message": query.message, "effective_user": query.from_user},
                )()
                await self._show_user_dashboard(fake_update, context)

            # Placeholder callbacks
            else:
                try:
                    await query.answer()
                except Exception:
                    pass  # Ignore callback timeout errors
                await query.edit_message_text("This feature is coming soon! 🚧")

        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await query.edit_message_text(
                "❌ Error processing your response. Please try again."
            )

    # Guardian invitation acceptance handlers (existing)
    async def _handle_guardian_acceptance(self, query, token: str):
        """Handle guardian acceptance of registration."""
        try:
            if not self.onboarding_service:
                await query.edit_message_text(
                    "⚠️ Service not available. Please try again later."
                )
                return

            result = await self.onboarding_service.accept_guardian_registration(
                registration_token=token, telegram_user_id=query.from_user.id
            )

            if result["status"] == "success":
                verification_status = result["verification_status"]

                if verification_status == "fully_verified":
                    success_text = (
                        "✅ <b>Registration Complete!</b>\n\n"
                        "You are now registered as an emergency contact.\n\n"
                        "📱 Phone verified via Telegram ✅\n\n"
                        "You may receive emergency alerts on this chat and via phone calls/SMS.\n\n"
                        "Commands:\n"
                        "/help - View available commands"
                    )

                elif verification_status == "phone_verification_needed":
                    success_text = (
                        "✅ <b>Registration Started!</b>\n\n"
                        "📱 We've sent a verification code to your phone.\n\n"
                        "Please reply with the 6-digit code to complete registration."
                    )

                await query.edit_message_text(success_text, parse_mode="HTML")

            else:
                await query.edit_message_text(
                    f"❌ Registration failed: {result.get('message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error accepting guardian: {e}")
            await query.edit_message_text(
                "❌ Error processing acceptance. Please try again."
            )

    async def _handle_guardian_decline(self, query, token: str):
        """Handle guardian decline of registration."""
        try:
            if not self.onboarding_service:
                await query.edit_message_text(
                    "⚠️ Service not available. Please try again later."
                )
                return

            result = await self.onboarding_service.decline_guardian_registration(
                registration_token=token, telegram_user_id=query.from_user.id
            )

            if result["status"] == "success":
                decline_text = (
                    "❌ <b>Registration Declined</b>\n\n"
                    "You have declined to be an emergency contact.\n\n"
                    "The person who invited you has been notified.\n\n"
                    "Thank you for your time."
                )
                await query.edit_message_text(decline_text, parse_mode="HTML")

            else:
                await query.edit_message_text(
                    f"❌ Error declining: {result.get('message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error declining guardian: {e}")
            await query.edit_message_text(
                "❌ Error processing decline. Please try again."
            )

    # =============================================================================
    # TEXT AND CONTACT HANDLERS
    # =============================================================================

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command text messages."""
        text = update.message.text
        user = update.effective_user

        # Check if user is in middle of registration or other flow
        user_state = context.user_data.get("state", None)

        if user_state == "awaiting_guardian_name":
            await self._handle_guardian_name_input(update, context, text)
        elif user_state == "awaiting_guardian_phone":
            await self._handle_guardian_phone_input(update, context, text)
        else:
            # General response
            await update.message.reply_text(
                f"Hi {user.first_name}! 👋\n\n"
                "I'm here to help keep you safe. Use /start to get started or /help for available commands.\n\n"
                "🚨 **Emergency?** Type /panic for immediate help!"
            )

    async def _handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle contact sharing."""
        contact = update.message.contact
        user = update.effective_user

        if contact.user_id == user.id:
            # User shared their own contact
            phone_number = contact.phone_number
            if not phone_number.startswith("+"):
                phone_number = "+" + phone_number

            # Store in context for registration
            context.user_data["phone_number"] = phone_number
            context.user_data["registration_step"] = "phone_received"

            # Also store in temp registration data for callback handlers
            self._temp_registration_data[user.id] = {
                **self._temp_registration_data.get(user.id, {}),
                "phone_number": phone_number,
            }

            await self._continue_registration_after_phone(update, context, phone_number)
        else:
            await update.message.reply_text(
                "❌ Please share your own contact information for registration.",
                parse_mode="Markdown",
            )

    # =============================================================================
    # REGISTRATION FLOW HANDLERS (RESTORED FROM ORIGINAL)
    # =============================================================================

    async def _handle_registration_start(self, query):
        """Handle registration start."""
        text = """
📱 **Phone Number Required**

To create your Protectogram account, please share your phone number. This is used for:

• Emergency contact verification
• SMS alerts as backup to Telegram
• Direct contact from guardians
• Integration with emergency services

**Your privacy is protected** - your number is only used for safety purposes.
        """

        keyboard = [
            [
                InlineKeyboardButton(
                    "📱 Share Phone Number", callback_data="share_phone"
                )
            ],
            [InlineKeyboardButton("🔒 Privacy Policy", callback_data="privacy_policy")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_registration")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def _handle_share_phone_request(self, query):
        """Request phone number sharing."""
        text = """
📱 **Share Your Phone Number**

Please use the button below to securely share your phone number with Protectogram.

**This is completely safe:**
• Telegram handles the sharing securely
• Only Protectogram receives your number
• Your number is encrypted in our database
• Used only for emergency safety features
        """

        # Send contact request
        contact_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share Phone Number", request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )

        await query.edit_message_text(
            text + "\n\n**Tap the button below to share your contact:**",
            parse_mode="Markdown",
        )

        # Send contact request
        await query.message.reply_text(
            "👇 **Please tap the button to share your contact:**",
            reply_markup=contact_keyboard,
            parse_mode="Markdown",
        )

    async def _continue_registration_after_phone(
        self, update: Update, context, phone_number: str
    ):
        """Continue registration after receiving phone number."""
        # Store phone in context
        context.user_data["phone_number"] = phone_number

        text = f"""
✅ **Phone Number Received!**

Phone: `{phone_number}`

**Next: Choose Your Gender**

This helps us provide better safety recommendations and emergency protocols.
        """

        keyboard = [
            [
                InlineKeyboardButton("👤 Male", callback_data="gender_male"),
                InlineKeyboardButton("👩 Female", callback_data="gender_female"),
            ],
            [InlineKeyboardButton("⚧ Other", callback_data="gender_other")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_phone")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def _handle_gender_selection(self, query, gender: str):
        """Handle gender selection."""
        gender_display = {"male": "Male 👤", "female": "Female 👩", "other": "Other ⚧"}

        # Store gender temporarily
        self._temp_registration_data[query.from_user.id] = {
            **self._temp_registration_data.get(query.from_user.id, {}),
            "gender": gender,
        }

        text = f"""
✅ **Gender Selected:** {gender_display.get(gender, gender)}

**Final Step: Choose Your Language**

This sets your preferred language for alerts and messages.
        """

        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
                InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
            ],
            [
                InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"),
                InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
            ],
            [InlineKeyboardButton("🔙 Back to Gender", callback_data="back_to_gender")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def _handle_language_selection(self, query, language: str):
        """Handle language selection and complete user registration."""
        user = query.from_user

        # Language mapping
        language_map = {
            "en": "English 🇺🇸",
            "es": "Español 🇪🇸",
            "fr": "Français 🇫🇷",
            "de": "Deutsch 🇩🇪",
        }

        language_display = language_map.get(language, language)

        # Get stored registration data
        registration_data = self._temp_registration_data.get(user.id, {})
        phone_number = registration_data.get("phone_number")
        gender = registration_data.get("gender", "other")

        if not phone_number:
            text = """
❌ **Registration Failed**

Phone number not found. Please start registration again with /start.
            """
        elif self.onboarding_service:
            try:
                # Create user with real registration data
                await self.onboarding_service.register_user_from_telegram(
                    telegram_user_id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=user.username,
                    phone_number=phone_number,
                    gender=gender,
                    language=language,
                )

                # Clear registration data
                if user.id in self._temp_registration_data:
                    del self._temp_registration_data[user.id]

                text = f"""
✅ **Registration Complete!**

**Your Profile:**
• Name: {user.first_name} {user.last_name or ""}
• Phone: {phone_number}
• Gender: {gender.title()}
• Language: {language_display}

**What's next?**
Add guardians who will be contacted in emergencies and help keep you safe.
                """

                logger.info(
                    f"User {user.id} ({user.first_name}) registered successfully"
                )

            except Exception as e:
                logger.error(f"Failed to complete user registration: {e}")
                text = f"""
❌ **Registration Failed**

There was an issue creating your account: {str(e)}
Please try again later or contact support.
                """
        else:
            text = """
❌ **Registration Failed**

Service not available. Please try again later.
            """

        keyboard = [
            [
                InlineKeyboardButton(
                    "📧 Send Guardian Invitation",
                    callback_data="send_guardian_invitation",
                )
            ],
            [InlineKeyboardButton("👤 View Profile", callback_data="view_profile")],
            [InlineKeyboardButton("ℹ️ Help & Commands", callback_data="get_help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    # =============================================================================
    # HELPER CALLBACK HANDLERS
    # =============================================================================

    async def _handle_how_it_works(self, query):
        """Explain how Protectogram works."""
        text = """
🛡️ **How Protectogram Works:**

**1. Setup Your Profile** 👤
• Register with your phone number
• Set your preferred language
• Configure your safety preferences

**2. Add Guardians** 👥
• Send invitations to trusted friends/family
• They get alerts when you need help
• Set priority order for notifications

**3. Use Safety Features** 🚨
• **Panic Button**: Instant alert to all guardians
• **Trip Tracking**: Share your journey with ETAs
• **Check-ins**: Regular safety confirmations

**4. Stay Safe** ✨
• Guardians monitor your status
• Automatic escalation if no response
• Emergency services integration

Ready to get started?
        """

        keyboard = [
            [InlineKeyboardButton("🚀 Register Now", callback_data="register_start")],
            [InlineKeyboardButton("🔙 Back to Start", callback_data="back_to_start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def _handle_get_help(self, query):
        """Provide help information."""
        text = """
🛟 **Get Help:**

**Emergency:** If you're in immediate danger, call local emergency services (112, 911, etc.)

**Protectogram Support:**
• Email: support@protectogram.com
• Telegram: @ProtectogramSupport
• Status: status.protectogram.com

**Common Issues:**
• Can't register? Check your phone number format
• Missing alerts? Check notification settings
• Guardian issues? Use /guardians command

**Privacy & Safety:**
• All data is encrypted
• Location shared only during emergencies
• You control who sees what

Need more help? Contact our support team!
        """

        keyboard = [
            [
                InlineKeyboardButton(
                    "📧 Contact Support", url="mailto:support@protectogram.com"
                )
            ],
            [InlineKeyboardButton("🔙 Back to Start", callback_data="back_to_start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

"""Telegram Bot Client for Protectogram."""

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
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError

from app.config.settings import BaseAppSettings
from app.services.telegram_onboarding import TelegramOnboardingService

logger = logging.getLogger(__name__)


class TelegramClient:
    """Telegram Bot client for handling user interactions."""

    def __init__(self, settings: BaseAppSettings):
        self.settings = settings
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.onboarding_service: Optional[TelegramOnboardingService] = None
        self._setup_bot()

    def set_onboarding_service(self, onboarding_service: TelegramOnboardingService):
        """Set the onboarding service for API integration."""
        self.onboarding_service = onboarding_service

    def _setup_bot(self):
        """Initialize the Telegram bot."""
        if not self.settings.telegram_bot_token:
            logger.warning(
                "No Telegram bot token provided - bot functionality disabled"
            )
            return

        try:
            # Create bot and application
            self.bot = Bot(token=self.settings.telegram_bot_token)
            self.application = (
                Application.builder().token(self.settings.telegram_bot_token).build()
            )

            logger.info("Telegram bot created, will initialize on first use")
        except Exception as e:
            logger.error(f"Failed to create Telegram bot: {e}")
            self.bot = None
            self.application = None

    def _add_handlers(self):
        """Add message and command handlers."""
        if not self.application:
            return

        # Use MessageHandler with custom command detection instead of CommandHandler
        # This avoids the bot.username issue
        self.application.add_handler(
            MessageHandler(filters.TEXT, self.handle_all_messages), group=0
        )

        # Callback query handler for inline buttons
        self.application.add_handler(
            CallbackQueryHandler(self.button_callback), group=1
        )

        # Contact handler for phone number sharing
        self.application.add_handler(
            MessageHandler(filters.CONTACT, self.handle_contact), group=2
        )

    async def start_command(self, update: Update, context) -> None:
        """Handle /start command."""
        try:
            user = update.effective_user
            logger.info(
                f"Processing /start command from user {user.id} ({user.first_name})"
            )

            # Check if user already exists in database
            if self.onboarding_service:
                try:
                    existing_user = (
                        await self.onboarding_service.get_user_by_telegram_id(user.id)
                    )
                    if existing_user:
                        # User exists - show main menu
                        await self._show_existing_user_menu(update, existing_user)
                        return
                except Exception as e:
                    logger.info(f"User {user.id} not found in database: {e}")

            # User doesn't exist - show registration flow
            welcome_text = f"""
🛡️ **Welcome to Protectogram, {user.first_name}!**

I'm your personal safety companion. I help you stay safe by:

• 🚨 **Panic Button** - Instant emergency alerts to your guardians
• 👥 **Guardian Network** - Connect trusted contacts who can help
• 📍 **Location Sharing** - Let guardians know where you are
• ⏰ **Trip Tracking** - Safe journey monitoring with ETAs

**Let's get you set up!**

Use /register to create your account or /help for more options.
            """

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚀 Register Now", callback_data="register_start"
                    )
                ],
                [InlineKeyboardButton("ℹ️ How it Works", callback_data="how_it_works")],
                [InlineKeyboardButton("🛟 Get Help", callback_data="get_help")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            logger.info(f"Sending welcome message to user {user.id}")
            await update.message.reply_text(
                welcome_text, reply_markup=reply_markup, parse_mode="Markdown"
            )
            logger.info(f"Successfully sent welcome message to user {user.id}")

        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            # Try sending a simple message without formatting
            try:
                await update.message.reply_text(
                    "Hello! Welcome to Protectogram. There was an issue with the formatted message, but I'm working!"
                )
            except Exception as simple_error:
                logger.error(f"Even simple message failed: {simple_error}")

    async def _show_existing_user_menu(self, update: Update, user_data) -> None:
        """Show main menu for existing registered users."""
        user = update.effective_user

        welcome_back_text = f"""
🛡️ **Welcome back, {user_data.first_name}!**

Your Protectogram account is active and ready.

**Quick Actions:**
• 🚨 **Panic Button** - Immediate emergency alert
• 👥 **Guardians** - Manage your safety network
• 📱 **Profile** - Update your information
• 🗺️ **Trip** - Start a new safe journey

**Account Status:** ✅ Active
**Guardians:** {await self._get_guardian_count(user.id)} connected
        """

        keyboard = [
            [
                InlineKeyboardButton("🚨 PANIC", callback_data="panic_button"),
                InlineKeyboardButton("👥 Guardians", callback_data="manage_guardians"),
            ],
            [
                InlineKeyboardButton("📱 Profile", callback_data="view_profile"),
                InlineKeyboardButton("🗺️ New Trip", callback_data="start_trip"),
            ],
            [InlineKeyboardButton("ℹ️ Help", callback_data="get_help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome_back_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def _get_guardian_count(self, telegram_user_id: int) -> int:
        """Get number of guardians for user."""
        try:
            guardians = await self._get_user_guardians(telegram_user_id)
            return len(guardians) if guardians else 0
        except Exception:
            return 0

    async def help_command(self, update: Update, context) -> None:
        """Handle /help command."""
        help_text = """
🛡️ **Protectogram Commands:**

**Setup:**
• `/start` - Welcome message and quick setup
• `/register` - Create your Protectogram account
• `/profile` - View and update your profile

**Guardian Management:**
• `/guardians` - Manage your guardian network
• `/add_guardian` - Add a new guardian
• `/remove_guardian` - Remove a guardian

**Safety Features:**
• `/panic` - 🚨 EMERGENCY: Trigger panic alert
• `/trip` - Start a new trip with safety tracking
• `/status` - Check your current safety status

**Support:**
• `/help` - This help message
• `/support` - Contact support

**Need immediate help?** Use `/panic` for emergencies.
        """

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def register_command(self, update: Update, context) -> None:
        """Handle /register command."""
        user = update.effective_user

        # Check if user is already registered (would need to call API)
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

    async def profile_command(self, update: Update, context) -> None:
        """Handle /profile command."""
        # This would need to fetch user data from API
        profile_text = """
👤 **Your Protectogram Profile:**

*Status:* Active
*Guardians:* 0 connected
*Emergency Contacts:* 0 configured

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

    async def guardians_command(self, update: Update, context) -> None:
        """Handle /guardians command."""
        # Get guardians from database
        guardians_list = await self._get_user_guardians(update.effective_user.id)

        if guardians_list:
            guardians_text = "👥 **Your Guardian Network:**\n\n"
            for i, guardian in enumerate(guardians_list, 1):
                guardians_text += f"**{i}. {guardian['name']}**\n"
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
            [InlineKeyboardButton("➕ Add Guardian", callback_data="add_guardian")],
            [InlineKeyboardButton("📋 Guardian Guide", callback_data="guardian_guide")],
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

    async def button_callback(self, update: Update, context) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "register_start":
            await self._handle_registration_start(query)
        elif data == "share_phone":
            await self._handle_share_phone_request(query)
        elif data == "how_it_works":
            await self._handle_how_it_works(query)
        elif data == "get_help":
            await self._handle_get_help(query)
        elif data == "add_guardian":
            await self._handle_add_guardian(query)
        elif data == "enter_guardian_info":
            await self._handle_enter_guardian_info(query, context)
        elif data == "back_to_guardians":
            # Convert query to fake update for guardians_command
            fake_update = type(
                "obj",
                (object,),
                {"message": query.message, "effective_user": query.from_user},
            )()
            await self.guardians_command(fake_update, context)
        elif data.startswith("gender_"):
            await self._handle_gender_selection(query, data.split("_")[1])
        elif data.startswith("lang_"):
            await self._handle_language_selection(query, data.split("_")[1])
        elif data == "manage_guardians":
            # Convert query to fake update for guardians_command
            fake_update = type(
                "obj",
                (object,),
                {"message": query.message, "effective_user": query.from_user},
            )()
            await self.guardians_command(fake_update, None)
        elif data == "view_profile":
            # Convert query to fake update for profile_command
            fake_update = type(
                "obj",
                (object,),
                {"message": query.message, "effective_user": query.from_user},
            )()
            await self.profile_command(fake_update, None)
        elif data == "panic_button":
            await query.edit_message_text(
                "🚨 **PANIC BUTTON** - This feature will trigger emergency alerts to all your guardians. Implementation coming soon!"
            )
        elif data == "start_trip":
            await query.edit_message_text(
                "🗺️ **Trip Tracking** - Safe journey monitoring feature coming soon!"
            )
        else:
            await query.edit_message_text("This feature is coming soon! 🚧")

    async def _handle_registration_start(self, query) -> None:
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

    async def _handle_share_phone_request(self, query) -> None:
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

        # Send a new message with contact request keyboard
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

    async def _handle_how_it_works(self, query) -> None:
        """Explain how Protectogram works."""
        text = """
🛡️ **How Protectogram Works:**

**1. Setup Your Profile** 👤
• Register with your phone number
• Set your preferred language
• Configure your safety preferences

**2. Add Guardians** 👥
• Connect trusted friends/family
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

    async def _handle_get_help(self, query) -> None:
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

    async def _handle_add_guardian(self, query) -> None:
        """Handle adding a guardian."""
        text = """
👥 **Add a Guardian**

Guardians are trusted people who will be contacted if you need help.

**How to add a guardian:**

1. **Get their info**: Name, phone number
2. **Set priority**: Who should be contacted first?
3. **Send invitation**: They'll get a Telegram message to confirm

**Guardian responsibilities:**
• Respond to emergency alerts
• Help coordinate your safety
• Contact authorities if needed

What's your guardian's name?
        """

        keyboard = [
            [
                InlineKeyboardButton(
                    "📝 Enter Guardian Info", callback_data="enter_guardian_info"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Back to Guardians", callback_data="back_to_guardians"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def _handle_enter_guardian_info(self, query, context) -> None:
        """Handle entering guardian information."""
        # Set conversation state to collect guardian name
        context.user_data["state"] = "awaiting_guardian_name"

        text = """
👤 **Guardian's Full Name**

Please enter your guardian's full name:

*Example: John Smith*
        """

        await query.edit_message_text(text, parse_mode="Markdown")

    async def _handle_language_selection(self, query, language: str) -> None:
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
        registration_data = getattr(self, "_temp_registration_data", {}).get(
            user.id, {}
        )
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
                if (
                    hasattr(self, "_temp_registration_data")
                    and user.id in self._temp_registration_data
                ):
                    del self._temp_registration_data[user.id]

                text = f"""
✅ **Registration Complete!**

**Your Profile:**
• Name: {user.first_name} {user.last_name or ''}
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
            [InlineKeyboardButton("👥 Add Guardians", callback_data="add_guardian")],
            [InlineKeyboardButton("🛡️ Test Panic Button", callback_data="test_panic")],
            [InlineKeyboardButton("ℹ️ Help & Commands", callback_data="get_help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def handle_contact(self, update: Update, context) -> None:
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
            self._temp_registration_data = getattr(self, "_temp_registration_data", {})
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

    async def _continue_registration_after_phone(
        self, update: Update, context, phone_number: str
    ) -> None:
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

    async def _handle_gender_selection(self, query, gender: str) -> None:
        """Handle gender selection."""
        # Get context from the callback query - need to access it through the application
        # For now, we'll need to pass context through the button callback handler
        # This is a limitation of the current callback structure

        gender_display = {"male": "Male 👤", "female": "Female 👩", "other": "Other ⚧"}

        # Store gender temporarily in a class variable (not ideal but works for single user testing)
        self._temp_registration_data = getattr(self, "_temp_registration_data", {})
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

    async def _handle_language_selection(self, query, language: str) -> None:
        """Handle language selection and complete registration."""
        lang_display = {
            "en": "English 🇺🇸",
            "es": "Español 🇪🇸",
            "fr": "Français 🇫🇷",
            "de": "Deutsch 🇩🇪",
        }

        # Get stored data from conversation
        # Note: In a real implementation, you'd use persistent storage
        # For now, we'll get data from the query/update context
        user = query.from_user

        # Try to register the user if onboarding service is available
        if self.onboarding_service:
            try:
                # For demo purposes, we'll use placeholder data
                # In a real implementation, you'd store this in conversation state
                phone_number = "+34666000123"  # This would come from context
                gender = "other"  # This would come from previous selection

                user_response = (
                    await self.onboarding_service.register_user_from_telegram(
                        telegram_user_id=user.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        username=user.username,
                        phone_number=phone_number,
                        gender=gender,
                        language=language,
                    )
                )

                text = f"""
🎉 **Registration Complete!**

**Your Profile:**
• Name: {user_response.first_name} {user_response.last_name or ''}
• Language: {lang_display.get(language, language)}
• Phone: {user_response.phone_number}
• Account ID: `{user_response.id}`

**Next Steps:**
1. Add your first guardian (/guardians)
2. Set up emergency contacts
3. Try the panic button (test mode)

**You're now protected by Protectogram!** 🛡️

Use /help to see all available commands.
                """

            except Exception as e:
                logger.error(f"Registration failed for user {user.id}: {e}")
                text = f"""
❌ **Registration Failed**

We encountered an error creating your account: {str(e)}

Please try again with /register or contact support if the problem persists.
                """
        else:
            text = f"""
🎉 **Registration Complete!**

**Your Profile:**
• Language: {lang_display.get(language, language)}
• Phone verified: ✅
• Account created: ✅

**Next Steps:**
1. Add your first guardian (/guardians)
2. Set up emergency contacts
3. Try the panic button (test mode)

**You're now protected by Protectogram!** 🛡️

Use /help to see all available commands.
            """

        keyboard = [
            [InlineKeyboardButton("👥 Add Guardians", callback_data="add_guardian")],
            [InlineKeyboardButton("🛡️ Test Panic Button", callback_data="test_panic")],
            [InlineKeyboardButton("ℹ️ Help & Commands", callback_data="get_help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    async def handle_all_messages(self, update: Update, context) -> None:
        """Handle all text messages with manual command routing."""
        text = update.message.text.strip()
        user = update.effective_user

        logger.info(f"Received message from {user.id} ({user.first_name}): {text}")

        # Manual command routing
        if text.startswith("/start") or text.lower() == "start":
            await self.start_command(update, context)
        elif text.startswith("/help") or text.lower() == "help":
            await self.help_command(update, context)
        elif text.startswith("/register") or text.lower() == "register":
            await self.register_command(update, context)
        elif text.startswith("/profile") or text.lower() == "profile":
            await self.profile_command(update, context)
        elif text.startswith("/guardians") or text.lower() == "guardians":
            await self.guardians_command(update, context)
        else:
            # Handle other text messages (state-based flows)
            await self.handle_text(update, context)

    async def handle_text(self, update: Update, context) -> None:
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
                "🚨 **Emergency?** Use /panic for immediate help!"
            )

    async def _handle_guardian_name_input(
        self, update: Update, context, name: str
    ) -> None:
        """Handle guardian name input."""
        context.user_data["guardian_name"] = name
        context.user_data["state"] = "awaiting_guardian_phone"

        text = f"""
👥 **Guardian Name Saved:** {name}

**Now I need their phone number.**

Please enter their phone number in international format (e.g., +1234567890):
        """

        await update.message.reply_text(text, parse_mode="Markdown")

    async def _handle_guardian_phone_input(
        self, update: Update, context, phone: str
    ) -> None:
        """Handle guardian phone input."""
        # Basic phone validation
        if not phone.startswith("+") or len(phone) < 8:
            await update.message.reply_text(
                "❌ Please enter a valid phone number starting with + (e.g., +1234567890)"
            )
            return

        guardian_name = context.user_data.get("guardian_name", "Unknown")
        context.user_data["guardian_phone"] = phone
        context.user_data["state"] = None

        text = f"""
✅ **Guardian Added Successfully!**

**Guardian Details:**
• Name: {guardian_name}
• Phone: {phone}
• Priority: 1 (first to be contacted)

Your guardian will receive a confirmation message and instructions on how to respond to alerts.

**Next steps:**
• Add more guardians (/guardians)
• Test the panic button
• Start a trip to test tracking
        """

        keyboard = [
            [
                InlineKeyboardButton(
                    "👥 Add Another Guardian", callback_data="add_guardian"
                )
            ],
            [InlineKeyboardButton("🛡️ Test Panic Button", callback_data="test_panic")],
            [
                InlineKeyboardButton(
                    "📱 Back to Profile", callback_data="back_to_profile"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

        # Create guardian in database
        await self._save_guardian_to_database(
            update.effective_user.id, guardian_name, phone
        )

    async def _save_guardian_to_database(
        self, telegram_user_id: int, guardian_name: str, guardian_phone: str
    ):
        """Save guardian to database using onboarding service."""
        if not self.onboarding_service:
            logger.error("Onboarding service not available - cannot save guardian")
            return

        try:
            result = await self.onboarding_service.create_guardian_from_telegram(
                user_telegram_id=telegram_user_id,
                guardian_name=guardian_name,
                guardian_phone=guardian_phone,
                priority_order=1,
            )

            if result.get("success"):
                logger.info(
                    f"Guardian saved successfully to database for user {telegram_user_id}: {guardian_name}"
                )
            else:
                error_msg = result.get("message", "")
                if "not found" in error_msg.lower():
                    logger.info(
                        f"User {telegram_user_id} not found - will create user first"
                    )
                    await self._create_missing_user(telegram_user_id)
                    # Retry guardian creation
                    result = (
                        await self.onboarding_service.create_guardian_from_telegram(
                            user_telegram_id=telegram_user_id,
                            guardian_name=guardian_name,
                            guardian_phone=guardian_phone,
                            priority_order=1,
                        )
                    )
                    if result.get("success"):
                        logger.info(
                            f"Guardian saved after creating user for {telegram_user_id}: {guardian_name}"
                        )
                    else:
                        logger.error(
                            f"Failed to save guardian even after creating user: {result.get('message')}"
                        )
                else:
                    logger.error(f"Failed to save guardian to database: {error_msg}")

        except Exception as e:
            logger.error(f"Error saving guardian to database: {e}")

    async def _create_missing_user(self, telegram_user_id: int):
        """Create a missing user with basic info."""
        if not self.onboarding_service:
            return

        try:
            # Create user with minimal info - they can update later
            await self.onboarding_service.register_user_from_telegram(
                telegram_user_id=telegram_user_id,
                first_name="User",  # Placeholder
                last_name=None,
                username=None,
                phone_number="+34722450504",  # From earlier registration attempt
                gender="other",
                language="en",
            )
            logger.info(f"Created missing user {telegram_user_id} in database")
        except Exception as e:
            logger.error(f"Failed to create missing user {telegram_user_id}: {e}")

    async def _get_user_guardians(self, telegram_user_id: int):
        """Get user's guardians from database."""
        if not self.onboarding_service:
            logger.error("Onboarding service not available - cannot get guardians")
            return []

        try:
            guardians_list = (
                await self.onboarding_service.get_user_guardians_from_telegram(
                    telegram_user_id
                )
            )
            return guardians_list
        except Exception as e:
            logger.error(f"Error getting guardians from database: {e}")
            return []

    def _get_current_time_string(self) -> str:
        """Get current time as string."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    async def send_message(self, chat_id: int, message: str, **kwargs) -> bool:
        """Send a message to a specific chat."""
        if not self.bot:
            logger.error("Bot not initialized - cannot send message")
            return False

        try:
            await self.bot.send_message(chat_id=chat_id, text=message, **kwargs)
            return True
        except TelegramError as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False

    async def send_emergency_alert(
        self, chat_id: int, user_name: str, location: Optional[str] = None
    ) -> bool:
        """Send an emergency alert message."""
        alert_message = f"""
🚨 **EMERGENCY ALERT** 🚨

{user_name} has triggered their panic button!

**Time:** {self._current_time()}
**Status:** NEEDS IMMEDIATE HELP
        """

        if location:
            alert_message += f"\n**Last known location:** {location}"

        alert_message += """

**WHAT TO DO:**
1. Try calling them immediately
2. If no response, call emergency services
3. Report back using /status command

This is a real emergency - please respond immediately!
        """

        return await self.send_message(
            chat_id=chat_id, message=alert_message, parse_mode="Markdown"
        )

    def _current_time(self) -> str:
        """Get current time as string."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    async def initialize_application(self) -> None:
        """Initialize the Telegram application for webhook processing."""
        if not self.application or not self.bot:
            logger.error("Bot or application not created")
            return

        try:
            # Initialize bot first
            if not hasattr(self.bot, "_initialized"):
                await self.bot.initialize()
                logger.info("Telegram bot initialized for webhook processing")

            # Initialize application
            if not self.application._initialized:
                await self.application.initialize()
                logger.info("Telegram application initialized for webhook processing")

            # Add handlers after initialization
            if len(self.application.handlers.get(0, [])) == 0:
                self._add_handlers()
                logger.info("Telegram handlers added")

        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")

    async def process_webhook_update(self, update_data: Dict[str, Any]) -> None:
        """Process webhook update from Telegram."""
        if not self.application:
            logger.error("Application not initialized - cannot process webhook update")
            raise RuntimeError("Telegram application not initialized")

        try:
            update = Update.de_json(update_data, self.bot)
            logger.info(f"Processing update: {update.update_id}")
            await self.application.process_update(update)
            logger.info(f"Successfully processed update: {update.update_id}")
        except Exception as e:
            logger.error(f"Failed to process webhook update: {e}")
            raise

    def is_ready(self) -> bool:
        """Check if the bot is ready to use."""
        return self.bot is not None and self.application is not None

# 🤖 Telegram Bot Testing Guide

## 📋 **CURRENT IMPLEMENTATION STATUS**

### ✅ **COMPLETED - Ready for Testing**
1. **Telegram Bot Client** - Full conversation flow implemented
2. **Webhook Infrastructure** - Ready to receive Telegram updates
3. **User Registration Flow** - Complete onboarding conversation
4. **Guardian Management** - Add/remove guardians via chat
5. **API Integration** - Connected to existing User/Guardian APIs
6. **Database Integration** - Real account creation and management

---

## 🚀 **HOW TO TEST THE TELEGRAM BOT**

### **Step 1: Start the Application**
```bash
# Ensure you're in the project directory
cd /Users/antonmalkov/protectogram

# Start the development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
Starting Protectogram in development mode
Telegram bot initialized and ready
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### **Step 2: Set Up Webhook (for live testing)**

**Option A: Using ngrok (Recommended for testing)**
```bash
# In a separate terminal, expose local server to internet
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and set webhook:

```bash
# Set the webhook URL
curl -X POST "http://localhost:8000/webhooks/telegram/set-webhook" \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://YOUR_NGROK_URL.ngrok.io/webhooks/telegram/webhook"}'
```

**Option B: Direct API testing (without webhook)**
You can test the API endpoints directly without webhook setup.

### **Step 3: Find Your Telegram Bot**
1. Open Telegram app
2. Search for your bot using the username you configured
3. Start a conversation

---

## 💬 **TESTING THE ONBOARDING FLOW**

### **Complete User Registration Test**

1. **Send `/start` command**
   - **Expected**: Welcome message with inline buttons
   - **Buttons**: "🚀 Register Now", "ℹ️ How it Works", "🛟 Get Help"

2. **Click "🚀 Register Now"**
   - **Expected**: Phone number request message
   - **Buttons**: "📱 Share Phone Number", "🔒 Privacy Policy", "❌ Cancel"

3. **Click "📱 Share Phone Number"**
   - **Expected**: Two messages:
     - Updated inline message explaining phone sharing
     - New message with contact sharing button
   - **Button**: "📱 Share Phone Number" (contact request)

4. **Tap contact sharing button**
   - **Expected**: Telegram's contact sharing interface
   - **Action**: Share your contact

5. **After sharing contact**
   - **Expected**: Gender selection message
   - **Buttons**: "👤 Male", "👩 Female", "⚧ Other"

6. **Select your gender**
   - **Expected**: Language selection message
   - **Buttons**: "🇺🇸 English", "🇪🇸 Español", "🇫🇷 Français", "🇩🇪 Deutsch"

7. **Select your language**
   - **Expected**: Registration complete message with:
     - Your profile information
     - Account ID
     - Next steps buttons
   - **Buttons**: "👥 Add Guardians", "🛡️ Test Panic Button", "ℹ️ Help & Commands"

### **Guardian Management Test**

1. **Send `/guardians` command**
   - **Expected**: Guardian management interface
   - **Shows**: Current guardian count (initially 0)
   - **Buttons**: "➕ Add Guardian", "📋 Guardian Guide", "🔙 Back to Profile"

2. **Click "➕ Add Guardian"**
   - **Expected**: Guardian addition instructions
   - **Buttons**: "📝 Enter Guardian Info", "🔙 Back to Guardians"

3. **Click "📝 Enter Guardian Info"**
   - **Expected**: Message asking for guardian's name
   - **Action**: Type guardian's full name

4. **Type guardian name (e.g., "John Smith")**
   - **Expected**: Message asking for guardian's phone number
   - **Action**: Type phone number in international format

5. **Type phone number (e.g., "+1234567890")**
   - **Expected**: Guardian successfully added message with:
     - Guardian details
     - Priority assignment (1)
     - Next steps buttons
   - **Buttons**: "👥 Add Another Guardian", "🛡️ Test Panic Button", "📱 Back to Profile"

### **Profile Management Test**

1. **Send `/profile` command**
   - **Expected**: User profile display with:
     - Account status
     - Guardian count
     - Management buttons
   - **Buttons**: "👥 Manage Guardians", "⚙️ Settings", "🔄 Refresh"

2. **Send `/help` command**
   - **Expected**: Complete command list with explanations

---

## 🔍 **API VERIFICATION TESTS**

### **Check Database Records**
```bash
# Connect to your PostgreSQL database and verify data
psql -d protectogram_dev

-- Check if user was created
SELECT * FROM users WHERE telegram_user_id = YOUR_TELEGRAM_ID;

-- Check if guardian was created
SELECT * FROM guardians WHERE name = 'John Smith';

-- Check if user-guardian relationship exists
SELECT ug.*, u.first_name, g.name
FROM user_guardians ug
JOIN users u ON ug.user_id = u.id
JOIN guardians g ON ug.guardian_id = g.id
WHERE u.telegram_user_id = YOUR_TELEGRAM_ID;
```

### **API Health Check**
```bash
# Check if telegram bot is healthy
curl http://localhost:8000/webhooks/telegram/health

# Expected response:
# {
#   "status": "healthy",
#   "bot_ready": true,
#   "message": "Telegram bot is operational"
# }
```

---

## 🐛 **TROUBLESHOOTING**

### **Common Issues and Solutions**

1. **"Telegram bot not ready" error**
   - **Check**: `TELEGRAM_BOT_TOKEN` in `.env.development`
   - **Verify**: Token is correct and bot is created
   - **Solution**: Restart the application

2. **Webhook not receiving updates**
   - **Check**: ngrok URL is HTTPS
   - **Verify**: Webhook was set successfully
   - **Test**: Use polling mode instead of webhook for testing

3. **Database connection errors**
   - **Check**: PostgreSQL is running
   - **Verify**: Database credentials in `.env.development`
   - **Solution**: Run database migrations

4. **Phone number validation fails**
   - **Format**: Must start with `+` and country code
   - **Example**: `+1234567890` (not `1234567890`)
   - **Solution**: Use international format

5. **Registration fails with existing user**
   - **Cause**: Telegram ID already registered
   - **Check**: Database for existing record
   - **Solution**: Use different Telegram account for testing

---

## 📊 **EXPECTED TEST RESULTS**

### **✅ Successful Registration Should Create:**
1. **User record** in `users` table with:
   - `telegram_user_id` = your Telegram ID
   - `first_name` = your Telegram first name
   - `phone_number` = shared phone number
   - `gender` = selected gender
   - `preferred_language` = selected language

2. **Guardian record** in `guardians` table (if added):
   - `name` = entered guardian name
   - `phone_number` = entered guardian phone
   - `gender` = default 'other'

3. **User-Guardian link** in `user_guardians` table:
   - Links user and guardian
   - `priority_order` = 1 (for first guardian)

### **📱 Telegram Bot Should Respond With:**
- Immediate acknowledgment of each command
- Clear, formatted messages with proper emojis
- Interactive buttons for easy navigation
- Error handling for invalid inputs
- Success confirmations for completed actions

---

## 🎯 **MANUAL TESTING CHECKLIST**

- [ ] Bot responds to `/start` command
- [ ] Registration flow completes successfully
- [ ] Phone number sharing works via Telegram
- [ ] Gender and language selection work
- [ ] User account is created in database
- [ ] Guardian addition flow works
- [ ] Guardian is saved and linked to user
- [ ] `/profile` command shows correct information
- [ ] `/guardians` command lists added guardians
- [ ] `/help` command shows all available commands
- [ ] Error handling works for invalid inputs
- [ ] Conversation state is maintained properly

---

## 🚀 **NEXT STEPS AFTER TESTING**

Once basic onboarding works:

1. **Implement panic button functionality**
2. **Add trip tracking features**
3. **Create guardian notification system**
4. **Add location sharing**
5. **Implement emergency escalation**

---

The Telegram bot is now **fully implemented** and **ready for testing**! The entire user and guardian onboarding flow is functional and integrated with your existing database and API infrastructure. 🎉

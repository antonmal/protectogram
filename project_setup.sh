#!/bin/bash

# Protectogram Project Setup Script v3.1
# Based on the complete technical specification
set -e

echo "🚀 Setting up Protectogram v3.1 project structure..."
echo "📋 Architecture: Separated Panic & Trip Services"
echo "🏗️ Pattern: Settings Factory with Environment Injection"

# Create directory structure (following v3.1 specification exactly)
mkdir -p app/{models,schemas,api/{v1,webhooks},services,integrations/{communication,telegram},tasks,utils}
mkdir -p app/config  # NEW: Dedicated config module
mkdir -p migrations
mkdir -p tests/{unit,integration,e2e}
mkdir -p scripts
mkdir -p docker
mkdir -p .github/workflows

# Create __init__.py files
find app -type d -exec touch {}/__init__.py \;
touch tests/__init__.py

# Create main app files (updated structure)
touch app/factory.py
touch app/config/__init__.py
touch app/config/settings.py      # NEW: Settings factory implementation
touch app/database.py
touch app/celery_app.py
touch app/dependencies.py
touch app/exceptions.py
touch app/i18n.py

# Create model files
touch app/models/base.py
touch app/models/user.py
touch app/models/guardian.py
touch app/models/panic.py
touch app/models/trip.py
touch app/models/subscription.py

# Create schema files
touch app/schemas/user.py
touch app/schemas/guardian.py
touch app/schemas/panic.py
touch app/schemas/trip.py
touch app/schemas/location.py
touch app/schemas/telegram.py

# Create API files
touch app/api/deps.py
touch app/api/v1/panic.py
touch app/api/v1/trips.py
touch app/api/v1/guardians.py
touch app/api/v1/users.py
touch app/api/webhooks/telegram.py
touch app/api/webhooks/twilio.py
touch app/api/webhooks/sms_reply.py

# Create service files (SEPARATED)
touch app/services/panic.py
touch app/services/trip.py
touch app/services/notification.py
touch app/services/guardian.py
touch app/services/location.py
touch app/services/subscription.py

# Create integration files
touch app/integrations/communication/base.py
touch app/integrations/communication/manager.py
touch app/integrations/communication/twilio.py
touch app/integrations/communication/mock.py
touch app/integrations/telegram/bot.py
touch app/integrations/telegram/handlers.py
touch app/integrations/telegram/keyboards.py

# Create task files (SEPARATED by context - CRITICAL for v3.1)
touch app/tasks/panic_alerts.py      # ONLY panic-related tasks
touch app/tasks/trip_reminders.py    # ONLY trip-related tasks  
touch app/tasks/notifications.py     # General notification tasks
touch app/tasks/cleanup.py           # Maintenance tasks

# Create utility files
touch app/utils/security.py
touch app/utils/geo.py
touch app/utils/validators.py

# Create configuration files
touch requirements.txt
touch requirements-dev.txt
touch .env.example
touch .env.local
touch .gitignore
touch Dockerfile
touch docker-compose.yml
touch alembic.ini
touch pytest.ini
touch fly.toml
touch fly.staging.toml

echo "✅ Project structure created successfully!"
echo ""
echo "📂 Key Architecture Components Created:"
echo "   🚨 app/services/panic.py - Independent panic logic"
echo "   🛣️  app/services/trip.py - Independent trip logic" 
echo "   ⚙️  app/config/settings.py - Settings factory pattern"
echo "   📡 app/tasks/panic_alerts.py - Panic-specific tasks"
echo "   📡 app/tasks/trip_reminders.py - Trip-specific tasks"
echo ""
echo "🎯 Next steps:"
echo "1. Set up Python virtual environment"
echo "2. Install dependencies" 
echo "3. Configure environment variables (4 environments)"
echo "4. Initialize database with separation schema"
echo "5. Test panic + trip separation logic"

# Make the script executable
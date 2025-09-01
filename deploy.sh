#!/bin/bash

# Krill Deployment Script for DigitalOcean App Platform
# This script helps deploy your Django app with the correct configuration

set -e

echo "🚀 Krill Deployment Script for DigitalOcean App Platform"
echo "========================================================"

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI tool not found. Please install it first:"
    echo "   https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Check if user is authenticated
if ! doctl account get &> /dev/null; then
    echo "❌ Not authenticated with DigitalOcean. Please run:"
    echo "   doctl auth init"
    exit 1
fi

echo "✅ Authenticated with DigitalOcean"

# Get app ID from user
read -p "Enter your DigitalOcean App ID: " APP_ID

if [ -z "$APP_ID" ]; then
    echo "❌ App ID is required"
    exit 1
fi

echo "📱 Using App ID: $APP_ID"

# Check if app exists
if ! doctl apps get "$APP_ID" &> /dev/null; then
    echo "❌ App with ID $APP_ID not found"
    exit 1
fi

echo "✅ App found"

# Set required environment variables
echo "🔧 Setting required environment variables..."

doctl apps update "$APP_ID" --set-env-vars \
    DATABASE_ENGINE=postgresql \
    DJANGO_DEBUG=False \
    DJANGO_SETTINGS_MODULE=krill.settings_production \
    ENVIRONMENT=production \
    DB_SSLMODE=require

echo "✅ Environment variables set"

# Get current app configuration
echo "📋 Current app configuration:"
doctl apps get "$APP_ID" --format YAML | grep -A 20 "services:" | head -20

echo ""
echo "🔍 Checking for common issues..."

# Check if database is bound
if doctl apps get "$APP_ID" --format YAML | grep -q "db:"; then
    echo "✅ Database is bound"
else
    echo "⚠️  Database is not bound. Please bind a PostgreSQL database in the DO Console:"
    echo "   1. Go to your app in DO Console"
    echo "   2. Click 'Settings' → 'Resources'"
    echo "   3. Click 'Link Resource' → 'Database'"
    echo "   4. Select PostgreSQL and choose a plan"
fi

# Check if DJANGO_SECRET_KEY is set
if doctl apps get "$APP_ID" --format YAML | grep -q "DJANGO_SECRET_KEY"; then
    echo "✅ DJANGO_SECRET_KEY is set"
else
    echo "⚠️  DJANGO_SECRET_KEY is not set. Please set it:"
    echo "   doctl apps update $APP_ID --set-env-vars DJANGO_SECRET_KEY=your-secret-key"
fi

echo ""
echo "🚀 Ready to deploy! Run the following command to deploy:"
echo "   doctl apps create-deployment $APP_ID"
echo ""
echo "📊 Monitor deployment with:"
echo "   doctl apps logs $APP_ID --follow"
echo ""
echo "🔍 Check app status with:"
echo "   doctl apps get $APP_ID"

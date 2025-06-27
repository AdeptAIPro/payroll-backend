#!/usr/bin/env python3
"""
Setup script to create .env file from template
"""
import os
import shutil

def setup_env_file():
    """Create .env file from env.template if it doesn't exist"""
    template_path = "env.template"
    env_path = ".env"
    
    if os.path.exists(env_path):
        print(f"✅ .env file already exists at {env_path}")
        return
    
    if not os.path.exists(template_path):
        print(f"❌ Template file {template_path} not found!")
        return
    
    try:
        shutil.copy2(template_path, env_path)
        print(f"✅ Created .env file from {template_path}")
        print("📝 Please review and update the values in .env file as needed")
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

if __name__ == "__main__":
    setup_env_file() 
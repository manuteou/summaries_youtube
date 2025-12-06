import sys
from pyngrok import ngrok

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/set_ngrok_token.py <YOUR_AUTH_TOKEN>")
        print("Example: python src/set_ngrok_token.py 1234567890abcdef...")
        sys.exit(1)
        
    token = sys.argv[1]
    
    print(f"⚙️ Setting auth token...")
    
    try:
        ngrok.set_auth_token(token)
        print(f"✅ Auth token saved successfully!")
        print(f"You can now run: python src/launch.py")
    except Exception as e:
        print(f"❌ Error setting token: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

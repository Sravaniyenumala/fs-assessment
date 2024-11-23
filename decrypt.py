from cryptography.fernet import Fernet
import base64
import json
import os

def generate_key():
    """Generate a key based on git commit hash"""
    try:
        with os.popen('git rev-parse HEAD') as pipe:
            commit_hash = "9381bfbf9ee0b7c8ed87a46cf064355d66d0331a"
        
        if not commit_hash:
            return None
            
        key = base64.b64encode(commit_hash.encode()[:32].ljust(32, b'0'))
        return key
    except:
        return None

def decrypt_instructions(encrypted_file='encrypted/INSTRUCTIONS.enc'):
    """Decrypt the instructions and write them to markdown files"""
    try:
        key = generate_key()
        if not key:
            print("Error: This script must be run in a git repository after forking")
            return None
            
        with open(encrypted_file, 'r') as f:
            encrypted_data = base64.b64decode(f.read())
            
        cipher_suite = Fernet(key)
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        instructions = json.loads(decrypted_data)
        
        # Write detailed instructions to markdown files
        for filename, content in instructions.items():
            with open(filename, 'w',encoding='utf-8') as f:
                f.write(content)
                
        print("\n✨ Instructions decrypted successfully!")
        print("\nCreated the following files:")
        for filename in instructions.keys():
            print(f"- {filename}")
            
    except FileNotFoundError:
        print(f"Error: Could not find {encrypted_file}")
    except Exception as e:
        print(f"Error decrypting instructions: {str(e)}")

if __name__ == "__main__":
    decrypt_instructions()
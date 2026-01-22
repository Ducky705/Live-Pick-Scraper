import webview
import time
import json
import os
import sys

# File to save cookies
COOKIES_PATH = "twitter_cookies.json"

def check_cookies(window):
    print("Waiting for login...")
    failed_attempts = 0
    while True:
        try:
            cookies = window.get_cookies()
            cookie_dict = {}
            
            # Handle list of dicts or strings
            if isinstance(cookies, list):
                for c in cookies:
                    # Convert to string to be safe
                    s = str(c)
                    
                    # Parse "Set-Cookie: key=value; args"
                    if 'Set-Cookie:' in s:
                        # Remove prefix
                        s = s.replace('Set-Cookie:', '').strip()
                    
                    # Take the first part before semicolon as key=value
                    # e.g. "auth_token=12345; Path=/..." -> "auth_token=12345"
                    if ';' in s:
                        first_part = s.split(';', 1)[0]
                    else:
                        first_part = s
                        
                    if '=' in first_part:
                        k, v = first_part.split('=', 1)
                        cookie_dict[k.strip()] = v.strip()

            # Check for tokens
            if 'auth_token' in cookie_dict:
                print(f"[DEBUG] Found auth_token: {cookie_dict['auth_token'][:5]}...")
            
            if 'auth_token' in cookie_dict and 'ct0' in cookie_dict:
                print("\nSUCCESS! Authentication tokens detected.")
                
                with open(COOKIES_PATH, 'w') as f:
                    json.dump(cookie_dict, f, indent=2)
                
                print(f"Cookies saved to {COOKIES_PATH}")
                print("Closing window in 3 seconds...")
                time.sleep(3)
                window.destroy()
                break
            else:
                 failed_attempts += 1
                 if failed_attempts % 5 == 0:
                     print(f"[DEBUG] Waiting... found {len(cookie_dict)} cookies.")
            
        except Exception as e:
            print(f"[ERROR] Exception checking cookies: {e}")
            pass
        
        time.sleep(2)

def main():
    window = webview.create_window('Twitter Login - Please Log In', 'https://x.com/login', width=600, height=900)
    webview.start(func=check_cookies, args=(window,), debug=True, private_mode=False)

if __name__ == '__main__':
    main()

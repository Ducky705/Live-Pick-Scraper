
import sys
import os

# Add project root
sys.path.append(os.getcwd())

def verify():
    print("--- Verifying Optimizations ---")
    
    # 1. Verify Aliases
    try:
        from src.team_aliases import TEAM_ALIASES
        print(f"✅ TEAM_ALIASES loaded. Total entries: {len(TEAM_ALIASES)}")
        
        # Check for specific improvements
        checks = ["orlando magic", "phoenix suns", "miami heat"]
        for team in checks:
            aliases = TEAM_ALIASES.get(team, [])
            print(f"   {team}: {aliases}")
            
        # Check if we have the "short" codes we missed before
        # e.g. for Orlando (magic), did we get "ORL"?
        # Notes: The generator script puts them in the list.
        # Let's check 'orlando magic'
        magic_aliases = [a.lower() for a in TEAM_ALIASES.get("orlando magic", [])]
        if "orl" in magic_aliases:
            print("✅ Found 'ORL' alias for Orlando Magic")
        else:
            print("❌ 'ORL' alias missing for Orlando Magic")
            
    except Exception as e:
        print(f"❌ Alias verification failed: {e}")

    # 2. Verify Score Fetcher
    try:
        from src.score_fetcher import LEAGUES_TO_SCRAPE
        if "rugby" in LEAGUES_TO_SCRAPE and "boxing" in LEAGUES_TO_SCRAPE:
             print("✅ Score Fetcher has Rugby and Boxing")
        else:
             print("❌ Score Fetcher missing new sports")
    except Exception as e:
        print(f"❌ Score Fetcher verification failed: {e}")

    # 3. Verify Constants
    try:
        from src.grading.constants import ESPN_LEAGUE_MAP, LEAGUE_ALIASES_MAP
        if "rugby" in ESPN_LEAGUE_MAP and "boxing" in ESPN_LEAGUE_MAP:
            print("✅ Constants have Rugby and Boxing in ESPN_LEAGUE_MAP")
        else:
            print("❌ Constants missing new sports in ESPN_LEAGUE_MAP")
            
        if LEAGUE_ALIASES_MAP.get("rugby") == "rugby":
            print("✅ Constants have Rugby in LEAGUE_ALIASES_MAP")
        else:
            print("❌ Constants missing new sports in LEAGUE_ALIASES_MAP")
            
    except Exception as e:
         print(f"❌ Constants verification failed: {e}")

if __name__ == "__main__":
    verify()

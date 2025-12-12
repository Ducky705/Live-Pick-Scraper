import re
from typing import Optional
import config

# ==============================================================================
# LEAGUE KEYWORDS DATABASE (The "Brain")
# ==============================================================================

LEAGUE_KEYWORDS = {
    'NFL': [
        'Lions', 'Chiefs', 'Bills', 'Eagles', '49ers', 'Ravens', 'Cowboys', 'Bengals', 
        'Dolphins', 'Browns', 'Texans', 'Jaguars', 'Steelers', 'Colts', 'Seahawks', 
        'Buccaneers', 'Packers', 'Rams', 'Falcons', 'Saints', 'Vikings', 'Bears', 
        'Raiders', 'Broncos', 'Chargers', 'Giants', 'Commanders', 'Titans', 'Cardinals', 
        'Panthers', 'Patriots', 'Jets', 'Niners', 'Bucs', 'Pats', 'Commies', 'G-Men'
    ],
    'NBA': [
        'Celtics', 'Nuggets', 'Bucks', 'Timberwolves', 'Thunder', 'Clippers', 'Suns', 
        'Knicks', 'Cavaliers', 'Magic', 'Sixers', '76ers', 'Pacers', 'Heat', 'Kings', 
        'Mavericks', 'Lakers', 'Warriors', 'Pelicans', 'Rockets', 'Grizzlies', 'Hawks', 
        'Nets', 'Jazz', 'Bulls', 'Raptors', 'Hornets', 'Wizards', 'Pistons', 'Spurs', 
        'Trail Blazers', 'Blazers', 'Cavs', 'Mavs', 'Wolves', 'T-Wolves'
    ],
    'NHL': [
        'Bruins', 'Rangers', 'Stars', 'Canucks', 'Panthers', 'Avalanche', 'Jets', 
        'Oilers', 'Hurricanes', 'Maple Leafs', 'Leafs', 'Golden Knights', 'Knights', 
        'Predators', 'Preds', 'Kings', 'Lightning', 'Bolts', 'Red Wings', 'Wings', 
        'Blues', 'Flyers', 'Capitals', 'Caps', 'Islanders', 'Isles', 'Devils', 
        'Flames', 'Kraken', 'Penguins', 'Pens', 'Wild', 'Sabres', 'Senators', 'Sens', 
        'Coyotes', 'Utah HC', 'Utah Mammoth', 'Canadiens', 'Habs', 'Blackhawks', 
        'Hawks', 'Ducks', 'Blue Jackets', 'Jackets', 'Sharks'
    ],
    'MLB': [
        'Yankees', 'Dodgers', 'Orioles', 'Phillies', 'Braves', 'Guardians', 'Brewers', 
        'Padres', 'Royals', 'Twins', 'Astros', 'Mariners', 'Diamondbacks', 'D-Backs', 
        'Mets', 'Rays', 'Red Sox', 'Tigers', 'Cubs', 'Giants', 'Reds', 'Cardinals', 
        'Blue Jays', 'Jays', 'Pirates', 'Nationals', 'Nats', 'Angels', 'Rangers', 
        'Marlins', 'Rockies', 'Athletics', "A's", 'White Sox', 'Guardians'
    ],
    'NCAAF': [
        # --- SEC ---
        'Alabama', 'Bama', 'Crimson Tide', 'Georgia', 'Bulldogs', 'Texas', 'Longhorns', 
        'Oklahoma', 'Sooners', 'LSU', 'Tigers', 'Ole Miss', 'Rebels', 'Missouri', 'Mizzou', 
        'Tennessee', 'Vols', 'Volunteers', 'Kentucky', 'Wildcats', 'Florida', 'Gators', 
        'Auburn', 'Texas A&M', 'Aggies', 'South Carolina', 'Gamecocks', 'Arkansas', 
        'Razorbacks', 'Mississippi State', 'Bulldogs', 'Vanderbilt', 'Commodores',
        # --- Big Ten ---
        'Ohio State', 'Buckeyes', 'Michigan', 'Wolverines', 'Penn State', 'Nittany Lions', 
        'Oregon', 'Ducks', 'USC', 'Trojans', 'Washington', 'Huskies', 'UCLA', 'Bruins', 
        'Nebraska', 'Cornhuskers', 'Wisconsin', 'Badgers', 'Iowa', 'Hawkeyes', 
        'Michigan State', 'Spartans', 'Minnesota', 'Gophers', 'Illinois', 'Illini', 
        'Purdue', 'Boilermakers', 'Northwestern', 'Wildcats', 'Maryland', 'Terps', 
        'Rutgers', 'Scarlet Knights', 'Indiana', 'Hoosiers',
        # --- ACC ---
        'Clemson', 'Tigers', 'Miami', 'Canes', 'Hurricanes', 'Florida State', 'FSU', 
        'Seminoles', 'SMU', 'Mustangs', 'Louisville', 'Cardinals', 'North Carolina', 
        'UNC', 'Tar Heels', 'Virginia Tech', 'Hokies', 'Georgia Tech', 'Yellow Jackets', 
        'NC State', 'Wolfpack', 'Pitt', 'Pittsburgh', 'Panthers', 'Syracuse', 'Orange', 
        'Duke', 'Blue Devils', 'Virginia', 'Cavaliers', 'Wahoos', 'Wake Forest', 
        'Demon Deacons', 'Boston College', 'Eagles', 'Cal', 'Bears', 'Stanford', 'Cardinal',
        # --- Big 12 ---
        'Utah', 'Utes', 'Kansas State', 'Wildcats', 'Oklahoma State', 'Cowboys', 
        'Iowa State', 'Cyclones', 'BYU', 'Cougars', 'Colorado', 'Buffaloes', 'TCU', 
        'Horned Frogs', 'Texas Tech', 'Red Raiders', 'Baylor', 'Bears', 'Kansas', 
        'Jayhawks', 'West Virginia', 'Mountaineers', 'UCF', 'Knights', 'Cincinnati', 
        'Bearcats', 'Arizona', 'Wildcats', 'Arizona State', 'Sun Devils', 'Houston', 'Cougars',
        # --- Group of 5 & Independents ---
        'Notre Dame', 'Fighting Irish', 'Boise State', 'Broncos', 'UNLV', 'Rebels', 
        'Liberty', 'Flames', 'Tulane', 'Green Wave', 'Memphis', 'Tigers', 'USF', 'Bulls', 
        'James Madison', 'JMU', 'Dukes', 'App State', 'Appalachian State', 'Mountaineers', 
        'Coastal Carolina', 'Chanticleers', 'Louisiana', 'Ragin Cajuns', 'Troy', 'Trojans', 
        'South Alabama', 'Jaguars', 'Arkansas State', 'Red Wolves', 'Texas State', 'Bobcats', 
        'Georgia Southern', 'Eagles', 'Marshall', 'Thundering Herd', 'Old Dominion', 
        'Monarchs', 'Georgia State', 'Panthers', 'Toledo', 'Rockets', 'Miami (OH)', 
        'Miami OH', 'RedHawks', 'Ohio', 'Bobcats', 'Bowling Green', 'Falcons', 
        'Northern Illinois', 'Huskies', 'Western Michigan', 'Broncos', 'Central Michigan', 
        'Chippewas', 'Eastern Michigan', 'Eagles', 'Buffalo', 'Bulls', 'Kent State', 
        'Golden Flashes', 'Akron', 'Zips', 'Ball State', 'Cardinals', 'Fresno State', 
        'Bulldogs', 'San Diego State', 'Aztecs', 'San Jose State', 'Spartans', 'Air Force', 
        'Falcons', 'Wyoming', 'Cowboys', 'Colorado State', 'Rams', 'New Mexico', 'Lobos', 
        'Utah State', 'Aggies', 'Nevada', 'Wolf Pack', 'Hawaii', 'Rainbow Warriors', 
        'Army', 'Black Knights', 'Navy', 'Midshipmen', 'UConn', 'Huskies', 'UMass', 
        'Minutemen', 'Oregon State', 'Beavers', 'Washington State', 'Cougars', 'Wazzu', 
        'North Texas', 'Mean Green', 'UTSA', 'Roadrunners', 'Rice', 'Owls', 'UAB', 
        'Blazers', 'FAU', 'Owls', 'Charlotte', '49ers', 'Tulsa', 'Golden Hurricane', 
        'East Carolina', 'Pirates', 'Temple', 'Owls', 'Western Kentucky', 'WKU', 
        'Hilltoppers', 'Middle Tennessee', 'Blue Raiders', 'Sam Houston', 'Bearkats', 
        'Jacksonville State', 'Jax State', 'Gamecocks', 'FIU', 'Panthers', 'UTEP', 
        'Miners', 'New Mexico State', 'Aggies', 'Kennesaw State', 'Owls'
    ],
    'NCAAB': [
        # --- Power 6 + Gonzaga/Dayton/SDSU ---
        'Gonzaga', 'Zags', 'UConn', 'Huskies', 'Houston', 'Cougars', 'Purdue', 
        'Boilermakers', 'Arizona', 'Wildcats', 'Marquette', 'Golden Eagles', 'Creighton', 
        'Bluejays', 'North Carolina', 'Tar Heels', 'Duke', 'Blue Devils', 'Kansas', 
        'Jayhawks', 'Auburn', 'Tigers', 'Tennessee', 'Vols', 'Illinois', 'Illini', 
        'Baylor', 'Bears', 'Iowa State', 'Cyclones', 'Kentucky', 'Wildcats', 'Saint Marys', 
        'St Marys', 'Gaels', 'San Diego State', 'Aztecs', 'Dayton', 'Flyers', 
        'Florida Atlantic', 'FAU', 'Owls', 'Michigan State', 'Spartans', 'Villanova', 
        'Wildcats', 'Virginia', 'Cavaliers', 'Wisconsin', 'Badgers', 'Texas', 'Longhorns', 
        'Texas Tech', 'Red Raiders', 'Texas A&M', 'Aggies', 'TCU', 'Horned Frogs', 
        'Clemson', 'Tigers', 'Colorado', 'Buffaloes', 'Utah', 'Utes', 'Nevada', 
        'Wolf Pack', 'Boise State', 'Broncos', 'New Mexico', 'Lobos', 'Utah State', 
        'Aggies', 'UNLV', 'Rebels', 'Colorado State', 'Rams', 'Providence', 'Friars', 
        'Seton Hall', 'Pirates', 'St Johns', 'St. Johns', 'Red Storm', 'Xavier', 
        'Musketeers', 'Butler', 'Bulldogs', 'Georgetown', 'Hoyas', 'Memphis', 'Tigers', 
        'North Texas', 'Mean Green', 'UAB', 'Blazers', 'South Florida', 'Bulls', 'VCU', 
        'Rams', 'St Bonaventure', 'Bonnies', 'Richmond', 'Spiders', 'Loyola Chicago', 
        'Ramblers', 'Drake', 'Bulldogs', 'Bradley', 'Braves', 'Indiana State', 'Sycamores', 
        'Northern Iowa', 'Panthers', 'Grand Canyon', 'Lopes', 'San Francisco', 'Dons', 
        'Santa Clara', 'Broncos', 'Princeton', 'Tigers', 'Yale', 'Bulldogs', 'Cornell', 
        'Big Red', 'McNeese', 'Cowboys', 'Samford', 'Bulldogs', 'Vermont', 'Catamounts', 
        'Colgate', 'Raiders', 'Charleston', 'Cougars', 'UNC Wilmington', 'UNCW', 
        'Seahawks', 'Drexel', 'Dragons', 'Hofstra', 'Pride', 'Delaware', 'Blue Hens', 
        'Towson', 'Tigers', 'High Point', 'Panthers', 'Winthrop', 'Eagles', 'Longwood', 
        'Lancers', 'Morehead State', 'Eagles', 'Quinnipiac', 'Bobcats', 'Iona', 'Gaels', 
        'Saint Peters', 'Peacocks', 'Fairfield', 'Stags', 'Marist', 'Red Foxes', 'Siena', 
        'Saints', 'Rider', 'Broncs', 'Manhattan', 'Jaspers', 'Mount St Marys', 'The Mount', 
        'Niagara', 'Purple Eagles', 'Canisius', 'Golden Griffins', 'Merrimack', 'Warriors', 
        'Sacred Heart', 'Pioneers', 'Wagner', 'Seahawks', 'LIU', 'Sharks', 'Le Moyne', 
        'Dolphins', 'Stonehill', 'Skyhawks', 'Saint Francis', 'Red Flash', 'CCSU', 
        'Blue Devils', 'Duquesne', 'Dukes', 'George Mason', 'Patriots', 'George Washington', 
        'Colonials', 'La Salle', 'Explorers', 'UMass', 'Minutemen', 'Rhode Island', 'Rams', 
        'Saint Josephs', 'St Joes', 'Hawks', 'Saint Louis', 'Billikens', 'Davidson', 
        'Wildcats', 'Fordham', 'Rams', 'Loyola Marymount', 'LMU', 'Lions', 'Pacific', 
        'Tigers', 'Pepperdine', 'Waves', 'Portland', 'Pilots', 'San Diego', 'Toreros', 
        'Akron', 'Zips', 'Ohio', 'Bobcats', 'Toledo', 'Rockets', 'Kent State', 
        'Golden Flashes', 'Bowling Green', 'Falcons', 'Miami OH', 'RedHawks', 
        'Central Michigan', 'Chippewas', 'Western Michigan', 'Broncos', 'Northern Illinois', 
        'Huskies', 'Ball State', 'Cardinals', 'Eastern Michigan', 'Eagles', 'Buffalo', 
        'Bulls', 'Furman', 'Paladins', 'UNC Greensboro', 'Spartans', 'Western Carolina', 
        'Catamounts', 'ETSU', 'Buccaneers', 'Samford', 'Bulldogs', 'Chattanooga', 'Mocs', 
        'Mercer', 'Bears', 'Wofford', 'Terriers', 'The Citadel', 'Bulldogs', 'VMI', 
        'Keydets', 'Liberty', 'Flames', 'Louisiana Tech', 'Bulldogs', 'Western Kentucky', 
        'Hilltoppers', 'Sam Houston', 'Bearkats', 'Middle Tennessee', 'Blue Raiders', 
        'UTEP', 'Miners', 'New Mexico State', 'Aggies', 'FIU', 'Panthers', 
        'Jacksonville State', 'Gamecocks', 'Kennesaw State', 'Owls'
    ],
    'EPL': [
        'Man City', 'Manchester City', 'Arsenal', 'Gunners', 'Liverpool', 'Reds', 
        'Aston Villa', 'Tottenham', 'Spurs', 'Chelsea', 'Blues', 'Newcastle', 'Magpies', 
        'Man Utd', 'Manchester United', 'Red Devils', 'West Ham', 'Hammers', 
        'Crystal Palace', 'Eagles', 'Brighton', 'Seagulls', 'Bournemouth', 'Cherries', 
        'Fulham', 'Cottagers', 'Wolves', 'Wolverhampton', 'Everton', 'Toffees', 
        'Brentford', 'Bees', 'Nottm Forest', 'Nottingham', 'Luton', 'Hatters', 
        'Burnley', 'Clarets', 'Sheffield Utd', 'Blades', 'Leicester', 'Foxes', 
        'Leeds', 'Southampton', 'Saints', 'Ipswich'
    ],
    'UCL': [
        # --- La Liga ---
        'Real Madrid', 'Barcelona', 'Barca', 'Atletico Madrid', 'Atleti', 'Girona', 
        'Athletic Club', 'Bilbao', 'Real Sociedad', 'Betis', 'Sevilla', 'Valencia', 
        'Villarreal',
        # --- Bundesliga ---
        'Bayern Munich', 'Bayern', 'Dortmund', 'BVB', 'Leverkusen', 'Leipzig', 
        'Stuttgart', 'Frankfurt', 'Wolfsburg', 'Gladbach',
        # --- Serie A ---
        'Inter Milan', 'Inter', 'AC Milan', 'Milan', 'Juventus', 'Juve', 'Bologna', 
        'Atalanta', 'Roma', 'Lazio', 'Napoli', 'Fiorentina',
        # --- Ligue 1 ---
        'PSG', 'Paris SG', 'Monaco', 'Lille', 'Brest', 'Nice', 'Lens', 'Marseille', 
        'Lyon',
        # --- Other Euro Giants ---
        'Benfica', 'Sporting CP', 'Porto', 'Feyenoord', 'PSV', 'Ajax', 'Celtic', 
        'Rangers', 'Galatasaray', 'Fenerbahce', 'Shakhtar', 'Salzburg'
    ],
    'MLS': [
        'Inter Miami', 'Messi', 'Cincinnati', 'Columbus Crew', 'LAFC', 'LA Galaxy', 
        'Orlando City', 'Philadelphia Union', 'Real Salt Lake', 'Seattle Sounders', 
        'St Louis City', 'Atlanta United', 'Nashville SC', 'New England Revolution', 
        'NY Red Bulls', 'NYCFC', 'Houston Dynamo', 'Vancouver Whitecaps', 'Portland Timbers',
        'Sporting KC', 'Minnesota United', 'Charlotte FC', 'Austin FC', 'FC Dallas'
    ],
    'WNBA': [
        'Aces', 'Liberty', 'Sun', 'Lynx', 'Storm', 'Mercury', 'Fever', 'Dream', 
        'Mystics', 'Sky', 'Wings', 'Sparks', 'Caitlin Clark', 'Angel Reese'
    ],
    'UFC': [
        'Makhachev', 'Jones', 'Pereira', 'Topuria', "O'Malley", 'Strickland', 
        'Du Plessis', 'Edwards', 'Aspinall', 'Pantoja', 'Grasso', 'Zhang', 'Shevchenko', 
        'Nunes', 'McGregor', 'Poirier', 'Gaethje', 'Oliveira', 'Holloway', 'Volkanovski', 
        'Adesanya', 'Whittaker', 'Chimaev', 'Usman', 'Covington', 'Muhammad', 
        'Rakhmonov', 'Ankalaev', 'Prochazka', 'Hill', 'Blaydes', 'Gane', 'Almeida', 
        'Merab', 'Dvalishvili', 'Sterling', 'Yan', 'Sandhagen', 'Nurmagomedov', 
        'Gamrot', 'Tsarukyan', 'Chandler', 'Dariush', 'Fiziev', 'Burns', 'Brady', 
        'Holland', 'Wonderboy', 'Costa', 'Cannonier', 'Imavov', 'Allen', 'Evloev', 
        'Mitchell', 'Lopes', 'Ortega', 'Rodriguez', 'Kattar', 'Emmett', 'Chikadze', 
        'Figueiredo', 'Garbrandt', 'Cejudo', 'Albazi', 'Royval', 'Kara-France', 
        'Namajunas', 'Suarez', 'Blanchfield', 'Fiorot', 'Barber', 'Harrison', 'Pena'
    ],
    'TENNIS': [
        'Djokovic', 'Alcaraz', 'Sinner', 'Medvedev', 'Zverev', 'Rublev', 'Rune', 
        'Hurkacz', 'Ruud', 'Dimitrov', 'Tsitsipas', 'De Minaur', 'Fritz', 'Paul', 
        'Shelton', 'Tiafoe', 'Nadal', 'Murray', 'Swiatek', 'Sabalenka', 'Gauff', 
        'Rybakina', 'Pegula', 'Jabeur', 'Vondrousova', 'Zheng', 'Sakkari', 'Ostapenko', 
        'Collins', 'Navarro', 'Raducanu', 'Osaka', 'Wimbledon', 'Roland Garros', 'US Open'
    ],
    'PGA': [
        'Scheffler', 'McIlroy', 'Schauffele', 'Wyndham Clark', 'Hovland', 'Morikawa', 
        'Aberg', 'Cantlay', 'Homa', 'Harman', 'Fitzpatrick', 'Fleetwood', 'Matsuyama', 
        'Spieth', 'Thomas', 'Koepka', 'Rahm', 'DeChambeau', 'Smith', 'Mickelson', 
        'Johnson', 'Woods', 'Masters', 'PGA Championship', 'Ryder Cup'
    ],
    'F1': [
        'Verstappen', 'Perez', 'Red Bull', 'Hamilton', 'Russell', 'Mercedes', 
        'Leclerc', 'Sainz', 'Ferrari', 'Norris', 'Piastri', 'McLaren', 'Alonso', 
        'Stroll', 'Aston Martin', 'Gasly', 'Ocon', 'Alpine', 'Albon', 'Sargeant', 
        'Williams', 'Tsunoda', 'Ricciardo', 'RB', 'Bottas', 'Zhou', 'Sauber', 
        'Hulkenberg', 'Magnussen', 'Haas', 'Grand Prix'
    ]
}

def standardize_league(val: str) -> str:
    if not val: return 'Other'
    val = val.upper().strip()
    if val in config.LEAGUE_MAP: return config.LEAGUE_MAP[val]
    
    aliases = {
        'NCAA FOOTBALL': 'NCAAF', 'CFB': 'NCAAF', 'COLLEGE FOOTBALL': 'NCAAF',
        'NCAA BASKETBALL': 'NCAAB', 'CBB': 'NCAAB', 'COLLEGE BASKETBALL': 'NCAAB', 
        'COLLEGE HOOPS': 'NCAAB', 'NCAAM': 'NCAAB', 'CBK': 'NCAAB',
        'PREMIER LEAGUE': 'EPL', 'CHAMPIONS LEAGUE': 'UCL', 'LA LIGA': 'UCL', 
        'BUNDESLIGA': 'UCL', 'SERIE A': 'UCL', 'LIGUE 1': 'UCL', 'EURO SOCCER': 'UCL',
        'MMA': 'UFC', 'FIGHTING': 'UFC', 'BOXING': 'UFC',
        'KBO': 'MLB', 'NPB': 'MLB',
        'FORMULA 1': 'F1', 'FORMULA ONE': 'F1',
        'GOLF': 'PGA', 'PGA TOUR': 'PGA',
        'TENNIS': 'TENNIS', 'ATP': 'TENNIS', 'WTA': 'TENNIS'
    }
    
    # Check aliases
    if val in aliases: return aliases[val]
    
    # Check partial matches (e.g. "MEN'S CBB")
    for alias, standard in aliases.items():
        if alias in val:
            return standard
            
    return 'Other'

def standardize_bet_type(val: str) -> str:
    if not val: return 'Unknown'
    val = val.upper().strip()
    mapping = {
        'MONEYLINE': 'Moneyline', 'ML': 'Moneyline', 'M/L': 'Moneyline', 'WIN': 'Moneyline',
        'SPREAD': 'Spread', 'POINT SPREAD': 'Spread', 'RUN LINE': 'Spread', 
        'PUCK LINE': 'Spread', 'ATS': 'Spread', 'HANDICAP': 'Spread',
        'TOTAL': 'Total', 'OVER/UNDER': 'Total', 'O/U': 'Total',
        'PLAYER PROP': 'Player Prop', 'PROP': 'Player Prop', 'PRA': 'Player Prop',
        'TEAM PROP': 'Team Prop', 'GAME PROP': 'Game Prop', 
        'TT': 'Team Prop', 'TTU': 'Team Prop', 'TTO': 'Team Prop',
        'PARLAY': 'Parlay', 'TEASER': 'Teaser', 'SGP': 'Parlay',
        'FUTURE': 'Future', 'TO WIN': 'Future', 'OUTRIGHT': 'Future',
        'PERIOD': 'Period', 'QUARTER': 'Period', 'HALF': 'Period', 
        '1H': 'Period', '1Q': 'Period', '2H': 'Period', '2Q': 'Period',
        'YRFI': 'Game Prop', 'NRFI': 'Game Prop',
        'ANYTIME TD': 'Player Prop', 'ATD': 'Player Prop'
    }
    for k, v in mapping.items():
        if k in val: return v
    return 'Unknown'

def _smart_title_case(text: str) -> str:
    if not text: return ""
    text = text.title()
    
    # Fix specific casing issues for acronyms and common abbreviations
    replacements = {
        # Leagues / Sports
        r'\bMl\b': 'ML', r'\bNfl\b': 'NFL', r'\bNba\b': 'NBA', r'\bMlb\b': 'MLB',
        r'\bNhl\b': 'NHL', r'\bNcaaf\b': 'NCAAF', r'\bNcaab\b': 'NCAAB',
        r'\bUfc\b': 'UFC', r'\bWnba\b': 'WNBA', r'\bMls\b': 'MLS',
        r'\bPga\b': 'PGA', r'\bAtp\b': 'ATP', r'\bWta\b': 'WTA',
        
        # Stats / Props
        r'\bPra\b': 'PRA', r'\bSog\b': 'SOG', r'\bTtu\b': 'TTU', r'\bTto\b': 'TTO',
        r'\bAtt\b': 'ATT', r'\bYds\b': 'Yds', r'\bTds\b': 'TDs', r'\bTd\b': 'TD',
        r'\bPts\b': 'Pts', r'\bReb\b': 'Reb', r'\bAst\b': 'Ast',
        r'\bYrfi\b': 'YRFI', r'\bNrfi\b': 'NRFI', r'\bSgp\b': 'SGP',
        r'\bAtd\b': 'Anytime TD', r'\bAnytime Td\b': 'Anytime TD',
        
        # Periods
        r'\b1H\b': '1H', r'\b2H\b': '2H', r'\b1Q\b': '1Q', r'\b2Q\b': '2Q',
        r'\b3Q\b': '3Q', r'\b4Q\b': '4Q', r'\bOt\b': 'OT',
        
        # Schools / Teams / Locations
        r'\bVs\b': 'vs', r'\bJmu\b': 'JMU', r'\bTcu\b': 'TCU', r'\bUnlv\b': 'UNLV', 
        r'\bEtsu\b': 'ETSU', r'\bLa\b': 'LA', r'\bNy\b': 'NY', r'\bKc\b': 'KC', 
        r'\bUsc\b': 'USC', r'\bLsu\b': 'LSU', r'\bByu\b': 'BYU', r'\bUcf\b': 'UCF',
        r'\bSmu\b': 'SMU', r'\bUcla\b': 'UCLA', r'\bUnc\b': 'UNC', r'\bUtep\b': 'UTEP',
        r'\bUtsa\b': 'UTSA', r'\bFau\b': 'FAU', r'\bFiu\b': 'FIU', r'\bUab\b': 'UAB',
        r'\bVcu\b': 'VCU', r'\bUconn\b': 'UConn', r'\bUmass\b': 'UMass',
        r'\bPsg\b': 'PSG', r'\bOm\b': 'OM', r'\bBvb\b': 'BVB', r'\bPsv\b': 'PSV',
        r'\bUncw\b': 'UNCW', r'\bCcsu\b': 'CCSU', r'\bLiu\b': 'LIU', r'\bLmu\b': 'LMU',
        r'\bVmi\b': 'VMI', r'\bWku\b': 'WKU', r'\bNc\b': 'NC', r'\bSt\b': 'St.',
        r'\bA&M\b': 'A&M', r'\bA&T\b': 'A&T'
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return text

def format_pick_value(pick: str, bet_type: str, league: str) -> str:
    if not pick: return "Unknown Pick"
    pick = pick.strip()
    pick = _smart_title_case(pick)
    
    if bet_type == 'Unknown': return pick

    if bet_type == 'Moneyline':
        clean = re.sub(r'\bML\b|\bMoneyline\b', '', pick, flags=re.I).strip()
        return f"{clean} ML"

    if bet_type == 'Spread':
        match = re.search(r'(.+?)\s*([-+]\d+(\.\d+)?)', pick)
        if match:
            team = match.group(1).strip()
            spread = match.group(2).strip()
            return f"{team} {spread}"
        return pick

    if bet_type == 'Total':
        pick = re.sub(r'\b(O|Over)\s*(\d)', r'Over  ', pick, flags=re.I)
        pick = re.sub(r'\b(U|Under)\s*(\d)', r'Under  ', pick, flags=re.I)
        return pick

    if bet_type == 'Player Prop':
        # Handle Anytime TD specifically
        if "Anytime TD" in pick or "ATD" in pick:
            clean = re.sub(r'\b(Anytime TD|ATD)\b', '', pick, flags=re.I).strip()
            return f"{clean} Anytime TD"
            
        if ':' not in pick:
            parts = pick.split()
            if len(parts) > 2:
                # Try to format as "Player Name: Prop Type"
                return f"{parts[0]} {parts[1]}: {' '.join(parts[2:])}"
        return pick

    return pick

def infer_league(pick_text: str) -> str:
    if not pick_text: return 'Other'
    
    # Check exact team matches
    for league, teams in LEAGUE_KEYWORDS.items():
        for team in teams:
            # Word boundary check to avoid partial matches (e.g. "Iowa" matching "Iowa State")
            # We use re.IGNORECASE to match "lakers" to "Lakers"
            if re.search(r'\b' + re.escape(team) + r'\b', pick_text, re.IGNORECASE):
                return league
                
    return 'Other'

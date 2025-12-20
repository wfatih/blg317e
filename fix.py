import csv
import shutil
import os

INPUT_CSV = "data/teams.csv"
TEMP_CSV = "data/teams_full_legends.csv"

# --- URL'LERİN HEPSİ PROXY'DEN GEÇİRİLDİ ---
# "https://wsrv.nl/?url=..." yapısı sayesinde hotlink koruması delinir.
# Artık resimlerin yüklenmeme şansı yok.

ALL_LEGENDS = {
    # Atlanta Hawks - Dominique Wilkins
    "1610612737": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/4/4e/Dominique_Wilkins_2018.jpg&w=800",
    
    # Boston Celtics - Larry Bird
    "1610612738": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/6/6f/Larry_Bird_Lipofsky.jpg&w=800",
    
    # Brooklyn Nets - Dr. J (Julius Erving)
    "1610612751": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/d/d4/Julius_Erving_1981.jpg&w=800",
    
    # Charlotte Hornets - Kemba Walker
    "1610612766": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/f/fe/Kemba_Walker_2014.jpg&w=800",
    
    # Chicago Bulls - Michael Jordan
    "1610612741": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/b/b3/Jordan_Lipofsky.jpg&w=800",
    
    # Cleveland Cavaliers - LeBron James
    "1610612739": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/c/cf/LeBron_James_crop_%282012%29.jpg&w=800",
    
    # Dallas Mavericks - Dirk Nowitzki
    "1610612742": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/7/7c/Dirk_Nowitzki_2010.jpg&w=800",
    
    # Denver Nuggets - Nikola Jokic
    "1610612743": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/3/36/Nikola_Joki%C4%87_free_throw_%28cropped%29.jpg&w=800",
    
    # Detroit Pistons - Isiah Thomas
    "1610612765": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/5/52/Isiah_Thomas_2012.jpg&w=800",
    
    # Golden State Warriors - Stephen Curry
    "1610612744": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/3/36/Stephen_Curry_dribbling_2016_%28cropped%29.jpg&w=800",
    
    # Houston Rockets - Hakeem Olajuwon
    "1610612745": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/1/13/Hakeem_Olajuwon_Lipofsky.jpg&w=800",
    
    # Indiana Pacers - Reggie Miller
    "1610612754": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/2/27/Reggie_Miller_2019.jpg&w=800",
    
    # LA Clippers - Kawhi Leonard
    "1610612746": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/d/d3/Kawhi_Leonard_dribbling_2019_%28cropped%29.jpg&w=800",
    
    # LA Lakers - Kobe Bryant
    "1610612747": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/5/56/Kobe_Bryant_2014.jpg&w=800",
    
    # Memphis Grizzlies - Ja Morant
    "1610612763": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/1/1a/Ja_Morant_dribbling_2019_%28cropped%29.jpg&w=800",
    
    # Miami Heat - Dwyane Wade
    "1610612748": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/4/4d/Dwyane_Wade_waving_2018.jpg&w=800",
    
    # Milwaukee Bucks - Giannis
    "1610612749": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/9/93/Giannis_Antetokounmpo_2019.jpg&w=800",
    
    # Minnesota Timberwolves - Kevin Garnett
    "1610612750": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/5/57/Kevin_Garnett_2008.jpg&w=800",
    
    # New Orleans Pelicans - Anthony Davis
    "1610612740": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/7/72/Anthony_Davis_2013.jpg&w=800",
    
    # New York Knicks - Patrick Ewing
    "1610612752": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/a/ae/Patrick_Ewing_Lipofsky.jpg&w=800",
    
    # OKC Thunder - Kevin Durant
    "1610612760": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/b/b5/Kevin_Durant_2014.jpg&w=800",
    
    # Orlando Magic - Shaquille O'Neal
    "1610612753": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/e/ea/Shaquille_O%27Neal_2009.jpg&w=800",
    
    # Philadelphia 76ers - Allen Iverson
    "1610612755": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/c/c9/Allen_Iverson_Lipofsky.jpg&w=800",
    
    # Phoenix Suns - Steve Nash
    "1610612756": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/1/10/Steve_Nash_2008.jpg&w=800",
    
    # Portland Trail Blazers - Damian Lillard
    "1610612757": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/d/df/Damian_Lillard_2018.jpg&w=800",
    
    # Sacramento Kings - Chris Webber
    "1610612758": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/c/cb/Chris_Webber_1.jpg&w=800",
    
    # San Antonio Spurs - Tim Duncan
    "1610612759": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/0/05/Tim_Duncan_2013.jpg&w=800",
    
    # Toronto Raptors - Vince Carter
    "1610612761": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/e/e3/Vince_Carter_dunk.jpg&w=800",
    
    # Utah Jazz - Karl Malone
    "1610612762": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/9/90/Karl_Malone_Lipofsky.jpg&w=800",
    
    # Washington Wizards - John Wall
    "1610612764": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/2/29/John_Wall_2014.jpg&w=800"
}

DEFAULT_IMG = "https://images.unsplash.com/photo-1546519638-68e109498ffc?q=80&w=800&auto=format&fit=crop"

print("Tüm efsaneler CSV'ye (Proxy korumalı) işleniyor...")

with open(INPUT_CSV, 'r', encoding='utf-8') as infile, \
     open(TEMP_CSV, 'w', encoding='utf-8', newline='') as outfile:
    
    reader = csv.DictReader(infile)
    
    # Sütun varsa koru, yoksa ekle
    fieldnames = reader.fieldnames
    if 'LEGENDARY_IMG' not in fieldnames:
        fieldnames.append('LEGENDARY_IMG')
    
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in reader:
        t_id = row['TEAM_ID']
        
        if t_id in ALL_LEGENDS:
            row['LEGENDARY_IMG'] = ALL_LEGENDS[t_id]
        else:
            row['LEGENDARY_IMG'] = DEFAULT_IMG
            
        writer.writerow(row)

# Dosyayı değiştir
shutil.move(TEMP_CSV, INPUT_CSV)
print("------------------------------------------------")
print("✅ GÖREV TAMAMLANDI!")
print("Proxy linkleri data/teams.csv dosyasına başarıyla kaydedildi.")
print("Şimdi 'python load-data.py' komutunu çalıştır.")
print("------------------------------------------------")
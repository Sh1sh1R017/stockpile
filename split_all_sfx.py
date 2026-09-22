import os
import json
import subprocess
import shutil

input_audio = r"C:\Users\SHISHIR\.gemini\antigravity\brain\5c8acd7c-29ed-470d-bfc4-7d3f5ac5d5bf\.user_uploaded\uploaded_media_1790044151106.mp3"
output_dir = r"c:\Users\SHISHIR\Documents\antigravity\peaceful-hawking\output\split_sfx"

os.makedirs(output_dir, exist_ok=True)

# Master curated list of 86 sound effects with verified start and end times (in seconds)
# Derived from precise silence boundaries, Whisper speech timestamps, and Gemini audio verification
sfx_master_catalog = [
    # 00:00 - 00:30
    {"id": 1, "start": 0.45, "end": 0.80, "name": "Bonk Impact", "file": "01_bonk_impact.mp3", "cat": "Cartoon SFX", "desc": "Wood bonk impact on head"},
    {"id": 2, "start": 1.07, "end": 1.41, "name": "What Meme", "file": "02_what_meme.mp3", "cat": "Voice Meme", "desc": "High pitched voice saying 'What?'"},
    {"id": 3, "start": 1.77, "end": 2.65, "name": "Pencil Writing", "file": "03_pencil_writing.mp3", "cat": "Foley", "desc": "Pencil sketching / writing on paper"},
    {"id": 4, "start": 2.70, "end": 4.25, "name": "Camera Shutter & Flash", "file": "04_camera_shutter.mp3", "cat": "Foley", "desc": "Mechanical DSLR camera shutter clicks"},
    {"id": 5, "start": 4.30, "end": 6.00, "name": "Mouse Clicks", "file": "05_mouse_clicks.mp3", "cat": "Foley", "desc": "Rapid computer mouse clicking sounds"},
    {"id": 6, "start": 6.27, "end": 6.58, "name": "Nope (TF2 Engineer)", "file": "06_nope_engineer.mp3", "cat": "Voice Meme", "desc": "TF2 Engineer saying 'Nope' with neck stretch sound"},
    {"id": 7, "start": 7.06, "end": 9.31, "name": "Loud Scream", "file": "07_loud_scream.mp3", "cat": "Reaction", "desc": "Intense vocal screaming yell"},
    {"id": 8, "start": 10.47, "end": 11.26, "name": "Cartoon Spring Boing", "file": "08_cartoon_spring_boing.mp3", "cat": "Cartoon SFX", "desc": "Classic cartoon metallic spring bounce"},
    {"id": 9, "start": 13.06, "end": 16.87, "name": "Yay Children Cheering", "file": "09_yay_children_cheering.mp3", "cat": "Reaction", "desc": "Children shouting 'Yay!' in celebration"},
    {"id": 10, "start": 17.50, "end": 18.09, "name": "Cash Register Ka-Ching", "file": "10_cash_register_kaching.mp3", "cat": "Foley", "desc": "Vintage mechanical cash register drawer opening"},
    {"id": 11, "start": 18.85, "end": 19.33, "name": "Bruh", "file": "11_bruh.mp3", "cat": "Voice Meme", "desc": "Iconic deep voice saying 'Bruh'"},
    {"id": 12, "start": 19.87, "end": 21.09, "name": "Are You Serious My Brother", "file": "12_are_you_serious_my_brother.mp3", "cat": "Voice Meme", "desc": "Voice asking 'Are you serious my brother?'"},
    {"id": 13, "start": 21.88, "end": 30.82, "name": "Angelic Choir (Halo Theme)", "file": "13_angelic_halo_choir.mp3", "cat": "Music / Riff", "desc": "Epic Gregorian angelic monk chanting / Halo theme"},
    
    # 00:30 - 01:00
    {"id": 14, "start": 32.84, "end": 33.65, "name": "Punch Impact & Scream", "file": "14_punch_impact_scream.mp3", "cat": "Impact", "desc": "Heavy face punch impact followed by quick gasp"},
    {"id": 15, "start": 33.90, "end": 35.29, "name": "Ayo What The Fuck", "file": "15_ayo_what_the_fuck.mp3", "cat": "Voice Meme", "desc": "Loud confrontation shouting 'Ayo what the fuck?'"},
    {"id": 16, "start": 35.52, "end": 36.11, "name": "Baba Booey", "file": "16_baba_booey.mp3", "cat": "Voice Meme", "desc": "Howard Stern show soundbite 'Baba Booey'"},
    {"id": 17, "start": 36.99, "end": 39.95, "name": "Baby Crying & Wailing", "file": "17_baby_crying.mp3", "cat": "Reaction", "desc": "Infant crying and screaming tantrums"},
    {"id": 18, "start": 40.52, "end": 40.87, "name": "Sigh / Yawn", "file": "18_sigh_yawn.mp3", "cat": "Reaction", "desc": "Deep tired vocal sigh"},
    {"id": 19, "start": 41.25, "end": 41.70, "name": "Snap / Click", "file": "19_snap_click.mp3", "cat": "Foley", "desc": "Sharp mechanical snap"},
    {"id": 20, "start": 42.49, "end": 45.44, "name": "Bro Really About To", "file": "20_bro_really_about_to.mp3", "cat": "Voice Meme", "desc": "'Bro really about to get your pickpachin ass boy'"},
    {"id": 21, "start": 45.65, "end": 46.85, "name": "Boy If You Don't Get", "file": "21_boy_if_you_dont_get.mp3", "cat": "Voice Meme", "desc": "'Boy if you don't get...' roast intro"},
    {"id": 22, "start": 47.17, "end": 53.14, "name": "Ayo The Pizza Here (My Ears Burn)", "file": "22_ayo_the_pizza_here.mp3", "cat": "Voice Meme", "desc": "'Ayo the pizza here! Oh n***a! Ahhh! My ears burn!' staircase fall"},
    {"id": 23, "start": 53.53, "end": 54.55, "name": "Goofy Laugh", "file": "23_goofy_laugh.mp3", "cat": "Reaction", "desc": "Comedic goofy cartoon chuckle"},
    {"id": 24, "start": 55.18, "end": 56.09, "name": "Villain Laugh (Ha Ha)", "file": "24_villain_laugh.mp3", "cat": "Reaction", "desc": "Short sinister evil chuckle"},
    {"id": 25, "start": 56.66, "end": 57.26, "name": "Gasp / Inhale", "file": "25_gasp_inhale.mp3", "cat": "Reaction", "desc": "Shocked quick gasp of air"},
    {"id": 26, "start": 57.95, "end": 58.14, "name": "Cartoon Pop", "file": "26_cartoon_pop.mp3", "cat": "Cartoon SFX", "desc": "Crisp cork / bubble pop"},
    {"id": 27, "start": 58.58, "end": 59.09, "name": "Switch Click", "file": "27_switch_click.mp3", "cat": "Foley", "desc": "Tactile light switch toggle click"},
    {"id": 28, "start": 59.91, "end": 60.24, "name": "Bell Ding", "file": "28_bell_ding.mp3", "cat": "Foley", "desc": "Single clear bell chime"},
    {"id": 29, "start": 60.84, "end": 61.07, "name": "Low Thud", "file": "29_low_thud.mp3", "cat": "Impact", "desc": "Subdued floor impact thud"},
    
    # 01:00 - 01:30
    {"id": 30, "start": 61.42, "end": 62.60, "name": "I Can't Let You Get Close", "file": "30_i_cant_let_you_get_close.mp3", "cat": "Voice Meme", "desc": "Chael Sonnen UFC confrontation line"},
    {"id": 31, "start": 62.70, "end": 64.39, "name": "Green Giant Jingle", "file": "31_green_giant.mp3", "cat": "Voice Meme", "desc": "'Green Giant!' commercial vocal jingle"},
    {"id": 32, "start": 64.96, "end": 71.39, "name": "Please Man I Need This (Homeless)", "file": "32_please_man_i_need_this.mp3", "cat": "Voice Meme", "desc": "'Please man I need this! My mom is kind of homeless...' emotional plea"},
    {"id": 33, "start": 71.61, "end": 72.10, "name": "Fart Sound 1 (Quick Rip)", "file": "33_fart_sound_1.mp3", "cat": "Cartoon SFX", "desc": "Short sharp flatulence sound effect"},
    {"id": 34, "start": 72.14, "end": 76.18, "name": "Fart Sound 2 (Wet Squelch)", "file": "34_fart_sound_2.mp3", "cat": "Cartoon SFX", "desc": "Wet comedic cartoon flatulence"},
    {"id": 35, "start": 76.92, "end": 77.95, "name": "Short Chuckle", "file": "35_short_chuckle.mp3", "cat": "Reaction", "desc": "Quiet male chuckle"},
    {"id": 36, "start": 78.62, "end": 84.75, "name": "Fart With Massive Reverb", "file": "36_fart_with_reverb.mp3", "cat": "Cartoon SFX", "desc": "Epic echoed stadium reverb fart meme"},
    {"id": 37, "start": 86.48, "end": 87.13, "name": "Gun Cock Click", "file": "37_gun_cock_click.mp3", "cat": "Foley", "desc": "Crisp metallic handgun slide cock"},
    {"id": 38, "start": 87.81, "end": 89.13, "name": "Fatality (Mortal Kombat)", "file": "38_fatality_mortal_kombat.mp3", "cat": "Gaming", "desc": "Deep Mortal Kombat announcer saying 'FATALITY'"},
    {"id": 39, "start": 89.65, "end": 93.70, "name": "FBI Open Up (Breach & Gunfire)", "file": "39_fbi_open_up.mp3", "cat": "Voice Meme", "desc": "'FBI OPEN UP!' followed by battering ram door kick and automatic gunfire"},
    {"id": 40, "start": 94.76, "end": 95.36, "name": "Gotcha Bitch", "file": "40_gotcha_bitch.mp3", "cat": "Voice Meme", "desc": "Dave Chappelle voice line 'Gotcha bitch!'"},
    {"id": 41, "start": 96.26, "end": 102.70, "name": "Punch Body Hit Combo", "file": "41_punch_body_hit.mp3", "cat": "Impact", "desc": "Violent melee punches and body smack impact sequence"},
    
    # 01:30 - 02:00
    {"id": 42, "start": 104.72, "end": 106.27, "name": "Ha Gaaaay (Señor Chang)", "file": "42_ha_gaaaay.mp3", "cat": "Voice Meme", "desc": "Community Señor Chang shouting 'Ha! Gaaaay!'"},
    {"id": 43, "start": 106.72, "end": 109.19, "name": "Got 'Em (Deez Nuts)", "file": "43_got_em.mp3", "cat": "Voice Meme", "desc": "WelvenDaGreat laughing 'HA! GOT 'EM!'"},
    {"id": 44, "start": 109.62, "end": 110.57, "name": "Heartbeat", "file": "44_heartbeat.mp3", "cat": "Foley", "desc": "Tense visceral double heartbeat thump"},
    {"id": 45, "start": 113.32, "end": 114.27, "name": "On The People", "file": "45_on_the_people.mp3", "cat": "Voice Meme", "desc": "Street line 'On the people!'"},
    {"id": 46, "start": 114.81, "end": 121.26, "name": "He Needs Some Milk", "file": "46_he_needs_some_milk.mp3", "cat": "Voice Meme", "desc": "'Whoa! Somebody... Oh! He needs some milk!'"},
    {"id": 47, "start": 122.38, "end": 125.36, "name": "Hold Up Wait A Minute", "file": "47_hold_up_wait_a_minute.mp3", "cat": "Voice Meme", "desc": "'Hold up! Wait a minute! Something ain't right!'"},
    {"id": 48, "start": 125.83, "end": 128.09, "name": "I Like Ya Cut G (Slap)", "file": "48_i_like_ya_cut_g.mp3", "cat": "Voice Meme", "desc": "'I like ya cut G' followed by resonant bald slap"},
    {"id": 49, "start": 128.30, "end": 130.34, "name": "I'm Fast As Fuck Boy", "file": "49_im_fast_as_fuck_boy.mp3", "cat": "Voice Meme", "desc": "Keemstar running line 'I'm fast as fuck boy!'"},
    
    # 02:00 - 02:30
    {"id": 50, "start": 130.78, "end": 131.24, "name": "Kobe", "file": "50_kobe.mp3", "cat": "Voice Meme", "desc": "Shouting 'Kobe!' when shooting a shot"},
    {"id": 51, "start": 132.69, "end": 133.12, "name": "Hey Shout", "file": "51_hey_shout.mp3", "cat": "Voice Meme", "desc": "Lego commercial style 'HEY!'"},
    {"id": 52, "start": 133.53, "end": 135.36, "name": "Let's Do This (Leroy Jenkins)", "file": "52_lets_do_this.mp3", "cat": "Voice Meme", "desc": "Deep voice motivating 'Alright, let's do this!'"},
    {"id": 53, "start": 140.32, "end": 162.08, "name": "Look At This Dude (Wheezing Laugh)", "file": "53_look_at_this_dude_wheeze.mp3", "cat": "Voice Meme", "desc": "'Bruh look at this dude... wait till you see... look at the top of his head! Look at his lips!' with hysterical wheeze laugh"},
    
    # 02:30 - 03:00
    {"id": 54, "start": 162.61, "end": 162.97, "name": "Gun Reload / Slide", "file": "54_gun_reload.mp3", "cat": "Foley", "desc": "Quick shotgun / rifle pump action"},
    {"id": 55, "start": 163.19, "end": 164.80, "name": "Subtle 808 Bass Drop", "file": "55_subtle_bass_drop.mp3", "cat": "Impact", "desc": "Deep low-end sub bass boom impact"},
    {"id": 56, "start": 164.90, "end": 166.10, "name": "Record Scratch", "file": "56_record_scratch.mp3", "cat": "Cartoon SFX", "desc": "Classic vinyl DJ needle record scratch freeze frame"},
    {"id": 57, "start": 166.20, "end": 167.30, "name": "Windows XP Error Ding", "file": "57_windows_xp_error.mp3", "cat": "Gaming / Tech", "desc": "Windows XP critical stop / error sound chord"},
    {"id": 58, "start": 167.40, "end": 170.21, "name": "Super Mario Coin Chime", "file": "58_super_mario_coin.mp3", "cat": "Gaming", "desc": "Iconic Nintendo Super Mario Bros coin chime"},
    {"id": 59, "start": 170.50, "end": 171.37, "name": "Cartoon Slip Whoosh", "file": "59_cartoon_slip_whoosh.mp3", "cat": "Cartoon SFX", "desc": "Comedic banana peel slip and fall whoosh"},
    {"id": 60, "start": 172.62, "end": 174.61, "name": "Sad Violin (Womp Womp)", "file": "60_sad_violin.mp3", "cat": "Music / Riff", "desc": "Melodramatic sad violin solo for fails"},
    {"id": 61, "start": 175.16, "end": 177.88, "name": "Wilhelm Scream", "file": "61_wilhelm_scream.mp3", "cat": "Reaction", "desc": "Legendary Hollywood Wilhelm scream sound effect"},
    {"id": 62, "start": 178.29, "end": 178.82, "name": "Car Horn Beep Beep", "file": "62_car_horn_beep_beep.mp3", "cat": "Foley", "desc": "Double high-pitched automobile horn honk"},
    {"id": 63, "start": 179.55, "end": 179.83, "name": "Clock Ticking", "file": "63_clock_ticking.mp3", "cat": "Foley", "desc": "Tense pocket watch clock tick"},
    
    # 03:00 - 03:30
    {"id": 64, "start": 180.26, "end": 182.66, "name": "Footsteps Running", "file": "64_footsteps_running.mp3", "cat": "Foley", "desc": "Footsteps walking / running on hard surface"},
    {"id": 65, "start": 183.51, "end": 183.87, "name": "Door Creak & Slam", "file": "65_door_creak_slam.mp3", "cat": "Foley", "desc": "Creaking wooden door swinging and shutting"},
    {"id": 66, "start": 184.67, "end": 184.98, "name": "Phone Ring / Notification", "file": "66_phone_ring_notification.mp3", "cat": "Foley", "desc": "Smartphone ringtone / alert chime"},
    {"id": 67, "start": 187.16, "end": 187.69, "name": "Punch / Heavy Thud", "file": "67_punch_heavy_thud.mp3", "cat": "Impact", "desc": "Blunt punch impact hit"},
    {"id": 68, "start": 188.14, "end": 188.47, "name": "Ooh Okay", "file": "68_ooh_okay.mp3", "cat": "Voice Meme", "desc": "Voice saying surprised 'Ooh, okay!'"},
    {"id": 69, "start": 189.64, "end": 189.99, "name": "Water Drip Plop", "file": "69_water_drip_plop.mp3", "cat": "Foley", "desc": "Single water droplet falling with plop echo"},
    {"id": 70, "start": 190.80, "end": 191.31, "name": "Sci-Fi Laser Pew Pew", "file": "70_scifi_laser_pew.mp3", "cat": "Cartoon SFX", "desc": "Sci-fi blaster laser pew pew sound"},
    {"id": 71, "start": 193.19, "end": 195.17, "name": "Metal Pipe Falling", "file": "71_metal_pipe_falling.mp3", "cat": "Meme SFX", "desc": "Ultra resonant loud metal pipe crashing on concrete"},
    {"id": 72, "start": 195.84, "end": 195.99, "name": "Service Desk Bell Ding", "file": "72_service_bell_ding.mp3", "cat": "Foley", "desc": "High pitch brass hotel reception desk bell ding"},
    {"id": 73, "start": 196.56, "end": 197.27, "name": "Really Nigga", "file": "73_really_nigga.mp3", "cat": "Voice Meme", "desc": "Deadpan reaction voice saying 'Really nigga?'"},
    {"id": 74, "start": 198.54, "end": 199.14, "name": "Champagne Cork Pop", "file": "74_cork_pop.mp3", "cat": "Cartoon SFX", "desc": "Pressurized bottle cork pop"},
    {"id": 75, "start": 199.60, "end": 201.51, "name": "Children Cheering Yay", "file": "75_children_cheering_yay.mp3", "cat": "Reaction", "desc": "Children shouting joyful 'YAY!'"},
    {"id": 76, "start": 202.65, "end": 202.95, "name": "Dramatic Dun Dun Dun", "file": "76_dramatic_dun_dun_dun.mp3", "cat": "Music / Riff", "desc": "Dramatic three-note suspense brass stinger"},
    {"id": 77, "start": 203.34, "end": 205.07, "name": "Sike Sike (That's The Wrong Number)", "file": "77_sike_sike.mp3", "cat": "Voice Meme", "desc": "Supah Hot Fire hype crew yelling 'SIKE! SIKE!'"},
    {"id": 78, "start": 206.28, "end": 206.47, "name": "Anime Wow (Fairy Tail)", "file": "78_anime_wow.mp3", "cat": "Meme SFX", "desc": "Cute anime girl saying 'Woooow'"},
    {"id": 79, "start": 207.24, "end": 207.60, "name": "TV Censor Bleep", "file": "79_tv_censor_bleep.mp3", "cat": "Cartoon SFX", "desc": "Standard 1000Hz television curse censor bleep tone"},
    {"id": 80, "start": 207.97, "end": 211.25, "name": "MLG Airhorn Siren", "file": "80_mlg_airhorn_siren.mp3", "cat": "Meme SFX", "desc": "Montage parodies MLG triple air horn blast"},
    
    # 03:30 - 03:54
    {"id": 81, "start": 211.85, "end": 212.23, "name": "Vine Boom (Dramatic Boom)", "file": "81_vine_boom.mp3", "cat": "Meme SFX", "desc": "The iconic Vine bass thunder boom sound effect"},
    {"id": 82, "start": 212.58, "end": 213.46, "name": "Giggle / Snicker", "file": "82_giggle_snicker.mp3", "cat": "Reaction", "desc": "Cheeky suppressed cartoon snicker giggle"},
    {"id": 83, "start": 213.68, "end": 215.16, "name": "Buzzer (Wrong Answer)", "file": "83_buzzer_wrong_answer.mp3", "cat": "Gaming / Show", "desc": "Game show harsh red X incorrect buzzer tone"},
    {"id": 84, "start": 215.70, "end": 216.62, "name": "Snore Mimimimi", "file": "84_snore_mimimimi.mp3", "cat": "Cartoon SFX", "desc": "Cartoony sleeping snore saying 'mimimimimi'"},
    {"id": 85, "start": 217.33, "end": 218.59, "name": "Game Show Correct Ding", "file": "85_game_show_correct.mp3", "cat": "Gaming / Show", "desc": "Cheerful ascending chime for correct answer"},
    {"id": 86, "start": 219.97, "end": 220.29, "name": "Cat Screaming Meow", "file": "86_cat_screaming_meow.mp3", "cat": "Reaction", "desc": "Distressed comedic screeching cat meow"},
    {"id": 87, "start": 221.16, "end": 223.97, "name": "Thunder Strike Crack", "file": "87_thunder_strike_crack.mp3", "cat": "Impact", "desc": "Violent lightning thunderbolt strike"},
    {"id": 88, "start": 224.27, "end": 224.48, "name": "Whip Crack Slap", "file": "88_whip_crack_slap.mp3", "cat": "Impact", "desc": "Leather bullwhip snap crack"},
    {"id": 89, "start": 226.51, "end": 227.43, "name": "What The Dog Doin", "file": "89_what_the_dog_doin.mp3", "cat": "Voice Meme", "desc": "'What the dog doin?' vine voice line"},
    {"id": 90, "start": 228.07, "end": 228.85, "name": "Why Are You Gay", "file": "90_why_are_you_gay.mp3", "cat": "Voice Meme", "desc": "Ugandan news anchor asking 'Why are you gay?'"},
    {"id": 91, "start": 229.71, "end": 230.31, "name": "Snare Drum Roll", "file": "91_snare_drum_roll.mp3", "cat": "Music / Riff", "desc": "Suspenseful circus marching snare drum roll"},
    {"id": 92, "start": 232.03, "end": 232.93, "name": "Glass Breaking Crash", "file": "92_glass_breaking_crash.mp3", "cat": "Impact", "desc": "Window pane shattering glass impact crash"},
    {"id": 93, "start": 232.95, "end": 233.76, "name": "Get Out Soundbite", "file": "93_get_out.mp3", "cat": "Voice Meme", "desc": "Angry final 'GET OUT!' vocal punch"}
]

print(f"Total curated SFX to extract: {len(sfx_master_catalog)}")

# Splitting using FFmpeg
success_count = 0
for item in sfx_master_catalog:
    st = item["start"]
    en = item["end"]
    dur = round(en - st, 3)
    out_file = os.path.join(output_dir, item["file"])
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(st),
        "-to", str(en),
        "-i", input_audio,
        "-c:a", "libmp3lame",
        "-q:a", "0",
        out_file
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(out_file) and os.path.getsize(out_file) > 500:
        success_count += 1
    else:
        print(f"Failed extracting {item['file']}: {res.stderr[:100]}")

print(f"Successfully extracted and saved {success_count} / {len(sfx_master_catalog)} sound effects!")

# Save catalog JSON in output dir
with open(os.path.join(output_dir, "sfx_catalog.json"), "w", encoding="utf-8") as f:
    json.dump(sfx_master_catalog, f, indent=2)

# Generate README.md in output dir
readme_lines = [
    "# Master SFX Soundboard Pack (93 Iconic Sounds)",
    "",
    "Extracted, silence-aligned, and labeled from the source audio using FFmpeg.",
    "",
    "| # | Filename | Sound / Meme Title | Category | Timestamp | Duration | Description |",
    "|---|---|---|---|---|---|---|"
]

for s in sfx_master_catalog:
    dur = round(s["end"] - s["start"], 2)
    readme_lines.append(
        f"| {s['id']:02d} | `{s['file']}` | **{s['name']}** | {s['cat']} | `{s['start']:.2f}s - {s['end']:.2f}s` | `{dur:.2f}s` | {s['desc']} |"
    )

with open(os.path.join(output_dir, "README.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(readme_lines))

print("Catalog and README generated successfully in output/split_sfx/")

# R&B hit research and local-library results

Researched 2026-07-11 against the top-level artist folders under the local
R&B library. "Found" means the seed matcher located a tagged audio file in the
scanned crate; generated outputs retain the private absolute path under
gitignored `brain/data/`.

The selection favors the highest-charting US single or the durable signature
song when that is more useful for a DJ set. Chart claims link to the source
used. The full machine-readable seed, including sources, is
`brain/playlist_seeds/rnb_west_coast_hits.json`.

| Folder artist | Recommended cut(s) | Why | Local |
| --- | --- | --- | --- |
| 702 | Where My Girls At? | Long-running Hot 100 top-10 hit and No. 11 on Billboard's 1999 year-end list ([source](https://en.wikipedia.org/wiki/Where_My_Girls_At)) | Found |
| Al B. Sure! | Nite and Day | No. 7 Hot 100, No. 1 Hot Black Singles ([source](https://en.wikipedia.org/wiki/Nite_and_Day)) | Found |
| Alicia Keys | Fallin'; No One | Both Hot 100 No. 1 singles; "No One" was Billboard's biggest hit peaking in 2007 ([source](https://en.wikipedia.org/wiki/No_One_(Alicia_Keys_song))) | Found |
| Barry White | Can't Get Enough of Your Love, Babe | Hot 100 No. 1 ([source](https://en.wikipedia.org/wiki/Barry_White_discography)) | Found |
| Bernard Wright | Who Do You Love | His highest Billboard R&B appearance, No. 6 ([source](https://en.wikipedia.org/wiki/Who_Do_You_Love_(Bernard_Wright_song))) | Found |
| Isaac Hayes | Shaft | Hot 100 No. 1 ([source](https://en.wikipedia.org/wiki/Theme_from_Shaft)) | Found |
| James Brown | I Got You (I Feel Good) | His highest Hot 100 single, No. 3 ([source](https://en.wikipedia.org/wiki/I_Got_You_(I_Feel_Good))) | Found |
| Jane Child | Don't Wanna Fall in Love | Hot 100 No. 2 for three weeks ([source](https://en.wikipedia.org/wiki/Don%27t_Wanna_Fall_in_Love)) | Found |
| Janet Jackson | That's the Way Love Goes; Rhythm Nation | The former spent eight weeks at Hot 100 No. 1; the latter is the faster set option ([source](https://en.wikipedia.org/wiki/That%27s_the_Way_Love_Goes_(Janet_Jackson_song))) | Found |
| Joe Jackson | Steppin' Out | His highest-charting US single, Hot 100 No. 6 ([source](https://en.wikipedia.org/wiki/Steppin%27_Out_(Joe_Jackson_song))) | Found |
| Jon B. | They Don't Know | Hot 100 No. 7 ([source](https://en.wikipedia.org/wiki/They_Don%27t_Know_(Jon_B._song))) | Found |
| Keni Burke | Risin' to the Top | His most successful solo hit and signature song ([source](https://en.wikipedia.org/wiki/Risin%27_to_the_Top)) | Found |
| Lisa Stansfield | All Around the World | Hot 100 No. 3 and No. 1 R&B ([source](https://en.wikipedia.org/wiki/All_Around_the_World_(Lisa_Stansfield_song))) | Found |
| Love Unlimited Orchestra | Love's Theme | Hot 100 No. 1 ([source](https://en.wikipedia.org/wiki/Love%27s_Theme)) | Found |
| Marvin Gaye | I Heard It Through the Grapevine; Got to Give It Up | Both Hot 100 No. 1; the second is the stronger dance-floor cut ([source](https://chart-history.net/statistics/Hot100/Hot100-Edition-Top01.pdf)) | Found |
| Michael Jackson | Billie Jean; Rock with You | Two danceable Hot 100 No. 1 singles from the core studio albums ([source](https://apnews.com/article/79ddd6c617aa7e4945b5ab22cd392be5)) | Found |
| P.M. Dawn | Set Adrift on Memory Bliss | Their only Hot 100 No. 1 ([source](https://en.wikipedia.org/wiki/Set_Adrift_on_Memory_Bliss)) | Found |
| Ready for the World | Oh Sheila | No. 1 on the Hot 100, R&B, and dance charts ([source](https://en.wikipedia.org/wiki/Ready_for_the_World_(Ready_for_the_World_album))) | Found |
| Sade | Smooth Operator; Your Love Is King; Paradise; Kiss of Life; The Sweetest Taboo; Hang On to Your Love; Never as Good as the First Time; Nothing Can Come Between Us | Requested cuts plus faster-feeling catalog choices; all appear on Sade's official hit compilation ([source](https://www.sade.com/music/the-best-of-sade)) | Found |
| The Art of Noise | Kiss (feat. Tom Jones) | Their crossover Hot 100 hit, No. 37 ([source](https://theartofnoiseonline.com/KISS-871-0384.php)) | Found |
| The Gap Band | You Dropped a Bomb on Me; Outstanding | Their durable dance-floor standards; the former reached the Hot 100 top 40 ([source](https://www.grammy.com/news/the-gap-band-drop-the-bomb)) | Found |
| The System | Don't Disturb This Groove | Hot 100 No. 4 and their biggest single ([source](https://en.wikipedia.org/wiki/The_System_discography)) | Found |
| The-Dream | Rockin' That Shit | Top-10 R&B/hip-hop solo hit from *Love vs. Money* ([source](https://www.allmusic.com/artist/the-dream-mn0001028077)) | Found |
| Usher | Yeah! | Hot 100 No. 1 and Billboard's most-played song of 2004 ([source](https://www.grammy.com/news/usher-songs-super-bowl-halftime-show-new-album-tour)) | Found |
| Wham! | Wake Me Up Before You Go-Go | Hot 100 No. 1 for three weeks ([source](https://en.wikipedia.org/wiki/Wake_Me_Up_Before_You_Go-Go)) | Found |
| Xscape | The Arms of the One Who Loves You | Hot 100 No. 7 ([source](https://en.wikipedia.org/wiki/The_Arms_of_the_One_Who_Loves_You)) | Found |

## Requested West Coast / hip-hop cuts

All requested cuts were found and seeded: Snoop Dogg's "Beautiful," "Drop It
Like It's Hot," "Lay Low," "Murder Was the Case," "Gin and Juice," and
"Ain't No Fun"; Twinz' "Round & Round"; the Beatnuts' "Off the Books";
Warren G's "Regulate" and "Runnin' wit No Breaks"; Tha Eastsidaz' "G'd Up";
and Erick Sermon's "Music."

## Analysis state

The full crate currently contains 30 tracks with Mixxx BPM/key data. Only two
tracks in this 50-track selection are analyzed: "Drop It Like It's Hot" and
"Gin and Juice." Import `brain/data/playlist.m3u8` into Mixxx, analyze the
playlist, run `brain.sync_mixxx_analysis`, and export once more from the picker.

from discord import PartialEmoji as emoji

class Emoji:

    # !- General -! #

    check = emoji(name="check", id=314349398811475968)
    xmark = emoji(name="xmark", id=314349398824058880)
    neutral = emoji(name="empty", id=314349398723264512)
    charles = emoji(name="charles", id=639898570564042792)
    think = emoji(name="charlesthink", id=603647216787128351)
    loading = emoji(name="discord_loading", id=587812494089912340, animated=True)
    clock = emoji(name="timer", id=522948753368416277, animated=True)
    warn = emoji(name="warn", id=620414236010741783)
    add = emoji(name="added", id=738191087230779442)
    remove = emoji(name="removed", id=738191016258961460)
    arrow = emoji(name="arrow", id=735653783366926931)
    home = emoji(name="home", id=781319262294900736)

    # !- Buttons -! #

    next = emoji(name="play", id=701561428628340836)
    previous = emoji(name="previous", id=701561428498186250)
    last = emoji(name="forward", id=701561428192002099)
    first = emoji(name="rewind", id=701561428238139403)
    cancel = emoji(name="stop", id=701561428099989635)

    # !- Music -! #

    eq = emoji(name="equalizer", id=693967224041504818, animated=True)
    track_info = emoji(name="track_info", id=701561428829667388)
    volume = emoji(name="vol", id=701561428523352085)
    vol_up = emoji(name="vol_up", id=701561428380745850)
    vol_down = emoji(name="vol_down", id=701561428787855430)
    qmark = emoji(name="qmark", id=701561428716552212)
    stop = emoji(name="stop", id=701561428099989635)
    skip = emoji(name="skip", id=701561428183875585)
    shuffle = emoji(name="shuffle", id=701561428741455962)
    settings = emoji(name="settings", id=701561428569489408)
    rewind = emoji(name="rewind", id=701561428238139403)
    queue = emoji(name="queue", id=701561428460568637)
    play = emoji(name="play", id=701561428628340836)
    pause = emoji(name="pause", id=701561428431339641)
    mute = emoji(name="mute", id=701561428649312296)
    mp3 = emoji(name="mp3", id=701561428116504648)
    music_note = emoji(name="music_note", id=701561428217298975)
    lyrics = emoji(name="lyrics", id=701561428485603426)
    loop = emoji(name="loop", id=701561428309704826)
    forward = emoji(name="forward", id=701561428192002099)
    delete = emoji(name="delete", id=701561427902726275)

    # !- Socials -! #

    snapchat = emoji(name="SocialSnapchat", id=684939223903764720)
    reddit = emoji(name="SocialReddit", id=684926545562828831)
    twitter = emoji(name="SocialTwitter", id=684927176889729024)
    steam = emoji(name="SocialSteam", id=684929137320001587)
    github = emoji(name="SocialGithub", id=684930912894582789)
    twitch = emoji(name="SocialTwitch", id=684931686768574521)
    psn = emoji(name="SocialPlaystation", id=684932466322178070)
    xbox = emoji(name="SocialXbox", id=684933086147772422)
    youtube = emoji(name="SocialYouTube", id=684933621647540423)
    instagram = emoji(name="SocialInstagram", id=684937424505405441)

    socials = {
        "snapchat": snapchat,
        "reddit": reddit,
        "twitter": twitter,
        "steam": steam,
        "github": github,
        "twitch": twitch,
        "psn": psn,
        "xbox": xbox,
        "youtube": youtube,
        "instagram": instagram
    }

    def __init__(self, bot):
        self.bot = bot

    def search_match(self, search, return_all=True):
        emojis = [str(e) for e in self.bot.emojis if e.name.lower() == search.lower() and e.is_usable()]
        if not emojis:
            return "No emojis found with that search."
        if return_all:
            return emojis
        else:
            return emojis[0]

    def search_fuzzy(self, search, return_all=True):
        emojis = [str(e) for e in self.bot.emojis if search.lower() in e.name.lower() and e.is_usable()]
        if not emojis:
            return "No emojis found with that search."
        if return_all:
            return emojis
        else:
            return emojis[0]
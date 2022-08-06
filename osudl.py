"""
    @author milk
    @description i love spaghetti
"""
import os
import re
import sys
import time
import queue
import buffer
import shutil
import logging
import requests

# import cloudscraper
import multiprocessing
import concurrent.futures
from time import sleep
from tqdm import tqdm
from sys import platform
from bs4 import BeautifulSoup, SoupStrainer

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

from requests.packages.urllib3.exceptions import InsecureRequestWarning

# import utils.database

DEBUG = False

API_URL = "https://osu.ppy.sh/api/v2"
OAUTH_TOKEN =""

# webdriver manager options
# os.environ["WDM_LOCAL"] = "1"  # save driver to root dir instead of home dir
os.environ["WDM_LOG_LEVEL"] = "0"  # no logging

# shush ssl certificate expiry
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# cloudscraper
# scraper = cloudscraper.create_scraper()

# songs folder
osu_dict = {}
osudb_file = None

gamemode_names = {1: "osu", 2: "taiko", 3: "fruits", 4: "mania"}

mirrors = {
    1: ["[Beatconnect]", "https://beatconnect.io/b/{}", "https://beatconnect.io/"],
    2: [
        "[Sayobot]    ",
        "https://txy1.sayobot.cn/beatmaps/download/full/{}?server=null",
        "https://osu.sayobot.cn/",
    ],
    3: ["[NeriNyan]   ", "https://xiiov.com/d/{}", "https://nerina.pw/"],
    4: [
        "[Chimu.moe]  ",
        "https://api.chimu.moe/v1/download/{}?n=1",
        "https://chimu.moe/",
    ],
}


class color:
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


# Cosmetics
def clearline(n):
    for i in range(0, n):
        print("\033[A                                                          \033[A")


def print_msg_box(msg, indent=1, width=None, title=None):
    """Print message-box with optional title."""
    lines = msg.split("\n")
    space = " " * indent
    if not width:
        width = max(map(len, lines))
    box = f'╔{"═" * (width + indent * 2)}╗\n'
    if title:
        box += f"║{space}{title:<{width}}{space}║\n"
        box += f'║{space}{"-" * len(title):<{width}}{space}║\n'
    box += "".join([f"║{space}{line:<{width}}{space}║\n" for line in lines])
    box += f'╚{"═" * (width + indent * 2)}╝'
    print(box)


def print_garbage():
    print(color.DARKCYAN)
    print_msg_box(
        f"""
        Pre-Release v3:
            Removed official site download because it's against osu TOS and it is a restrictable offense. Thank you ThePooN for telling me.
            If there are other violations for any service this program obtains data from dm milk#6908 on discord

            Multithreading: Spawn one pool for each beatmap mirror selected with user specified threads for each
                            Added workload balancing for multithreaded download from mirrors
                            NOT DONE: Redirect the pool for misbehaving mirror to other pools (rate limiting, offline, etc)

            Mirrors:        Added mirrors Beatconnect, Sayobot, NeriNyan, Chimu.moe

            Download list:  Avoid duplicates by reading from osu.db file
                            Added more sources for beatmap list (check the options)

            Utilities:      NOT DONE: Added support for specified difficulty download instead of the whole beatmapset
                            NOT DONE: Check validity for exisiting beatmaps in download directory (check CRC Headers of files after unzip)
                            NOT DONE: Automatic thread detection using rate of data transfer from each mirror (user specified for now)
                            NOT DONE: Misc validity and sanity check for anything relating to user input, exception handling for some functions and cleanups

        v2: Added terminal colors
            Added basic multithreading

        v1: Singlethread downloading from official osu site
            """,
        title="Changelog",
    )
    print(color.YELLOW)
    print(
        "\nNOTICE: There is only ncurses (command line interface) for now, if you have any good ideas for GUI dm milk#6908 on discord"
    )
    print(
        "\nNOTICE: Collection database reading and wrting is still wip, checking beatmap existence, merging and creating collections will not work."
    )
    print(
        "\nNOTICE: Rate limiting handling is still scuffed and wip (only checks the filesize)."
    )
    print(
        f"\nNOTICE: Please check out the following projects they are very helpful and I use them (just google the keywords): \n        {color.UNDERLINE}Osuplus, Beatconnect desktop client, osucollector.com, osu trainer, collections manager, osu-cleaner-cli.{color.END}"
    )
    print("─" * 150)
    print("\n" + color.END)


def setup_logging():
    if not DEBUG:
        return None
    logging.basicConfig(
        filename="osudl.txt",
        filemode="a",
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )  # logging.DEBUG

    logging.info("osudl Beatmap downloader")

    return logging.getLogger("osudl")


lock = None
logger = setup_logging()

# Actual shit
def setup_webdriver(headless):
    chrome_install = Service(ChromeDriverManager().install())
    chrome_options = webdriver.ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=chrome_install, options=chrome_options)


def mirrors_check(mirror_list):
    mirror_check_progress = tqdm(
        ascii=True,
        desc=f"Checking availability of mirrors selected",
        total=len(mirror_list),
        leave=False,
    )

    if 1 in mirror_list:
        r1 = requests.head(mirrors[1][1].format(1))
        if not r1.ok:
            print("Beatconnect is offline")
            mirror_list.remove(1)
        mirror_check_progress.update(1)
    if 2 in mirror_list:
        r2 = requests.head(mirrors[2][1].format(1), verify=False)  # sayobot ssl broken
        if not r2.ok:
            print("Sayobot is offline")
            mirror_list.remove(2)
        mirror_check_progress.update(1)
    if 3 in mirror_list:
        r3 = requests.get(mirrors[3][1].format(1))
        if not r3.ok:
            print("NeriNyan is offline")
            mirror_list.remove(3)
        mirror_check_progress.update(1)
    if 4 in mirror_list:
        r4 = requests.head(mirrors[4][1].format(1))
        if not r4.ok:
            print("Chimu.moe is offline")
            mirror_list.remove(4)
        mirror_check_progress.update(1)
    mirror_check_progress.close()
    return mirror_list


def driver_get(driver, url, timeout):
    sleep(
        timeout
    )  # sleep before just in case a request was immediately made before calling this
    driver.get(url)
    return ActionChains(driver)


def get_beatmapsetid(beatmap_id):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {OAUTH_TOKEN}",
    }
    response = requests.get(f"{API_URL}/beatmaps/{beatmap_id}", headers=headers)
    beatmapset_id = response.json().get("beatmapset_id")
    if beatmapset_id is None:
        return (0, beatmap_id)
    else:
        return (int(beatmapset_id), beatmap_id)


def check_file(file, folder_name, mirror, beatmapset_id, skip):
    if not skip:
        progress_bars[mirror - 1].refresh()
        if not os.path.isfile(file):
            failed_maps.append("https://osu.ppy.sh/beatmapsets/" + str(beatmapset_id))
        else:
            if os.path.getsize(file) < 150000:
                # print(color.RED)
                # print(f"[{mirror}]You are being rate limited (download size lower than 100kb). The thread will now terminate.")
                # print(color.END)
                progress_bars[mirror - 1].set_description_str(
                    desc=f"[{mirror}] is rate limited"
                )
                failed_maps.append(
                    "https://osu.ppy.sh/beatmapsets/" + str(beatmapset_id)
                )
                os.remove(file)

            if bulk == "Y":
                if platform == "linux" or platform == "linux2":
                    os.system("wine {} >/dev/null 2>&1".format(file))
                else:
                    os.startfile(file)
            else:
                if folder_name:
                    os.makedirs(folder_name, exist_ok=True)
                    shutil.move(
                        os.path.join(download_path, file),
                        os.path.join(download_path, folder_name, file),
                    )

    mirror_queue.put(mirror)

    return True


def format_website_number(number):
    return int(number.replace(",", ""))


def get_pack(driver, actions, page_num, pack_titles, pack_progress, gamemode):
    maps = []
    for i, section in enumerate(
        driver.find_elements(
            By.XPATH, "//div[@class='beatmap-pack js-beatmap-pack js-accordion__item']"
        )
    ):
        t = pack_titles[i].text
        if gamemode == 1:
            if (
                "Taiko" in t
                or "osu!taiko" in t
                or "Catch" in t
                or "osu!catch" in t
                or "Mania" in t
                or "osu!mania" in t
            ):
                continue
        if gamemode == 2:
            if "Taiko" not in t and "osu!taiko" not in t:
                continue
        if gamemode == 3:
            if "Catch" not in t and "osu!catch" not in t:
                continue
        if gamemode == 4:
            if "Mania" not in t and "osu!mania" not in t:
                continue
        actions.move_to_element(section).click(section).perform()
        sleep(2)  # TODO: is there a better way to do this?
        for link in BeautifulSoup(
            driver.page_source, "html.parser", parse_only=SoupStrainer("a")
        ):
            if link.has_attr("href") and "beatmapsets/" in link["href"]:
                maps.append((pack_titles[i].text, link["href"]))
        pack_progress.update(1)
    return maps


def download_file(index, folder_name, url):
    # Links that are from userpage needs to get redirected because the link only contains a query to the
    # difficulty id not the beatmapset id
    if "?" in url or "#" not in url and "/beatmapsets/" not in url:
        if not use_api:
            with lock:
                url = requests.head(url, allow_redirects=True).url
                sleep(1)  # timeout if you get rate limited by official server
        else:
            beatmapset_id, beatmap_id = get_beatmapsetid(
                [int(s) for s in re.split("#|/|?", url) if s.isdigit()][-1]
            )
            if beatmapset_id == 0:
                return True
            # do we skip this one?
            if beatmapset_id is None:
                return True
            if prevent_duplicates == "Y":
                if beatmapset_id in osu_dict.values():
                    logger.debug(f"Skipping {beatmapsetid}")
                    return True

            url = beatmapset_id + "/" + beatmap_id

    # TODO: get beatmapid along with beatmapsetid, then use it later to handle the downloaded file (unzip_osz() in utilities.py)
    ids = [
        int(s) for s in re.split("#|/", url) if s.isdigit()
    ]  # index 0 is beatmapset id, index 1 is diff id
    if ids[0] in downloaded_maps:
        return check_file("", "", "", "", False)
    else:
        downloaded_maps.append(ids[0])

    mirror = mirror_queue.get()
    # lower group means more priority
    # TODO: mirror specific download
    group = 1
    if mirror < download_threads + 1:
        group = 1
    elif mirror < 2 * download_threads + 1:
        group = 2
    elif mirror < 3 * download_threads + 1:
        group = 3
    elif mirror < 4 * download_threads + 1:
        group = 4
    local_filename = str(ids[0]) + ".osz"
    url = mirrors[mirror_list[group - 1]][1].format(ids[0])
    referer_link = mirrors[mirror_list[group - 1]][2]
    info = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="96"',
        "sec-fetch-dest": "document",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
        "referer": referer_link,
    }

    # TODO: this is not the cause, YOU WILL BE RATE LIMTED NEXT TIME SO FIX IT FIRST
    # downloads not working (eithre the redirection caused it or download)
    try:
        # maybe do with lock here if theres fail, timeout TODO
        with requests.get(url, stream=True, verify=False) as r:
            r.raise_for_status()  # raise exception if erroneous status code
            progress_bars[mirror - 1].reset(
                total=int(r.headers.get("content-length", 0))
            )
            progress_bars[mirror - 1].set_description_str(
                desc="{} Downloading beatmapset {} ({}/{})".format(
                    mirrors[mirror_list[group - 1]][0], ids[0], index, num
                )
            )
            progress_bars[mirror - 1].refresh()  # flush progress bar for reuse
            # TODO: Use the filename in content-disposition and id as fallback
            # DO A HEAD REQUEST NOT A GET REQUEST
            # fname = re.findall("filename=(.+)", r.headers['content-disposition'])[0]
            # warning: old file will be wiped if it exists
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=block_size):
                    progress_bars[mirror - 1].update(len(chunk))
                    f.write(chunk)
    # except requests.exceptions.Timeout:
    #    progress_bars[mirror-1].set_description_str(desc="Timeout")
    # Maybe set up for a retry, or continue in a retry loop
    # except requests.exceptions.HTTPError as err:
    #    progress_bars[mirror-1].set_description_str(desc="Thread is dead")
    #    raise SystemExit(err)
    except Exception as e:
        progress_bars[mirror - 1].set_description_str(desc=str(e))
        pass
    # this has to be run no matter what
    check_file(local_filename, folder_name, mirror, ids[0], False)
    return True


def click_showmorebtn(actions, section, button_position, expected_buttons, map_cnt):
    tried = 0
    chunk = 50
    if map_cnt < 50:
        chunk = map_cnt
    initial_button_position = button_position
    initial_button_count = len(
        section.find_elements(
            By.XPATH, ".//button[@class='show-more-link show-more-link--profile-page']"
        )
    )
    userpage_progress = tqdm(
        ascii=True, desc=f"Retrieving beatmaps", total=map_cnt, leave=False
    )
    for i in range(0, button_position + 1):
        if not expected_buttons[i]:
            button_position -= 1
            continue
    while True:
        showmore_buttons = section.find_elements(
            By.XPATH, ".//button[@class='show-more-link show-more-link--profile-page']"
        )
        if len(showmore_buttons) < initial_button_count and tried == 35:
            userpage_progress.close()
            break
        if len(showmore_buttons) == initial_button_count:
            button = showmore_buttons[button_position]
            actions.move_to_element(button).click(button).perform()
            tried = 0
            sleep(0.2)
        else:
            tried += 1
            sleep(0.2)
    expected_buttons[initial_button_position] = 0
    return expected_buttons


# database
# stolen from https://github.com/jaasonw/osu-db-tools


def enumerate_collectiondb(custom_osu_dict, collectiondb_file):
    collections = []
    with open(collectiondb_file, "rb") as db:
        buffer.read_uint(db)
        for i in range(buffer.read_uint(db)):
            collection = {}
            collection["name"] = buffer.read_string(db)
            collection["size"] = buffer.read_uint(db)
            collection["hashes"] = []
            for i in range(collection["size"]):
                hash = buffer.read_string(db)
                if hash in custom_osu_dict:
                    collections.append(custom_osu_dict[hash])
    return collections


def enumerate_osudb(file):
    custom_osu_dict = {}
    with open(file, "rb") as db:
        version = buffer.read_uint(db)
        folder_count = buffer.read_uint(db)
        account_unlocked = buffer.read_bool(db)
        # skip this datetime shit for now (8 bytes)
        buffer.read_uint(db)
        buffer.read_uint(db)
        name = buffer.read_string(db)
        num_beatmaps = buffer.read_uint(db)

        database_progress = tqdm(
            ascii=True, desc=f"Enumerating {file}", total=num_beatmaps, leave=False
        )
        for _ in range(num_beatmaps):
            artist = buffer.read_string(db)
            artist_unicode = buffer.read_string(db)
            song_title = buffer.read_string(db)
            song_title_unicode = buffer.read_string(db)
            mapper = buffer.read_string(db)
            difficulty = buffer.read_string(db)
            audio_file = buffer.read_string(db)
            md5_hash = buffer.read_string(db)
            map_file = buffer.read_string(db)
            ranked_status = buffer.read_ubyte(db)
            num_hitcircles = buffer.read_ushort(db)
            num_sliders = buffer.read_ushort(db)
            num_spinners = buffer.read_ushort(db)
            last_modified = buffer.read_ulong(db)
            approach_rate = buffer.read_float(db)
            circle_size = buffer.read_float(db)
            hp_drain = buffer.read_float(db)
            overall_difficulty = buffer.read_float(db)
            slider_velocity = buffer.read_double(db)
            # skip these int double pairs, personally i dont think they're
            # important for the purpose of this database
            i = buffer.read_uint(db)
            for _ in range(i):
                buffer.read_int_double(db)

            i = buffer.read_uint(db)
            for _ in range(i):
                buffer.read_int_double(db)

            i = buffer.read_uint(db)
            for _ in range(i):
                buffer.read_int_double(db)

            i = buffer.read_uint(db)
            for _ in range(i):
                buffer.read_int_double(db)

            drain_time = buffer.read_uint(db)
            total_time = buffer.read_uint(db)
            preview_time = buffer.read_uint(db)
            # skip timing points
            # i = buffer.read_uint(db)
            for _ in range(buffer.read_uint(db)):
                buffer.read_timing_point(db)
            beatmap_id = buffer.read_uint(db)
            beatmapset_id = buffer.read_uint(db)
            thread_id = buffer.read_uint(db)
            grade_standard = buffer.read_ubyte(db)
            grade_taiko = buffer.read_ubyte(db)
            grade_ctb = buffer.read_ubyte(db)
            grade_mania = buffer.read_ubyte(db)
            local_offset = buffer.read_ushort(db)
            stack_leniency = buffer.read_float(db)
            gameplay_mode = buffer.read_ubyte(db)
            song_source = buffer.read_string(db)
            song_tags = buffer.read_string(db)
            online_offset = buffer.read_ushort(db)
            title_font = buffer.read_string(db)
            is_unplayed = buffer.read_bool(db)
            last_played = buffer.read_ulong(db)
            is_osz2 = buffer.read_bool(db)
            folder_name = buffer.read_string(db)
            last_checked = buffer.read_ulong(db)
            ignore_sounds = buffer.read_bool(db)
            ignore_skin = buffer.read_bool(db)
            disable_storyboard = buffer.read_bool(db)
            disable_video = buffer.read_bool(db)
            visual_override = buffer.read_bool(db)
            last_modified2 = buffer.read_uint(db)
            scroll_speed = buffer.read_ubyte(db)
            custom_osu_dict[md5_hash] = (beatmapset_id, beatmap_id)
            database_progress.update(1)
        database_progress.close()
    return custom_osu_dict

def main():
    if not DEBUG:
        print_garbage()
    print(
        color.BLUE
        + "Select the mirrors to download from:"
        + color.CYAN
        + "\n(Space separate your number choice(s), in decending order of priority for retries)\n"
    )  # TODO: add colors to show offline or online
    options = [f"Beatconnect", "Sayobot", "NeriNyan", "Chimu.moe"]
    for i, item in enumerate(options, 1):
        print(color.PURPLE + f"  {i}. " + color.CYAN + item)
    print(color.END)
    # print(color.RED + "PLEASE VISIT ALL THE MIRRORS YOU SELECT AND SOLVE THE CAPCHA(S) IF ANY FOR THE SCRIPT TO WORK\n" + color.END)
    # print(color.RED + "The check is not implemented because I can't get to the capcha page lol\n" + color.END)
    mirror_choice = input(
        "Your choice(s) >> "
    ).split()  # user input mirror numbers 1 2 3 4
    mirror_list = [
        int(x.strip()) for x in mirror_choice
    ]  # list of mirror numbers 1 2 3 4
    mirror_list = mirrors_check(mirror_list)  # TODO: use this instead of the notice
    mirror_cnt = len(mirror_list)
    failed_maps = []
    if not DEBUG:
        print("\n")
        download_threads = int(
            input(
                "How many simultaneous downloads for each mirror? (Higher thread count increases number of failed maps) >> "
            )
        )
        print("\n")
        download_change = input(
            "Change download directory? ({}) [Y/n] >> ".format(
                os.path.join(os.getcwd(), "downloads")
            )
        )
        print("\n")
        bulk = input("Import the osu maps after download? [Y/n] >> ").strip()
        print("\n")
        prevent_duplicates = input("Prevent duplicate downloads by reading existing beatmaps from osu!.db file? [Y/n] >> ")
        print("\n")
        if prevent_duplicates == "Y":
            # TODO: test the not download if exisiting works
            if not DEBUG:
                osudb_file = input("osu.db file location >>")
                print("\n")
            else:
                osudb_file = "/home/milk/osudl/database/osu!.db"
                osu_dict = enumerate_osudb(osudb_file)
    else:
        download_threads = 1
        download_path = r"/home/milk/osudl/downloads"
        bulk = "n"
        prevent_duplicates = "n"

    print(
        color.BLUE
        + "What to download? [The program will ask for a similar link later]\n"
    )
    options = [
        "User plays / Mapper Creations [https://osu.ppy.sh/users/2]",
        "Beatmap packs [https://osu.ppy.sh/beatmaps/packs]",
        "Mappool [https://osu.ppy.sh/wiki/en/Tournaments/OWC/2021]",
        "Target osu.db / collection.db file (in root folder of osu install)",
        "Aggregated osu.ppy.sh beatmap pages .txt file / Mappool spreadsheet .xls file (NOT FINISHED)",
        "osu-pps.com / osucollector.com bulk downloading (NOT FINISHED)",
    ]
    for i, item in enumerate(options, 1):
        print(color.PURPLE + f"  {i}. " + color.CYAN + item)
    print(color.END)
    choice = input("Your choice >> ")
    if not DEBUG and download_change == "n":
        download_path = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_path, exist_ok=True)
    os.chdir(download_path)

    maps = []
    total_threads = download_threads * mirror_cnt
    mirror_queue = queue.Queue(maxsize=total_threads)  # multithreading queue
    progress_bars = []

    if len(sys.argv) <= 1:
        # Fetching the beatmaps
        match int(choice):
            case 1:
                try:
                    # Parsing html is alot like writing html
                    print(
                        "\nSetting up browser emulation to retrieve all maps from osu website"
                    )
                    driver = setup_webdriver(headless=True)

                    # the data-page-id are as follows: me, recent_activity, top_ranks, medals, historical, beatmaps, kudosu
                    # title_count items, respectively
                    # section 0:recent_activity[0] (recent top 1000)
                    # section 1:top_ranks[0] and top_ranks[1] (top plays, first place ranks)
                    # section 2:historical[0] (all plays, recent submission)
                    # section 3:beatmaps[0](favourites))
                    title_count = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                    section_order = [0, 0, 0, 0]
                    # This is unecessary cuz it's only used to check for relative order of Ranks and Historical that is play-detail-list order
                    # Get section order by checking titles (user can alter this order)
                    # This works because selenium use breadth first search and these headers are same level in DOM (thanks bebby)
                    for i, section_header in enumerate(
                        driver.find_elements(
                            By.XPATH, "//h2[@class='title title--page-extra']"
                        )
                    ):
                        if section_header.text == "Recent":
                            section_order[0] = i
                        if section_header.text == "Ranks":
                            section_order[1] = i
                        if section_header.text == "Historical":
                            section_order[2] = i
                        if section_header.text == "Beatmaps":
                            section_order[3] = i

                    # https://osu.ppy.sh/beatmaps/687841?mode=mania
                    site = input("\nPlayer/Mapper link? >> ")
                    print(color.BLUE + "\nWhat gamemode for this user??\n")
                    options = ["Standard", "Taiko", "Catch", "Mania"]
                    for i, item in enumerate(options, 1):
                        print(color.PURPLE + f"  {i}. " + color.CYAN + item)
                    print(color.END)
                    gamemode = int(input("Your choice >> "))
                    clearline(10)
                    print(
                        color.PURPLE
                        + f"{gamemode_names[gamemode]} has been selected"
                        + color.END
                    )
                    site = site.rstrip("/")

                    if all(x in ["osu", "taiko", "fruits", "mania"] for x in site):
                        tmp = site.rfind("/")
                        site = site[:tmp]

                    site = site + "/{}".format(gamemode_names[gamemode])
                    if DEBUG:
                        site = "https://osu.ppy.sh/users/5139042/osu"

                    # option->title_count
                    # 1->2 2->0 3->1 4->4 5->5 6->3 7->6 8->7 9->8 10->9
                    print(color.BLUE + "\nUser Options" + color.END)
                    user_options = [
                        "All plays",
                        "Top plays",
                        "First place ranks",
                        "Favorites",
                        "Recent top 1000",
                        "Recent 24h submissions",
                    ]
                    for i, item in enumerate(user_options, 1):
                        print(color.PURPLE + f"  {i}. " + color.CYAN + item)
                    print(color.BLUE + "\nMapper Options" + color.END)
                    mapper_options = ["Ranked", "Loved", "Pending", "Graveyarded"]
                    for i, item in enumerate(mapper_options, 7):
                        print(color.PURPLE + f"  {i}. " + color.CYAN + item)
                    print(color.END)
                    choice_choice = input("Your choice(s) >> ").split()
                    choice_choice = list(map(int, choice_choice))

                    use_api = True
                    # if all(x in [1, 2, 3, 5, 6] for x in choice_choice):
                    #     if not DEBUG:
                    #         print("osu! api key for downloading unlimited beatmaps much faster (https://osu.ppy.sh/p/api)")
                    #         osu_api_key=input("key >> ").strip()
                    #         if not osu_api_key:
                    #             use_api=True
                    #             print("Proceeding without api key is possible, but you will get rate limited on osu.ppy.sh if you download too many beatmaps")
                    #     else:
                    #         osu_api_key="dd0653458de7f3ccb1128162966a8248b83b3d13"

                    # get site
                    actions = driver_get(
                        driver, site, 1
                    )  # this is blocking until site is loaded

                    # get user info
                    user_name = driver.find_element(
                        By.XPATH, "//span[@class='u-ellipsis-pre-overflow']"
                    ).text
                    user_country = driver.find_element(
                        By.XPATH, "//span[@class='profile-info__flag-text']"
                    ).text

                    print(
                        f'Fetching beatmaps from player "{user_name}" from {user_country}'
                    )
                    # The following for loop checks each choice for being selected and does pre and post checking:

                    # Prechecking
                    # find title and title__count
                    # exist:
                    # title = useless
                    # title, title__count=0 = not so useless, zero maps that satisfies condition
                    # title, title__conut>0 = useful
                    # then we find the buttons inside the second occurence of section data-page-id

                    # Postchecking
                    # Get inital button count (check for not so useless)
                    # expected_buttons is needed for checking which is which suppose there is not min or max possible buttons

                    if 1 in choice_choice or 6 in choice_choice:
                        historical_section = driver.find_element(
                            By.XPATH, "//div[@data-page-id='historical']"
                        )
                        # Prechecking
                        expected_buttons = [1, 1]
                        section_titles = historical_section.find_elements(
                            By.XPATH, ".//h3[@class='title title--page-extra-small']"
                        )
                        for title in section_titles:
                            if "Play History" in title.text:
                                continue
                            if "Most Played Beatmaps" in title.text:
                                title_count[2] = format_website_number(
                                    section_titles[1]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[2] <= 5:
                                    expected_buttons[0] = 0

                            if "Recent Plays (24h)" in title.text:
                                title_count[3] = format_website_number(
                                    section_titles[2]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[3] <= 5:
                                    expected_buttons[1] = 0

                        # Postchecking
                        if title_count[2] != 0 and 1 in choice_choice:
                            print(
                                "1: Fetching all beatmaps ever played ({} beatmaps)".format(
                                    title_count[2]
                                ),
                                end="\r",
                            )
                            expected_buttons = click_showmorebtn(
                                actions,
                                historical_section,
                                0,
                                expected_buttons,
                                title_count[2],
                            )
                            soup = BeautifulSoup(driver.page_source, "html.parser")
                            # We use BS4 to parse cuz selenium getAttribute is slow
                            # all_user_maps_played=driver.find_elements(By.XPATH, "//a[@class='beatmap-playcount__cover']")
                            for i in soup.find_all(
                                "a", {"class", "beatmap-playcount__title"}
                            ):
                                maps.append(("All plays", i["href"]))
                            print(
                                "1: Fetched all beatmaps ever played ({} beatmaps)".format(
                                    title_count[2]
                                )
                            )

                        if title_count[3] != 0 and 6 in choice_choice:
                            print(
                                f"6: Fetching beatmaps played in last 24h ({title_count[3]} beatmaps)",
                                end="\r",
                            )
                            click_showmorebtn(
                                actions,
                                historical_section,
                                1,
                                expected_buttons,
                                title_count[3],
                            )
                            play_list = historical_section.find_element(
                                By.XPATH, ".//div[@class='play-detail-list']"
                            )
                            soup = BeautifulSoup(
                                play_list.get_attribute("innerHTML"), "html.parser"
                            )
                            for i in soup.find_all(
                                "a", {"class", "play-detail__title u-ellipsis-overflow"}
                            ):
                                maps.append(("Recent Plays (24h)", i["href"]))
                            print(
                                f"6: Fetched beatmaps played in last 24h ({title_count[3]} beatmaps)"
                            )

                    if 5 in choice_choice:
                        recentactivity_section = driver.find_element(
                            By.XPATH, "//div[@data-page-id='recent_activity']"
                        )
                        # Prechecking
                        expected_buttons = [1]
                        title_count[5] = len(
                            driver.find_elements(
                                By.XPATH, "//li[@class='profile-extra-entries__item']"
                            )
                        )
                        if title_count[5] != 0:
                            click_showmorebtn(
                                actions,
                                recentactivity_section,
                                0,
                                expected_buttons,
                                title_count[5],
                            )
                            soup = BeautifulSoup(driver.page_source, "html.parser")
                            extra_entries = soup.find_all(
                                "div", {"class", "profile-extra-entries__text"}
                            )
                            for entry in extra_entries:
                                for a in entry.find_all("a", href=True):
                                    if "/b/" in a["href"]:
                                        maps.append(
                                            (
                                                "Recent top 1000 plays",
                                                "https://osu.ppy.sh{}".format(a["href"]),
                                            )
                                        )

                    if 2 in choice_choice or 3 in choice_choice:
                        if section_order[1] > section_order[2]:
                            # ranks are later
                            play_detail_list = 1
                        else:
                            play_detail_list = 0                        topranks_section = driver.find_element(
                            By.XPATH, "//div[@data-page-id='top_ranks']"
                        )
                        # Prechecking
                        expected_buttons = [1, 1]
                        section_titles = topranks_section.find_elements(
                            By.XPATH, ".//h3[@class='title title--page-extra-small']"
                        )
                        for title in section_titles:
                            if "Best Performance" in title.text:
                                title_count[0] = format_website_number(
                                    section_titles[0]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[0] <= 5:
                                    expected_buttons[0] = 0
                            if "First Place Ranks" in title.text:
                                title_count[1] = format_website_number(
                                    section_titles[1]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[1] <= 5:
                                    expected_buttons[1] = 0
                        # Postchecking
                        if title_count[0] != 0 and 2 in choice_choice:
                            print(
                                f"2: Fetching top pp plays ({title_count[0]} beatmaps)",
                                end="\r",
                            )
                            expected_buttons = click_showmorebtn(
                                actions,
                                topranks_section,
                                0,
                                expected_buttons,
                                title_count[0],
                            )
                            play_list = topranks_section.find_elements(
                                By.XPATH, ".//div[@class='play-detail-list']"
                            )[play_detail_list]
                            soup = BeautifulSoup(
                                play_list.get_attribute("innerHTML"), "html.parser"
                            )
                            for i in soup.find_all(
                                "a", {"class", "play-detail__title u-ellipsis-overflow"}
                            ):
                                maps.append(("Top plays", i["href"]))
                            play_detail_list += 1
                            print(f"2: Fetched top pp plays ({title_count[0]} beatmaps)")

                        if title_count[1] != 0 and 3 in choice_choice:
                            print(
                                f"3: Fetching global #1 scores ({title_count[1]} beatmaps)",
                                end="\r",
                            )
                            click_showmorebtn(
                                actions,
                                topranks_section,
                                1,
                                expected_buttons,
                                title_count[1],
                            )
                            play_list = topranks_section.find_elements(
                                By.XPATH, ".//div[@class='play-detail-list']"
                            )[play_detail_list]
                            soup = BeautifulSoup(
                                play_list.get_attribute("innerHTML"), "html.parser"
                            )
                            for i in soup.find_all(
                                "a", {"class", "play-detail__title u-ellipsis-overflow"}
                            ):
                                maps.append(("First place ranks", i["href"]))
                            print(
                                f"3: Fetched global #1 scores by user ({title_count[1]} beatmaps)"
                            )

                    if all(x in [4, 7, 8, 9, 10] for x in choice_choice):
                        beatmaps_section = driver.find_element(
                            By.XPATH, "//div[@data-page-id='beatmaps']"
                        )
                        # Prechecking
                        expected_buttons = [1, 1, 1, 1, 1]
                        expected_containers = [1, 1, 1, 1, 1]
                        section_titles = beatmaps_section.find_elements(
                            By.XPATH, ".//h3[@class='title title--page-extra-small']"
                        )
                        for title in section_titles:
                            if "Favourite" in title.text:
                                title_count[4] = format_website_number(
                                    section_titles[0]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[4] == 0:
                                    expected_containers[0] = 0
                                if title_count[4] <= 6:
                                    expected_buttons[0] = 0
                            if "Ranked" in title.text:
                                title_count[6] = format_website_number(
                                    section_titles[1]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[6] == 0:
                                    expected_containers[1] = 0
                                if title_count[6] <= 6:
                                    expected_buttons[1] = 0
                            if "Loved" in title.text:
                                title_count[7] = format_website_number(
                                    section_titles[2]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[7] == 0:
                                    expected_containers[2] = 0
                                if title_count[7] <= 6:
                                    expected_buttons[2] = 0
                            if "Pending" in title.text:
                                title_count[8] = format_website_number(
                                    section_titles[3]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[8] == 0:
                                    expected_containers[3] = 0
                                if title_count[8] <= 6:
                                    expected_buttons[3] = 0
                            if "Graveyarded" in title.text:
                                title_count[9] = format_website_number(
                                    section_titles[4]
                                    .find_element(
                                        By.XPATH, ".//span[@class='title__count']"
                                    )
                                    .text
                                )
                                if title_count[9] == 0:
                                    expected_containers[4] = 0
                                if title_count[9] <= 6:
                                    expected_buttons[4] = 0

                        # Postchecking
                        if title_count[4] != 0 and 4 in choice_choice:
                            print(
                                f"4: Fetching favourite maps ({title_count[4]} beatmaps)",
                                end="\r",
                            )
                            expected_buttons = click_showmorebtn(
                                actions,
                                beatmaps_section,
                                0,
                                expected_buttons,
                                title_count[4],
                            )
                            play_list = beatmaps_section.find_elements(
                                By.XPATH,
                                ".//div[@class='osu-layout__col-container osu-layout__col-container--with-gutter js-audio--group']",
                            )[0]
                            soup = BeautifulSoup(
                                play_list.get_attribute("innerHTML"), "html.parser"
                            )
                            for i in soup.find_all(
                                "a", {"class", "beatmapset-panel__cover-container"}
                            ):
                                maps.append(("Favourites", i["href"]))
                            print(f"4: Fetched favourite maps ({title_count[4]} beatmaps)")

                        if title_count[6] != 0 and 7 in choice_choice:
                            print(
                                f"7: Fetching ranked maps ({title_count[6]} beatmaps)",
                                end="\r",
                            )
                            expected_buttons = click_showmorebtn(
                                actions,
                                beatmaps_section,
                                1,
                                expected_buttons,
                                title_count[6],
                            )
                            container_pos = 1
                            for i in range(0, container_pos):
                                if not expected_containers[i]:
                                    container_pos -= 1
                            play_list = beatmaps_section.find_elements(
                                By.XPATH,
                                ".//div[@class='osu-layout__col-container osu-layout__col-container--with-gutter js-audio--group']",
                            )[container_pos]
                            soup = BeautifulSoup(
                                play_list.get_attribute("innerHTML"), "html.parser"
                            )
                            for i in soup.find_all(
                                "a", {"class", "beatmapset-panel__cover-container"}
                            ):
                                maps.append(("Ranked", i["href"]))
                            print(f"7: Fetched ranked maps ({title_count[6]} beatmaps)")

                        if title_count[7] != 0 and 8 in choice_choice:
                            print(
                                f"8: Fetching loved maps ({title_count[7]} beatmaps)",
                                end="\r",
                            )
                            expected_buttons = click_showmorebtn(
                                actions,
                                beatmaps_section,
                                2,
                                expected_buttons,
                                title_count[7],
                            )
                            container_pos = 2
                            for i in range(0, container_pos):
                                if not expected_containers[i]:
                                    container_pos -= 1
                            play_list = beatmaps_section.find_elements(
                                By.XPATH,
                                ".//div[@class='osu-layout__col-container osu-layout__col-container--with-gutter js-audio--group']",
                            )[container_pos]
                            soup = BeautifulSoup(
                                play_list.get_attribute("innerHTML"), "html.parser"
                            )
                            for i in soup.find_all(
                                "a", {"class", "beatmapset-panel__cover-container"}
                            ):
                                maps.append(("Loved", i["href"]))
                            print(f"8: Fetched loved maps ({title_count[7]} beatmaps)")

                        if title_count[8] != 0 and 9 in choice_choice:
                            print(
                                f"9: Fetching pending maps ({title_count[8]} beatmaps)",
                                end="\r",
                            )
                            expected_buttons = click_showmorebtn(
                                actions,
                                beatmaps_section,
                                3,
                                expected_buttons,
                                title_count[8],
                            )
                            container_pos = 3
                            for i in range(0, container_pos):
                                if not expected_containers[i]:
                                    container_pos -= 1
                            play_list = beatmaps_section.find_elements(
                                By.XPATH,
                                ".//div[@class='osu-layout__col-container osu-layout__col-container--with-gutter js-audio--group']",
                            )[container_pos]
                            soup = BeautifulSoup(
                                play_list.get_attribute("innerHTML"), "html.parser"
                            )
                            for i in soup.find_all(
                                "a", {"class", "beatmapset-panel__cover-container"}
                            ):
                                maps.append(("Pending", i["href"]))
                            print(f"9: Fetched pending maps ({title_count[8]} beatmaps)")

                        if title_count[9] != 0 and 10 in choice_choice:
                            print(
                                f"10: Fetching graveyarded maps ({title_count[9]} beatmaps)",
                                end="\r",
                            )
                            click_showmorebtn(
                                actions,
                                beatmaps_section,
                                4,
                                expected_buttons,
                                title_count[9],
                            )
                            play_list = beatmaps_section.find_elements(
                                By.XPATH,
                                ".//div[@class='osu-layout__col-container osu-layout__col-container--with-gutter js-audio--group']",
                            )[-1]
                            soup = BeautifulSoup(
                                play_list.get_attribute("innerHTML"), "html.parser"
                            )
                            for i in soup.find_all(
                                "a", {"class", "beatmapset-panel__cover-container"}
                            ):
                                maps.append(("Graveyarded", i["href"]))
                            print(f"10: Fetched graveyarded ({title_count[9]} beatmaps)")

                    # There is missing checks here cuz it be done earlier
                    # is there nothing to do? (Check for all useless)
                    if title_count[2] == 0 and 1 in choice_choice:
                        print("1: No maps detected")
                    if title_count[0] == 0 and 2 in choice_choice:
                        print("2: No top plays")
                    if title_count[1] == 0 and 3 in choice_choice:
                        print("3: No #1 scores")
                    if title_count[4] == 0 and 4 in choice_choice:
                        print("4: No favourite maps")
                    if title_count[5] == 0 and 5 in choice_choice:
                        print("5: No recent top 1000 scores")
                    if title_count[3] == 0 and 6 in choice_choice:
                        print("6: No recent plays")
                    if title_count[6] == 0 and 7 in choice_choice:
                        print("7: No ranked beatmaps")
                    if title_count[7] == 0 and 8 in choice_choice:
                        print("8: No loved beatmaps")
                    if title_count[8] == 0 and 9 in choice_choice:
                        print("9: No pending maps")
                    if title_count[9] == 0 and 10 in choice_choice:
                        print("10: No graveyarded maps")
                except NoSuchElementException:
                    print("Site did not load properly. Try running this script again.")

            # packs
            case 2:
                print(color.BLUE + "Select beatmap pack type\n")
                options = ["Standard", "Spotlights", "Theme", "Artist"]
                for i, item in enumerate(options, 1):
                    print(color.PURPLE + f"  {i}. " + color.CYAN + item)
                print(color.END)
                pack_type = int(input("Your choice >> "))
                gamemode = 0
                if pack_type == 1 or pack_type == 2:
                    print(color.BLUE + "Select gamemode for beatmap pack\n")
                    options = ["Standard", "Taiko", "Catch", "Mania"]
                    for i, item in enumerate(options, 1):
                        print(color.PURPLE + f"  {i}. " + color.CYAN + item)
                    print(color.END)
                    gamemode = int(input("Your choice >> "))

                sites = [
                    "https://osu.ppy.sh/beatmaps/packs?type=standard&page={}",
                    "https://osu.ppy.sh/beatmaps/packs?type=chart&page={}",
                    "https://osu.ppy.sh/beatmaps/packs?type=theme&page={}",
                    "https://osu.ppy.sh/beatmaps/packs?type=artist&page={}",
                ]

                driver = setup_webdriver(headless=True)
                site = sites[pack_type - 1]
                response = requests.get(site.format(1)).content
                soup = BeautifulSoup(response, "html.parser")
                page_cnt = int(
                    soup.find_all("a", {"class": "pagination-v2__link"})[-2].text
                )

                for page_num in range(1, page_cnt + 1):
                    print(f"Scanning page {page_num}/{page_cnt}", end="\r")
                    # get pack titles
                    actions = driver_get(driver, site.format(page_num), 1)
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    pack_titles = soup.find_all("div", {"class", "beatmap-pack__name"})
                    pack_progress = tqdm(
                        ascii=True,
                        desc=f"Retrieving beatmaps",
                        total=len(pack_titles),
                        leave=False,
                    )
                    maps += get_pack(
                        driver, actions, page_num, pack_titles, pack_progress, gamemode
                    )
                    pack_progress.close()

            # https://osu.ppy.sh/beatmapsets/1450344#mania/2981853
            case 3:
                if not DEBUG:
                    site = input("Tourney website url? >> ")
                else:
                    site = "https://osu.ppy.sh/wiki/en/Tournaments/SOFT/5"
                response = requests.get(site).content
                soup = BeautifulSoup(response, "html.parser")
                # if bulk=="n":
                # TODO scrape and folders
                # section_titles=[x.text for x in soup.find_all("h3", {"class", "osu-md__header osu-md__header--3"})]
                # sort_maps=input(f"You selected no imports, so do you want maps to be sorted into folders? [Y/n] >> ").strip()
                name = soup.find("h1", {"class": "osu-md__header osu-md__header--1"}).text
                for link in BeautifulSoup(
                    response, "html.parser", parse_only=SoupStrainer("a")
                ):
                    if link.has_attr("href") and "beatmapsets/" in link["href"]:
                        maps.append((name, link["href"]))
                print(color.BLUE)
                print(color.BLUE + name + color.YELLOW)

            case 4:
                print(color.BLUE + "Which database file to get beatmaps from?\n")
                options = ["osu.db", "collection.db"]
                for i, item in enumerate(options, 1):
                    print(color.PURPLE + f"  {i}. " + color.CYAN + item)
                print(color.END)
                choice = int(input("Your choice >> "))

                folder_name = "osu.db"
                if not DEBUG:
                    if choice == 2:
                        print(
                            color.PURPLE
                            + "collections.db requires a osu.db with all collection maps indexed inside! Until I figure out how to avoid this.\n"
                        )
                    print(color.BLUE + "Which database file to get beatmaps from?\n")
                    osudb_file = input("Target osu.db file location >> ")
                else:
                    osudb_file = "/home/milk/osudl/database/osu!.db"
                custom_osu_dict = enumerate_osudb(osudb_file)
                if choice == 1:
                    maps = list(custom_osu_dict.values())
                elif choice == 2:
                    folder_name = "collection.db"
                    if not DEBUG:
                        collectiondb_file = input("collection.db file location >> ")
                    else:
                        collectiondb_file = "/home/milk/osudl/database/collection.db"
                    maps = enumerate_collectiondb(custom_osu_dict, collectiondb_file)

                for i, beatmapset_id in enumerate(maps):
                    maps[i] = (
                        folder_name,
                        "https://osu.ppy.sh/beatmapsets/"
                        + str(maps[i][0])
                        + "/"
                        + str(maps[i][1]),
                    )  # TODO: !! in download_file check the validity of beatmapsetid with api
            case 5:
                print(color.BLUE + "Which database file to get beatmaps from?\n")
                options = [".txt file"]
                for i, item in enumerate(options, 1):
                    print(color.PURPLE + f"  {i}. " + color.CYAN + item)
                print(color.END)
                choice = int(input("Your choice >> "))
                if choice == 1:
                    text_file = input("Target .txt file location >> ")
                with open(text_file, "r", encoding="UTF-8") as file:
                    data = file.read().rstrip()
                    for url in re.findall(
                        "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                        data,
                    ):
                        maps.append("txt", url)
                # text, xls
            # case 6:
            # websites
        else:
            maps=sys.argv[2]
            OAUTH_TOKEN=sys.argv[1]

    # get rid of duplicates
    maps = list(set(maps))

    # log downladed maps beatmapset_id
    downloaded_maps = []

    num = len(maps)
    if num == 0:
        print("There is nothing to download. Bye.")
        sys.exit()
    if mirror_cnt > 1:
        text = f"{num} unique maps will be downloaded from {mirror_cnt} mirrors with {download_threads*mirror_cnt} simultaneous downloads"
    else:
        text = f"{num} unique maps will be downloaded from 1 mirror"
    if prevent_duplicates == "Y":
        print(text + ", subject to skips if file is existent in songs folder")
    else:
        print(text)
    print(color.END)

    # Downloading the beatmaps
    block_size = 1024  # 1 Kibibyte
    start = time.time()
    for i in range(1, 1 + total_threads):
        # if (i+2)%download_threads==0:
        #     print("[{}] ".format(mirrors[mirror_list[int(i/download_threads)-1]][0])) #TODO: check the order of mirrors
        # else:
        progress_bars.append(
            tqdm(
                unit="iB",
                unit_scale=True,
                ascii=True,
                leave=True,
                desc="Starting download",
            )
        )  # position=1
        mirror_queue.put(i)
    # for i in maps:
    #    print(i)
    # only_diff=input("Save only the specified difficulty instead of the whole beatmapset? [Y/n] >> ").strip()
    lock = multiprocessing.Manager().Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=total_threads) as executor:
        res = [
            executor.submit(download_file, i, data[0], data[1])
            for i, data in enumerate(maps, 1)
        ]
        executor.shutdown(wait=True)
    # maybe we dont need this idk how tqdm works lol
    for bar in progress_bars:
        bar.close()
    now = time.time()
    duration_mins = int((now - start) / 60)
    duration_secs = int((now - start) - int(now - start))
    print(
        color.GREEN
        + "\nDownloaded {} beatmaps in {} minutes and {} seconds".format(
            num - len(failed_maps), duration_mins, duration_secs
        )
    )

    with open("failed.txt", "w") as f:
        for url in failed_maps:
            f.write(url)
            f.write("\n")
    print(
        color.RED
        + "\n{} beatmaps failed to download. Failed beatmap urls are written to {}\n".format(
            len(failed_maps), os.path.join(download_path, "failed.txt")
        )
    )
    print(
        "Retry the failed beatmaps by running osudl option 5 with failed.txt as input\n"
    )
    print(
        "If there are still failures even after retries, it is likely that the beatmap requested does not exist (I didn't write something to check beatmapset validity yet)"
    )


if __name__ == "__main__":
    main()

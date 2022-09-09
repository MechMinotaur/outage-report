import re
from datetime import datetime, timedelta
from time import sleep
from git import Repo


def line_is_outage(line: str) -> bool:
    match = re.search(r"time=(\d+)[.]*(\d*)[ ]*ms", line)

    if match is not None:
        s = match[0].replace("time=", "").replace("ms", "").strip()
        ms = float(s)
        if ms < 100:
            return False

    return True


def git_push() -> None:
    repo = Repo(".git")
    repo.git.add("outages.txt")
    repo.index.commit(datetime.now().isoformat())
    origin = repo.remote(name='origin')
    while True:
        try:
            origin.push()
            print(f"{datetime.now()}: successfully pushed")
            return
        except Exception as e:
            retry_seconds = 60
            print(f"{datetime.now()}: failed to push, retrying in {retry_seconds} seconds", e)
            sleep(retry_seconds)


def log_outage(last_good_time: str, new_good_time: str, threshold: int) -> bool:
    s_fmt = "%m/%d/%Y %I:%M:%S %p"
    new_dt = datetime.strptime(new_good_time, s_fmt)
    last_dt = datetime.strptime(last_good_time, s_fmt)

    elapsed = new_dt - last_dt
    if elapsed > timedelta(seconds=threshold):
        with open("outages.txt", "r+") as fw:
            content = fw.read()
            fw.seek(0, 0)
            _from = last_dt.strftime(s_fmt)
            to = new_dt.strftime(s_fmt)
            fw.write(f"{_from} - {to} : out for {str(elapsed)} \n" + content)
        return True
    return False


def get_line_to_begin(filepath: str) -> int:
    try:
        with open(filepath, "r") as pf:
            return int(pf.read())
    except Exception as e:
        print(e)
        return 2  # first two lines are always nonsense


if __name__ == '__main__':
    while True:
        ping_log_file = "ping.log"
        previously_read_line_file = "previously.readline.txt"

        outage_threshold_seconds = 11  # seconds before considering an outage

        line_to_begin = get_line_to_begin(previously_read_line_file)
        post_to_git_every_seconds = 3600  # hourly

        outages_logged = 0

        with open(ping_log_file, "r", encoding="utf-16-le") as fr:
            last_good_time = None  # last time we had connection
            outage = False

            # read all lines in ping_log_file started where we stopped last
            lines = fr.readlines()[line_to_begin:]
            for i, line in enumerate(lines):
                if line_is_outage(line):
                    outage = True
                    continue

                split = line.split(" ")
                new_good_time = f"{split[0]} {split[1]} {split[2]}"

                if last_good_time is not None and outage:
                    logged = log_outage(
                        last_good_time,
                        new_good_time,
                        outage_threshold_seconds)
                    if logged:
                        outages_logged += 1
                    outage = False

                last_good_time = new_good_time

            line_to_begin = line_to_begin + i

        print(f"{datetime.now()}: logged {outages_logged} outages to outages.txt")

        with open("previously.readline.txt", "w") as pf:
            pf.write(str(line_to_begin))

        if outages_logged > 0:
            git_push()
            sleep(post_to_git_every_seconds)

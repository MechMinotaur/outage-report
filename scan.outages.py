import re
from datetime import datetime, timedelta
from time import sleep
from git import Repo


def line_is_outage(line: str) -> bool:
    return re.search(r"time=(\d+)ms", line) is None


def git_push() -> None:
    while True:
        try:
            repo = Repo(".git")
            repo.git.add("outages.txt")
            repo.index.commit(datetime.now().isoformat())
            origin = repo.remote(name='origin')
            origin.push()
            return
        except Exception as e:
            print(e)
            sleep(60)


def log_outage(last_good_time: str, new_good_time: str, threshold: int) -> None:
    new_dt = datetime.strptime(new_good_time, "%m/%d/%Y %I:%M:%S %p")
    last_dt = datetime.strptime(last_good_time, "%m/%d/%Y %I:%M:%S %p")

    elapsed = new_dt - last_dt
    if elapsed > timedelta(seconds=threshold):
        with open("outages.txt", "r+") as fw:
            content = fw.read()
            fw.seek(0, 0)
            _from = last_dt.strftime("%m/%d/%Y %I:%M:%S %p")
            to = new_dt.strftime("%m/%d/%Y %I:%M:%S %p")
            fw.write(f"{_from} - {to} : out for {str(elapsed)} \n" + content)


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

        with open(ping_log_file, "r", encoding="utf-16-le") as fr:
            last_good_time = None  # last time we had connection
            outage = False

            # read all lines in ping_log_file started where we stopped last
            lines = fr.readlines()[line_to_begin:]
            for i, line in enumerate(lines):
                if not line_is_outage(line):
                    split = line.split(" ")
                    new_good_time = f"{split[0]} {split[1]} {split[2]}"

                    if last_good_time is not None and outage:
                        log_outage(
                            last_good_time,
                            new_good_time,
                            outage_threshold_seconds)
                        outage = False

                    last_good_time = new_good_time
                else:
                    outage = True

            line_to_begin = line_to_begin + i

        with open("previously.readline.txt", "w") as pf:
            pf.write(str(line_to_begin))

        git_push()
        sleep(post_to_git_every_seconds)

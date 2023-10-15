import argparse
import os
import sys
import time
from hashlib import md5
from random import uniform

from bs4 import BeautifulSoup
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
from rich.style import Style
from rich.table import Table
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager


def custom_sleep(degree=1):
    time_ = 0.1
    if degree == 1:
        time_ = round(uniform(2.01, 5.01), 2)
    elif degree == 2:
        time_ = round(uniform(60, 180), 2)
    elif degree == 3:
        time_ = round(uniform(0.66, 1.66), 2)
    time.sleep(time_)


class Browser:
    def __init__(self, stud_id, url):
        self.stud_id = stud_id
        self.url = url
        global console
        self.logged_in = False

        self.browser = webdriver.Firefox(service=Service(GeckoDriverManager().install(), log_path=os.devnull))
        self.options = Options()

        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        self.browser.fullscreen_window()
        self.browser.get("http://" + self.url)
        time.sleep(1)
        self.actions = ActionChains(self.browser)
        self.log_in()
        with console.status("Logging in..."):
            while not self.logged_in:
                for c in range(int(uniform(300, 400))):
                    time.sleep(1)
                    if not self.logged_in:
                        if self.hexdump_is_visible():
                            self.logged_in = True
                    else:
                        break
                if not self.logged_in:
                    self.browser.refresh()
                    custom_sleep()
                    self.log_in()

        self.textarea = self.browser.find_element(By.XPATH, '//*[@id="exampleFormControlTextarea1"]')  # 1

    def log_in(self):
        field_login = self.browser.find_element(By.XPATH, '//*[@id="login"]')
        self.browser.execute_script("arguments[0].click();", field_login)
        field_login.send_keys(self.stud_id)
        custom_sleep(3)
        btn_log_in = self.browser.find_element(By.XPATH, '/html/body/div[2]/div/div/div[3]/button')
        btn_log_in.click()

    def insert_answer(self, answer):
        field_answer = self.browser.find_element(By.XPATH, '//*[@id="answer"]')
        field_answer.clear()
        custom_sleep(3)
        field_answer.send_keys(answer)
        time.sleep(1)
        btn_check = self.browser.find_element(By.XPATH, '/html/body/div[1]/div/div[2]/div[6]/div/div/button')
        btn_check.click()

    def hexdump_is_visible(self):
        soup_ = BeautifulSoup(self.browser.page_source, 'lxml')
        hexdump_holder = soup_.find('pre', {'id': 'hexdump', 'class': 'hex'})
        if hexdump_holder:
            if not (hexdump_holder['style'] in 'display: none;') and not (hexdump_holder['style'] in 'display:none;'):
                return True

    def get_page(self, sector_id_, leave_offset_untouched=False, one_line=False):
        arrows = self.browser.find_element(By.XPATH, '//*[@id="sector"]')
        custom_sleep(3)
        arrows.clear()
        arrows.send_keys(f'{sector_id_}')
        custom_sleep(3)
        arrows.send_keys(Keys.ENTER)
        custom_sleep(3)
        while not self.hexdump_is_visible():
            custom_sleep(3)
        soup_ = BeautifulSoup(self.browser.page_source, 'lxml')
        hexdump_holder = soup_.find('pre', {'id': 'hexdump', 'class': 'hex'})
        rows = [i.text for i in list(hexdump_holder)[1:] if not (i.text in ('<br>', ''))]
        if leave_offset_untouched:
            rows = [(row.split('|')[0]).lower().split() for row in rows]
            return rows
        else:
            rows = [(row.split('|')[0]).lower().split()[1:] for row in rows]
            if one_line:
                return [item for sublist in rows for item in sublist]
            else:
                return rows

    def take_from(self, _start_page, _from_offset, lim):
        res = []
        start_row = None
        page = self.get_page(_start_page, True)
        rob = _from_offset % 16  # remaining offset bytes
        eoc = _from_offset - rob  # entire offset ( /16 = 0 )
        got_start_row = False

        # Finding out start row id
        for id_r in enumerate(page):
            if not got_start_row:
                _num, _r = id_r
                if (hex(eoc))[2:] in _r[0]:
                    start_row = _num
                    got_start_row = True
            else:
                break

        if got_start_row:
            style_comp = Style.parse('blue3')
            style_fin = Style.parse('green1')
            style_bg = Style.parse('black')
            with Progress(TextColumn("[progress.description]{task.description}"),
                          BarColumn(bar_width=30,
                                    complete_style=style_comp,
                                    finished_style=style_fin,
                                    style=style_bg),
                          MofNCompleteColumn()) as progress:
                retrieve = progress.add_task(
                    f"[turquoise2]     "
                    f"getting bytes from [italic dark_slate_gray1]{hex(_from_offset)} [/italic dark_slate_gray1]",
                    total=lim)
                page = [r[1:] for r in page]  # offset removed
                # 1) taking bytes from row
                for b in (page[start_row])[rob:]:
                    if len(res) != lim:
                        res.append(b)
                        progress.update(retrieve, advance=1)
                        time.sleep(0.02)
                    else:
                        break

                # 2) from page
                if len(res) != lim:
                    if len(res) != lim:
                        for r in page[start_row + 1:]:
                            if len(res) != lim:
                                for b in r:
                                    if len(res) != lim:
                                        res.append(b)
                                        progress.update(retrieve, advance=1)
                                        time.sleep(0.0005)  # graphics
                                    else:
                                        break
                            else:
                                break
                    if len(res) != lim:
                        # 3) from other pages
                        while True:
                            if len(res) == lim:
                                break
                            _start_page += 1
                            page = self.get_page(_start_page)
                            for r in page:
                                if len(res) < lim:
                                    for b in r:
                                        if len(res) < lim:
                                            res.append(b)
                                            progress.update(retrieve, advance=1)
                                            time.sleep(0.0005)  # graphics
                                        else:
                                            break
                                else:
                                    break
                return res
        else:
            console.print('[red]: getting start row')

    def extract_filename(self):
        soup_ = BeautifulSoup(self.browser.page_source, 'lxml')
        filename_holder = soup_.find('span', {'id': 'filename'})
        if filename_holder is not None:
            if len(filename_holder) > 0:
                return filename_holder.text
            else:
                console.print('[red] Browser failed to extract filename')
        else:
            console.print('[red] Browser failed to extract filename')

    def print(self, data):
        self.textarea.send_keys(f'\n{data}')

    def finish(self):
        self.browser.quit()


class Image:
    def __init__(self):
        global console
        self.file = []
        self.current_parsed = False
        self.file_trace = list()

        self.file_system = None  # FileSystem

        self.bps = None  # BytesPerSector
        self.spc = None  # SectorsPerCluster
        self.cs = None  # ClusterSize

        # FAT ONLY
        self.rs = None  # Reserved Sectors
        self.fc = None  # Fat Count
        self.spf = None  # Sectors Per Fat
        self.rec = None  # Root Entries Count
        self.bpre = 32  # Bytes Per RootNote
        self.rdo = None  # Root Dir Offset
        self.dao = None  # Data Area Offset
        self.depth = 0
        self.depth_max = 0
        self.cluster_chain = []
        self.offset_size_links = []
        self.next_cluster_offset = None

        # tmp
        self.next_offset = None

        self.file_size = None
        self.fs_entire = None
        self.fs_remaining = None

    @staticmethod
    def o2p(offset_):
        res = (offset_ // 512)
        return res

    def import_path(self, raw_filename):
        raw_filename = raw_filename.split('/')
        if len(raw_filename) >= 1:
            if self.file_system in ('fat12', 'fat16'):
                for i in enumerate(raw_filename):
                    self.file_trace.append([i[0], i[1]])
                self.depth_max = len(raw_filename) - 1
        else:
            console.print('[red] Browser failed to extract filename')

    def what_fs(self, zeroth_page_bytes):
        pol = ''
        for row in zeroth_page_bytes:
            for h in row:
                pol += h
        if '4641543132' in pol:
            self.file_system = 'fat12'
        elif '4641543136' in pol:
            self.file_system = 'fat16'

    def boot_parser(self, boot_page, browser_):
        console.print('1. BIOS parameter block (BPB) data:', style="bold bright_green")
        self.what_fs(boot_page)
        table_bpb = Table(title="BPB")
        table_bpb.add_column('Option', style="")
        table_bpb.add_column('Value', style="")
        table_bpb.add_column('(hex)', style="")
        if self.file_system in ('fat12', 'fat16'):
            self.bps = int('0x' + boot_page[0][12] + boot_page[0][11], 16)
            self.spc = int('0x' + boot_page[0][13], 16)
            self.rs = int('0x' + boot_page[0][15] + boot_page[0][14], 16)
            self.fc = int('0x' + boot_page[1][0], 16)
            self.rec = int('0x' + boot_page[1][2] + boot_page[1][1], 16)
            self.spf = int('0x' + boot_page[1][7] + boot_page[1][6], 16)
            self.cs = self.bps * self.spc
            self.rdo = (self.rs + self.fc * self.spf) * self.bps
            self.dao = self.rdo + self.rec * self.bpre
            self.next_offset = self.rdo
            data = [['File system', self.file_system, None],
                    ['Bytes per sector', str(self.bps), hex(self.bps)],
                    ['Sectors per cluster', str(self.spc), hex(self.spc)],
                    ['Reserved sectors', str(self.rs), hex(self.rs)],
                    ['Fat count', str(self.fc), hex(self.fc)],
                    ['Sectors per fat', str(self.spf), hex(self.spf)],
                    ['Root entries count', str(self.rec), hex(self.rec)],
                    ['Bytes per root entry', str(self.bpre), hex(self.bpre)],
                    ['Root dir offset', str(self.rdo), hex(self.rdo)],
                    ['Data area offset', str(self.dao), hex(self.dao)],
                    ['Cluster size', str(self.cs), hex(self.cs)]]
            for i in data:
                browser_.print(f'{i[0]}: {i[1]} {i[2]}')
            with Live(table_bpb, refresh_per_second=10):
                for i in data:
                    table_bpb.add_row(*i)
                    time.sleep(0.1)  # graphics

        else:
            console.print('[red]failed to recognize file system')

    def fat_finder(self, browser_):
        def offset_finder(num_, filename_):
            page_num = self.o2p(self.next_offset)
            browser_.print(f'   {filename_} -> page {page_num}')
            console.print(f'   {filename_} -> page {page_num}', style="deep_sky_blue1")
            while not self.current_parsed:
                page = browser_.get_page(page_num)
                for row in page[::2]:
                    if not self.current_parsed:
                        mention_ascii = ''
                        for h in row[:8]:
                            b = bytes.fromhex(h)
                            a = ''
                            try:
                                a = b.decode('ASCII')
                            except UnicodeDecodeError:
                                pass
                            finally:
                                if a in '.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
                                    mention_ascii += a
                        if filename_.upper() == mention_ascii:
                            self.current_parsed = True
                            mention_data = page[page.index(row) + 1]
                            cluster_num = int(f'0x{mention_data[11]}{mention_data[10]}', 16)
                            if num_ == self.depth_max:
                                size = int(f'0x{"".join(list(reversed(mention_data))[:4])}', 16)
                                self.file_size = size
                                self.cluster_chain.append(cluster_num)
                                browser_.print(f'   1st_clus = {cluster_num}')
                                console.print(f'   Adding cluster {cluster_num} to chain', style="deep_sky_blue1")
                            self.next_offset = self.dao + (cluster_num - 2) * self.cs
                            self.file_trace[num_].append(self.next_offset)
                            self.current_parsed = True
                    else:
                        break
                page_num += 1

        def chain_follower():
            if self.file_system == 'fat16':
                self.next_cluster_offset = self.bps * self.rs + 2 * self.cluster_chain[-1]
                browser_.print(f'going to offset: {hex(self.next_cluster_offset)}')
            elif self.file_system == 'fat12':
                self.next_cluster_offset = self.bps * self.rs + ((self.cluster_chain[-1]) // 2) * 3
                browser_.print(f'going to offset: {hex(self.next_cluster_offset)}')
            c = self.o2p(self.next_cluster_offset)
            bytes_list = browser_.take_from(_start_page=c, _from_offset=self.next_cluster_offset, lim=3)
            if self.file_system == 'fat16':
                self.cluster_chain.append(int(f'0x{bytes_list[1]}{bytes_list[0]}', 16))
                browser_.print(f'points to {hex(self.cluster_chain[-1])}')
            elif self.file_system == 'fat12':
                tmp = f'{bytes_list[2]}{bytes_list[1][0]} {bytes_list[1][1]}{bytes_list[0]}'.split()
                if self.cluster_chain[-1] % 2 == 0:
                    converted = int(f'0x{tmp[-1]}', 16)
                    browser_.print(f'points to {hex(converted)}')
                    self.cluster_chain.append(converted)
                else:
                    converted = int(f'0x{tmp[0]}', 16)
                    browser_.print(f'points to {hex(converted)}')
                    self.cluster_chain.append(converted)

        console.print('\n2. Tracing path:', style="bold bright_green")
        browser_.print('\n 2. Tracing path:')
        for note in self.file_trace:
            num, filename = note[0], note[1]
            self.current_parsed = False
            offset_finder(num, filename)
        if self.file_size and self.next_offset:
            self.fs_entire = self.file_size // self.cs
            self.fs_remaining = self.file_size % self.cs
            console.print(f'\n3. Restoring cluster chain:', style="bold bright_green")
            console.print(f'   Doing job for {self.fs_entire} times\'cause already got 1:', style="deep_sky_blue1")
            browser_.print(f'\n3. Restoring cluster chain:')
            browser_.print(f'   Doing job for {self.fs_entire} times\'cause already got 1:')
            # Целые кластеры. Не добавляем 1 т.к. уже имеем 1
            for i in range(self.fs_entire):
                chain_follower()
            console.print(f'   chain: {self.cluster_chain}', style="deep_sky_blue1")
            browser_.print(f'   chain: {self.cluster_chain}')

            if len(self.cluster_chain) == self.fs_entire + 1:
                console.print(f'\n4. Collecting file clusters:', style="bold bright_green")
                for i in enumerate(self.cluster_chain):
                    n, k = i
                    offset = self.dao + (k - 2) * self.cs
                    browser_.print(f'   {n}) cluster {k}, offset {hex(offset)}')
                    if (n + 1) == len(self.cluster_chain):
                        to_extend = browser_.take_from(self.o2p(offset), offset, self.fs_remaining)
                        self.file.extend(to_extend)
                    else:
                        to_extend = browser_.take_from(self.o2p(offset), offset, self.cs)
                        self.file.extend(to_extend)
                console.print(f'')
            else:
                console.print('[red]cluster chain\'s length doesn\'t match clusters count')
        else:
            console.print('[red] error: file searching')
        # offset =  deo + (k-2)*cs

    def md5(self, browser_):
        with console.status("Going to compute md5", spinner='arc') as status:
            time.sleep(1)
            status.update("Joining bytes...", spinner='betaWave')
            bytes_one_line_1 = ''.join(self.file)
            bytes_one_line_1 = bytes_one_line_1.lower()
            with open('bytes.txt', 'w') as file:
                file.write(bytes_one_line_1)
            self.file = bytes.fromhex(bytes_one_line_1)
            time.sleep(1)
            status.update("Computing md5", spinner="bouncingBar")
            time.sleep(1)
            answer = md5(self.file).hexdigest()
            status.update("Done!", spinner="star")
            console.print(f'md5: {answer}', style="green1")
            browser_.insert_answer(answer)
            duration = round((time.time() - start_time), 0)
            console.print(f'time: {int(duration // 60)} min {int(duration % 60)} s', style="purple")


start_time = time.time()
console = Console()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='Actual server\'s url', required=True)
    parser.add_argument('-i', '--id', help='Your id', required=True)
    args = vars(parser.parse_args())
    user_url = args['url']
    user_id = args['id']

    browser = Browser(user_id, user_url)

    os.system('cls' if os.name == 'nt' else 'clear')
    image = Image()

    boot_sector = browser.get_page(0)
    image.boot_parser(boot_sector, browser)
    raw_filename = browser.extract_filename()
    image.import_path(raw_filename)

    if image.file_system in ('fat12', 'fat16'):
        image.fat_finder(browser)
        image.md5(browser)
        inp = '+'
        while not (inp in ('Y', 'y', 'yes',)):
            inp = input('Close Firefox (y/N): ')
        browser.finish()
    elif image.file_system == 'ntfs':
        main()
    browser.finish()


if __name__ == "__main__":
    main()

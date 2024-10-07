#! /usr/bin/env python3

import psutil
import time
import argparse
from typing import Optional
import os

IGNORE_USER_CPU_THRESH = 0.0
HISTORY_MAXLEN = 100

COL_RESET  = '\u001b[0m'
COL_RED    = '\u001b[31m'
COL_YELLOW = '\u001b[33m'
COL_GREEN  = '\u001b[32m'
COL_BLUE   = '\u001b[34m'

def main(only_show_user:Optional[str], iter_sleep:float):

    if only_show_user != None:
        cpu_history = []

    while True:

        # quickly remember all processes

        user_procs = {}

        for proc in psutil.process_iter():

            try:
                user = proc.username()
                name = proc.name()
                cpu_usage = proc.cpu_percent()
                mem = proc.memory_info()
            except psutil.NoSuchProcess:
                continue
            
            if only_show_user != None:
                if user != only_show_user:
                    continue

            mem_non_swap_bytes = mem.rss
            mem_all_bytes = mem.vms

            if user not in user_procs:
                user_procs[user] = []

            user_procs[user].append((name, cpu_usage, mem_non_swap_bytes))

        # calc user usage

        user_usages = []

        for user, procs in user_procs.items():
            
            cpu = 0
            mem = 0
            for _p_name, p_cpu, p_mem in procs:
                cpu += p_cpu
                mem += p_mem

            user_usages.append((user, cpu, mem))

        # save history

        for user, cpu, _mem in user_usages:
            if user == only_show_user:
                cpu_history.insert(0, cpu)
                while len(cpu_history) > HISTORY_MAXLEN:
                    del cpu_history[-1]

        # draw separator

        print()
        print()

        terminal_size = os.get_terminal_size()

        # draw history

        if only_show_user:

            free_space_y = terminal_size.lines - 2
            history = cpu_history[:free_space_y]

            highest = max(history)
            if highest == 0:
                highest = 1

            value_prev = 0
            for value in reversed(history):

                # if value >= highest * 2/3:
                #     col = COL_RED
                # elif value >= highest * 1/3:
                #     col = COL_YELLOW
                # else:
                #     col = COL_GREEN

                highness = value / highest

                col = '\u001b[38;2;'
                col += str(int(220 * highness)) + ';'
                col += str(int(220 * (1.0 - highness))) + ';'
                col += f'30'
                col += 'm'

                free_space_x = terminal_size.columns - 6 - 3 - 2
                length = (value / highest) * free_space_x
                length = int(length)
                print(f'{value:6.2f}[%]', end='')

                print(col, end='')

                print('|', end='')

                print('#' * length, end='')

                if value > value_prev:
                    print('\\', end='')
                elif value < value_prev:
                    print('/', end='')
                else:
                    print('|', end='')

                print(COL_RESET)

                value_prev = value

        # print usage

        longest_username = 0

        for user, cpu, _ in user_usages:

            length = len(user)
            if length > longest_username:
                longest_username = length

        user_usages.sort(key=lambda i: i[1])

        for idx, (user, cpu, mem) in enumerate(user_usages):

            if cpu <= IGNORE_USER_CPU_THRESH:
                continue

            fill_char = '~' if idx % 2 == 0 else '-'

            user += ' '
            user = user.ljust(longest_username + 1, fill_char)

            cpu = f'{cpu:.2f}'
            cpu = ' ' + cpu
            cpu = cpu.rjust(7, fill_char)

            print(f'{user}{cpu}[%] {mem/1024/1024/1024:5.2f}[GB]')

        # sleep

        time.sleep(iter_sleep)

if __name__ == '__main__':
    parser = argparse.ArgumentParser('shows usage based on user')
    parser.add_argument('--iter-sleep', type=float, default=5.0)
    parser.add_argument('--user',       type=str,   default=None)
    args = parser.parse_args()

    main(args.user, args.iter_sleep)

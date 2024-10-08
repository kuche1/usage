#! /usr/bin/env python3

import psutil
import time
import argparse
from typing import Optional
import os
import drawille

IGNORE_USER_CPU_THRESH = 0.0
HISTORY_MAXLEN = 200
DETERMINE_COLOR_BASED_ON_HIGHEST_AVG = True # otherwise: based on highest

BRILE_WIDTH_MUL = 2 # brile characters are 0.5 the width of a normal character
BRILE_HEIGHT_MUL = 4 # brile characters are 0.25 the height of a normal character

COL_RESET  = '\u001b[0m'
COL_RED    = '\u001b[31m'
COL_YELLOW = '\u001b[33m'
COL_GREEN  = '\u001b[32m'
COL_BLUE   = '\u001b[34m'

def main(only_show_user:Optional[str], iter_sleep:float):

    cpu_history = []

    while True:

        # quickly remember all processes
        user_procs = get_processes(only_show_user)

        # calc user usage
        user_usages = calc_user_usages(user_procs)

        # save history
        save_history(only_show_user, cpu_history, user_usages)

        # prepare buffered output
        output = ''

        # draw separator
        output += '\n'

        # draw history
        output += draw_history(only_show_user, cpu_history)

        # print usage
        output += print_usage(only_show_user, user_usages)

        # show buffered output
        print(output, end='')

        # sleep
        time.sleep(iter_sleep)

def get_processes(only_show_user):
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

    return user_procs

def calc_user_usages(user_procs):
    user_usages = []

    for user, procs in user_procs.items():

        cpu = 0
        mem = 0
        for _p_name, p_cpu, p_mem in procs:
            cpu += p_cpu
            mem += p_mem

        user_usages.append((user, cpu, mem))

    return user_usages

def save_history(only_show_user, cpu_history, user_usages):
    if only_show_user:
        for user, cpu, _mem in user_usages:
            if user == only_show_user:
                cpu_history.insert(0, cpu)
                while len(cpu_history) > HISTORY_MAXLEN:
                    del cpu_history[-1]
                break

def draw_history(only_show_user, cpu_history):
    output = ''

    if only_show_user:

        terminal_size = os.get_terminal_size()

        free_space_y = terminal_size.lines - 1
        free_space_y *= BRILE_HEIGHT_MUL
        history = cpu_history[:free_space_y]

        highest_value = max(history)
        if highest_value == 0:
            highest_value = 0.1

        # ...

        cur_line_values = []
        all_line_values = []

        for idx, graph_elem_value in enumerate(history):

            cur_line_values.insert(0, graph_elem_value)

            if idx % BRILE_HEIGHT_MUL == BRILE_HEIGHT_MUL - 1:
                all_line_values.insert(0, cur_line_values)
                cur_line_values = []

        if len(cur_line_values):
            while len(cur_line_values) < BRILE_HEIGHT_MUL:
                cur_line_values.insert(0, 0)
            all_line_values.insert(0, cur_line_values)

        # ...

        highest_avg_value = 0.1

        for line_values in all_line_values:
            avg = sum(line_values) / len(line_values)
            if avg > highest_avg_value:
                highest_avg_value = avg

        # ...

        for line_values in all_line_values:

            avg_value = sum(line_values) / len(line_values)
            output += f'{avg_value:6.2f}[%]'

            canvas = drawille.Canvas()

            for y, value in enumerate(line_values):

                free_space_x = terminal_size.columns - 6 - 3
                free_space_x *= BRILE_WIDTH_MUL
                free_space_x *= (value / highest_value)
                free_space_x = int(free_space_x)

                for x in range(free_space_x):
                    canvas.set(x, y)

            if DETERMINE_COLOR_BASED_ON_HIGHEST_AVG:
                redness = avg_value / highest_avg_value
            else:
                redness = avg_value / highest_value
            col = '\u001b[38;2;'
            col += str(int(220 * redness)) + ';'
            col += str(int(220 * (1.0 - redness))) + ';'
            col += f'30'
            col += 'm'

            output += col
            output += canvas.frame()
            output += COL_RESET

            output += '\n'

    return output

def print_usage(only_show_user, user_usages):
    output = ''

    longest_username = 0

    for user, cpu, _ in user_usages:

        length = len(user)
        if length > longest_username:
            longest_username = length

    user_usages.sort(key=lambda i: i[1])

    user_usages_output = ''

    for idx, (user, cpu, mem) in enumerate(user_usages):

        if cpu <= IGNORE_USER_CPU_THRESH:
            continue

        fill_char = '~' if idx % 2 == 0 else '-'

        user += ' '
        user = user.ljust(longest_username + 1, fill_char)

        cpu = f'{cpu:.2f}'
        cpu = ' ' + cpu
        cpu = cpu.rjust(7, fill_char)

        user_usages_output += f'{user}{cpu}[%] {mem/1024/1024/1024:5.2f}[GB]'
        user_usages_output += '\n'

    if only_show_user:
        if user_usages_output.endswith('\n'):
            user_usages_output = user_usages_output[:-1]
    else:
        user_usages_output += '\n'

    output += user_usages_output

    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser('shows usage based on user')
    parser.add_argument('--iter-sleep', type=float, default=5.0)
    parser.add_argument('--user',       type=str,   default=None)
    args = parser.parse_args()

    main(args.user, args.iter_sleep)

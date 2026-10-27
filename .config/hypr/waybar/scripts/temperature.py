"""CPU temperature from discovered Linux sensors, or root filesystem usage."""
import html
import json
from pathlib import Path
import re
import shutil


def read(path):
    try:
        return path.read_text().strip()
    except (OSError, UnicodeError):
        return ''


def temperature(sysfs=Path('/sys')):
    candidates = []
    for chip in (sysfs / 'class/hwmon').glob('hwmon*'):
        name = read(chip / 'name').lower()
        # Kernel CPU drivers, not a processor model or a fixed hwmon index.
        cpu_driver = name in ('coretemp', 'k10temp', 'zenpower', 'cpu_thermal', 'cpu-thermal')
        if any(part in name for part in ('gpu', 'nvme', 'drivetemp', 'wifi', 'iwlwifi')):
            continue
        for sensor in chip.glob('temp*_input'):
            label = read(sensor.with_name(sensor.name.replace('_input', '_label')))
            cpu_label = re.search(r'^(package id \d+|physical id \d+|core \d+|tctl|tdie|cpu(?:\s|$)|cputin)', label, re.I)
            if cpu_driver or cpu_label:
                candidates.append((read(sensor), name + (' / ' + label if label else '')))
    for zone in (sysfs / 'class/thermal').glob('thermal_zone*'):
        name = read(zone / 'type')
        if re.search(r'(^|[_-])(cpu|cpuss|x86_pkg_temp)([_-]|$)', name, re.I):
            candidates.append((read(zone / 'temp'), name))
    valid = []
    for value, name in candidates:
        try:
            value = int(value) / 1000
        except ValueError:
            continue
        if 0 < value <= 130:
            valid.append((value, name))
    return max(valid, default=None)


def status(sysfs=Path('/sys'), disk_usage=shutil.disk_usage):
    measured = temperature(sysfs)
    if measured is not None:
        value, source = measured
        return {'text': f'\uf2c9 {value:.0f}°C', 'tooltip': f'CPU: {value:.1f}°C\n{html.escape(source)}',
                'class': 'temperature', 'percentage': round(value)}
    try:
        total, used, free = disk_usage('/')
        percent = round(100 * used / total)
        return {'text': f'\uf0a0 {percent}%', 'tooltip': f'Root /: {percent}% used\n{used / 2**30:.1f} / {total / 2**30:.1f} GiB\nCPU temperature unavailable',
                'class': 'storage', 'percentage': percent}
    except (OSError, ZeroDivisionError):
        return {'text': '—', 'tooltip': 'CPU temperature and root storage unavailable', 'class': 'unavailable'}


if __name__ == '__main__':
    print(json.dumps(status(), ensure_ascii=False))
